"""
Deep Q-Network (DQN) Agent — Autonomous Blue Team Defender.

Implements a DQN with:
  - Experience Replay (uniform sampling from past transitions)
  - Target Network (stabilizes Q-value estimates)
  - Epsilon-Greedy exploration (decays over training)

Architecture is deliberately lightweight for fast inference 
in a real-time pipeline (sub-1ms per decision).
"""

import os
import logging
import numpy as np
from collections import deque
import random

import torch
import torch.nn as nn
import torch.optim as optim

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class QNetwork(nn.Module):
    """
    Lightweight feedforward Q-network.
    Maps state → Q-values for each action.
    """
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_dim)
        )
        # Xavier init
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        return self.net(x)


class ReplayBuffer:
    """Fixed-size FIFO buffer storing (s, a, r, s', done) transitions."""
    def __init__(self, capacity: int = 50_000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32)
        )

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    """
    DQN Agent with target network and epsilon-greedy exploration.
    """
    def __init__(self, state_dim: int, action_dim: int,
                 lr: float = 1e-3,
                 gamma: float = 0.99,
                 epsilon_start: float = 1.0,
                 epsilon_end: float = 0.05,
                 epsilon_decay: float = 0.995,
                 batch_size: int = 64,
                 target_update_freq: int = 10,
                 buffer_capacity: int = 50_000):

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq

        # Epsilon schedule
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay

        # Networks
        self.policy_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        self.criterion = nn.SmoothL1Loss()  # Huber loss for stability

        # Replay buffer
        self.memory = ReplayBuffer(buffer_capacity)

        # Training stats
        self.train_steps = 0

        logging.info(f"DQN Agent initialized on {self.device}")
        logging.info(f"  State dim: {state_dim} | Action dim: {action_dim}")
        params = sum(p.numel() for p in self.policy_net.parameters())
        logging.info(f"  Network parameters: {params:,}")

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """Epsilon-greedy action selection."""
        if training and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)

        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax(dim=1).item()

    def store_transition(self, state, action, reward, next_state, done):
        """Store a transition in replay memory."""
        self.memory.push(state, action, reward, next_state, done)

    def learn(self):
        """Sample a batch from replay buffer and perform one gradient step."""
        if len(self.memory) < self.batch_size:
            return 0.0

        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)

        states_t      = torch.FloatTensor(states).to(self.device)
        actions_t     = torch.LongTensor(actions).to(self.device)
        rewards_t     = torch.FloatTensor(rewards).to(self.device)
        next_states_t = torch.FloatTensor(next_states).to(self.device)
        dones_t       = torch.FloatTensor(dones).to(self.device)

        # Current Q-values for chosen actions
        q_values = self.policy_net(states_t).gather(1, actions_t.unsqueeze(1)).squeeze(1)

        # Target Q-values (from frozen target network)
        with torch.no_grad():
            next_q_values = self.target_net(next_states_t).max(1)[0]
            target_q = rewards_t + self.gamma * next_q_values * (1 - dones_t)

        loss = self.criterion(q_values, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=1.0)
        self.optimizer.step()

        self.train_steps += 1

        # Periodically sync target network
        if self.train_steps % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        return loss.item()

    def decay_epsilon(self):
        """Decay exploration rate."""
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def save(self, path: str):
        """Save the trained policy network."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.policy_net.state_dict(), path)
        logging.info(f"Policy model saved to {path}")

    def load(self, path: str):
        """Load a trained policy network."""
        self.policy_net.load_state_dict(
            torch.load(path, map_location=self.device, weights_only=True)
        )
        self.policy_net.eval()
        logging.info(f"Policy model loaded from {path}")
