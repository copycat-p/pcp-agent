import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TaskPersistence:
    """
    v2 요구사항: 진행 중 Task 디스크 영속화 및 Agent 재시작 시 복구
    """
    def __init__(self, persistence_path: str = "./data/tasks.json"):
        self.persistence_path = persistence_path
        os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)

    def save_task(self, task_id: str, task_data: Dict[str, Any]):
        tasks = self.load_all_tasks()
        tasks[task_id] = task_data
        try:
            with open(self.persistence_path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist task {task_id}: {e}")

    def load_all_tasks(self) -> Dict[str, Any]:
        if not os.path.exists(self.persistence_path):
            return {}
        try:
            with open(self.persistence_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

class ResultBuffer:
    """
    v2 요구사항: 네트워크 단절 시 결과를 로컬에 임시 저장 후 재연결 시 전송
    """
    def __init__(self, buffer_path: str = "./data/result_buffer.json"):
        self.buffer_path = buffer_path
        os.makedirs(os.path.dirname(self.buffer_path), exist_ok=True)

    def push_result(self, result_data: Dict[str, Any]):
        buffer = self.load_buffer()
        buffer.append(result_data)
        try:
            with open(self.buffer_path, "w", encoding="utf-8") as f:
                json.dump(buffer, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to buffer result: {e}")

    def load_buffer(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.buffer_path):
            return []
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def clear_buffer(self):
        try:
            if os.path.exists(self.buffer_path):
                os.remove(self.buffer_path)
        except Exception:
            pass
