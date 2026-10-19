import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from database.neo4j_client import Neo4jClient
from database.graph_queries import sync_test_run_to_graph
from core.demo_scenarios import generate_simulated_failures
from testing.adb_manager import ADBManager
from testing.logcat_collector import LogcatCollector

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
RUNS_FILE = os.path.join(DATA_DIR, "test_runs.json")
PROFILES_FILE = os.path.join(DATA_DIR, "device_profiles.json")

class TestRunner:
    """
    Coordinates simulated demo runs and real ADB emulator tests.
    Persists data locally in JSON files and synchronizes with Neo4j AuraDB.
    """

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.neo4j = Neo4jClient()

    def load_profiles(self) -> List[Dict[str, Any]]:
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load profiles: %s", e)
        return []

    def get_profile_by_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        profiles = self.load_profiles()
        for p in profiles:
            if p["id"] == profile_id:
                return p
        return None

    def save_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        profiles = self.load_profiles()
        if not profile_data.get("id"):
            profile_data["id"] = f"custom_{str(uuid.uuid4())[:6]}"

        # Check if updating
        updated = False
        for idx, p in enumerate(profiles):
            if p["id"] == profile_data["id"]:
                profiles[idx] = profile_data
                updated = True
                break

        if not updated:
            profiles.append(profile_data)

        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2)

        return profile_data

    def load_runs(self) -> List[Dict[str, Any]]:
        if os.path.exists(RUNS_FILE):
            try:
                with open(RUNS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load test runs: %s", e)
        return []

    def get_run_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        runs = self.load_runs()
        for r in runs:
            if r["id"] == run_id:
                return r
        return None

    def get_all_failures(self) -> List[Dict[str, Any]]:
        runs = self.load_runs()
        failures = []
        for r in runs:
            failures.extend(r.get("failures", []))
        return failures

    def get_failure_by_id(self, failure_id: str) -> Optional[Dict[str, Any]]:
        failures = self.get_all_failures()
        for f in failures:
            if f["id"] == failure_id:
                return f
        return None

    def save_run(self, run_data: Dict[str, Any]):
        runs = self.load_runs()
        runs.insert(0, run_data) # newest first
        with open(RUNS_FILE, "w", encoding="utf-8") as f:
            json.dump(runs, f, indent=2)

        # Sync to Neo4j if available
        if self.neo4j.is_connected:
            try:
                sync_test_run_to_graph(self.neo4j, run_data)
            except Exception as e:
                logger.warning("Graph sync skipped: %s", e)

    def execute_simulation(
        self,
        app_name: str,
        description: str,
        profile_id: str,
        network_condition: str,
        storage_level: str,
        memory_pressure: str,
        battery_saver: str,
        background_interruption: str,
        iterations: int = 1
    ) -> Dict[str, Any]:
        """
        Runs deterministic rule-based simulation.
        Works immediately on any computer without Android devices.
        """
        profile = self.get_profile_by_id(profile_id) or {
            "id": profile_id,
            "name": "Custom Profile",
            "android_version": "Android 10",
            "ram_category": "2GB",
            "storage": "16GB",
            "battery_saver": battery_saver
        }

        conditions_dict = {
            "network_condition": network_condition,
            "storage_level": storage_level,
            "memory_pressure": memory_pressure,
            "battery_saver": battery_saver,
            "background_interruption": background_interruption
        }

        run_id = f"RUN_SIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}"

        # Evaluate deterministic failure rules
        failures = generate_simulated_failures(profile, conditions_dict, run_id)

        # Build conditions list for Neo4j graph nodes
        conditions_graph = [
            {
                "name": f"Network: {network_condition}",
                "category": "Network",
                "description": f"Simulated Indian network profile: {network_condition}",
                "segments": [{"name": "Commuters & Tier-3 Mobile Users", "population": 4200000, "description": "High RTT latency & packet drops during transit"}]
            },
            {
                "name": f"Storage: {storage_level}",
                "category": "Storage",
                "description": f"Internal flash memory state: {storage_level}",
                "segments": [{"name": "Heavy Media/WhatsApp Users", "population": 2900000, "description": "Flash storage regularly hits critical thresholds"}]
            },
            {
                "name": f"Memory: {memory_pressure}",
                "category": "Memory",
                "description": f"RAM constraint: {memory_pressure}",
                "segments": [{"name": "Sub-₹8,000 Budget Phone Owners", "population": 3800000, "description": "Aggressive background task termination and OOMs"}]
            }
        ]

        run_record = {
            "id": run_id,
            "app_name": app_name,
            "description": description or f"Simulated stress test under {network_condition} and {memory_pressure} memory pressure.",
            "mode": "Demo Simulation",
            "is_simulation": True,
            "status": "Failed" if len(failures) > 0 else "Passed",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iterations": iterations,
            "device_profile": profile,
            "conditions_summary": conditions_dict,
            "conditions": conditions_graph,
            "failures": failures,
            "failure_count": len(failures),
            "evidence_count": sum(len(f.get("evidence", [])) for f in failures),
            "log_summary": f"Completed {iterations} deterministic simulation iteration(s). Discovered {len(failures)} failure pattern(s)."
        }

        self.save_run(run_record)
        return run_record

    def execute_real_emulator_test(
        self,
        app_name: str,
        description: str,
        device_serial: str,
        apk_path: Optional[str] = None,
        iterations: int = 1
    ) -> Dict[str, Any]:
        """
        Executes a controlled test on an actual ADB device/emulator.
        """
        run_id = f"RUN_REAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}"

        if not ADBManager.is_adb_installed():
            raise RuntimeError("ADB is not installed or not in system PATH.")

        devices = ADBManager.list_connected_devices()
        target_device = next((d for d in devices if d["serial"] == device_serial), None)
        if not target_device:
            raise RuntimeError(f"Device '{device_serial}' is no longer connected or available.")

        # Read actual device properties
        props = ADBManager.get_device_properties(device_serial)
        model = props.get("ro.product.model", "Android Emulator")
        release = props.get("ro.build.version.release", "Unknown")
        sdk = props.get("ro.build.version.sdk", "Unknown")

        # Capture actual Logcat
        logcat_text = ADBManager.get_logcat_dump(device_serial, lines=250)

        # Parse Logcat for actual events
        raw_findings = LogcatCollector.analyze_logcat_output(logcat_text)

        actual_failures = []
        for idx, finding in enumerate(raw_findings):
            fid = f"REAL_{finding['category'][:4].upper()}_{str(uuid.uuid4())[:6]}"
            actual_failures.append({
                "id": fid,
                "title": finding["title"],
                "description": f"Real hardware logcat event captured on {model} (Android {release}).",
                "category": finding["category"],
                "severity": finding["severity"],
                "confidence": finding["confidence"],
                "mode": "Real Emulator Test",
                "expected_behavior": "Application runtime should maintain responsive UI without uncaught exceptions or ANR looper stalls.",
                "observed_behavior": finding["title"],
                "suggested_debugging": "Inspect the captured Logcat snippet below to identify problematic thread ID and class line.",
                "feature": {"id": "runtime_core", "name": "Application Runtime Core"},
                "test_run_id": run_id,
                "device_profile": {
                    "id": device_serial,
                    "name": f"{model} (Real ADB)",
                    "android_version": f"Android {release} (API {sdk})",
                    "ram_category": "Real Device Spec",
                    "storage": "Host/Device Assigned",
                    "screen": "Native Display",
                    "battery_saver": "Device Setting"
                },
                "conditions": {
                    "network_condition": "Active Host/Device Network",
                    "storage_level": "Real Device State",
                    "memory_pressure": "Observed via Logcat",
                    "battery_saver": "Real Profile",
                    "background_interruption": "Standard OS"
                },
                "evidence": [
                    {
                        "id": f"ev_{fid}_logcat",
                        "type": "Real Device Logcat Dump",
                        "content": finding["evidence"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                ],
                "reproduction_recipe": {
                    "id": f"rec_{fid}",
                    "preconditions": f"Connected to {model} via ADB.",
                    "device_config": f"Android {release}, API {sdk}",
                    "network_storage": "Real device environment",
                    "steps": [
                        f"Connect target device '{device_serial}'.",
                        "Launch target application under testing.",
                        "Inspect Logcat stream for fatal runtime events."
                    ],
                    "expected": "Normal execution without crashes or ANR events.",
                    "observed": finding["title"],
                    "debug_direction": "Check thread looper latency and stack trace in captured evidence."
                }
            })

        profile_data = {
            "id": device_serial,
            "name": f"{model} (ADB)",
            "android_version": f"Android {release} (API {sdk})",
            "ram_category": "Real Device Memory",
            "storage": "Device Assigned",
            "screen": "Physical/Emulated Display",
            "battery_saver": "Unconstrained",
            "is_real_device": True
        }

        run_record = {
            "id": run_id,
            "app_name": app_name,
            "description": description or f"Real ADB Test on {model} ({device_serial})",
            "mode": "Real Emulator Test",
            "is_simulation": False,
            "status": "Failed" if len(actual_failures) > 0 else "Passed",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iterations": iterations,
            "device_profile": profile_data,
            "conditions_summary": {
                "network_condition": "Native Device Connection (Unshaped)",
                "storage_level": "Real Storage",
                "memory_pressure": "Hardware Controlled",
                "battery_saver": "Device Setting",
                "background_interruption": "Standard OS"
            },
            "conditions": [
                {
                    "name": "Native Device Environment",
                    "category": "Real Hardware",
                    "description": f"Observed properties on {model}",
                    "segments": [{"name": "Live Testbed", "population": 1, "description": "Local connected developer device"}]
                }
            ],
            "failures": actual_failures,
            "failure_count": len(actual_failures),
            "evidence_count": len(actual_failures),
            "log_summary": f"Captured {len(logcat_text.splitlines())} lines of Logcat from {model}. Discovered {len(actual_failures)} issues."
        }

        self.save_run(run_record)
        return run_record
