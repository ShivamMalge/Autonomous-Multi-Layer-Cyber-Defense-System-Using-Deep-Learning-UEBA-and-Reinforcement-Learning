"""
Clustering Model — Learns behavioral profiles of normal users.

Uses Gaussian Mixture Models (GMM) which capture the fact that
"normal" behavior isn't a single cluster — different roles
(admins, analysts, executives) have legitimately different patterns.

GMM is preferred over KMeans here because:
  - It provides soft cluster assignments (probability-based)
  - It naturally produces a log-likelihood score usable as an anomaly metric
  - It handles clusters of different shapes/sizes
"""

import os
import logging
import joblib
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class BehavioralClusterModel:
    """
    Fits a Gaussian Mixture Model on normal user behavioral profiles.
    Users whose behavior has low likelihood under the learned distribution
    are flagged as anomalous.
    """
    def __init__(self, n_components: int = 3):
        self.n_components = n_components
        self.gmm = GaussianMixture(
            n_components=n_components,
            covariance_type='full',
            random_state=42,
            n_init=3
        )
        self.scaler = StandardScaler()
        self.fitted = False

    def fit(self, X: np.ndarray):
        """
        Fit on NORMAL user profiles only.
        Learns the 'manifold' of legitimate behavioral patterns.
        """
        logging.info(f"Fitting GMM with {self.n_components} components on {X.shape[0]} users...")
        
        # Scale features to unit variance for stable clustering
        X_scaled = self.scaler.fit_transform(X)
        self.gmm.fit(X_scaled)
        self.fitted = True
        
        # Log cluster sizes
        labels = self.gmm.predict(X_scaled)
        for i in range(self.n_components):
            count = np.sum(labels == i)
            logging.info(f"  Cluster {i}: {count} users ({count/len(labels)*100:.1f}%)")
        
        return self

    def score_users(self, X: np.ndarray) -> np.ndarray:
        """
        Score each user profile. Lower log-likelihood = more anomalous.
        Returns a per-sample anomaly score (inverted log-likelihood).
        """
        assert self.fitted, "Model must be fitted before scoring."
        X_scaled = self.scaler.transform(X)
        
        # GMM score_samples returns log-likelihood (higher = more normal)
        # We negate it so higher score = more anomalous
        log_likelihoods = self.gmm.score_samples(X_scaled)
        anomaly_scores = -log_likelihoods
        
        return anomaly_scores

    def predict_clusters(self, X: np.ndarray) -> np.ndarray:
        """Assign each user to their most likely behavioral cluster."""
        X_scaled = self.scaler.transform(X)
        return self.gmm.predict(X_scaled)

    def save(self, model_dir: str):
        os.makedirs(model_dir, exist_ok=True)
        joblib.dump(self.gmm, os.path.join(model_dir, "ueba_gmm.pkl"))
        joblib.dump(self.scaler, os.path.join(model_dir, "ueba_scaler.pkl"))
        logging.info(f"UEBA clustering model saved to {model_dir}")

    def load(self, model_dir: str):
        self.gmm = joblib.load(os.path.join(model_dir, "ueba_gmm.pkl"))
        self.scaler = joblib.load(os.path.join(model_dir, "ueba_scaler.pkl"))
        self.fitted = True
        logging.info("UEBA clustering model loaded.")
