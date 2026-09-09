import platform
from typing import Dict, Any
from diagnostic.windows_diagnostic import WindowsDiagnostic
from diagnostic.linux_diagnostic import LinuxDiagnostic

class MetricAggregator:
    """
    가독성 중심 멀티 OS 진단 총괄 관리자 (Strategy Pattern 적용)
    """
    def __init__(self, window_sec: int = 5, interval_sec: int = 1):
        self.window_sec = window_sec
        self.interval_sec = interval_sec
        self.os_type = platform.system().lower()

    def collect_system_status(self) -> Dict[str, Any]:
        if "win" in self.os_type:
            return WindowsDiagnostic.collect(self.window_sec, self.interval_sec)
        elif "lin" in self.os_type:
            return LinuxDiagnostic.collect(self.window_sec, self.interval_sec)
        else:
            return LinuxDiagnostic.collect(self.window_sec, self.interval_sec)
