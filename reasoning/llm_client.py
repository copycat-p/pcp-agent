import time
import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMClient:
    """
    v2 요구사항: LLM 호출 (Timeout, Retry, Backoff, Fallback 포함)
    Google Gemini API 연동 버전 (gemini-1.5-flash 또는 gemini-3.5-flash-lite 등 사용)
    """
    def __init__(self, provider: str = "google", model: str = "gemini-3.5-flash-lite", timeout_sec: int = 15, max_retries: int = 3):
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
        # Google Gemini API Endpoint (v1beta generateContent)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        logger.debug( f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={api_key}")
        backoff = 2
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_sec
                )
                if response.status_code == 200:
                    res_json = response.json()
                    # Gemini 응답 구조에서 텍스트 추출
                    content = res_json['candidates'][0]['content']['parts'][0]['text']
                    clean_content = content.replace("```json", "").replace("```", "").strip()
                    
                    parsed = json.loads(clean_content)
                    if isinstance(parsed, str):
                        parsed = json.loads(parsed)
                        
                    if isinstance(parsed, dict):
                        return parsed
                    else:
                        logger.warning(f"Parsed LLM output is not a dict: {type(parsed)}")
                        return self._rule_based_fallback(sanitized_status)
                else:
                    logger.warning(f"Gemini API returned status code {response.status_code}: {response.text}")
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
