import math
import random

def generate_rl_training_curves(episodes=300):
    """
    Synthesize mathematical RL convergence curves matching a standard DQN architecture.
    - Loss: exponential decay + noise
    - Reward: logarithmic growth + noise
    - Epsilon: standard exponential decay
    """
    data = []
    
    # Starting parameters
    epsilon = 1.0
    epsilon_min = 0.05
    decay_rate = 0.015
    
    for ep in range(1, episodes + 1):
        # Epsilon Decay
        epsilon = max(epsilon_min, epsilon * math.exp(-decay_rate))
        
        # Reward (Converging towards ~98 with some volatility)
        base_reward = 20 + 80 * (1 - math.exp(-0.01 * ep))
        reward_noise = random.uniform(-10, 15) if ep < 150 else random.uniform(-2, 5)
        reward = min(100, max(0, base_reward + reward_noise))
        
        # Loss (Converging downwards)
        base_loss = 2.5 * math.exp(-0.015 * ep)
        loss_noise = random.uniform(0, 0.4) if ep < 100 else random.uniform(0, 0.1)
        loss = max(0, base_loss + loss_noise)
        
        data.append({
            "episode": ep,
            "reward": round(reward, 2),
            "loss": round(loss, 4),
            "epsilon": round(epsilon, 3),
            "total_steps": ep * random.randint(450, 550) # Approx 500 steps per episode
        })
        
    return data

def generate_performance_metrics(latency_ms=2.5, queue_size=10):
    """Generate dynamic system performance statistics."""
    return {
        "avg_latency_ms": round(latency_ms + random.uniform(-0.5, 0.5), 2),
        "throughput_eps": random.randint(1900, 2100),
        "active_queue": queue_size + random.randint(-5, 5),
        "total_uptime_hrs": 12.4
    }
