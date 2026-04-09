"""
UEBA Pipeline — Phase 3 Orchestrator
======================================
End-to-end pipeline that:
  1. Simulates user activity data
  2. Engineers behavioral features per user
  3. Clusters normal behavior (GMM)
  4. Scores anomalies and assigns risk levels
  5. Generates alerts and logs

Usage:
  python src/ueba/ueba_pipeline.py
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.ueba.user_simulator import UserActivitySimulator
from src.ueba.feature_engineering import UEBAFeatureEngineer
from src.ueba.clustering_model import BehavioralClusterModel
from src.ueba.risk_engine import RiskEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# ANSI colors
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def generate_alerts(risk_df: pd.DataFrame, log_dir: str):
    """Print color-coded UEBA alerts and write to log file."""
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "ueba_logs.txt")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"UEBA Alert Log — Generated: {timestamp}\n")
        f.write("=" * 70 + "\n\n")
        
        high_risk = risk_df[risk_df['risk_level'] == 'HIGH_RISK'].sort_values('risk_score', ascending=False)
        suspicious = risk_df[risk_df['risk_level'] == 'SUSPICIOUS'].sort_values('risk_score', ascending=False)
        
        # High risk alerts
        print(f"\n{RED}{BOLD}{'='*60}")
        print(f"  🚨 HIGH RISK USERS ({len(high_risk)})")
        print(f"{'='*60}{RESET}")
        
        for _, row in high_risk.iterrows():
            gt = "✓ CONFIRMED THREAT" if row['is_threat_ground_truth'] else "✗ FALSE POSITIVE"
            alert = (
                f"[UEBA ALERT] {row['user_id']} flagged "
                f"(risk={row['risk_score']:.2f}) | "
                f"Cluster: {row['cluster_deviation_score']:.2f} | "
                f"Spike: {row['activity_spike_score']:.2f} | "
                f"Time: {row['time_anomaly_score']:.2f} | "
                f"{gt}"
            )
            print(f"  {RED}{alert}{RESET}")
            f.write(alert + "\n")
        
        # Suspicious alerts
        print(f"\n{YELLOW}{BOLD}{'='*60}")
        print(f"  ⚠️  SUSPICIOUS USERS ({len(suspicious)})")
        print(f"{'='*60}{RESET}")
        
        for _, row in suspicious.iterrows():
            gt = "✓ CONFIRMED" if row['is_threat_ground_truth'] else "—"
            alert = (
                f"[UEBA WATCH] {row['user_id']} under review "
                f"(risk={row['risk_score']:.2f}) | {gt}"
            )
            print(f"  {YELLOW}{alert}{RESET}")
            f.write(alert + "\n")
        
        # Normal summary
        normal_count = (risk_df['risk_level'] == 'NORMAL').sum()
        print(f"\n{GREEN}  ✅ {normal_count} users classified as NORMAL{RESET}")
        f.write(f"\n{normal_count} users classified as NORMAL\n")
    
    logging.info(f"UEBA alerts written to: {log_path}")


def plot_results(risk_df: pd.DataFrame, user_features: pd.DataFrame, 
                 feature_cols: list, gmm_scores: np.ndarray, plot_dir: str):
    """Generate improved UEBA visualization plots."""
    os.makedirs(plot_dir, exist_ok=True)
    
    # 1. Risk Score Distribution (bar chart)
    plt.figure(figsize=(9, 5))
    colors = {'NORMAL': '#2ecc71', 'SUSPICIOUS': '#f39c12', 'HIGH_RISK': '#e74c3c'}
    for level, color in colors.items():
        mask = risk_df['risk_level'] == level
        subset = risk_df[mask]
        if len(subset) > 0:
            plt.bar(subset['user_id'], subset['risk_score'], color=color, label=level, alpha=0.85)
    
    plt.axhline(y=0.3, color='orange', linestyle='--', linewidth=1, label='Suspicious Threshold')
    plt.axhline(y=0.7, color='red', linestyle='--', linewidth=1, label='High Risk Threshold')
    plt.xlabel('User ID')
    plt.ylabel('Risk Score')
    plt.title('UEBA Risk Scores per User', fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=8)
    plt.xticks(rotation=90, fontsize=5)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, 'ueba_risk_scores.png'), dpi=150)
    plt.close()
    
    # 2. Risk Components Heatmap (top 30)
    top_risky = risk_df.nlargest(30, 'risk_score')
    heatmap_data = top_risky[['cluster_deviation_score', 'activity_spike_score', 'time_anomaly_score']]
    heatmap_data.index = top_risky['user_id'].values
    
    plt.figure(figsize=(8, 10))
    sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='YlOrRd', cbar_kws={'label': 'Score'})
    plt.title('Risk Component Breakdown - Top 30 Riskiest Users', fontsize=13, fontweight='bold')
    plt.ylabel('User ID')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, 'ueba_risk_heatmap.png'), dpi=150)
    plt.close()
    
    # ================================================================
    # 3. IMPROVED GMM Anomaly Score Visualization (3-panel figure)
    # ================================================================
    # 
    # Why log1p? GMM negative log-likelihood scores are heavily
    # right-skewed. Raw values compress normal users near zero and
    # push anomalies off-scale. log1p(x) = ln(1 + x) compresses
    # the tail while preserving order and keeping zero at zero.
    # This is preferred over StandardScaler (loses interpretability)
    # or MinMax (still distorted by extreme outliers).
    # ================================================================
    
    is_threat = user_features['is_threat'].values
    normal_raw  = gmm_scores[is_threat == 0]
    threat_raw  = gmm_scores[is_threat == 1]
    
    # Shift scores to be >= 0 (needed for log1p), then transform
    shift = gmm_scores.min()
    scores_shifted = gmm_scores - shift  # now all >= 0
    scores_log = np.log1p(scores_shifted)
    
    normal_log  = scores_log[is_threat == 0]
    threat_log  = scores_log[is_threat == 1]
    
    # Auto-calculate a visual threshold (midpoint between group medians)
    threshold_log = (np.median(normal_log) + np.median(threat_log)) / 2
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle('GMM Anomaly Score Analysis — Normal vs Threat Users', 
                 fontsize=15, fontweight='bold', y=1.02)
    
    # --- Panel A: KDE Distribution ---
    ax = axes[0]
    sns.kdeplot(normal_log, ax=ax, color='#2ecc71', fill=True, alpha=0.4, 
                linewidth=2, label=f'Normal (n={len(normal_log)})', bw_adjust=0.8)
    sns.kdeplot(threat_log, ax=ax, color='#e74c3c', fill=True, alpha=0.4,
                linewidth=2, label=f'Threat (n={len(threat_log)})', bw_adjust=0.8)
    
    ax.axvline(threshold_log, color='#2c3e50', linestyle='--', linewidth=2,
               label=f'Threshold = {threshold_log:.2f}')
    ax.axvline(np.median(normal_log), color='#27ae60', linestyle=':', linewidth=1.5,
               label=f'Normal median = {np.median(normal_log):.2f}')
    ax.axvline(np.median(threat_log), color='#c0392b', linestyle=':', linewidth=1.5,
               label=f'Threat median = {np.median(threat_log):.2f}')
    
    ax.set_xlabel('Anomaly Score (log-transformed)', fontsize=11)
    ax.set_ylabel('Density', fontsize=11)
    ax.set_title('A. Score Distribution (KDE)', fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, loc='upper right')
    
    # --- Panel B: Box Plot ---
    ax = axes[1]
    box_data = pd.DataFrame({
        'score': scores_log,
        'type': np.where(is_threat == 0, 'Normal', 'Threat')
    })
    bp = sns.boxplot(data=box_data, x='type', y='score', ax=ax,
                     palette={'Normal': '#2ecc71', 'Threat': '#e74c3c'},
                     width=0.5, fliersize=4)
    # Overlay individual data points
    sns.stripplot(data=box_data, x='type', y='score', ax=ax,
                  color='#2c3e50', alpha=0.5, size=5, jitter=True)
    
    ax.axhline(threshold_log, color='#2c3e50', linestyle='--', linewidth=1.5,
               label=f'Threshold = {threshold_log:.2f}')
    ax.set_ylabel('Anomaly Score (log-transformed)', fontsize=11)
    ax.set_xlabel('')
    ax.set_title('B. Box Plot Comparison', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    
    # --- Panel C: Per-User Strip (sorted by score, colored by truth) ---
    ax = axes[2]
    sort_idx = np.argsort(scores_log)
    sorted_scores = scores_log[sort_idx]
    sorted_labels = is_threat[sort_idx]
    
    bar_colors = ['#e74c3c' if lbl == 1 else '#2ecc71' for lbl in sorted_labels]
    ax.barh(range(len(sorted_scores)), sorted_scores, color=bar_colors, height=0.8, alpha=0.8)
    ax.axvline(threshold_log, color='#2c3e50', linestyle='--', linewidth=2, label='Threshold')
    
    ax.set_xlabel('Anomaly Score (log-transformed)', fontsize=11)
    ax.set_ylabel('Users (sorted)', fontsize=11)
    ax.set_title('C. Per-User Ranking', fontsize=12, fontweight='bold')
    # Custom legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='#2ecc71', label='Normal'),
                       Patch(facecolor='#e74c3c', label='Threat')]
    ax.legend(handles=legend_elements, fontsize=9, loc='lower right')
    
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, 'ueba_gmm_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close()
    
    # Log summary statistics
    logging.info("GMM Score Statistics (log-transformed):")
    logging.info(f"  Normal  -> Mean: {normal_log.mean():.3f}, Median: {np.median(normal_log):.3f}, Std: {normal_log.std():.3f}")
    logging.info(f"  Threat  -> Mean: {threat_log.mean():.3f}, Median: {np.median(threat_log):.3f}, Std: {threat_log.std():.3f}")
    logging.info(f"  Threshold (median midpoint): {threshold_log:.3f}")
    logging.info(f"UEBA plots saved to {plot_dir}")


def main():
    MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
    PLOTS_DIR  = os.path.join(PROJECT_ROOT, "reports", "figures")
    LOGS_DIR   = os.path.join(PROJECT_ROOT, "reports", "logs")

    # ==== Step 1: Simulate User Data ====
    simulator = UserActivitySimulator(n_users=100, n_days=30, anomaly_ratio=0.15)
    session_df = simulator.generate()

    # ==== Step 2: Feature Engineering ====
    engineer = UEBAFeatureEngineer()
    user_features = engineer.transform(session_df)
    feature_cols = engineer.get_feature_columns()

    X = user_features[feature_cols].values
    
    # ==== Step 3: Behavioral Clustering (train on normal users only) ====
    normal_mask = user_features['is_threat'] == 0
    X_normal = X[normal_mask.values]
    
    cluster_model = BehavioralClusterModel(n_components=3)
    cluster_model.fit(X_normal)
    cluster_model.save(MODELS_DIR)
    
    # ==== Step 4: Score ALL users ====
    gmm_scores = cluster_model.score_users(X)
    clusters = cluster_model.predict_clusters(X)
    user_features['cluster'] = clusters

    # ==== Step 5: Risk Scoring ====
    risk_engine = RiskEngine()
    risk_df = risk_engine.compute_risk(user_features, gmm_scores)

    # ==== Step 6: Alerts ====
    generate_alerts(risk_df, LOGS_DIR)
    
    # ==== Step 7: Plots ====
    plot_results(risk_df, user_features, feature_cols, gmm_scores, PLOTS_DIR)

    # ==== Summary ====
    print(f"\n{CYAN}{BOLD}{'='*60}")
    print(f"  UEBA SESSION SUMMARY")
    print(f"{'='*60}{RESET}")
    
    # Detection accuracy
    high_risk_users = risk_df[risk_df['risk_level'] == 'HIGH_RISK']
    true_positives = high_risk_users['is_threat_ground_truth'].sum()
    false_positives = len(high_risk_users) - true_positives
    
    actual_threats = risk_df['is_threat_ground_truth'].sum()
    detected = risk_df[risk_df['risk_level'].isin(['HIGH_RISK', 'SUSPICIOUS'])]['is_threat_ground_truth'].sum()
    
    print(f"  Total Users Analyzed  : {len(risk_df)}")
    print(f"  {RED}High Risk             : {len(high_risk_users)} (TP: {true_positives}, FP: {false_positives}){RESET}")
    print(f"  {YELLOW}Suspicious            : {(risk_df['risk_level'] == 'SUSPICIOUS').sum()}{RESET}")
    print(f"  {GREEN}Normal                : {(risk_df['risk_level'] == 'NORMAL').sum()}{RESET}")
    print(f"  Actual Threats        : {actual_threats}")
    print(f"  Detected (HR+Susp)    : {detected}/{actual_threats}")
    print(f"{'='*60}\n")

    logging.info("Phase 3 — UEBA Pipeline Complete!")


if __name__ == "__main__":
    main()
