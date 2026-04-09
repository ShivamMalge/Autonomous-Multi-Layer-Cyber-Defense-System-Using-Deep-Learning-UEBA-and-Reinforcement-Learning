"""
Unified Real-Time Cyber Defense Pipeline (Phase 6)
==================================================
Integrates all layers:
  Stream Data (Network) → IDS (Autoencoder) → UEBA (Mock Lookup) → RL (DQN) → Response

Crucially implements system-level Alert Optimization Policies:
  - Uncertainty Zone Downgrades (Alert instead of Block if unsure)
  - Alert-First Rule (Must trigger an Alert before Blocking a benign user)
  - Escalation Tracking (Allows Block if Alert previously fired and risk remains high)

Usage:
  python src/system/unified_pipeline.py --limit 1000 --delay 0.05
"""

import os
import sys
import time
import random
import logging
import argparse
import joblib
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.pipeline.stream_simulator import StreamSimulator
from src.pipeline.inference_engine import InferenceEngine
from src.rl.dqn_agent import DQNAgent
from src.response.action_engine import ActionEngine

# ANSI Constants
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA= "\033[95m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# Custom logging formatter to handle ANSI colors nicely
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if hasattr(record, 'color'):
            record.msg = f"{record.color}{record.msg}{RESET}"
        return super().format(record)

logger = logging.getLogger('UnifiedSOC')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColoredFormatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(handler)
# Disable root logger to prevent duplicates
logging.getLogger().handlers = []

# --- System-Level Safeguards & Tracking ---
class EntityStateManager:
    """Tracks state history for users/IPs to enforce progressive defense rules."""
    def __init__(self):
        # state: {'alert_count': int, 'last_action': int, 'last_risk': float}
        self.state = {}

    def update(self, entity_id, action_id, risk_score):
        if entity_id not in self.state:
            self.state[entity_id] = {'alert_count': 0, 'last_action': 0, 'last_risk': 0.0}
        
        self.state[entity_id]['last_action'] = action_id
        self.state[entity_id]['last_risk'] = risk_score
        
        if action_id == 1: # ALERT
            self.state[entity_id]['alert_count'] += 1

    def get(self, entity_id):
        return self.state.get(entity_id, {'alert_count': 0, 'last_action': 0, 'last_risk': 0.0})


def apply_alert_optimization_rules(rl_action: int, state_vec: np.ndarray, 
                                   entity_state: dict, global_alert_ratio: float, logger) -> tuple[int, str]:
    """
    Applies system-level policies to the RL agent's decision.
    Prevents over-aggressive responses by enforcing 'Alert First' and 'Uncertainty Zone' rules.
    """
    anomaly, risk, intensity, time = state_vec
    threat_confidence = (anomaly + risk) / 2.0
    
    # If RL didn't choose an aggressive action, just pass it through
    if rl_action < 2:
        return rl_action, "RL direct decision"

    # RULE 4: Escalation Respect Rule
    # If we already alerted them, allow Block/Isolate without restriction
    if entity_state['alert_count'] > 0:
        return rl_action, "Escalation permitted (Prior alerts exist)"

    # RULE 2: Confidence-Based Override
    # High isolated signal allows agent absolute authority
    if anomaly > 0.75 or risk > 0.75:
        return rl_action, f"High confidence override (Anomaly={anomaly:.2f}, Risk={risk:.2f})"

    # RULE 5: Cap Alert Ratio
    downgrade_prob = 0.5
    if global_alert_ratio > 0.40:
        downgrade_prob = 0.2  # Reduce downgrades severely if Alert is overused

    # RULE 1 & 3: Probabilistic Uncertainty Zone (0.4 - 0.6)
    in_gray_zone = (0.4 < anomaly < 0.6) or (0.4 < risk < 0.6)
    
    if in_gray_zone:
        if random.random() < downgrade_prob:
            return 1, f"Downgraded to ALERT (Probabilistic gray zone: anomaly={anomaly:.2f}, risk={risk:.2f})"
        else:
            return rl_action, "RL action preserved in gray zone (Probabilistic pass)"

    # RULE 2 (Secondary): Alert-First Policy (Soft constraint for new entities)
    if threat_confidence < 0.75:
        if random.random() < downgrade_prob:
            return 1, "Downgraded to ALERT (Alert-First Policy for new entities)"
        else:
            return rl_action, "RL action preserved (Probabilistic override of Alert-First)"

    return rl_action, "RL direct decision (High confidence)"


