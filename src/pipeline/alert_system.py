"""
Alert System — Handles real-time threat notifications and audit logging.
Prints color-coded console alerts and writes persistent logs to disk.
"""

import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


# ANSI color codes for terminal output
class Colors:
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"


class AlertSystem:
    """
    Real-time alert handler for the IDS pipeline.
    Outputs color-coded terminal alerts and logs all events to an audit file.
    """
    def __init__(self, log_dir: str):
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"ids_alerts_{timestamp}.log")
        
        # Dedicated file logger (separate from console)
        self.file_logger = logging.getLogger("AlertAudit")
        self.file_logger.setLevel(logging.INFO)
        fh = logging.FileHandler(self.log_file)
        fh.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
        self.file_logger.addHandler(fh)
        
        # Counters
        self.total_processed = 0
        self.total_alerts = 0
        self.total_normal = 0
        
        logging.info(f"Alert System initialized. Logging to: {self.log_file}")

    def process_result(self, prediction: int, score: float, latency_ms: float, 
                       true_label: int = -1, sample_id: int = -1):
        """
        Handle a single inference result — print to console and log to file.
        """
        self.total_processed += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        if prediction == 1:
            # ---- ATTACK DETECTED ----
            self.total_alerts += 1
            
            # Color-coded console output
            label_check = ""
            if true_label != -1:
                is_correct = "✓ TRUE POSITIVE" if true_label == 1 else "✗ FALSE POSITIVE"
                label_check = f" | {is_correct}"
            
            print(
                f"{Colors.RED}{Colors.BOLD}[ALERT]{Colors.RESET} "
                f"{Colors.RED}Anomaly detected!{Colors.RESET} "
                f"Score: {score:.6f} | "
                f"Latency: {latency_ms:.1f}ms | "
                f"Time: {timestamp}"
                f"{label_check}"
            )
            
            # Persistent log
            self.file_logger.info(
                f"ALERT | sample={sample_id} | score={score:.6f} | "
                f"latency={latency_ms:.1f}ms | true_label={true_label}"
            )
        else:
            # ---- NORMAL TRAFFIC ----
            self.total_normal += 1
            
            # Only print every 100th normal sample to avoid console flood
            if self.total_processed % 100 == 0:
                print(
                    f"{Colors.GREEN}[INFO]{Colors.RESET} "
                    f"Normal traffic (#{self.total_processed:,}) | "
                    f"Score: {score:.6f} | "
                    f"Latency: {latency_ms:.1f}ms"
                )

    def print_summary(self):
        """Print final session statistics."""
        alert_rate = (self.total_alerts / max(self.total_processed, 1)) * 100
        
        print(f"\n{'='*60}")
        print(f"{Colors.CYAN}{Colors.BOLD}  IDS SESSION SUMMARY{Colors.RESET}")
        print(f"{'='*60}")
        print(f"  Total Packets Processed : {self.total_processed:,}")
        print(f"  {Colors.RED}Alerts (Anomalies)      : {self.total_alerts:,}{Colors.RESET}")
        print(f"  {Colors.GREEN}Normal Traffic          : {self.total_normal:,}{Colors.RESET}")
        print(f"  Alert Rate              : {alert_rate:.2f}%")
        print(f"  Log File                : {self.log_file}")
        print(f"{'='*60}\n")
        
        self.file_logger.info(
            f"SESSION END | total={self.total_processed} | "
            f"alerts={self.total_alerts} | normal={self.total_normal} | "
            f"alert_rate={alert_rate:.2f}%"
        )
