"""
User Activity Simulator — Generates synthetic enterprise user telemetry.

Simulates two populations:
  - Normal users   (~85%): consistent work-hour logins, moderate activity
  - Anomalous users (~15%): odd-hour access, data exfiltration spikes, 
                             excessive privilege use — mimicking insider threats

Each record represents a single user session.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class UserActivitySimulator:
    """
    Generates realistic synthetic user session logs for UEBA training.
    """
    def __init__(self, n_users: int = 100, n_days: int = 30, 
                 anomaly_ratio: float = 0.15, seed: int = 42):
        self.n_users = n_users
        self.n_days = n_days
        self.anomaly_ratio = anomaly_ratio
        self.rng = np.random.default_rng(seed)
        
        # Decide which users are anomalous
        n_anomalous = max(1, int(n_users * anomaly_ratio))
        all_ids = np.arange(n_users)
        self.rng.shuffle(all_ids)
        self.anomalous_users = set(all_ids[:n_anomalous])
        self.normal_users = set(all_ids[n_anomalous:])
        
        logging.info(f"Simulator: {n_users} users, {n_anomalous} anomalous, {n_days} days")

    def _generate_normal_session(self, user_id: int, day: datetime) -> dict:
        """Normal user: works 9-6, moderate file access, small transfers."""
        login_hour = self.rng.normal(loc=9.0, scale=1.0)  # ~9 AM ± 1hr
        login_hour = np.clip(login_hour, 7, 11)
        
        session_dur = self.rng.normal(loc=4.5, scale=1.5)  # ~4.5 hrs ± 1.5
        session_dur = np.clip(session_dur, 0.5, 10)
        
        files = int(self.rng.poisson(lam=8))               # ~8 files/session
        commands = int(self.rng.poisson(lam=15))            # ~15 commands
        bytes_tx = self.rng.exponential(scale=5_000)        # ~5 KB avg
        
        timestamp = day + timedelta(hours=float(login_hour))
        
        return {
            'user_id': f"user_{user_id:03d}",
            'timestamp': timestamp,
            'login_hour': round(login_hour, 2),
            'session_duration_hrs': round(session_dur, 2),
            'files_accessed': files,
            'commands_executed': commands,
            'bytes_transferred': round(bytes_tx, 0),
            'is_anomalous': 0
        }

    def _generate_anomalous_session(self, user_id: int, day: datetime) -> dict:
        """
        Anomalous user: behaviors that mimic insider threats.
        Not every session is anomalous — they have normal days too,
        with periodic 'bursts' of suspicious activity.
        """
        # 40% chance this particular session shows anomalous behavior
        is_burst = self.rng.random() < 0.40
        
        if is_burst:
            # Off-hours login (midnight to 5 AM, or late evening)
            login_hour = self.rng.choice([
                self.rng.uniform(0, 5),     # middle of night
                self.rng.uniform(21, 23.5)  # late evening
            ])
            session_dur = self.rng.uniform(0.5, 12)      # erratic duration
            files = int(self.rng.poisson(lam=80))         # 10x normal file access
            commands = int(self.rng.poisson(lam=120))      # 8x normal commands
            bytes_tx = self.rng.exponential(scale=500_000) # 100x data transfer
        else:
            # Normal-looking session (blending in)
            login_hour = self.rng.normal(loc=9.5, scale=1.5)
            login_hour = np.clip(login_hour, 7, 12)
            session_dur = self.rng.normal(loc=5.0, scale=2.0)
            session_dur = np.clip(session_dur, 0.5, 10)
            files = int(self.rng.poisson(lam=12))
            commands = int(self.rng.poisson(lam=20))
            bytes_tx = self.rng.exponential(scale=8_000)
        
        timestamp = day + timedelta(hours=float(login_hour))
        
        return {
            'user_id': f"user_{user_id:03d}",
            'timestamp': timestamp,
            'login_hour': round(float(login_hour), 2),
            'session_duration_hrs': round(float(session_dur), 2),
            'files_accessed': files,
            'commands_executed': commands,
            'bytes_transferred': round(float(bytes_tx), 0),
            'is_anomalous': 1 if is_burst else 0
        }

    def generate(self) -> pd.DataFrame:
        """Generate the full synthetic dataset."""
        logging.info("Generating synthetic user activity data...")
        records = []
        base_date = datetime(2026, 3, 1)
        
        for day_offset in range(self.n_days):
            day = base_date + timedelta(days=day_offset)
            
            for uid in range(self.n_users):
                # Users may have 1-3 sessions per day
                n_sessions = self.rng.poisson(lam=1.5)
                n_sessions = max(1, min(n_sessions, 4))
                
                for _ in range(n_sessions):
                    if uid in self.anomalous_users:
                        records.append(self._generate_anomalous_session(uid, day))
                    else:
                        records.append(self._generate_normal_session(uid, day))
        
        df = pd.DataFrame(records)
        n_anom = df['is_anomalous'].sum()
        logging.info(f"Generated {len(df):,} sessions ({n_anom:,} anomalous bursts)")
        return df
