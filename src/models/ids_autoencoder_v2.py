"""
Phase 1.3 — Improved Autoencoder IDS
=====================================
Root Cause Analysis of v1 failure:
  - RobustScaler does NOT clip outliers. Network traffic data has extreme
    values (e.g., packet counts of 10M+) that dominate MSE loss.
  - The model wastes all capacity fitting these outliers, destroying
    sensitivity to actual anomaly patterns.
  - Threshold of 789 MSE means virtually nothing gets flagged.

Key Improvements in v2:
  1. Pre-training data conditioning: clip outliers + log1p transform
  2. BatchNorm + LeakyReLU architecture for stable gradient flow
  3. Feature-wise reconstruction error (not raw MSE)
  4. Validation-driven threshold search using F1 optimization
  5. Learning rate scheduling + early stopping
  6. Proper weight initialization (Xavier)
"""

import os
import time
import joblib
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import (
    confusion_matrix, precision_score, recall_score, 
    f1_score, roc_curve, auc, precision_recall_curve
)

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
np.random.seed(42)
torch.manual_seed(42)


# ============================================================
# 1. DATA CONDITIONER — Fixes the scaling problem at its root
# ============================================================
class DataConditioner:
    """
    Applies outlier clipping + log1p transform to tame extreme values
    before feeding into the Autoencoder. This is saved alongside the 
    model so the same transform can be applied during inference.
    """
    def __init__(self, clip_percentile=99.5):
        self.clip_percentile = clip_percentile
        self.clip_mins = None
        self.clip_maxs = None
        self.fitted = False

    def fit(self, X: np.ndarray):
        """Learn clipping bounds from benign training data."""
        self.clip_mins = np.percentile(X, 100 - self.clip_percentile, axis=0)
        self.clip_maxs = np.percentile(X, self.clip_percentile, axis=0)
        self.fitted = True
        logging.info(f"DataConditioner fitted: clipping at [{100-self.clip_percentile}, {self.clip_percentile}] percentiles")
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Clip outliers and apply log1p to reduce skew."""
        assert self.fitted, "DataConditioner must be fitted before transform."
        X_clipped = np.clip(X, self.clip_mins, self.clip_maxs)
        # log1p handles negative values gracefully: sign(x) * log1p(|x|)
        X_transformed = np.sign(X_clipped) * np.log1p(np.abs(X_clipped))
        return X_transformed.astype(np.float32)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)


# ============================================================
# 2. IMPROVED AUTOENCODER ARCHITECTURE
# ============================================================
class ImprovedAutoencoder(nn.Module):
    """
    Symmetric autoencoder with BatchNorm and LeakyReLU.
    BatchNorm stabilizes training when input distributions vary.
    LeakyReLU prevents dead neurons (common failure mode with ReLU).
    """
    def __init__(self, input_dim):
        super().__init__()

        # Calculate layer sizes proportionally
        l1 = input_dim
        l2 = max(int(input_dim * 0.8), 8)
        l3 = max(int(input_dim * 0.5), 4)
        bottleneck = max(int(input_dim * 0.25), 2)

        self.encoder = nn.Sequential(
            nn.Linear(l1, l2),
            nn.BatchNorm1d(l2),
            nn.LeakyReLU(0.1),
            nn.Linear(l2, l3),
            nn.BatchNorm1d(l3),
            nn.LeakyReLU(0.1),
            nn.Linear(l3, bottleneck),
            nn.BatchNorm1d(bottleneck),
            nn.LeakyReLU(0.1),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck, l3),
            nn.BatchNorm1d(l3),
            nn.LeakyReLU(0.1),
            nn.Linear(l3, l2),
            nn.BatchNorm1d(l2),
            nn.LeakyReLU(0.1),
            nn.Linear(l2, l1),
        )
        # Xavier initialization for stable gradients
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        return self.decoder(self.encoder(x))


# ============================================================
# 3. TRAINING ENGINE WITH EARLY STOPPING & LR SCHEDULING
# ============================================================
class AutoencoderTrainer:
    def __init__(self, input_dim, lr=1e-3, epochs=50, batch_size=512, patience=7):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = ImprovedAutoencoder(input_dim).to(self.device)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr, weight_decay=1e-5)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=3
        )
        self.epochs = epochs
        self.batch_size = batch_size
        self.patience = patience
        self.threshold = 0.0
        self.conditioner = DataConditioner(clip_percentile=99.5)

        logging.info(f"Improved Autoencoder initialized on {self.device}")
        total_params = sum(p.numel() for p in self.model.parameters())
        logging.info(f"Total Parameters: {total_params:,}")

    def fit(self, X_train_benign: np.ndarray, X_val: np.ndarray = None, y_val: np.ndarray = None):
        """
        Train on benign data only. Optionally use a validation set 
        containing both classes for threshold optimization.
        """
        # Condition the data BEFORE training
        X_conditioned = self.conditioner.fit_transform(X_train_benign)
        logging.info(f"Conditioned data range: [{X_conditioned.min():.4f}, {X_conditioned.max():.4f}]")

        dataset = TensorDataset(torch.FloatTensor(X_conditioned))
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True, drop_last=True)

        # Early stopping state
        best_loss = float('inf')
        patience_counter = 0
        best_state = None

        self.model.train()
        for epoch in range(self.epochs):
            epoch_loss = 0.0
            for batch in dataloader:
                x_batch = batch[0].to(self.device)
                self.optimizer.zero_grad()
                recon = self.model(x_batch)
                loss = self.criterion(recon, x_batch)
                loss.backward()
                # Gradient clipping for stability
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()
                epoch_loss += loss.item()

            avg_loss = epoch_loss / len(dataloader)
            self.scheduler.step(avg_loss)

            # Early stopping check
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
                best_state = {k: v.clone() for k, v in self.model.state_dict().items()}
            else:
                patience_counter += 1

            if (epoch + 1) % 3 == 0 or epoch == 0:
                lr_current = self.optimizer.param_groups[0]['lr']
                logging.info(
                    f"Epoch {epoch+1:3d}/{self.epochs} | "
                    f"Loss: {avg_loss:.6f} | LR: {lr_current:.2e} | "
                    f"Patience: {patience_counter}/{self.patience}"
                )

            if patience_counter >= self.patience:
                logging.info(f"Early stopping triggered at epoch {epoch+1}")
                break

        # Restore best weights
        if best_state is not None:
            self.model.load_state_dict(best_state)
            logging.info(f"Restored best model weights (loss: {best_loss:.6f})")

        # Threshold Selection
        if X_val is not None and y_val is not None:
            self._optimize_threshold_f1(X_val, y_val)
        else:
            self._set_percentile_threshold(X_conditioned)

    def _set_percentile_threshold(self, X_conditioned: np.ndarray, percentile: float = 95.0):
        """Fallback: percentile-based threshold on benign training errors."""
        errors = self._compute_errors(X_conditioned)
        self.threshold = np.percentile(errors, percentile)
        logging.info(f"Percentile threshold ({percentile}%): {self.threshold:.6f}")

    def _optimize_threshold_f1(self, X_val: np.ndarray, y_val: np.ndarray):
        """
        Uses a validation set (with both classes) to sweep thresholds 
        and find the one maximizing F1-score. This is the CRITICAL fix.
        """
        logging.info("Optimizing threshold using F1-score on validation data...")
        X_val_cond = self.conditioner.transform(X_val)
        errors = self._compute_errors(X_val_cond)

        # Sweep across candidate thresholds
        percentiles = np.arange(50, 99.5, 0.5)
        benign_errors = errors[y_val == 0]
        
        best_f1 = 0.0
        best_threshold = 0.0
        best_percentile = 0.0

        for p in percentiles:
            candidate = np.percentile(benign_errors, p)
            preds = (errors > candidate).astype(int)
            f1 = f1_score(y_val, preds, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = candidate
                best_percentile = p

        self.threshold = best_threshold
        logging.info(
            f"Optimal threshold: {self.threshold:.6f} "
            f"(benign percentile: {best_percentile}%) -> F1: {best_f1:.4f}"
        )

    def _compute_errors(self, X_conditioned: np.ndarray) -> np.ndarray:
        """Compute per-sample reconstruction error."""
        self.model.eval()
        with torch.no_grad():
            x_tensor = torch.FloatTensor(X_conditioned).to(self.device)
            recon = self.model(x_tensor)
            # Feature-wise MSE, then mean across features
            errors = torch.mean((x_tensor - recon) ** 2, dim=1).cpu().numpy()
        return errors

    def predict(self, X: np.ndarray):
        """Run inference on raw (unconditioned) data."""
        X_cond = self.conditioner.transform(X)
        errors = self._compute_errors(X_cond)
        preds = (errors > self.threshold).astype(int)
        return preds, errors


# ============================================================
# 4. EVALUATION ENGINE
# ============================================================
class EvaluationEngine:
    @staticmethod
    def full_report(y_true, y_pred, y_scores, model_name, plot_dir):
        os.makedirs(plot_dir, exist_ok=True)

        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()

        logging.info(f"\n{'='*50}")
        logging.info(f"  {model_name} — PERFORMANCE REPORT")
        logging.info(f"{'='*50}")
        logging.info(f"  Precision : {precision:.4f}")
        logging.info(f"  Recall    : {recall:.4f}")
        logging.info(f"  F1-Score  : {f1:.4f}")
        logging.info(f"  TP={tp:,} | FP={fp:,} | FN={fn:,} | TN={tn:,}")
        logging.info(f"{'='*50}\n")

        # Confusion Matrix
        plt.figure(figsize=(7, 5))
        sns.heatmap(cm, annot=True, fmt=',d', cmap='Blues', cbar=False,
                    xticklabels=['Normal', 'Attack'],
                    yticklabels=['Normal', 'Attack'])
        plt.title(f'{model_name} — Confusion Matrix', fontsize=14, fontweight='bold')
        plt.ylabel('Actual')
        plt.xlabel('Predicted')
        plt.tight_layout()
        plt.savefig(os.path.join(plot_dir, f'{model_name}_confusion_matrix.png'), dpi=150)
        plt.close()

        # ROC Curve
        if y_scores is not None:
            fpr, tpr, _ = roc_curve(y_true, y_scores)
            roc_auc = auc(fpr, tpr)
            plt.figure(figsize=(7, 5))
            plt.plot(fpr, tpr, color='#e74c3c', lw=2, label=f'AUC = {roc_auc:.3f}')
            plt.plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--')
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.title(f'{model_name} — ROC Curve', fontsize=14, fontweight='bold')
            plt.legend(loc='lower right')
            plt.tight_layout()
            plt.savefig(os.path.join(plot_dir, f'{model_name}_roc_curve.png'), dpi=150)
            plt.close()

        return {'precision': precision, 'recall': recall, 'f1': f1}

    @staticmethod
    def plot_error_distribution(errors, y_true, threshold, plot_dir, model_name):
        plt.figure(figsize=(10, 6))
        
        benign_errors = errors[y_true == 0]
        attack_errors = errors[y_true == 1]

        sns.histplot(benign_errors, bins=100, color='#2ecc71', alpha=0.6, 
                     label=f'Benign (n={len(benign_errors):,})', stat='density')
        sns.histplot(attack_errors, bins=100, color='#e74c3c', alpha=0.6,
                     label=f'Attack (n={len(attack_errors):,})', stat='density')
        plt.axvline(threshold, color='black', linestyle='--', linewidth=2,
                    label=f'Threshold = {threshold:.4f}')
        plt.title(f'{model_name} — Reconstruction Error Distribution', fontsize=14, fontweight='bold')
        plt.xlabel('Reconstruction Error (MSE)')
        plt.ylabel('Density')
        plt.legend(fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(plot_dir, f'{model_name}_error_distribution.png'), dpi=150)
        plt.close()

        # Also log summary statistics
        logging.info(f"Error Statistics:")
        logging.info(f"  Benign  -> Mean: {benign_errors.mean():.4f}, Median: {np.median(benign_errors):.4f}, Std: {benign_errors.std():.4f}")
        logging.info(f"  Attack  -> Mean: {attack_errors.mean():.4f}, Median: {np.median(attack_errors):.4f}, Std: {attack_errors.std():.4f}")


# ============================================================
# 5. MAIN EXECUTION PIPELINE
# ============================================================
def main():
    PROCESSED_DIR = r"c:\Users\manoj\OneDrive\Desktop\AIML\data\processed"
    MODELS_DIR    = r"c:\Users\manoj\OneDrive\Desktop\AIML\models"
    PLOTS_DIR     = r"c:\Users\manoj\OneDrive\Desktop\AIML\reports\figures"

    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    # ---- Load Data ----
    logging.info("Loading datasets...")
    train_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "train_dataset.parquet"))
    test_df  = pd.read_parquet(os.path.join(PROCESSED_DIR, "test_dataset.parquet"))

    feature_cols = [c for c in train_df.columns if c not in ('Label_Binary', 'Label_Multi')]

    X_train_full = train_df[feature_cols].values
    y_train_full = train_df['Label_Binary'].values

    X_test = test_df[feature_cols].values
    y_test = test_df['Label_Binary'].values

    # ---- Split benign training data & create validation set ----
    benign_mask = y_train_full == 0
    X_train_benign = X_train_full[benign_mask]

    # Use a portion of the FULL training set (benign + attack) as validation
    # for threshold optimization. This is critical for finding the right threshold.
    from sklearn.model_selection import StratifiedShuffleSplit
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.15, random_state=42)
    _, val_idx = next(splitter.split(X_train_full, y_train_full))
    X_val = X_train_full[val_idx]
    y_val = y_train_full[val_idx]

    logging.info(f"Training samples (benign only): {X_train_benign.shape[0]:,}")
    logging.info(f"Validation samples (mixed):     {X_val.shape[0]:,}")
    logging.info(f"Test samples:                   {X_test.shape[0]:,}")

    # ---- Train Improved Autoencoder ----
    input_dim = X_train_benign.shape[1]
    trainer = AutoencoderTrainer(
        input_dim=input_dim,
        lr=5e-4,
        epochs=50,
        batch_size=512,
        patience=7
    )
    trainer.fit(X_train_benign, X_val=X_val, y_val=y_val)

    # ---- Evaluate on Test Set ----
    ae_preds, ae_errors = trainer.predict(X_test)
    ae_metrics = EvaluationEngine.full_report(y_test, ae_preds, ae_errors, "AE_v2_Improved", PLOTS_DIR)
    EvaluationEngine.plot_error_distribution(ae_errors, y_test, trainer.threshold, PLOTS_DIR, "AE_v2_Improved")

    # ---- Save Model & Artifacts ----
    torch.save(trainer.model.state_dict(), os.path.join(MODELS_DIR, "autoencoder_v2.pt"))
    joblib.dump(trainer.conditioner, os.path.join(MODELS_DIR, "data_conditioner.pkl"))
    joblib.dump({'threshold': trainer.threshold, 'input_dim': input_dim}, 
                os.path.join(MODELS_DIR, "ae_v2_config.pkl"))
    logging.info("All models and artifacts saved.")

    # ---- Comparison with v1 baseline ----
    v1_metrics = {'precision': 0.0912, 'recall': 0.0249, 'f1': 0.0391}
    comparison = pd.DataFrame(
        [v1_metrics, ae_metrics],
        index=['AE v1 (Original)', 'AE v2 (Improved)']
    )
    logging.info(f"\n{'='*55}")
    logging.info(f"  BEFORE vs AFTER COMPARISON")
    logging.info(f"{'='*55}")
    logging.info(f"\n{comparison.to_string()}")
    logging.info(f"{'='*55}")

    logging.info("Phase 1.3 Complete!")


if __name__ == "__main__":
    main()
