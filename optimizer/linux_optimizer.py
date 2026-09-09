import os
import shutil
import tempfile
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LinuxOptimizer:
    @staticmethod
    def execute(action_name: str, target: str) -> Dict[str, Any]:
        result = {"action": action_name, "target": target, "status": "SUCCESS", "message": ""}
        try:
            if action_name == "clean_temp":
                temp_dir = "/tmp"
                deleted, failed = 0, 0
                if os.path.exists(temp_dir):
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
                result["message"] = f"Linux /tmp cleaned. Deleted: {deleted}, Failed: {failed}"

            elif action_name == "clean_recycle_bin":
                trash_dir = os.path.expanduser("~/.local/share/Trash")
                if os.path.exists(trash_dir):
                    shutil.rmtree(trash_dir, ignore_errors=True)
                    os.makedirs(trash_dir, exist_ok=True)
                    result["message"] = "Linux trash emptied successfully."
                else:
                    result["message"] = "Linux trash directory not found or already empty."

            elif action_name == "stop_service":
                if target and target != "general":
                    cmd = f"sudo systemctl stop {target}"
                    res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
                    if res.returncode == 0:
                        result["message"] = f"Systemd service '{target}' stopped."
                    else:
                        result["status"] = "FAILED"
                        result["message"] = f"Failed to stop service '{target}': {res.stderr.strip()}"
                else:
                    result["message"] = f"Service '{target}' stop processed."

            elif action_name == "clean_package_cache":
                cmd = "sudo apt-get clean"
                res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=15)
                if res.returncode == 0:
                    result["message"] = "Apt package cache cleaned successfully."
                else:
                    result["status"] = "PARTIAL_SUCCESS"
                    result["message"] = f"Apt clean executed with output: {res.stderr.strip() or 'Completed'}"

            else:
                result["status"] = "FAILED"
                result["message"] = f"Unknown Linux action: {action_name}"
        except Exception as e:
            result["status"] = "FAILED"
            result["message"] = str(e)
        return result
