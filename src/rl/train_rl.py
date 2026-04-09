"""
Phase 4.1 — Progressive Defense RL Training Pipeline
======================================================
Trains the DQN with the v2 reward function that encourages:
  - Alert as a meaningful intermediate action
  - Escalation patterns (Alert → Block)
  - Proportional response in uncertainty zones

Compares v1 (aggressive) vs v2 (progressive) action distributions.

Usage:
  python src/rl/train_rl.py
  python src/rl/train_rl.py --episodes 400
"""

import os
import sys
import argparse
import logging
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.rl.environment import CyberDefenseEnv, ACTION_NAMES
from src.rl.dqn_agent import DQNAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def train(agent: DQNAgent, env: CyberDefenseEnv, n_episodes: int):
    """Training loop."""
    logging.info(f"Training DQN for {n_episodes} episodes...")

    episode_rewards = []
    episode_losses = []
    action_counts_history = []

    for ep in range(n_episodes):
        state = env.reset()
        total_reward = 0.0
        total_loss = 0.0
        loss_steps = 0
        action_counts = {a: 0 for a in range(env.action_dim)}

        while True:
            action = agent.select_action(state, training=True)
            next_state, reward, done, info = env.step(action)

            agent.store_transition(state, action, reward, next_state, done)
            loss = agent.learn()

            total_reward += reward
            if loss > 0:
                total_loss += loss
                loss_steps += 1
            action_counts[action] += 1

            state = next_state
            if done:
                break

        agent.decay_epsilon()
        episode_rewards.append(total_reward)
        avg_loss = total_loss / max(loss_steps, 1)
        episode_losses.append(avg_loss)
        action_counts_history.append(action_counts.copy())

        if (ep + 1) % 25 == 0 or ep == 0:
            total_actions = sum(action_counts.values())
            pcts = {ACTION_NAMES[a]: f"{action_counts[a]/total_actions*100:.1f}%" 
                    for a in range(4)}
            logging.info(
                f"Ep {ep+1:4d}/{n_episodes} | "
                f"Reward: {total_reward:8.1f} | "
                f"Loss: {avg_loss:.4f} | "
                f"Eps: {agent.epsilon:.3f} | "
                f"M={pcts['MONITOR']} A={pcts['ALERT']} "
                f"B={pcts['BLOCK_IP']} I={pcts['ISOLATE_USER']}"
            )

    return episode_rewards, episode_losses, action_counts_history


def evaluate(agent: DQNAgent, env: CyberDefenseEnv, n_episodes: int = 20):
    """Evaluate trained policy."""
    logging.info(f"\nEvaluating policy over {n_episodes} episodes...")

    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_tn = 0
    total_reward = 0
    action_dist = {a: 0 for a in range(env.action_dim)}

    for ep in range(n_episodes):
        state = env.reset()
        ep_reward = 0

        for step in range(env.n_events):
            action = agent.select_action(state, training=False)
            next_state, reward, done, info = env.step(action)

            true_label = info['true_label']
            acted = action > 0

            if true_label == 1 and acted:
                total_tp += 1
            elif true_label == 0 and acted:
                total_fp += 1
            elif true_label == 1 and not acted:
                total_fn += 1
            else:
                total_tn += 1

            action_dist[action] += 1
            ep_reward += reward
            state = next_state
            if done:
                break

        total_reward += ep_reward

    total = total_tp + total_fp + total_fn + total_tn
    precision = total_tp / max(total_tp + total_fp, 1)
    recall    = total_tp / max(total_tp + total_fn, 1)
    f1        = 2 * precision * recall / max(precision + recall, 1e-8)

    print(f"\n{CYAN}{BOLD}{'='*60}")
    print(f"  RL POLICY EVALUATION (Progressive Defense v2)")
    print(f"{'='*60}{RESET}")
    print(f"  Episodes           : {n_episodes}")
    print(f"  Avg Reward/Episode : {total_reward / n_episodes:.1f}")
    print(f"  {GREEN}True Positives (TP)  : {total_tp:,}{RESET}")
    print(f"  {RED}False Positives (FP) : {total_fp:,}{RESET}")
    print(f"  {RED}False Negatives (FN) : {total_fn:,}{RESET}")
    print(f"  {GREEN}True Negatives (TN)  : {total_tn:,}{RESET}")
    print(f"  Precision          : {precision:.4f}")
    print(f"  Recall             : {recall:.4f}")
    print(f"  F1-Score           : {f1:.4f}")
    print(f"\n  Action Distribution:")
    for a, count in action_dist.items():
        pct = count / max(total, 1) * 100
        bar = '#' * int(pct / 2)
        print(f"    {ACTION_NAMES[a]:15s}: {count:6,} ({pct:5.1f}%) {bar}")
    print(f"{'='*60}\n")

    return {
        'precision': precision, 'recall': recall, 'f1': f1,
        'avg_reward': total_reward / n_episodes,
        'action_dist': action_dist
    }


