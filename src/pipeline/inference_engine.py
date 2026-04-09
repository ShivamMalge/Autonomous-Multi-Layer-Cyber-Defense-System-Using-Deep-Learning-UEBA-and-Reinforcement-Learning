"""
Inference Engine — Loads the trained Autoencoder v2 and runs real-time anomaly detection.
Designed for low-latency, single-sample or batch inference.
"""

import os
import logging
import joblib
import numpy as np
import time

import torch
import torch.nn as nn

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


# ---- DataConditioner (must match Phase 1.3 definition for pickle compatibility) ----
class DataConditioner:
    """Clip outliers + log1p transform. Matches the class saved in data_conditioner.pkl."""
    def __init__(self, clip_percentile=99.5):
        self.clip_percentile = clip_percentile
        self.clip_mins = None
        self.clip_maxs = None
        self.fitted = False

    def fit(self, X):
        self.clip_mins = np.percentile(X, 100 - self.clip_percentile, axis=0)
        self.clip_maxs = np.percentile(X, self.clip_percentile, axis=0)
        self.fitted = True
        return self

    def transform(self, X):
        X_clipped = np.clip(X, self.clip_mins, self.clip_maxs)
        X_transformed = np.sign(X_clipped) * np.log1p(np.abs(X_clipped))
        return X_transformed.astype(np.float32)

    def fit_transform(self, X):
        return self.fit(X).transform(X)


# Patch __main__ so joblib can deserialize the conditioner saved from __main__
import __main__
if not hasattr(__main__, 'DataConditioner'):
    __main__.DataConditioner = DataConditioner


# ---- Reproduce the exact same architecture from Phase 1.3 ----
class ImprovedAutoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        l1 = input_dim
        l2 = max(int(input_dim * 0.8), 8)
        l3 = max(int(input_dim * 0.5), 4)
        bottleneck = max(int(input_dim * 0.25), 2)

        self.encoder = nn.Sequential(
            nn.Linear(l1, l2), nn.BatchNorm1d(l2), nn.LeakyReLU(0.1),
            nn.Linear(l2, l3), nn.BatchNorm1d(l3), nn.LeakyReLU(0.1),
            nn.Linear(l3, bottleneck), nn.BatchNorm1d(bottleneck), nn.LeakyReLU(0.1),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck, l3), nn.BatchNorm1d(l3), nn.LeakyReLU(0.1),
            nn.Linear(l3, l2), nn.BatchNorm1d(l2), nn.LeakyReLU(0.1),
            nn.Linear(l2, l1),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


class InferenceEngine:
    """
    Production inference engine. Loads the v2 Autoencoder weights,
    the DataConditioner, and the optimized threshold, then exposes
    a fast `detect()` method for streaming use.
    """
    def __init__(self, model_path: str, conditioner_path: str, config_path: str):
        logging.info("Initializing Inference Engine...")

        # Load config (threshold + input_dim)
        config = joblib.load(config_path)
        self.threshold = config['threshold']
        input_dim = config['input_dim']
        logging.info(f"  Threshold: {self.threshold:.6f} | Input dim: {input_dim}")

        # Load DataConditioner (clip + log1p transform)
        self.conditioner = joblib.load(conditioner_path)

        # Load PyTorch model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = ImprovedAutoencoder(input_dim).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
        self.model.eval()

        logging.info(f"  Inference Engine ready on {self.device}")

    def detect(self, X: np.ndarray):
        """
        Run anomaly detection on a single sample or batch.

        Args:
            X: numpy array of shape (n_samples, n_features), already RobustScaled.

        Returns:
            predictions: array of 0 (normal) or 1 (attack)
            scores: array of reconstruction error (anomaly score)
            latency_ms: inference time in milliseconds
        """
        start = time.perf_counter()

        # Apply data conditioning (clip + log1p)
        X_cond = self.conditioner.transform(X).astype(np.float32)

        with torch.no_grad():
            x_tensor = torch.FloatTensor(X_cond).to(self.device)
            recon = self.model(x_tensor)
            errors = torch.mean((x_tensor - recon) ** 2, dim=1).cpu().numpy()

        predictions = (errors > self.threshold).astype(int)
        latency_ms = (time.perf_counter() - start) * 1000

        return predictions, errors, latency_ms
