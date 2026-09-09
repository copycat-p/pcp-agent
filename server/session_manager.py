import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SessionContext:
    def __init__(self, task_id: str, llm_api_key: Optional[str], expires_in_sec: int = 300):
        self.task_id = task_id
        self._llm_api_key = llm_api_key
        self.expires_at = time.time() + expires_in_sec

    @property
    def llm_api_key(self) -> Optional[str]:
        if time.time() > self.expires_at:
            return None
        return self._llm_api_key

    def clear(self):
        self._llm_api_key = None
        logger.info(f"Session context cleared for task {self.task_id}")

class SessionManager:
    """
    LLM API Key를 메모리에만 임시 저장하고 TTL 만료 또는 작업 완료 시 즉시 파기
    """
    def __init__(self):
        self.sessions: Dict[str, SessionContext] = {}

    def create_session(self, task_id: str, llm_api_key: Optional[str]) -> SessionContext:
        session = SessionContext(task_id, llm_api_key)
        self.sessions[task_id] = session
        return session

    def get_session(self, task_id: str) -> Optional[SessionContext]:
        session = self.sessions.get(task_id)
        if session and session.llm_api_key is None:
            del self.sessions[task_id]
            return None
        return session

    def destroy_session(self, task_id: str):
        if task_id in self.sessions:
            self.sessions[task_id].clear()
            del self.sessions[task_id]
