"""
Orchestration Engine — Phase 5
================================
Runs the closed-loop autonomous defense pipeline:
  Stream Data → IDS Detection → UEBA Enrichment → RL Agent → Action Response
  
Usage:
  python src/response/orchestrator.py
"""

import os
import sys
import time
import argparse
import random
import logging
import joblib
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.pipeline.stream_simulator import StreamSimulator
from src.pipeline.inference_engine import InferenceEngine
from src.rl.dqn_agent import DQNAgent
from src.response.action_engine import ActionEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class DummyUEBA:
    """
    Mock UEBA service to enrich network events with behavioral context.
    In a real system, this queries the RiskEngine DB for the active user.
    """
    def __init__(self):
        self.rng = np.random.default_rng(42)
        # Give high risk to specific users to simulate targeted insider threats
        self.high_risk_users = ['User_42', 'User_15', 'User_89']

    def get_context(self, user_id: str, is_anomalous_network: bool) -> tuple:
        """Returns (user_risk_score, activity_intensity)"""
        # If network is already highly anomalous, or user is known bad, risk is high
        if user_id in self.high_risk_users or is_anomalous_network:
            user_risk_score = np.clip(self.rng.beta(4, 3), 0, 1)
            activity_intensity = np.clip(self.rng.beta(6, 2), 0, 1)
        else:
            user_risk_score = np.clip(self.rng.beta(2, 7), 0, 1)
            activity_intensity = np.clip(self.rng.beta(2, 4), 0, 1)
            
        return user_risk_score, activity_intensity


def random_ip():
    return f"192.168.1.{random.randint(2, 200)}"

def random_user():
    # Occasionally inject high risk users
    if random.random() < 0.05:
        return random.choice(['User_42', 'User_15', 'User_89'])
    return f"User_{random.randint(1, 100)}"


def main():
    parser = argparse.ArgumentParser(description="Autonomous Defense Orchestrator")
    parser.add_argument('--limit', type=int, default=1000,
                        help="Max events to process (default: 1000)")
    parser.add_argument('--delay', type=float, default=0.05,
                        help="Seconds to wait between events")
    args = parser.parse_args()

    # ---- Paths ----
    DATA_PATH       = os.path.join(PROJECT_ROOT, "data", "processed", "test_dataset.parquet")
    MODEL_PATH      = os.path.join(PROJECT_ROOT, "models", "autoencoder_v2.pt")
    CONDITIONER_PATH= os.path.join(PROJECT_ROOT, "models", "data_conditioner.pkl")
    CONFIG_PATH     = os.path.join(PROJECT_ROOT, "models", "ae_v2_config.pkl")
    TOP_FEATURES    = os.path.join(PROJECT_ROOT, "data", "features", "top_features.pkl")
    RL_MODEL_PATH   = os.path.join(PROJECT_ROOT, "models", "rl_policy_model.pt")
    LOG_DIR         = os.path.join(PROJECT_ROOT, "reports", "logs")

    # ---- System Init ----
    feature_columns = joblib.load(TOP_FEATURES)
    
    # 1. Pipeline / IDS
    engine = InferenceEngine(MODEL_PATH, CONDITIONER_PATH, CONFIG_PATH)
    stream = StreamSimulator(DATA_PATH, feature_columns)
    
    # 2. UEBA Context
    ueba = DummyUEBA()
    
    # 3. RL Agent
    rl_agent = DQNAgent(state_dim=4, action_dim=4)
    if os.path.exists(RL_MODEL_PATH):
        rl_agent.load(RL_MODEL_PATH)
    else:
        logging.warning("RL Model not found. Acting randomly! Train phase 4 first.")

    # 4. Action Engine
    reactor = ActionEngine(log_dir=LOG_DIR, cooldown_sec=30)
    
    logging.info(f"Starting closed-loop orchestration | Limit: {args.limit} events")
    print("\n" + "="*70)
    
    events_processed = 0
    actions_taken = {0:0, 1:0, 2:0, 3:0}

    # Simulate real-time stream processing
    try:
        # Use single mode to simulate events arriving sequentially
        for sample, true_label in stream.stream_single(delay=args.delay):
            
            # --- Event Attributes ---
            ip_addr = random_ip()
            user_id = random_user()
            time_context = (time.time() % 86400) / 86400.0  # Normalized time of day
            
            # --- Step 1: Detect (IDS) ---
            preds, scores, _ = engine.detect(sample)
            raw_anomaly_score = scores[0]
            is_anomaly = preds[0] == 1
            
            # Normalize anomaly score for RL (0 to 1 bound)
            # engine.threshold defines the boundary of normal/attack
            norm_anomaly = min(raw_anomaly_score / (engine.threshold * 4.0), 1.0)
            
            # --- Step 2: Analyze (UEBA Context) ---
            risk_score, intensity = ueba.get_context(user_id, is_anomaly)
            
            # Formulate state for RL
            # [anomaly_score, user_risk_score, activity_intensity, time_context]
            rl_state = np.array([norm_anomaly, risk_score, intensity, time_context])
            
            # --- Step 3: Decide (RL) ---
            combined_threat = (norm_anomaly + risk_score) / 2.0
            action_id = rl_agent.select_action(rl_state, training=False)
            
            # --- Step 4: Act (Response) ---
            if action_id > 0:  # If anything above MONITOR, execute logging/action
                reactor.execute(action_id, ip_addr, user_id, combined_threat)
                
            actions_taken[action_id] += 1
            events_processed += 1
            
            if events_processed >= args.limit:
                break
                
    except KeyboardInterrupt:
        print("\nOrchestrator interrupted by user.")

    # Summary
    print("\n" + "="*70)
    print("  ORCHESTRATION SESSION SUMMARY")
    print("="*70)
    print(f"  Events Processed : {events_processed}")
    print(f"  Monitor Actions  : {actions_taken[0]}")
    print(f"  Alerts Sent      : {actions_taken[1]}")
    print(f"  IPs Blocked      : {actions_taken[2]}")
    print(f"  Users Isolated   : {actions_taken[3]}")
    print(f"  Log File         : {reactor.log_file}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
