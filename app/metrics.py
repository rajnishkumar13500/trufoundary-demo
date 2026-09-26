import time
import math
import collections
import logging
from typing import Dict, Any, List

logger = logging.getLogger("actionshield.telemetry")
logging.basicConfig(level=logging.INFO, format="%(message)s")

class MetricsCollector:
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.request_latencies: collections.deque = collections.deque(maxlen=window_size)
        self.db_latencies: collections.deque = collections.deque(maxlen=window_size)
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.start_time: float = time.time()
        self.route_counts: Dict[str, int] = collections.defaultdict(int)

    def record_request(self, route: str, status_code: int, latency_ms: float, db_query_ms: float):
        self.total_requests += 1
        self.route_counts[route] += 1
        if status_code >= 400:
            self.total_errors += 1
        self.request_latencies.append(latency_ms)
        if db_query_ms > 0:
            self.db_latencies.append(db_query_ms)

    def _percentile(self, data: List[float], p: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return round(sorted_data[int(k)], 2)
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return round(d0 + d1, 2)

    def get_snapshot(self) -> Dict[str, Any]:
        uptime_sec = max(1.0, time.time() - self.start_time)
        latencies = list(self.request_latencies)
        db_lats = list(self.db_latencies)

        return {
            "uptime_seconds": round(uptime_sec, 2),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round((self.total_errors / self.total_requests) if self.total_requests > 0 else 0.0, 4),
            "throughput_rps": round(self.total_requests / uptime_sec, 2),
            "latency_p50_ms": self._percentile(latencies, 50),
            "latency_p95_ms": self._percentile(latencies, 95),
            "latency_p99_ms": self._percentile(latencies, 99),
            "db_query_p50_ms": self._percentile(db_lats, 50),
            "db_query_p95_ms": self._percentile(db_lats, 95),
            "recent_sample_size": len(latencies),
            "routes": dict(self.route_counts)
        }

metrics_collector = MetricsCollector()
