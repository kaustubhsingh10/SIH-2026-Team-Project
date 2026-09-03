"""Observability and In-Memory Performance Metrics for CrimeGraph AI.

Lightweight, production-grade tracking of request latencies, error counts,
AI investigation throughput, and persistence health without external dependencies.
"""

import threading
import time
from typing import Any, Dict, List


class MetricsCollector:
    """Thread-safe performance and health metrics registry."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MetricsCollector, cls).__new__(cls)
                cls._instance._init_metrics()
            return cls._instance

    def _init_metrics(self):
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.total_requests = 0
        self.total_errors = 0
        self.route_counts: Dict[str, int] = {}
        self.route_latencies: Dict[str, List[float]] = {}
        self.status_codes: Dict[int, int] = {}
        self.ai_queries_total = 0
        self.ai_queries_by_tier: Dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        self.persistence_saves = 0
        self.persistence_errors = 0

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        """Records API request performance metrics."""
        route_key = f"{method} {path}"
        with self.lock:
            self.total_requests += 1
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
            if status_code >= 500:
                self.total_errors += 1

            self.route_counts[route_key] = self.route_counts.get(route_key, 0) + 1
            
            # Keep a rolling window of the last 100 latency samples per route
            if route_key not in self.route_latencies:
                self.route_latencies[route_key] = []
            lat_list = self.route_latencies[route_key]
            lat_list.append(duration_ms)
            if len(lat_list) > 100:
                lat_list.pop(0)

    def record_ai_query(self, confidence_tier: str):
        """Records AI query intelligence execution metrics."""
        tier = (confidence_tier or "MEDIUM").upper()
        with self.lock:
            self.ai_queries_total += 1
            self.ai_queries_by_tier[tier] = self.ai_queries_by_tier.get(tier, 0) + 1

    def record_persistence(self, success: bool = True):
        """Records manual data persistence operations."""
        with self.lock:
            if success:
                self.persistence_saves += 1
            else:
                self.persistence_errors += 1

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured metrics summary."""
        with self.lock:
            uptime_seconds = round(time.time() - self.start_time, 2)
            
            route_stats = {}
            for r, lats in self.route_latencies.items():
                if lats:
                    avg_lat = round(sum(lats) / len(lats), 2)
                    max_lat = round(max(lats), 2)
                    min_lat = round(min(lats), 2)
                else:
                    avg_lat = max_lat = min_lat = 0.0
                route_stats[r] = {
                    "count": self.route_counts.get(r, 0),
                    "avg_ms": avg_lat,
                    "min_ms": min_lat,
                    "max_ms": max_lat
                }

            return {
                "uptime_seconds": uptime_seconds,
                "total_requests": self.total_requests,
                "total_errors_5xx": self.total_errors,
                "status_codes": dict(self.status_codes),
                "route_performance": route_stats,
                "ai_intelligence": {
                    "total_queries": self.ai_queries_total,
                    "confidence_tiers": dict(self.ai_queries_by_tier)
                },
                "persistence": {
                    "successful_saves": self.persistence_saves,
                    "save_errors": self.persistence_errors
                }
            }


metrics = MetricsCollector()