def plot_training(rewards, losses, action_history, plot_dir):
    """Generate training visualizations."""
    os.makedirs(plot_dir, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 1. Reward Curve
    ax = axes[0]
    ax.plot(rewards, alpha=0.3, color='#3498db', label='Raw Reward')
    window = min(25, max(len(rewards) // 4, 2))
    if window > 1 and len(rewards) >= window:
        ma = np.convolve(rewards, np.ones(window)/window, mode='valid')
        ax.plot(range(window-1, len(rewards)), ma, color='#2c3e50', linewidth=2,
                label=f'{window}-ep Moving Avg')
    ax.set_xlabel('Episode')
    ax.set_ylabel('Total Reward')
    ax.set_title('Training Reward Curve', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)

    # 2. Loss Curve
    ax = axes[1]
    ax.plot(losses, alpha=0.4, color='#e74c3c', label='Avg Loss')
    if window > 1 and len(losses) >= window:
        ma_loss = np.convolve(losses, np.ones(window)/window, mode='valid')
        ax.plot(range(window-1, len(losses)), ma_loss, color='#c0392b', linewidth=2,
                label=f'{window}-ep Moving Avg')
    ax.set_xlabel('Episode')
    ax.set_ylabel('Loss')
    ax.set_title('Training Loss Curve', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)

    # 3. Action Distribution Over Training (stacked area)
    ax = axes[2]
    action_names = list(ACTION_NAMES.values())
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#9b59b6']
    
    n_eps = len(action_history)
    chunk_size = max(1, n_eps // 20)
    chunks = []
    for i in range(0, n_eps, chunk_size):
        chunk = action_history[i:i+chunk_size]
        agg = {a: sum(c[a] for c in chunk) for a in range(4)}
        total = sum(agg.values())
        chunks.append({ACTION_NAMES[a]: agg[a]/max(total,1)*100 for a in range(4)})

    x = range(len(chunks))
    bottom = np.zeros(len(chunks))

    for i, name in enumerate(action_names):
        vals = [c[name] for c in chunks]
        ax.bar(x, vals, bottom=bottom, color=colors[i], label=name, alpha=0.85)
        bottom += np.array(vals)

    ax.set_xlabel(f'Training Progress (chunks of {chunk_size} eps)')
    ax.set_ylabel('Action %')
    ax.set_title('Action Distribution Over Training', fontsize=13, fontweight='bold')
    ax.legend(fontsize=8, loc='upper right')

    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, 'rl_training_curves.png'), dpi=150)
    plt.close()

    # 4. Before vs After comparison chart
    v1_dist = {'MONITOR': 51.0, 'ALERT': 0.1, 'BLOCK_IP': 24.2, 'ISOLATE_USER': 24.7}
    
    # Get final-epoch distribution from training
    last_chunk = action_history[-max(1, n_eps//10):]
    agg_final = {a: sum(c[a] for c in last_chunk) for a in range(4)}
    total_final = sum(agg_final.values())
    v2_dist = {ACTION_NAMES[a]: agg_final[a]/max(total_final,1)*100 for a in range(4)}

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    bar_colors = ['#2ecc71', '#3498db', '#e74c3c', '#9b59b6']
    action_labels = list(ACTION_NAMES.values())

    # v1
    ax = axes[0]
    v1_vals = [v1_dist[n] for n in action_labels]
    bars = ax.bar(action_labels, v1_vals, color=bar_colors, alpha=0.85, edgecolor='white')
    for bar, val in zip(bars, v1_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{val:.1f}%', ha='center', fontweight='bold', fontsize=10)
    ax.set_ylabel('Action %')
    ax.set_title('BEFORE (v1): Aggressive Policy', fontsize=13, fontweight='bold', color='#c0392b')
    ax.set_ylim(0, max(v1_vals) * 1.2)

    # v2
    ax = axes[1]
    v2_vals = [v2_dist[n] for n in action_labels]
    bars = ax.bar(action_labels, v2_vals, color=bar_colors, alpha=0.85, edgecolor='white')
    for bar, val in zip(bars, v2_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{val:.1f}%', ha='center', fontweight='bold', fontsize=10)
    ax.set_ylabel('Action %')
    ax.set_title('AFTER (v2): Progressive Policy', fontsize=13, fontweight='bold', color='#27ae60')
    ax.set_ylim(0, max(max(v2_vals), max(v1_vals)) * 1.2)

    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, 'rl_before_vs_after.png'), dpi=150)
    plt.close()

    logging.info(f"Training + comparison plots saved to {plot_dir}")


def main():
    parser = argparse.ArgumentParser(description="Phase 4.1: Progressive Defense RL Training")
    parser.add_argument('--episodes', type=int, default=300, help='Training episodes')
    parser.add_argument('--events', type=int, default=500, help='Events per episode')
    parser.add_argument('--eval_episodes', type=int, default=20, help='Evaluation episodes')
    args = parser.parse_args()

    MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
    PLOTS_DIR  = os.path.join(PROJECT_ROOT, "reports", "figures")

    env = CyberDefenseEnv(n_episodes_events=args.events, attack_ratio=0.25, seed=42)
    agent = DQNAgent(
        state_dim=env.get_state_dim(),
        action_dim=env.get_action_dim(),
        lr=5e-4,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay=0.993,   # Slower decay → more exploration of Alert
        batch_size=64,
        target_update_freq=10
    )

    # Train
    rewards, losses, action_history = train(agent, env, n_episodes=args.episodes)

    # Save
    model_path = os.path.join(MODELS_DIR, "rl_policy_model.pt")
    agent.save(model_path)

    # Evaluate
    eval_env = CyberDefenseEnv(n_episodes_events=args.events, attack_ratio=0.25, seed=99)
    metrics = evaluate(agent, eval_env, n_episodes=args.eval_episodes)

    # Plots
    plot_training(rewards, losses, action_history, PLOTS_DIR)

    logging.info("Phase 4.1 — Progressive Defense RL Complete!")


if __name__ == "__main__":
    main()
