import time
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMClient_OPENAI:
    """
    v2 요구사항: LLM 호출 (Timeout, Retry, Backoff, Fallback 포함)
    OpenClaw 세션에서 전달받은 API Key를 메모리에서만 사용하여 LLM Provider 호출
    """
    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini", timeout_sec: int = 15, max_retries: int = 3):
        self.provider = provider
        self.model = model
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries

        def analyze_performance(self, sanitized_status: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
        if not api_key:
            logger.error("[LLMClient] No LLM API Key provided! Skipping LLM call and executing rule-based fallback.")
            return self._rule_based_fallback(sanitized_status)

        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
        logger.debug(f"[LLMClient] Initiating LLM call to provider '{self.provider}' (Model: {self.model}) with Key: {masked_key}")

        prompt = f"""
You are an expert Windows PC performance optimization AI Agent.
Analyze the following system status and return a JSON response with 'problem', 'root_cause', and 'actions'.

Each item in 'actions' MUST be an object with:
- 'name': One of ['clean_temp', 'clean_recycle_bin', 'disable_startup_program', 'stop_service', 'clean_windows_update_cache']
- 'target': Specific target name. For 'disable_startup_program' or 'stop_service', specify the exact program or service name (e.g. 'wizvera-veraport', 'SysMain', 'OneDrive'). Do NOT use 'general' for 'disable_startup_program' or 'stop_service'.
- 'risk_level': integer (1 or 2)

IMPORTANT:
- If multiple startup programs or services need optimization, return a separate action object for EACH individual program/service in the 'actions' array.
- Do NOT limit to only one target. Include all unneeded startup programs found in system status.

System Status:
{sanitized_status}
"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }

        backoff = 2
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_sec
                )
                if response.status_code == 200:
                    content = response.json()['choices'][0]['message']['content']
                    import json
                    # JSON 파싱 시도 (마크다운 블록 제거 등)
                    clean_content = content.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_content)
            except Exception as e:
                logger.warning(f"LLM call attempt {attempt+1} failed: {e}")
                time.sleep(backoff)
                backoff *= 2

        # 재시도 초과 시 폴백
        return self._rule_based_fallback(sanitized_status)

    def _rule_based_fallback(self, status: Dict[str, Any]) -> Dict[str, Any]:
        actions = []
        problem = "Normal Performance"
        root_cause = "No critical bottlenecks detected"

        cpu = status.get("cpu_usage_percent", 0)
        mem = status.get("memory_usage_percent", 0)
        disk = status.get("disk_usage_percent", 0)

        if disk > 90:
            problem = "High Disk Usage"
            root_cause = "Disk usage exceeds critical threshold (90%)"
            actions.append({"name": "clean_temp", "target": "system_temp", "risk_level": 1})
            actions.append({"name": "clean_recycle_bin", "target": "recycle_bin", "risk_level": 1})
        elif mem > 85:
            problem = "High Memory Usage"
            root_cause = "Available memory is low due to background processes"
            actions.append({"name": "clean_temp", "target": "user_temp", "risk_level": 1})
        elif cpu > 85:
            problem = "High CPU Usage"
            root_cause = "CPU utilization is high"
            actions.append({"name": "clean_temp", "target": "temp", "risk_level": 1})
        else:
            actions.append({"name": "clean_temp", "target": "routine_cleanup", "risk_level": 1})

        return {
            "problem": problem,
            "root_cause": root_cause,
            "actions": actions
        }
