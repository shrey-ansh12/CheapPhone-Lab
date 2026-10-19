import subprocess
import shutil
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ADBManager:
    """
    Manages controlled ADB interactions safely using argument lists (no shell injection).
    Handles missing ADB or disconnected emulators gracefully.
    """

    @staticmethod
    def is_adb_installed() -> bool:
        """Checks if adb binary is available in system PATH."""
        return shutil.which("adb") is not None

    @staticmethod
    def get_adb_version() -> Optional[str]:
        if not ADBManager.is_adb_installed():
            return None
        try:
            res = subprocess.run(["adb", "version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return res.stdout.strip().split("\n")[0]
        except Exception as e:
            logger.error("Failed to run adb version: %s", e)
        return None

    @staticmethod
    def list_connected_devices() -> List[Dict[str, Any]]:
        """
        Executes 'adb devices -l' and parses detected devices and status.
        """
        if not ADBManager.is_adb_installed():
            return []

        devices = []
        try:
            res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                return []

            lines = res.stdout.strip().splitlines()
            for line in lines[1:]: # skip 'List of devices attached'
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]
                    details = " ".join(parts[2:]) if len(parts) > 2 else ""
                    is_emulator = "emulator" in serial or "generic" in details.lower()
                    devices.append({
                        "serial": serial,
                        "state": state,
                        "is_emulator": is_emulator,
                        "details": details
                    })
        except Exception as e:
            logger.error("Error listing ADB devices: %s", e)

        return devices

    @staticmethod
    def get_device_properties(serial: str) -> Dict[str, Any]:
        """
        Queries basic getprop values (model, sdk, release) from connected device.
        """
        if not ADBManager.is_adb_installed():
            return {}

        props = {}
        try:
            res = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop"],
                capture_output=True,
                text=True,
                timeout=8
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if ":" in line:
                        parts = line.split(":", 1)
                        key = parts[0].strip("[] ")
                        val = parts[1].strip("[] ")
                        if key in ["ro.product.model", "ro.build.version.release", "ro.build.version.sdk", "ro.product.manufacturer"]:
                            props[key] = val
        except Exception as e:
            logger.error("Failed to read device props for %s: %s", serial, e)

        return props

    @staticmethod
    def capture_screenshot(serial: str, output_path: str) -> bool:
        """
        Captures screenshot via adb exec-out screencap -p and writes binary to output_path.
        """
        if not ADBManager.is_adb_installed():
            return False

        try:
            with open(output_path, "wb") as f:
                res = subprocess.run(
                    ["adb", "-s", serial, "exec-out", "screencap", "-p"],
                    stdout=f,
                    stderr=subprocess.PIPE,
                    timeout=10
                )
                return res.returncode == 0
        except Exception as e:
            logger.error("Failed to capture screenshot on %s: %s", serial, e)
            return False

    @staticmethod
    def get_logcat_dump(serial: str, lines: int = 100) -> str:
        """
        Collects the most recent Logcat output from device.
        """
        if not ADBManager.is_adb_installed():
            return "ADB is not installed on this system."

        try:
            res = subprocess.run(
                ["adb", "-s", serial, "logcat", "-d", "-t", str(lines)],
                capture_output=True,
                text=True,
                timeout=10
            )
            return res.stdout if res.returncode == 0 else f"Error: {res.stderr}"
        except Exception as e:
            return f"Logcat capture error: {str(e)}"
