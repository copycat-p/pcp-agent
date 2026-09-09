import requests
import json

# 테스트 설정 (agent_config.yaml과 일치해야 함)
#AGENT_URL = "http://127.0.0.1:8765/mcp/diagnose"
AGENT_URL = "http://192.168.0.19:8765/mcp/diagnose"
AGENT_TOKEN = "secret-agent-token-12345"
TASK_ID = "task-test-2026-001"
API_KEY = "AIzaSyDGGlXQZHyClBeQI1XM1p6aIbjsKDvk2k4"

def test_agent():
    headers = {
        "Authorization": f"Bearer {AGENT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "task_id": TASK_ID,
        "llm_api_key": API_KEY  # API Key가 없으면 자동 규칙 기반 폴백(Rule-based Fallback) 실행
    }

    print(f"Sending request to PC Performance AI Agent at {AGENT_URL}...")
    try:
        response = requests.post(AGENT_URL, json=payload, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the agent. Make sure main.py is running!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_agent()
