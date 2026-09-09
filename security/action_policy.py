import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ActionPolicy:
    """
    v2 요구사항: 허용된 Action 관리, Risk Level 분류 및 승인 여부 판단
    """
    def __init__(self, allowed_actions: List[str], approval_required_actions: List[str]):
        self.allowed_actions = set(allowed_actions)
        self.approval_required_actions = set(approval_required_actions)

    def validate_action(self, action_name: str) -> Dict[str, Any]:
        if action_name in self.allowed_actions:
            return {"status": "ALLOWED", "risk_level": 1, "requires_approval": False}
        elif action_name in self.approval_required_actions:
            return {"status": "APPROVAL_REQUIRED", "risk_level": 2, "requires_approval": True}
        else:
            return {"status": "DENIED", "risk_level": 3, "requires_approval": True}
