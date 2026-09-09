import platform
from typing import Dict, Any
from optimizer.windows_optimizer import WindowsOptimizer
from optimizer.linux_optimizer import LinuxOptimizer

class OptimizerExecutor:
    """
    가독성 중심 멀티 OS 최적화 실행 총괄 관리자 (Strategy Pattern 적용)
    """
    @staticmethod
    def execute_action(action_name: str, target: str) -> Dict[str, Any]:
        os_type = platform.system().lower()
        
        if "win" in os_type:
            return WindowsOptimizer.execute(action_name, target)
        elif "lin" in os_type:
            return LinuxOptimizer.execute(action_name, target)
        else:
            return LinuxOptimizer.execute(action_name, target)
