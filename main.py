import yaml
import logging
import asyncio
import traceback
import sys
from fastapi import FastAPI, Depends, Header, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from diagnostic.metric_aggregator import MetricAggregator
from reasoning.privacy_filter import PrivacyFilter
from reasoning.llm_client import LLMClient
from security.action_policy import ActionPolicy
from optimizer.snapshot_manager import SnapshotManager
from optimizer.optimizer_executor import OptimizerExecutor
from verification.performance_verifier import PerformanceVerifier
from server.session_manager import SessionManager
from server.auth_middleware import AuthMiddleware
from resilience.task_persistence import TaskPersistence, ResultBuffer

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("PCPerformanceAgent")
logger.setLevel(logging.DEBUG)

# 1. 설정 로드
with open("config/agent_config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

AGENT_ID = config["agent"]["id"]
EXPECTED_TOKEN = config["agent"]["auth_token"]
HOST = config["agent"]["host"]
PORT = config["agent"]["port"]

allowed_actions = config["security"]["allowed_actions"]
approval_required_actions = config["security"]["approval_required_actions"]

# 2. 핵심 엔진 초기화
aggregator = MetricAggregator(window_sec=5)
privacy_filter = PrivacyFilter()
llm_client = LLMClient(
    provider=config["llm"]["default_provider"],
    model=config["llm"]["model"],
    timeout_sec=config["llm"]["timeout_sec"],
    max_retries=config["llm"]["max_retries"]
)
action_policy = ActionPolicy(allowed_actions, approval_required_actions)
snapshot_manager = SnapshotManager()
verifier = PerformanceVerifier(aggregator)
session_manager = SessionManager()
task_persistence = TaskPersistence(config["resilience"]["task_persistence_path"])
result_buffer = ResultBuffer(config["resilience"]["result_buffer_path"])
auth_middleware = AuthMiddleware(EXPECTED_TOKEN)

app = FastAPI(title="PC Performance AI Agent", version="2.0")

class RunTaskRequest(BaseModel):
    task_id: str
    llm_api_key: Optional[str] = None
    approved_actions: Optional[List[str]] = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent_id": AGENT_ID}

@app.post("/mcp/diagnose")
async def diagnose(req: RunTaskRequest, authorization: Optional[str] = Header(None)):
    # 토큰 검증
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Bearer Token")
    token = authorization.split(" ")[1]
    if token != EXPECTED_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Agent Auth Token")

    # 세션 생성 (LLM API Key는 메모리에만 임시 보관)
    session = session_manager.create_session(req.task_id, req.llm_api_key)
    task_persistence.save_task(req.task_id, {"status": "RUNNING", "step": "diagnosing"})

    try:
        # 1. 상태 수집 (구간 평균)
        before_status = aggregator.collect_system_status()

        # 2. 프라이버시 필터 적용
        sanitized = privacy_filter.sanitize(before_status)

        # 3. LLM 분석 (또는 폴백)
        analysis = llm_client.analyze_performance(sanitized, api_key=session.llm_api_key)

        # 방어 코드: analysis가 딕셔너리가 아닌 경우 처리
        if isinstance(analysis, str):
            try:
                import json
                analysis = json.loads(analysis)
            except Exception:
                analysis = {
                    "problem": "Analysis Error",
                    "root_cause": "LLM returned invalid string format",
                    "actions": [{"name": "clean_temp", "target": "temp", "risk_level": 1}]
                }
        
        if not isinstance(analysis, dict):
            analysis = {
                "problem": "Analysis Error",
                "root_cause": "LLM returned non-dict format",
                "actions": [{"name": "clean_temp", "target": "temp", "risk_level": 1}]
            }

        # 사용자가 --approve로 명시 승인한 액션이 분석 결과에 없다면 강제 추가
        if req.approved_actions:
            existing_actions = set()
            for a in analysis.get("actions", []):
                if isinstance(a, str):
                    existing_actions.add(a)
                elif isinstance(a, dict) and "name" in a:
                    existing_actions.add(a["name"])
            
            for approved in req.approved_actions:
                if approved not in existing_actions:
                    analysis.setdefault("actions", []).append({
                        "name": approved,
                        "target": "general",
                        "risk_level": 2
                    })

        # 4. 개선 계획 실행 (Self-Correction & Policy 검증)
        actions_result = []
        for action_def in analysis.get("actions", []):
            if isinstance(action_def, str):
                action_name = action_def
                target = "general"
            elif isinstance(action_def, dict):
                action_name = action_def.get("name")
                target = action_def.get("target", "general")
            else:
                continue

            if not action_name:
                continue
            
            validation = action_policy.validate_action(action_name)
            if validation["requires_approval"] and action_name not in (req.approved_actions or []):
                actions_result.append({
                    "action": action_name,
                    "status": "PENDING_APPROVAL",
                    "risk_level": validation["risk_level"]
                })
                continue

            # Level 2 이상 시 스냅샷 저장
            snapshot_id = None
            if validation["risk_level"] >= 2:
                snapshot_id = snapshot_manager.capture(action_name, target)

            # 실행
            exec_res = OptimizerExecutor.execute_action(action_name, target)
            exec_res["risk_level"] = validation["risk_level"]
            if snapshot_id:
                exec_res["snapshot_id"] = snapshot_id

            # 검증
            verification = verifier.verify(before_status)
            if not verification["success"] and snapshot_id:
                snapshot_manager.rollback(snapshot_id)
                exec_res["rollback"] = True

            actions_result.append(exec_res)

        after_status = aggregator.collect_system_status()

        result_data = {
            "task_id": req.task_id,
            "status": "SUCCESS",
            "summary": f"Completed diagnosis and optimization for {analysis.get('problem', 'Unknown')}",
            "before": before_status,
            "after": after_status,
            "actions": actions_result,
            "analysis": analysis
        }

        task_persistence.save_task(req.task_id, {"status": "COMPLETED", "result": result_data})
        return result_data

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = exc_tb.tb_frame.f_code.co_filename
        lineno = exc_tb.tb_lineno
        logger.error(f"Task execution failed at [{filename}:{lineno}] - {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())

        error_result = {"task_id": req.task_id, "status": "FAILED", "error": f"[{filename}:{lineno}] {str(e)}"}
        result_buffer.push_result(error_result)
        raise HTTPException(status_code=500, detail=f"Error at {filename}:{lineno} - {str(e)}")
    finally:
        session_manager.destroy_session(req.task_id)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting PC Performance AI Agent in DEBUG mode on {HOST}:{PORT}")
    # 2. uvicorn 실행 시 log_level을 "debug"로 명시
    uvicorn.run(app, host=HOST, port=PORT, log_level="debug")
