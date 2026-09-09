import os
import shutil
import tempfile
import subprocess
import platform
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WindowsOptimizer:
    @staticmethod
    def execute(action_name: str, target: str) -> Dict[str, Any]:
        result = {"action": action_name, "target": target, "status": "SUCCESS", "message": ""}
        try:
            if action_name == "clean_temp":
                temp_dir = tempfile.gettempdir()
                deleted, failed = 0, 0
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                            deleted += 1
                        elif os.path.isdir(item_path):      
                            shutil.rmtree(item_path, ignore_errors=True)
                            deleted += 1
                    except Exception:
                        failed += 1
                result["message"] = f"Windows temp cleaned. Deleted: {deleted}, Failed: {failed}"

            elif action_name == "clean_recycle_bin":
                cmd = 'powershell "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"'
                res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
                if res.returncode == 0:
                    result["message"] = "Windows recycle bin emptied successfully."
                else:
                    result["status"] = "PARTIAL_SUCCESS"
                    result["message"] = f"Recycle bin cleared with output: {res.stderr.strip()}"

            elif action_name == "disable_startup_program":
                if target and target != "general":
                    ps_cmd = (
                        'powershell "'
                        "$paths = @("
                        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',"
                        "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',"
                        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce',"
                        "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce'"
                        ");"
                        "$removed = $false;"
                        "foreach ($p in $paths) {"
                        f"if (Test-Path \\\"$p\\{target}\\\") {{"
                        f"Remove-ItemProperty -Path $p -Name '{target}' -Force -ErrorAction SilentlyContinue;"
                        "$removed = $true;"
                        "}"
                        "}"
                        "if ($removed) { exit 0 } else { exit 1 }"
                        '"'
                    )
                    res = subprocess.run(ps_cmd, capture_output=True, text=True, shell=True, timeout=10)
                    if res.returncode == 0:
                        result["message"] = f"Startup program '{target}' successfully removed from registry."
                    else:
                        result["status"] = "FAILED"
                        result["message"] = f"Failed to remove startup program '{target}' or not found in registry. Details: {res.stderr.strip() or 'Registry key not found'}"
                else:
                    result["status"] = "FAILED"
                    result["message"] = "Invalid target specified for disabling startup program."

            elif action_name == "stop_service":
                if target and target != "general":
                    cmd = f'powershell "Stop-Service -Name \'{target}\' -Force -ErrorAction SilentlyContinue"'
                    res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
                    if res.returncode == 0:
                        result["message"] = f"Windows service '{target}' stopped."
                    else:
                        result["status"] = "FAILED"
                        result["message"] = f"Failed to stop Windows service '{target}': {res.stderr.strip()}"
                else:
                    result["message"] = f"Service '{target}' stop processed."

            elif action_name == "clean_windows_update_cache":
                cmd = 'powershell "Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue; $path = \\"$env:systemroot\\SoftwareDistribution\\Download\\*\"; Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue; Start-Service -Name wuauserv -ErrorAction SilentlyContinue"'
                subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=15)
                result["message"] = "Windows Update cache cleaned and service restarted."

            else:
                result["status"] = "FAILED"
                result["message"] = f"Unknown Windows action: {action_name}"
        except Exception as e:
            result["status"] = "FAILED"
            result["message"] = str(e)
        return result
