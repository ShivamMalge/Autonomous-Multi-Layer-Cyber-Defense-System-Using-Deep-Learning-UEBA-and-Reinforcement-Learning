"""
Risk Engine — Computes composite risk scores for each user.

Combines multiple behavioral signals into a single normalized threat score:
  - Cluster deviation (GMM anomaly score)
  - Activity spike magnitude
  - Off-hours access pattern

Risk Levels:
  0.0 – 0.3  →  NORMAL
  0.3 – 0.7  →  SUSPICIOUS
  0.7 – 1.0  →  HIGH RISK
"""

import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class RiskEngine:
    """
    Multi-signal risk scoring system for user behavioral analytics.
    """
    # Risk thresholds
    NORMAL_THRESHOLD = 0.3
    SUSPICIOUS_THRESHOLD = 0.7

    def __init__(self, weights: dict = None):
        """
        Args:
            weights: dict mapping signal names to their importance.
                     Default gives equal weight to all three signals.
        """
        self.weights = weights or {
            'cluster_deviation': 0.40,   # How far from normal behavioral clusters
            'activity_spike':    0.35,   # Magnitude of file/data transfer spikes
            'time_anomaly':      0.25,   # Off-hours access pattern
        }

    def _normalize_scores(self, values: np.ndarray) -> np.ndarray:
        """Min-max normalize to [0, 1] range."""
        v_min, v_max = values.min(), values.max()
        if v_max - v_min < 1e-10:
            return np.zeros_like(values)
        return (values - v_min) / (v_max - v_min)

    def compute_risk(self, user_profiles: pd.DataFrame, 
                     gmm_anomaly_scores: np.ndarray) -> pd.DataFrame:
        """
        Compute composite risk score for each user.
        
        Args:
            user_profiles: DataFrame with per-user features (from feature_engineering)
            gmm_anomaly_scores: array of GMM negative log-likelihood scores
            
        Returns:
            DataFrame with user_id, component scores, risk_score, and risk_level
        """
        logging.info("Computing composite risk scores...")
        
        # Signal 1: Cluster Deviation (from GMM)
        cluster_scores = self._normalize_scores(gmm_anomaly_scores)
        
        # Signal 2: Activity Spike (combining file and bytes spike ratios)
        spike_raw = (
            user_profiles['file_spike_ratio'].values * 0.5 +
            user_profiles['bytes_spike_ratio'].values * 0.5
        )
        spike_scores = self._normalize_scores(spike_raw)
        
        # Signal 3: Time Anomaly (off-hours ratio)
        time_scores = self._normalize_scores(user_profiles['off_hours_ratio'].values)
        
        # Weighted combination
        risk_scores = (
            self.weights['cluster_deviation'] * cluster_scores +
            self.weights['activity_spike']    * spike_scores +
            self.weights['time_anomaly']      * time_scores
        )
        
        # Classify risk level
        risk_levels = np.where(
            risk_scores >= self.SUSPICIOUS_THRESHOLD, 'HIGH_RISK',
            np.where(risk_scores >= self.NORMAL_THRESHOLD, 'SUSPICIOUS', 'NORMAL')
        )
        
        # Build result DataFrame
        result = pd.DataFrame({
            'user_id': user_profiles['user_id'].values,
            'cluster_deviation_score': np.round(cluster_scores, 4),
            'activity_spike_score': np.round(spike_scores, 4),
            'time_anomaly_score': np.round(time_scores, 4),
            'risk_score': np.round(risk_scores, 4),
            'risk_level': risk_levels,
            'is_threat_ground_truth': user_profiles['is_threat'].values
        })
        
        # Summary
        for level in ['NORMAL', 'SUSPICIOUS', 'HIGH_RISK']:
            count = (result['risk_level'] == level).sum()
            logging.info(f"  {level:12s}: {count} users")
        
        return result
