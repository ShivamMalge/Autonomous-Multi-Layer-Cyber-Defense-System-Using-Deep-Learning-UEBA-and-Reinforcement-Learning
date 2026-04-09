import os
import time
import joblib
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_curve, auc

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Set random seeds for reproducibility
np.random.seed(42)
torch.manual_seed(42)

# ==========================================
# 1. EVALUATION ENGINE
# ==========================================
class EvaluationEngine:
    @staticmethod
    def evaluate_model(y_true, y_pred, y_scores, model_name, plot_dir):
        """Calculates metrics and generates Visualizations."""
        os.makedirs(plot_dir, exist_ok=True)
        
        # Calculate Metrics
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        logging.info(f"--- {model_name} Performance ---")
        logging.info(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1-Score: {f1:.4f}")
        
        # Plot Confusion Matrix
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
                    xticklabels=['Normal (0)', 'Attack (1)'],
                    yticklabels=['Normal (0)', 'Attack (1)'])
        plt.title(f'Confusion Matrix: {model_name}')
        plt.ylabel('Actual Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        plt.savefig(os.path.join(plot_dir, f'{model_name}_confusion_matrix.png'))
        plt.close()

        # Plot ROC Curve if scores are available
        if y_scores is not None:
            fpr, tpr, _ = roc_curve(y_true, y_scores)
            roc_auc = auc(fpr, tpr)
            
            plt.figure(figsize=(6, 5))
            plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
            plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.title(f'ROC Curve: {model_name}')
            plt.legend(loc="lower right")
            plt.tight_layout()
            plt.savefig(os.path.join(plot_dir, f'{model_name}_roc_curve.png'))
            plt.close()
            
        return {'precision': precision, 'recall': recall, 'f1': f1}

# ==========================================
# 2. BASELINE MODEL: ISOLATION FOREST
# ==========================================
class BaselineIsolationForest:
    def __init__(self, contamination=0.05):
        # Isolation Forest isolates anomalies. Contamination sets the expected prior.
        self.model = IsolationForest(
            n_estimators=100, 
            max_samples='auto', 
            contamination=contamination, 
            random_state=42,
            n_jobs=-1
        )
        
    def fit(self, X_train):
        logging.info("Training Isolation Forest on purely benign traffic...")
        start_time = time.time()
        self.model.fit(X_train)
        logging.info(f"Isolation Forest trained in {time.time() - start_time:.2f} seconds.")
        
    def predict(self, X_test):
        logging.info("Running Isolation Forest Inference...")
        # IF returns 1 for normal, -1 for anomaly. We map to 0 (normal), 1 (anomaly)
        preds = self.model.predict(X_test)
        binary_preds = np.where(preds == 1, 0, 1)
        
        # Get continuous anomaly scores (lower means more anomalous, so we invert)
        scores = -self.model.score_samples(X_test)
        return binary_preds, scores

# ==========================================
# 3. DEEP LEARNING MODEL: AUTOENCODER
# ==========================================
class DeepAutoencoder(nn.Module):
    def __init__(self, input_dim):
        super(DeepAutoencoder, self).__init__()
        # Encoder: compress dimensionality
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, int(input_dim * 0.75)),
            nn.ReLU(),
            nn.Linear(int(input_dim * 0.75), int(input_dim * 0.5)),
            nn.ReLU(),
            nn.Linear(int(input_dim * 0.5), int(input_dim * 0.25)), # Bottleneck
            nn.ReLU()
        )
        # Decoder: reconstruct original dimensionality
        self.decoder = nn.Sequential(
            nn.Linear(int(input_dim * 0.25), int(input_dim * 0.5)),
            nn.ReLU(),
            nn.Linear(int(input_dim * 0.5), int(input_dim * 0.75)),
            nn.ReLU(),
            nn.Linear(int(input_dim * 0.75), input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

class AutoencoderDetector:
    def __init__(self, input_dim, learning_rate=1e-3, epochs=10, batch_size=256):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DeepAutoencoder(input_dim).to(self.device)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.epochs = epochs
        self.batch_size = batch_size
        self.threshold = 0
        logging.info(f"Initialized Autoencoder on {self.device}")

    def fit(self, X_train):
        logging.info("Training Autoencoder on benign traffic...")
        dataset = TensorDataset(torch.FloatTensor(X_train))
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        self.model.train()
        for epoch in range(self.epochs):
            epoch_loss = 0
            for batch in dataloader:
                x_batch = batch[0].to(self.device)
                
                self.optimizer.zero_grad()
                reconstruction = self.model(x_batch)
                loss = self.criterion(reconstruction, x_batch)
                
                loss.backward()
                self.optimizer.step()
                epoch_loss += loss.item()
                
            if (epoch+1) % 2 == 0 or epoch == 0:
                logging.info(f"Epoch {epoch+1}/{self.epochs} | Loss: {epoch_loss/len(dataloader):.6f}")

        # Determine reconstruction error threshold based on the Train (Benign) set
        logging.info("Calculating Percentile-based Anomaly Threshold...")
        self.model.eval()
        with torch.no_grad():
            x_train_tensor = torch.FloatTensor(X_train).to(self.device)
            reconstructed = self.model(x_train_tensor)
            mse_errors = torch.mean((x_train_tensor - reconstructed) ** 2, dim=1).cpu().numpy()
            
            # Using 95th percentile of benign reconstruction errors as our threshold
            self.threshold = np.percentile(mse_errors, 95)
        logging.info(f"Threshold set to reconstruction MSE: {self.threshold:.6f}")

    def predict(self, X_test):
        logging.info("Running Autoencoder Inference...")
        self.model.eval()
        with torch.no_grad():
            x_tensor = torch.FloatTensor(X_test).to(self.device)
            reconstructed = self.model(x_tensor)
            mse_errors = torch.mean((x_tensor - reconstructed) ** 2, dim=1).cpu().numpy()
        
        # Classification: if error > threshold => 1 (Attack), else 0 (Normal)
        binary_preds = (mse_errors > self.threshold).astype(int)
        return binary_preds, mse_errors
        
    def plot_reconstruction_errors(self, mse_errors, y_true, plot_dir):
        """Visualizes the reconstruction error distributions for Benign vs Attack."""
        plt.figure(figsize=(8, 5))
        sns.histplot(mse_errors[y_true == 0], bins=50, color='green', alpha=0.6, label='Benign', stat='density', log_scale=(True, False))
        sns.histplot(mse_errors[y_true == 1], bins=50, color='red', alpha=0.6, label='Attack', stat='density', log_scale=(True, False))
        plt.axvline(self.threshold, color='black', linestyle='dashed', linewidth=2, label=f'Threshold ({self.threshold:.4f})')
        plt.title('Reconstruction Error Distribution (Log Scale)')
        plt.xlabel('Mean Squared Error')
        plt.ylabel('Density')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(plot_dir, 'AE_reconstruction_distribution.png'))
        plt.close()

# ==========================================
# 4. MAIN PIPELINE EXECUTION
# ==========================================
def main():
    PROCESSED_DATA_DIR = r"c:\Users\manoj\OneDrive\Desktop\AIML\data\processed"
    MODELS_DIR = r"c:\Users\manoj\OneDrive\Desktop\AIML\models"
    PLOTS_DIR = r"c:\Users\manoj\OneDrive\Desktop\AIML\reports\figures"
    
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    # 1. Load Data
    logging.info("Loading train and test datasets from Parquet...")
    train_df = pd.read_parquet(os.path.join(PROCESSED_DATA_DIR, "train_dataset.parquet"))
    test_df = pd.read_parquet(os.path.join(PROCESSED_DATA_DIR, "test_dataset.parquet"))

    # Separate Features and Labels
    # We ignore 'Label_Multi' for this binary classification phase
    X_train_full = train_df.drop(columns=['Label_Binary', 'Label_Multi']).values
    y_train_full = train_df['Label_Binary'].values

    X_test = test_df.drop(columns=['Label_Binary', 'Label_Multi']).values
    y_test = test_df['Label_Binary'].values

    # Unsupervised Anomaly Detection relies on training ONLY on normal data
    logging.info("Filtering Training set for Benign variables only...")
    X_train_benign = X_train_full[y_train_full == 0]

    # 2. Isolation Forest (Baseline)
    if_model = BaselineIsolationForest(contamination=0.05)
    if_model.fit(X_train_benign)
    if_preds, if_scores = if_model.predict(X_test)
    
    if_metrics = EvaluationEngine.evaluate_model(y_test, if_preds, if_scores, "IsolationForest", PLOTS_DIR)

    # 3. Deep Autoencoder
    input_dim = X_train_benign.shape[1]
    ae_model = AutoencoderDetector(input_dim=input_dim, epochs=15, batch_size=256)
    ae_model.fit(X_train_benign)
    ae_preds, ae_scores = ae_model.predict(X_test)
    
    ae_metrics = EvaluationEngine.evaluate_model(y_test, ae_preds, ae_scores, "Autoencoder", PLOTS_DIR)
    ae_model.plot_reconstruction_errors(ae_scores, y_test, PLOTS_DIR)

    # 4. Save Models
    logging.info("Saving trained models...")
    joblib.dump(if_model.model, os.path.join(MODELS_DIR, "isolation_forest.pkl"))
    torch.save(ae_model.model.state_dict(), os.path.join(MODELS_DIR, "autoencoder.pt"))

    # 5. Model Comparison Logging
    logging.info("\n=== MODEL COMPARISON SUMMARY ===")
    df_compare = pd.DataFrame([if_metrics, ae_metrics], index=['Isolation Forest', 'Autoencoder'])
    logging.info(f"\n{df_compare.to_string()}")
    
    logging.info("Phase 1.2 Pipeline Execution Complete!")

if __name__ == "__main__":
    main()
