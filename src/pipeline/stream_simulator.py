"""
Stream Simulator — Simulates real-time network traffic ingestion.
Reads from the test dataset and yields samples row-by-row or in batches,
mimicking a live Kafka consumer or network tap.
"""

import time
import logging
import numpy as np
import pandas as pd
from typing import Iterator, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class StreamSimulator:
    """
    Simulates a real-time data stream from a Parquet dataset.
    In production, this would be replaced by a Kafka consumer
    pulling from topics like 'network.raw_telemetry'.
    """
    def __init__(self, data_path: str, feature_columns: list):
        logging.info(f"Loading stream source: {data_path}")
        df = pd.read_parquet(data_path)
        
        self.features = df[feature_columns].values
        self.labels = df['Label_Binary'].values if 'Label_Binary' in df.columns else None
        self.total_samples = len(df)
        self.current_index = 0
        
        logging.info(f"Stream loaded: {self.total_samples:,} samples ready for emission.")

    def stream_single(self, delay: float = 0.0) -> Iterator[Tuple[np.ndarray, int]]:
        """Yields one sample at a time with optional delay (simulates network latency)."""
        for i in range(self.total_samples):
            sample = self.features[i].reshape(1, -1)
            label = self.labels[i] if self.labels is not None else -1
            if delay > 0:
                time.sleep(delay)
            yield sample, label

    def stream_batch(self, batch_size: int = 64, delay: float = 0.0) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """Yields batches of samples for higher throughput inference."""
        for start in range(0, self.total_samples, batch_size):
            end = min(start + batch_size, self.total_samples)
            batch_features = self.features[start:end]
            batch_labels = self.labels[start:end] if self.labels is not None else np.full(end - start, -1)
            if delay > 0:
                time.sleep(delay)
            yield batch_features, batch_labels
