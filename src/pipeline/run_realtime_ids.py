"""
Real-Time IDS Runner — Phase 2
================================
Orchestrates the full real-time intrusion detection pipeline:

  Stream Simulator → Inference Engine → Alert System

Usage:
  python src/pipeline/run_realtime_ids.py                    # batch mode (fast)
  python src/pipeline/run_realtime_ids.py --mode single      # single-sample mode
  python src/pipeline/run_realtime_ids.py --limit 500        # process only 500 samples
  python src/pipeline/run_realtime_ids.py --delay 0.05       # 50ms delay per batch
"""

import os
import sys
import time
import argparse
import logging
import joblib
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.pipeline.stream_simulator import StreamSimulator
from src.pipeline.inference_engine import InferenceEngine
from src.pipeline.alert_system import AlertSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def main():
    parser = argparse.ArgumentParser(description="Real-Time IDS Pipeline")
    parser.add_argument('--mode', choices=['single', 'batch'], default='batch',
                        help="Streaming mode: 'single' (one at a time) or 'batch' (chunks)")
    parser.add_argument('--batch_size', type=int, default=64,
                        help="Batch size for batch mode (default: 64)")
    parser.add_argument('--delay', type=float, default=0.01,
                        help="Seconds to wait between emissions (default: 0.01)")
    parser.add_argument('--limit', type=int, default=2000,
                        help="Max samples to process (default: 2000, set 0 for all)")
    args = parser.parse_args()

    # ---- Paths ----
    DATA_PATH       = os.path.join(PROJECT_ROOT, "data", "processed", "test_dataset.parquet")
    MODEL_PATH      = os.path.join(PROJECT_ROOT, "models", "autoencoder_v2.pt")
    CONDITIONER_PATH= os.path.join(PROJECT_ROOT, "models", "data_conditioner.pkl")
    CONFIG_PATH     = os.path.join(PROJECT_ROOT, "models", "ae_v2_config.pkl")
    TOP_FEATURES    = os.path.join(PROJECT_ROOT, "data", "features", "top_features.pkl")
    LOG_DIR         = os.path.join(PROJECT_ROOT, "reports", "logs")

    # ---- Load feature list ----
    feature_columns = joblib.load(TOP_FEATURES)
    logging.info(f"Using {len(feature_columns)} features for inference.")

    # ---- Initialize Components ----
    engine = InferenceEngine(MODEL_PATH, CONDITIONER_PATH, CONFIG_PATH)
    alerts = AlertSystem(LOG_DIR)
    stream = StreamSimulator(DATA_PATH, feature_columns)

    limit = args.limit if args.limit > 0 else stream.total_samples
    logging.info(f"Starting real-time IDS | Mode: {args.mode} | Limit: {limit:,} samples")
    print()

    pipeline_start = time.perf_counter()
    samples_processed = 0

    try:
        if args.mode == 'single':
            # ---- Single-sample streaming ----
            for sample, true_label in stream.stream_single(delay=args.delay):
                preds, scores, latency = engine.detect(sample)
                alerts.process_result(
                    prediction=preds[0], score=scores[0],
                    latency_ms=latency, true_label=true_label,
                    sample_id=samples_processed
                )
                samples_processed += 1
                if samples_processed >= limit:
                    break

        elif args.mode == 'batch':
            # ---- Batch streaming (higher throughput) ----
            for batch_features, batch_labels in stream.stream_batch(
                batch_size=args.batch_size, delay=args.delay
            ):
                preds, scores, latency = engine.detect(batch_features)
                
                for i in range(len(preds)):
                    alerts.process_result(
                        prediction=preds[i], score=scores[i],
                        latency_ms=latency / len(preds),  # per-sample latency
                        true_label=batch_labels[i],
                        sample_id=samples_processed
                    )
                    samples_processed += 1
                    if samples_processed >= limit:
                        break
                
                if samples_processed >= limit:
                    break

    except KeyboardInterrupt:
        print(f"\n{AlertSystem.Colors if hasattr(AlertSystem, 'Colors') else ''}Pipeline interrupted by user.")

    # ---- Final Summary ----
    total_time = time.perf_counter() - pipeline_start
    throughput = samples_processed / max(total_time, 0.001)

    alerts.print_summary()
    print(f"  Pipeline Duration       : {total_time:.2f} seconds")
    print(f"  Throughput              : {throughput:,.0f} samples/sec")
    print()


if __name__ == "__main__":
    main()
