class MetricsAggregator:
    """
    Real-time metrics aggregator for the Unified SOC Pipeline.
    Tracks action distributions, intervention rates, and system latency.
    """
    def __init__(self):
        self.metrics = {
            "total_events": 0,
            "monitor": 0,
            "alert": 0,
            "block": 0,
            "isolate": 0,
            "interventions": 0,
            "avg_latency": 0.0
        }
        self._total_latency = 0.0

    def get_action_key(self, action_id: int) -> str:
        mapping = {0: "monitor", 1: "alert", 2: "block", 3: "isolate"}
        return mapping.get(action_id, "monitor")

    def update(self, event: dict):
        """Update metrics state with a new Unified Event."""
        self.metrics["total_events"] += 1
        
        # Action counts
        final_action_key = self.get_action_key(event["final_action"])
        self.metrics[final_action_key] += 1
        
        # Interventions
        if event["was_downgraded"]:
            self.metrics["interventions"] += 1
            
        # Latency Rolling Average
        self._total_latency += event.get("latency_ms", 0.0)
        self.metrics["avg_latency"] = self._total_latency / self.metrics["total_events"]

    def get_summary(self) -> dict:
        return self.metrics.copy()
