# Autonomous Multi-Layer Cyber Defense System Using Deep Learning, UEBA, and Reinforcement Learning

An AI-driven cybersecurity platform that performs real-time intrusion detection, user behavior analytics, and autonomous threat response using deep learning and reinforcement learning.

---

## Architecture

The system follows a **5-layer modular architecture**:

1. **Data Ingestion Layer** — Processes raw network traffic (CICIDS2017 dataset)
2. **Detection (Perception) Layer** — Autoencoder + Isolation Forest anomaly detection
3. **User Behavior Analytics Layer** — GMM-based behavioral profiling & risk scoring
4. **Decision (RL) Layer** — DQN agent for autonomous defense action selection
5. **Response & Audit Layer** — Real-time alerting, logging, and explainability

---

## Project Structure

```
AIML/
├── data/
│   ├── raw/CICIDS2017/              # Source dataset (8 CSV files)
│   ├── processed/                   # Train/test Parquet splits
│   └── features/                    # Scaler + selected features
│
├── models/                          # Trained model weights
│   ├── isolation_forest.pkl
│   ├── autoencoder_v2.pt
│   ├── data_conditioner.pkl
│   ├── ueba_gmm.pkl
│   └── rl_policy_model.pt
│
├── reports/
│   ├── figures/                     # Confusion matrices, ROC, training curves
│   └── logs/                        # Real-time IDS & UEBA alert logs
│
├── src/
│   ├── data/
│   │   └── preprocess_cicids2017.py # Phase 1.1: Data engineering pipeline
│   │
│   ├── models/
│   │   ├── ids_core_pipeline.py     # Phase 1.2: Baseline IDS models
│   │   └── ids_autoencoder_v2.py    # Phase 1.3: Improved Autoencoder
│   │
│   ├── pipeline/
│   │   ├── stream_simulator.py      # Phase 2: Stream data simulation
│   │   ├── preprocessor.py          # Phase 2: Real-time preprocessing
│   │   ├── inference_engine.py      # Phase 2: Low-latency inference
│   │   ├── alert_system.py          # Phase 2: Color-coded alerting
│   │   └── run_realtime_ids.py      # Phase 2: Main IDS runner
│   │
│   ├── ueba/
│   │   ├── user_simulator.py        # Phase 3: Synthetic user generation
│   │   ├── feature_engineering.py   # Phase 3: Behavioral feature extraction
│   │   ├── clustering_model.py      # Phase 3: GMM profiling
│   │   ├── risk_engine.py           # Phase 3: Composite risk scoring
│   │   └── ueba_pipeline.py         # Phase 3: UEBA runner
│   │
│   └── rl/
│       ├── environment.py           # Phase 4: Cyber defense MDP
│       ├── dqn_agent.py             # Phase 4: DQN with target network
│       └── train_rl.py              # Phase 4: Training & evaluation
│
├── project.md                       # Research document & literature survey
├── .gitignore
└── README.md
```

---

## Results Summary

| Component | Metric | Value |
|-----------|--------|-------|
| **Autoencoder IDS (v2)** | F1-Score | 0.748 |
| **Autoencoder IDS (v2)** | Recall | 0.818 |
| **Isolation Forest** | F1-Score | 0.627 |
| **UEBA Risk Engine** | Insider Detection | 15/15 threats identified |
| **RL Decision Engine** | F1-Score | ~0.97 |
| **Real-Time Pipeline** | Throughput | 701 samples/sec |
| **Real-Time Pipeline** | Latency | <1ms per sample |

---

## How to Run

### 1. Setup Environment
```bash
cd AIML
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install pandas numpy scikit-learn joblib pyarrow torch matplotlib seaborn
```

### 2. Phase 1 — Data Preprocessing & IDS Training
```bash
python src/data/preprocess_cicids2017.py
python src/models/ids_core_pipeline.py
python src/models/ids_autoencoder_v2.py
```

### 3. Phase 2 — Real-Time IDS Pipeline
```bash
python src/pipeline/run_realtime_ids.py
python src/pipeline/run_realtime_ids.py --mode single --delay 0.05 --limit 500
```

### 4. Phase 3 — UEBA System
```bash
python src/ueba/ueba_pipeline.py
```

### 5. Phase 4 — RL Decision Engine
```bash
python src/rl/train_rl.py
python src/rl/train_rl.py --episodes 500
```

---

## Tech Stack

- **Python 3.10** — Core language
- **PyTorch** — Deep learning (Autoencoder, DQN)
- **Scikit-Learn** — Isolation Forest, GMM, preprocessing
- **Pandas / NumPy** — Data engineering
- **Matplotlib / Seaborn** — Visualization
- **Apache Parquet** — Efficient data serialization

---

## Dataset

**CICIDS2017** — Canadian Institute for Cybersecurity Intrusion Detection Dataset
- 2.8M+ network flow records
- 80+ features per flow
- Attack types: DDoS, PortScan, Web Attacks, Infiltration, Botnet

---

## References

See `project.md` for the complete literature survey (2020–2025) covering:
- Transformer-based IDS architectures
- Adversarial ML defense mechanisms
- Multi-Agent Reinforcement Learning for cyber defense
- Explainable AI (SHAP/LIME) in cybersecurity
