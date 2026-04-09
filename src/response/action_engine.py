"""
Action Engine — Executes RL agent decisions.

Simulates cybersecurity defense actions (Block IP, Isolate User)
while maintaining state (preventing duplicate actions/spam).
Writes permanent audit logs to a response log file.
"""

import os
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# ANSI colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


class ActionEngine:
    """
    Executes RL defense decisions safely.
    Maintains active sets of blocked IPs and isolated users to prevent duplicate actions.
    """
    
    ACTION_MAP = {
        0: 'MONITOR',
        1: 'ALERT',
        2: 'BLOCK_IP',
        3: 'ISOLATE_USER'
    }

    def __init__(self, log_dir: str, cooldown_sec: int = 60):
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "response_logs.txt")
        self.cooldown_sec = cooldown_sec

        # State tracking (entity -> timestamp of action)
        self.blocked_ips = {}
        self.isolated_users = {}

        # Write log header
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Response Engine Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*70}\n")

    def _log_to_file(self, action_name: str, ip: str, user_id: str, score: float, message: str):
        """Append a standardized entry to the response audit log."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] Action={action_name:<12} | IP={ip:<15} | User={user_id:<10} | Score={score:.2f} | {message}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def execute(self, action_id: int, ip: str, user_id: str, threat_score: float):
        """
        Execute the defense action mapped to action_id.
        
        Args:
            action_id: 0(Monitor), 1(Alert), 2(Block IP), 3(Isolate User)
            ip: Target IP address
            user_id: Target internal user ID
            threat_score: Combined threat signal (for logging justification)
        """
        action_name = self.ACTION_MAP.get(action_id, 'UNKNOWN')
        now = time.time()

        if action_id == 0:
            # MONITOR
            self._log_to_file(action_name, ip, user_id, threat_score, "Monitored benign traffic.")
            return

        elif action_id == 1:
            # ALERT
            msg = f"User/IP showing suspicious activity."
            self._log_to_file(action_name, ip, user_id, threat_score, msg)
            print(f"{YELLOW}[ALERT]     | IP: {ip} | User: {user_id} | Threat: {threat_score:.2f} | Suspicious activity detected.{RESET}")
            return

        elif action_id == 2:
            # BLOCK IP
            # Check safety cooldown
            last_block = self.blocked_ips.get(ip, 0)
            if now - last_block < self.cooldown_sec:
                self._log_to_file("BLOCK_SKIP", ip, user_id, threat_score, "Cooldown active. Skipped duplicate IP block.")
                return

            self.blocked_ips[ip] = now
            msg = "Firewall rule applied to block IP."
            self._log_to_file(action_name, ip, user_id, threat_score, msg)
            print(f"{RED}{BOLD}[RESPONSE]  | IP: {ip} blocked by Firewall!{RESET}")
            return

        elif action_id == 3:
            # ISOLATE USER
            # Check safety cooldown
            last_isolation = self.isolated_users.get(user_id, 0)
            if now - last_isolation < self.cooldown_sec:
                self._log_to_file("ISOLATE_SKIP", ip, user_id, threat_score, "Cooldown active. Skipped duplicate User isolation.")
                return

            self.isolated_users[user_id] = now
            msg = "Account locked and endpoint isolated."
            self._log_to_file(action_name, ip, user_id, threat_score, msg)
            print(f"{MAGENTA}{BOLD}[RESPONSE]  | User: {user_id} isolated from domain!{RESET}")
            return

        else:
            logging.error(f"Unknown action ID: {action_id}")
