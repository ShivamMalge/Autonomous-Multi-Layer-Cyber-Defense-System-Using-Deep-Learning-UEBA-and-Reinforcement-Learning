"""
Preprocessor — Applies feature selection and scaling to raw incoming samples.
Wraps the saved RobustScaler and DataConditioner from training.
"""

import logging
import joblib
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class Preprocessor:
    """
    Loads saved preprocessing artifacts and applies the same 
    transformations used during training to live streaming data.
    
    Pipeline: Raw Features → RobustScaler → DataConditioner (clip + log1p)
    """
    def __init__(self, scaler_path: str, conditioner_path: str):
        logging.info("Loading preprocessing artifacts...")
        self.scaler = joblib.load(scaler_path)
        self.conditioner = joblib.load(conditioner_path)
        logging.info("Preprocessor ready.")

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Apply the full preprocessing chain to a single sample or batch.
        Input X is expected to already have the correct top features selected.
        """
        # Step 1: RobustScaler (same transform fitted in Phase 1.1)
        X_scaled = self.scaler.transform(X)
        # Step 2: DataConditioner (clip outliers + log1p, fitted in Phase 1.3)
        X_conditioned = self.conditioner.transform(X_scaled)
        return X_conditioned
