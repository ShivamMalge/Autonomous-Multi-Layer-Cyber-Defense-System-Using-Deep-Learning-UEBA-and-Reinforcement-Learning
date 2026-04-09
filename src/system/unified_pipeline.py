"""
Unified Real-Time Cyber Defense Pipeline (Phase 7 Refactor)
===========================================================
Production-grade orchestration system featuring:
  - Clean architecture and single control loop
  - Unified Event Schema
  - Central JSONL Logger
  - Real-time Metrics Aggregation
  - Runtime Mode Switch (live / replay)
  
Usage:
  python src/system/unified_pipeline.py --mode live --limit 1000
  python src/system/unified_pipeline.py --mode replay
"""

import os
import sys
import time
import json
import random
import logging
import argparse
import joblib
import numpy as np
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.pipeline.stream_simulator import StreamSimulator
from src.pipeline.inference_engine import InferenceEngine
from src.rl.dqn_agent import DQNAgent
from src.response.action_engine import ActionEngine
from src.system.event_logger import CentralEventLogger
from src.system.metrics import MetricsAggregator

# --- Global Configurations ---
ACTION_MAP = {
    0: "MONITOR",
    1: "ALERT",
    2: "BLOCK_IP",
    3: "ISOLATE_USER"
}

# ANSI Colors
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA= "\033[95m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# Logger Setup
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
logging.getLogger().handlers = []


# --- State & Optimization Rules ---
class EntityStateManager:
    def __init__(self):
        self.state = {}

    def update(self, entity_id, action_id, risk_score):
        if entity_id not in self.state:
            self.state[entity_id] = {'alert_count': 0, 'last_action': 0, 'last_risk': 0.0}
        self.state[entity_id]['last_action'] = action_id
        self.state[entity_id]['last_risk'] = risk_score
        if action_id == 1:
            self.state[entity_id]['alert_count'] += 1

    def get(self, entity_id):
        return self.state.get(entity_id, {'alert_count': 0, 'last_action': 0, 'last_risk': 0.0})


def apply_alert_optimization_rules(rl_action: int, state_vec: np.ndarray, 
                                   entity_state: dict, global_alert_ratio: float) -> tuple[int, str]:
    anomaly, risk, intensity, _ = state_vec
    threat_confidence = (anomaly + risk) / 2.0
    
    if rl_action < 2:
        return rl_action, "RL direct decision"

    # RULE: Escalation Respect
    if entity_state['alert_count'] > 0:
        return rl_action, "Escalation permitted (Prior alerts exist)"

    # RULE: Confidence-Based Override
    if anomaly > 0.75 or risk > 0.75:
        return rl_action, f"High confidence override (Anomaly={anomaly:.2f}, Risk={risk:.2f})"

    downgrade_prob = 0.5
    if global_alert_ratio > 0.40:
        downgrade_prob = 0.2  # Cap Alert Ratio

    # RULE: Uncertainty Zone
    if (0.4 < anomaly < 0.6) or (0.4 < risk < 0.6):
        if random.random() < downgrade_prob:
            return 1, f"Downgraded to ALERT (Probabilistic gray zone)"
        return rl_action, "RL action preserved in gray zone"

    # RULE: Alert-First Policy
    if threat_confidence < 0.75:
        if random.random() < downgrade_prob:
            return 1, "Downgraded to ALERT (Alert-First Policy)"
        return rl_action, "RL action preserved (Probabilistic override)"

    return rl_action, "RL direct decision (High confidence)"


# --- Mocks ---
class DummyUEBA:
    def __init__(self):
        self.rng = np.random.default_rng(99)
        self.high_risk_users = ['User_007', 'User_501', 'User_BAD']

    def get_context(self, user_id: str, is_anomalous_network: bool) -> tuple:
        if user_id in self.high_risk_users or is_anomalous_network:
            return np.clip(self.rng.beta(4, 3), 0, 1), np.clip(self.rng.beta(6, 2), 0, 1)
        return np.clip(self.rng.beta(2, 7), 0, 1), np.clip(self.rng.beta(2, 4), 0, 1)

def random_ip(): return f"10.0.0.{random.randint(1, 200)}"
def random_user(): return random.choice(['User_007', 'User_501', 'User_BAD']) if random.random() < 0.05 else f"User_{random.randint(100, 200)}"


