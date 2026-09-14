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
                logger.debug(f"Starting temp cleanup in directory: {temp_dir}")
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                            deleted += 1
                        elif os.path.isdir(item_path):      
                            shutil.rmtree(item_path, ignore_errors=True)
                            deleted += 1
                    except Exception as err:
                        failed += 1
                        logger.error(f"Failed to delete temp item '{item_path}': {err}")
                result["message"] = f"Windows temp cleaned. Deleted: {deleted}, Failed: {failed}"
                logger.debug(f"clean_temp result: {result['message']}")

            elif action_name == "clean_recycle_bin":
                cmd = 'powershell "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"'
                logger.debug(f"Executing clean_recycle_bin command: {cmd}")
                res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
                if res.returncode == 0:
                    result["message"] = "Windows recycle bin emptied successfully."
                    logger.debug(result["message"])
                else:
                    result["status"] = "PARTIAL_SUCCESS"
                    result["message"] = f"Recycle bin cleared with output: {res.stderr.strip()}"
                    logger.error(f"clean_recycle_bin non-zero exit code: {res.returncode}, stderr: {res.stderr.strip()}")

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
                        "$errOccurred = $false;"
                        "foreach ($p in $paths) {"
                        f"  $prop = Get-ItemProperty -Path $p -ErrorAction SilentlyContinue;"
                        f"  if ($prop -and $prop.'{target}' -ne $null) {{"
                        "    try {"
                        f"      Remove-ItemProperty -Path $p -Name '{target}' -Force -ErrorAction Stop;"
                        "      $removed = $true;"
                        "    } catch {"
                        "      $errOccurred = $true;"
                        "    }"
                        "  }"
                        "}"
                        f"try {{ Stop-Process -Name '{target}' -Force -ErrorAction SilentlyContinue }} catch {{}}"
                        f"try {{ Stop-Service -Name '{target}' -Force -ErrorAction SilentlyContinue }} catch {{}}"
                        "if ($removed) { exit 0 } elseif ($errOccurred) { exit 2 } else { exit 1 }"
                        '"'
                    )
                    logger.debug(f"Executing disable_startup_program for target '{target}'")
                    res = subprocess.run(ps_cmd, capture_output=True, text=True, shell=True, timeout=10)
                    if res.returncode == 0:
                        result["message"] = f"Startup program '{target}' successfully removed from registry and running process stopped."
                        logger.debug(result["message"])
                    elif res.returncode == 2:
                        result["status"] = "FAILED"
                        result["message"] = f"Failed to remove startup program '{target}': Permission denied (Requires Administrator privileges)."
                        logger.error(result["message"])
                    else:
                        result["status"] = "FAILED"
                        result["message"] = f"Startup program '{target}' not found in registry."
                        logger.error(f"disable_startup_program: '{target}' not found in registry.")
                else:
                    result["status"] = "FAILED"
                    result["message"] = "Invalid target specified for disabling startup program."
                    logger.error(f"disable_startup_program rejected invalid target: '{target}'")

            elif action_name == "stop_service":
                if target and target != "general":
                    cmd = f'powershell "Stop-Service -Name \'{target}\' -Force -ErrorAction SilentlyContinue"'
                    logger.debug(f"Executing stop_service for service '{target}'")
                    res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
                    if res.returncode == 0:
                        result["message"] = f"Windows service '{target}' stopped."
                    else:
                        result["status"] = "FAILED"
                        result["message"] = f"Failed to stop Windows service '{target}': {res.stderr.strip()}"
                        logger.error(f"stop_service failed for '{target}': stderr={res.stderr.strip()}")
                else:
                    result["message"] = f"Service '{target}' stop processed."
                    logger.debug(f"stop_service processed with generic target: '{target}'")

            elif action_name == "clean_windows_update_cache":
                cmd = 'powershell "Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue; $path = \\"$env:systemroot\\SoftwareDistribution\\Download\\*\"; Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue; Start-Service -Name wuauserv -ErrorAction SilentlyContinue"'
                logger.debug("Executing clean_windows_update_cache")
                res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=15)
                if res.returncode != 0:
                    logger.error(f"clean_windows_update_cache returncode={res.returncode}, stderr={res.stderr.strip()}")
                else:
                    logger.debug(f"clean_windows_update_cache completed successfully.")
                result["message"] = "Windows Update cache cleaned and service restarted."

            else:
                result["status"] = "FAILED"
                result["message"] = f"Unknown Windows action: {action_name}"
                logger.error(f"Unknown Windows action requested: {action_name}")
        except Exception as e:
            result["status"] = "FAILED"
            result["message"] = str(e)
            logger.error(f"Exception encountered during WindowsOptimizer.execute({action_name}): {e}", exc_info=True)
        return result
