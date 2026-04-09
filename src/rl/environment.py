"""
Cyber Defense Environment v2 — Progressive Defense Rewards.

Key changes from v1:
  1. Alert reward raised (+7 for attacks, -1 for benign) to make it viable
  2. Uncertainty-aware zone (0.3-0.7 signals) penalizes skipping Alert
  3. Aggression penalty: cumulative cost for excessive Block/Isolate
  4. Proportional response: Isolate only justified for high-severity events
  5. Previous action tracking enables escalation bonuses
"""

import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

ACTION_NAMES = {0: 'MONITOR', 1: 'ALERT', 2: 'BLOCK_IP', 3: 'ISOLATE_USER'}
ACTION_SEVERITY = {0: 0.0, 1: 0.2, 2: 0.6, 3: 1.0}


class CyberDefenseEnv:
    """
    Gym-style cyber defense environment with progressive defense rewards.
    Tracks previous actions to reward escalation patterns.
    """

    def __init__(self, n_episodes_events: int = 500, attack_ratio: float = 0.25,
                 seed: int = 42):
        self.n_events = n_episodes_events
        self.attack_ratio = attack_ratio
        self.rng = np.random.default_rng(seed)

        self.state_dim = 4
        self.action_dim = 4

        # Episode state
        self.current_step = 0
        self.events = None
        self.ground_truth = None
        self.done = False

        # Progressive defense tracking
        self.prev_action = 0
        self.aggressive_action_count = 0  # Tracks Block+Isolate frequency

    def reset(self) -> np.ndarray:
        """Reset environment and generate a new episode."""
        self.current_step = 0
        self.done = False
        self.prev_action = 0
        self.aggressive_action_count = 0

        n_attacks = int(self.n_events * self.attack_ratio)
        n_benign = self.n_events - n_attacks

        labels = np.array([1] * n_attacks + [0] * n_benign)
        self.rng.shuffle(labels)
        self.ground_truth = labels

        self.events = np.zeros((self.n_events, self.state_dim))

        for i in range(self.n_events):
            if labels[i] == 1:
                anomaly_score      = np.clip(self.rng.beta(5, 2), 0, 1)
                user_risk_score    = np.clip(self.rng.beta(4, 3), 0, 1)
                activity_intensity = np.clip(self.rng.beta(6, 2), 0, 1)
                time_context       = self.rng.uniform(0, 1)
            else:
                anomaly_score      = np.clip(self.rng.beta(2, 6), 0, 1)
                user_risk_score    = np.clip(self.rng.beta(2, 7), 0, 1)
                activity_intensity = np.clip(self.rng.beta(2, 4), 0, 1)
                time_context       = np.clip(self.rng.beta(5, 2), 0, 1)

            self.events[i] = [anomaly_score, user_risk_score,
                              activity_intensity, time_context]

        return self.events[0]

    def step(self, action: int):
        assert 0 <= action < self.action_dim

        true_label = self.ground_truth[self.current_step]
        state = self.events[self.current_step]
        reward = self._compute_reward(action, true_label, state)

        # Track action history
        self.prev_action = action
        if action >= 2:
            self.aggressive_action_count += 1

        self.current_step += 1
        self.done = self.current_step >= self.n_events

        next_state = self.events[self.current_step] if not self.done else np.zeros(self.state_dim)

        info = {
            'true_label': true_label,
            'action_name': ACTION_NAMES[action],
            'step': self.current_step
        }

        return next_state, reward, self.done, info

    def _compute_reward(self, action: int, true_label: int, state: np.ndarray) -> float:
        """
        Progressive defense reward function.
        
        Design principles:
          1. Alert is a VALID response to attacks (rewarded well)
          2. In the uncertainty zone (signals 0.3-0.7), Alert > Block
          3. Block/Isolate require HIGH confidence signals to be justified
          4. Cumulative aggression penalty discourages trigger-happy policies
          5. Escalation bonus: Alert→Block sequence gets rewarded
        """
        anomaly = state[0]
        risk = state[1]
        threat_signal = (anomaly + risk) / 2.0  # Combined confidence
        is_attack = true_label == 1

        reward = 0.0

        if is_attack:
            if action == 0:
                # MISSED ATTACK — worst outcome
                reward = -15.0
            elif action == 1:
                # ALERT on attack — valid early detection response
                # Boosted from +5 to +7 to make it competitive with Block
                reward = 7.0
            elif action == 2:
                # BLOCK attack — strong response
                reward = 10.0
                # Escalation bonus: if previous action was Alert, reward coordination
                if self.prev_action == 1:
                    reward += 2.0
            elif action == 3:
                # ISOLATE — only justified for severe threats
                if threat_signal > 0.7:
                    reward = 12.0  # High-confidence severe → full reward
                    if self.prev_action == 1:
                        reward += 2.0  # Escalation bonus
                else:
                    reward = 6.0   # Low-confidence → reduced (overkill)
        else:
            if action == 0:
                # Correctly pass benign traffic
                reward = 2.0
            elif action == 1:
                # Alert on benign — very mild penalty (it's just an alert)
                # Reduced from -3.0 to -1.0 so the agent isn't scared of alerting
                reward = -1.0
            elif action == 2:
                # Block benign — real disruption
                reward = -8.0
            elif action == 3:
                # Isolate benign — severe self-inflicted DoS
                reward = -12.0

        # ---- Uncertainty-Aware Penalty ----
        # In the "gray zone" (signals 0.3–0.7), aggressive actions without
        # prior Alert are penalized. The agent should investigate first.
        if 0.3 <= threat_signal <= 0.7:
            if action >= 2 and self.prev_action != 1:
                # Jumped straight to Block/Isolate without Alerting first
                reward -= 3.0

        # ---- Cumulative Aggression Penalty ----
        # If the agent is using Block/Isolate too frequently, apply a small
        # friction cost. This models operational fatigue / availability loss.
        if action >= 2:
            aggression_rate = self.aggressive_action_count / max(self.current_step + 1, 1)
            if aggression_rate > 0.4:  # More than 40% aggressive actions
                reward -= 1.5

        return reward

    def get_state_dim(self) -> int:
        return self.state_dim

    def get_action_dim(self) -> int:
        return self.action_dim
