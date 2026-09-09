from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SystemStatus(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    measurement_window_sec: int = 30
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_total_gb: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    top_processes: List[Dict[str, Any]] = []
    startup_programs: List[Dict[str, Any]] = []
    services: List[Dict[str, Any]] = []

class DiagnosticResult(BaseModel):
    task_id: str
    status: str
    before_status: SystemStatus
    analysis: Dict[str, Any] = {}

class OptimizationAction(BaseModel):
    name: str
    target: str
    risk_level: int
    parameters: Dict[str, Any] = {}

class OptimizationPlan(BaseModel):
    problem: str
    root_cause: str
    actions: List[OptimizationAction] = []

class TaskResult(BaseModel):
    task_id: str
    status: str # SUCCESS, PARTIAL_SUCCESS, FAILED, PENDING_APPROVAL
    summary: str
    before: Dict[str, Any] = {}
    after: Dict[str, Any] = {}
    actions: List[Dict[str, Any]] = []
    self_correction: Dict[str, Any] = {}
    rollback: Dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
