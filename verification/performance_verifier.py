from diagnostic.metric_aggregator import MetricAggregator
from reasoning.privacy_filter import PrivacyFilter
from reasoning.llm_client import LLMClient
from security.action_policy import ActionPolicy
from optimizer.snapshot_manager import SnapshotManager
from optimizer.optimizer_executor import OptimizerExecutor
import time
import logging

logger = logging.getLogger(__name__)

class PerformanceVerifier:
    """
    v2 요구사항: 작업 전/후 성능 비교 (순간값이 아닌 구간 평균)
    """
    def __init__(self, aggregator: MetricAggregator):
        self.aggregator = aggregator

    def verify(self, before_status: dict) -> dict:
        after_status = self.aggregator.collect_system_status()
        
        before_cpu = before_status.get("cpu_usage_percent", 0)
        after_cpu = after_status.get("cpu_usage_percent", 0)
        
        before_mem = before_status.get("memory_usage_percent", 0)
        after_mem = after_status.get("memory_usage_percent", 0)
        
        success = (after_cpu <= before_cpu + 5) and (after_mem <= before_mem + 5)
        
        return {
            "success": success,
            "before_cpu": before_cpu,
            "after_cpu": after_cpu,
            "before_memory": before_mem,
            "after_memory": after_mem,
            "measurement_window_sec": self.aggregator.window_sec
        }