# --- Main Pipeline ---
def play_live(args, paths):
    logger.info("Initializing Live Mode...", extra={'color': BOLD+CYAN})
    
    # Init Models
    engine = InferenceEngine(paths['MODEL'], paths['CONDITIONER'], paths['CONFIG'])
    stream = StreamSimulator(paths['DATA'], joblib.load(paths['TOP_FEATURES']))
    ueba = DummyUEBA()
    
    rl_agent = DQNAgent(state_dim=4, action_dim=4)
    if os.path.exists(paths['RL_MODEL']):
        rl_agent.load(paths['RL_MODEL'])
    else:
        logger.warning("RL Model not found! Will act randomly.")
        
    reactor = ActionEngine(log_dir=paths['LOG_DIR'], cooldown_sec=15)
    
    # Init System Tools
    tracker = EntityStateManager()
    event_logger = CentralEventLogger(paths['LOG_DIR'])
    metrics = MetricsAggregator()

    logger.info(f"Pipeline ready. Processing {args.limit} events...", extra={'color': BOLD+CYAN})
    print("="*80)

    try:
        for sample, true_label in stream.stream_single(delay=args.delay):
            start_time = time.perf_counter()
            
            # --- 1. Event Identification ---
            ip_addr, user_id = random_ip(), random_user()
            time_context = (time.time() % 86400) / 86400.0
            entity_key = f"{user_id}@{ip_addr}"

            # --- 2. IDS ---
            preds, scores, _ = engine.detect(sample)
            is_anomaly = preds[0] == 1
            if not is_anomaly and random.random() > 0.05:
                continue  # Sample benign traffic
            
            norm_anomaly = float(min(scores[0] / (engine.threshold * 4.0), 1.0))

            # --- 3. UEBA ---
            risk_score, intensity = map(float, ueba.get_context(user_id, is_anomaly))
            
            # --- 4. RL Decision ---
            state_vec = np.array([norm_anomaly, risk_score, intensity, time_context])
            rl_action = rl_agent.select_action(state_vec, training=False)
            
            # --- 5. System Rules ---
            global_alert_ratio = metrics.metrics["alert"] / max(metrics.metrics["total_events"], 1)
            final_action, justification = apply_alert_optimization_rules(
                rl_action, state_vec, tracker.get(entity_key), global_alert_ratio
            )
            
            # --- 6. UNIFIED SCHEMA CREATION ---
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            severity_score = float(0.6 * norm_anomaly + 0.4 * risk_score)
            
            event = {
                "timestamp": datetime.now().isoformat(),
                "ip": ip_addr,
                "user_id": user_id,
                "anomaly_score": round(norm_anomaly, 4),
                "user_risk_score": round(risk_score, 4),
                "activity_intensity": round(intensity, 4),
                "severity_score": round(severity_score, 4),
                "rl_action": int(rl_action),
                "rl_action_name": ACTION_MAP[rl_action],
                "final_action": int(final_action),
                "final_action_name": ACTION_MAP[final_action],
                "was_downgraded": final_action != rl_action,
                "downgrade_reason": justification if final_action != rl_action else "None",
                "latency_ms": round(latency_ms, 3)
            }
            
            # --- 7. Execution, Logging, Metrics ---
            tracker.update(entity_key, final_action, risk_score)
            metrics.update(event)
            event_logger.log_event(event)
            
            if final_action > 0:
                reactor.execute(final_action, ip_addr, user_id, severity_score)
                _print_event_snippet(event)

            if metrics.metrics["total_events"] >= args.limit:
                break
                
    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user.")

    _print_metrics_summary(metrics.get_summary())


def play_replay(log_dir: str):
    log_file = os.path.join(log_dir, "system_events.jsonl")
    if not os.path.exists(log_file):
        logger.error(f"No log file found at {log_file}")
        return
        
    logger.info(f"Replaying events from {log_file}...", extra={'color': BOLD+CYAN})
    print("="*80)
    
    with open(log_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip(): continue
            event = json.loads(line.strip())
            
            time.sleep(0.01) # Simulate pacing
            if event["final_action"] > 0:
                _print_event_snippet(event)
                
            if idx > 100: # Limit replay for demo
                break
    print("="*80 + "\nReplay Complete!")


def _print_event_snippet(event: dict):
    """Prints humans-readable representation of an event."""
    col = YELLOW if event["final_action"] == 1 else (RED if event["final_action"] == 2 else MAGENTA)
    print(f"[{event['timestamp'][11:19]}] {BOLD}Entity:{RESET} {event['user_id']} ({event['ip']})")
    print(f"  {CYAN}Scores:{RESET}  Anomaly:{event['anomaly_score']:.2f} | Risk:{event['user_risk_score']:.2f} | Sev:{event['severity_score']:.2f}")
    print(f"  {YELLOW}RL Action:{RESET} {event['rl_action_name']}")
    if event["was_downgraded"]:
        print(f"  {RED}System Override:{RESET} -> {event['final_action_name']} ({event['downgrade_reason']})")
    print(f"  {col}Final:{RESET}   Executed {event['final_action_name']} [Lat: {event['latency_ms']}ms]")
    print("-" * 60)

def _print_metrics_summary(metrics: dict):
    print("\n" + "="*80)
    print(f"{BOLD}UNIFIED PIPELINE METRICS SUMMARY{RESET}")
    print("="*80)
    print(f"  Total Events Processed  : {metrics['total_events']}")
    print(f"  Avg Pipeline Latency    : {metrics['avg_latency']:.2f} ms/event\n")
    print(f"  {BOLD}Action Distribution:{RESET}")
    print(f"    MONITOR : {metrics['monitor']}")
    print(f"    ALERT   : {metrics['alert']}")
    print(f"    BLOCK   : {metrics['block']}")
    print(f"    ISOLATE : {metrics['isolate']}\n")
    print(f"  {YELLOW}System Interventions    : {metrics['interventions']}{RESET}")
    print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['live', 'replay'], default='live')
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--delay', type=float, default=0.01)
    args = parser.parse_args()

    paths = {
        'DATA': os.path.join(PROJECT_ROOT, "data", "processed", "test_dataset.parquet"),
        'MODEL': os.path.join(PROJECT_ROOT, "models", "autoencoder_v2.pt"),
        'CONDITIONER': os.path.join(PROJECT_ROOT, "models", "data_conditioner.pkl"),
        'CONFIG': os.path.join(PROJECT_ROOT, "models", "ae_v2_config.pkl"),
        'TOP_FEATURES': os.path.join(PROJECT_ROOT, "data", "features", "top_features.pkl"),
        'RL_MODEL': os.path.join(PROJECT_ROOT, "models", "rl_policy_model.pt"),
        'LOG_DIR': os.path.join(PROJECT_ROOT, "reports", "logs")
    }

    if args.mode == "live":
        play_live(args, paths)
    elif args.mode == "replay":
        play_replay(paths['LOG_DIR'])

if __name__ == "__main__":
    main()
