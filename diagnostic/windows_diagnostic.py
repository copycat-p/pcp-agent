import psutil
import platform
import subprocess
from datetime import datetime
from typing import Dict, Any, List

class WindowsDiagnostic:
    @staticmethod
    def collect(window_sec: int = 5, interval_sec: int = 1) -> Dict[str, Any]:
        samples = int(window_sec / interval_sec)
        if samples < 1:
            samples = 1

        cpu_samples, mem_samples, disk_samples = [], [], []

        for _ in range(samples):
            cpu_samples.append(psutil.cpu_percent(interval=None))
            mem_samples.append(psutil.virtual_memory().percent)
            disk_samples.append(psutil.disk_usage('C:\\').percent)
            if samples > 1:
                import time
                time.sleep(interval_sec)

        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        avg_mem = sum(mem_samples) / len(mem_samples)
        avg_disk = sum(disk_samples) / len(disk_samples)

        mem_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('C:\\')

        top_processes = []
        for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']), 
                        key=lambda x: x.info['memory_percent'] or 0, reverse=True)[:5]:
            try:
                top_processes.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        startups = WindowsDiagnostic._get_startup_programs()
        services = WindowsDiagnostic._get_critical_services()

        return {
            "os": "windows",
            "timestamp": datetime.now().isoformat(),
            "measurement_window_sec": window_sec,
            "cpu_usage_percent": round(avg_cpu, 2),
            "memory_usage_percent": round(avg_mem, 2),
            "memory_total_gb": round(mem_info.total / (1024**3), 2),
            "memory_available_gb": round(mem_info.available / (1024**3), 2),
            "disk_usage_percent": round(avg_disk, 2),
            "disk_free_gb": round(disk_info.free / (1024**3), 2),
            "top_processes": top_processes,
            "startup_programs": startups,
            "services": services
        }

    @staticmethod
    def _get_startup_programs() -> List[Dict[str, Any]]:
        startups = []
        try:
            cmd = 'powershell "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | ConvertTo-Json"'
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data[:10]:
                    startups.append({
                        "name": item.get("Name", "Unknown"),
                        "command": item.get("Command", ""),
                        "location": item.get("Location", "")
                    })
        except Exception:
            pass
        return startups

    @staticmethod
    def _get_critical_services() -> List[Dict[str, Any]]:
        services = []
        try:
            for s in list(psutil.win_service_iter())[:15]:
                try:
                    serv_info = s.as_dict()
                    services.append({
                        "name": serv_info.get("name"),
                        "display_name": serv_info.get("display_name"),
                        "status": serv_info.get("status")
                    })
                except Exception:
                    pass
        except Exception:
            pass
        return services
