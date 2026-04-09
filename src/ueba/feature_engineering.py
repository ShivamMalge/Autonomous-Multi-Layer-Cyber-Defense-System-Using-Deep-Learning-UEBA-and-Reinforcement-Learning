"""
Feature Engineering — Aggregates raw session logs into per-user behavioral profiles.

Extracts features that capture:
  - Activity intensity (files, commands, bytes)
  - Temporal patterns (login hours, session lengths)
  - Statistical deviation (std, max spikes)
"""

import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class UEBAFeatureEngineer:
    """
    Transforms raw session-level logs into user-level behavioral feature vectors.
    Each user gets a single profile row summarizing their behavior across all sessions.
    """
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate session data into per-user behavioral features.
        
        Input:  DataFrame with individual session records
        Output: DataFrame with one row per user, containing behavioral features
        """
        logging.info("Extracting per-user behavioral features...")
        
        user_features = df.groupby('user_id').agg(
            # --- Activity Frequency ---
            total_sessions=('timestamp', 'count'),
            
            # --- Login Hour Patterns ---
            avg_login_hour=('login_hour', 'mean'),
            std_login_hour=('login_hour', 'std'),
            min_login_hour=('login_hour', 'min'),
            max_login_hour=('login_hour', 'max'),
            
            # --- Session Duration ---
            avg_session_duration=('session_duration_hrs', 'mean'),
            max_session_duration=('session_duration_hrs', 'max'),
            std_session_duration=('session_duration_hrs', 'std'),
            
            # --- File Access Intensity ---
            avg_files_accessed=('files_accessed', 'mean'),
            max_files_accessed=('files_accessed', 'max'),
            total_files_accessed=('files_accessed', 'sum'),
            
            # --- Command Execution ---
            avg_commands=('commands_executed', 'mean'),
            max_commands=('commands_executed', 'max'),
            
            # --- Data Transfer ---
            avg_bytes=('bytes_transferred', 'mean'),
            max_bytes=('bytes_transferred', 'max'),
            total_bytes=('bytes_transferred', 'sum'),
            std_bytes=('bytes_transferred', 'std'),
            
            # --- Ground Truth (for eval) ---
            anomalous_sessions=('is_anomalous', 'sum'),
        ).reset_index()
        
        # Fill any NaN std values (users with 1 session)
        user_features.fillna(0, inplace=True)
        
        # --- Derived Features ---
        
        # Off-hours ratio: fraction of sessions starting before 7 AM or after 8 PM
        off_hours = df.copy()
        off_hours['is_off_hours'] = ((off_hours['login_hour'] < 7) | 
                                      (off_hours['login_hour'] > 20)).astype(int)
        off_ratio = off_hours.groupby('user_id')['is_off_hours'].mean().reset_index()
        off_ratio.columns = ['user_id', 'off_hours_ratio']
        user_features = user_features.merge(off_ratio, on='user_id', how='left')
        
        # Activity spike: max_files / avg_files (how bursty the user is)
        user_features['file_spike_ratio'] = (
            user_features['max_files_accessed'] / 
            user_features['avg_files_accessed'].clip(lower=1)
        )
        
        # Data exfil indicator: max_bytes / avg_bytes
        user_features['bytes_spike_ratio'] = (
            user_features['max_bytes'] /
            user_features['avg_bytes'].clip(lower=1)
        )
        
        # Label: user is considered anomalous if they had ANY anomalous bursts
        user_features['is_threat'] = (user_features['anomalous_sessions'] > 0).astype(int)
        
        logging.info(f"Feature vectors created for {len(user_features)} users")
        logging.info(f"  Features: {len(user_features.columns) - 2} behavioral dimensions")
        logging.info(f"  Threats:  {user_features['is_threat'].sum()} users flagged as ground truth")
        
        return user_features

    def get_feature_columns(self) -> list:
        """Returns the list of feature column names used for modeling."""
        return [
            'total_sessions', 'avg_login_hour', 'std_login_hour',
            'min_login_hour', 'max_login_hour',
            'avg_session_duration', 'max_session_duration', 'std_session_duration',
            'avg_files_accessed', 'max_files_accessed', 'total_files_accessed',
            'avg_commands', 'max_commands',
            'avg_bytes', 'max_bytes', 'total_bytes', 'std_bytes',
            'off_hours_ratio', 'file_spike_ratio', 'bytes_spike_ratio'
        ]