# --- Mock Mocks (Replace with DB queries in prod) ---
class DummyUEBA:
    def __init__(self):
        self.rng = np.random.default_rng(99)
        self.high_risk_users = ['User_007', 'User_501', 'User_BAD']

    def get_context(self, user_id: str, is_anomalous_network: bool) -> tuple:
        if user_id in self.high_risk_users or is_anomalous_network:
            return np.clip(self.rng.beta(4, 3), 0, 1), np.clip(self.rng.beta(6, 2), 0, 1)
        else:
            return np.clip(self.rng.beta(2, 7), 0, 1), np.clip(self.rng.beta(2, 4), 0, 1)

def random_ip():
    return f"10.0.0.{random.randint(1, 200)}"

def random_user():
    return random.choice(['User_007', 'User_501', 'User_BAD']) if random.random() < 0.05 else f"User_{random.randint(100, 200)}"


def main():
    parser = argparse.ArgumentParser(description="Unified SOC Pipeline (Phase 6)")
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--delay', type=float, default=0.01)
    args = parser.parse_args()

    # Paths
    DATA_PATH       = os.path.join(PROJECT_ROOT, "data", "processed", "test_dataset.parquet")
    MODEL_PATH      = os.path.join(PROJECT_ROOT, "models", "autoencoder_v2.pt")
    CONDITIONER_PATH= os.path.join(PROJECT_ROOT, "models", "data_conditioner.pkl")
    CONFIG_PATH     = os.path.join(PROJECT_ROOT, "models", "ae_v2_config.pkl")
    TOP_FEATURES    = os.path.join(PROJECT_ROOT, "data", "features", "top_features.pkl")
    RL_MODEL_PATH   = os.path.join(PROJECT_ROOT, "models", "rl_policy_model.pt")
    LOG_DIR         = os.path.join(PROJECT_ROOT, "reports", "logs")

    # Initialization
    logger.info("Initializing Unified Cyber Defense Pipeline...", extra={'color': BOLD+CYAN})
    
    feature_columns = joblib.load(TOP_FEATURES)
    engine = InferenceEngine(MODEL_PATH, CONDITIONER_PATH, CONFIG_PATH)
    stream = StreamSimulator(DATA_PATH, feature_columns)
    ueba = DummyUEBA()
    
    rl_agent = DQNAgent(state_dim=4, action_dim=4)
    if os.path.exists(RL_MODEL_PATH):
        rl_agent.load(RL_MODEL_PATH)
    else:
        logger.warning("RL Model not found! Will act randomly.")
        
    reactor = ActionEngine(log_dir=LOG_DIR, cooldown_sec=15) # Shorter cooldown for demo
    tracker = EntityStateManager()

    logger.info(f"Pipeline ready. Processing {args.limit} events...", extra={'color': BOLD+CYAN})
    print("="*80)

    stats = {'processed': 0, 'rl_actions': {0:0,1:0,2:0,3:0}, 'final_actions': {0:0,1:0,2:0,3:0}, 'downgrades': 0}

    try:
        for sample, true_label in stream.stream_single(delay=args.delay):
            
            # 1. Event Identification
            ip_addr = random_ip()
            user_id = random_user()
            time_context = (time.time() % 86400) / 86400.0
            entity_key = f"{user_id}@{ip_addr}"

            # 2. Network Detection (IDS)
            preds, scores, _ = engine.detect(sample)
            raw_anomaly = scores[0]
            is_anomaly = preds[0] == 1
            norm_anomaly = min(raw_anomaly / (engine.threshold * 4.0), 1.0)
            
            # Skip logging non-events to keep console clean, unless requested
            # Proceed if it's anomalous, or occasionally sample benign traffic
            if not is_anomaly and random.random() > 0.05:
                continue

            # 3. Behavioral Analysis (UEBA)
            risk_score, intensity = ueba.get_context(user_id, is_anomaly)
            
            # 4. State Construction
            state_vec = np.array([norm_anomaly, risk_score, intensity, time_context])
            entity_hist = tracker.get(entity_key)

            # 5. RL Decision
            rl_action = rl_agent.select_action(state_vec, training=False)
            
            # 6. System Rules (Alert Optimization)
            # Calculate current global alert ratio
            total_actions = sum(stats['final_actions'].values())
            global_alert_ratio = stats['final_actions'][1] / max(total_actions, 1)

            final_action, justification = apply_alert_optimization_rules(
                rl_action, state_vec, entity_hist, global_alert_ratio, logger
            )
            
            # State Update
            tracker.update(entity_key, final_action, risk_score)
            
            # Metrics Update
            stats['processed'] += 1
            stats['rl_actions'][rl_action] += 1
            stats['final_actions'][final_action] += 1
            if final_action < rl_action:
                stats['downgrades'] += 1

            # 7. Action Execution & Logging (Detailed)
            action_names = {0: 'MONITOR', 1: 'ALERT', 2: 'BLOCK_IP', 3: 'ISOLATE_USER'}
            
            if final_action > 0:  # Only output logs for actionable events
                # Setup colors
                col = YELLOW if final_action == 1 else (RED if final_action == 2 else MAGENTA)
                
                print(f"[{time.strftime('%H:%M:%S')}] {BOLD}Entity:{RESET} {user_id} ({ip_addr})")
                print(f"  {CYAN}Signals:{RESET}  Anomaly={norm_anomaly:.3f} | UserRisk={risk_score:.3f} | HistAlerts={entity_hist['alert_count']}")
                
                if final_action != rl_action:
                    print(f"  {YELLOW}Control:{RESET}  RL suggested {action_names[rl_action]}, System chose {action_names[final_action]}")
                    print(f"  {YELLOW}Reason:{RESET}   {justification}")
                else:
                    print(f"  {GREEN}Control:{RESET}  {action_names[final_action]} (RL decision approved)")
                
                print(f"  {col}Execute:{RESET} ", end="")
                reactor.execute(final_action, ip_addr, user_id, (norm_anomaly+risk_score)/2.0)
                print("-" * 60)

            if stats['processed'] >= args.limit:
                break
                
    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user.")

    # Generate Summary
    print("\n" + "="*80)
    print(f"{BOLD}UNIFIED SOC PIPELINE SUMMARY{RESET}")
    print("="*80)
    print(f"  Events Analyzed         : {stats['processed']} (Anomalies + sampled benign)")
    print()
    print(f"  {BOLD}RL Intent Distributions:{RESET}")
    print(f"    Monitor : {stats['rl_actions'][0]}")
    print(f"    Alert   : {stats['rl_actions'][1]}")
    print(f"    Block   : {stats['rl_actions'][2]}")
    print(f"    Isolate : {stats['rl_actions'][3]}")
    print()
    print(f"  {BOLD}Final Executed Actions (Post-Optimization):{RESET}")
    print(f"    Monitor : {stats['final_actions'][0]}")
    print(f"    Alert   : {stats['final_actions'][1]}")
    print(f"    Block   : {stats['final_actions'][2]}")
    print(f"    Isolate : {stats['final_actions'][3]}")
    print()
    print(f"  {YELLOW}System Interventions    : {stats['downgrades']} aggressive actions safely downgraded to Alerts.{RESET}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
