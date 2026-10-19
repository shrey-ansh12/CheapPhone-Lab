import pytest
from core.impact_analyzer import ImpactAnalyzer
from core.demo_scenarios import generate_simulated_failures
from reports.report_generator import ReportGenerator
from database.neo4j_client import Neo4jClient
from testing.adb_manager import ADBManager

def test_impact_calculation_formula():
    """Verify formula: Pop * Prev * FailureProb and normalized priority score."""
    sample_failure = {
        "id": "FAIL_123",
        "title": "Out of Memory",
        "category": "Application crash",
        "severity": "Critical",
        "confidence": "Deterministic (High)"
    }
    assumptions = {
        "target_user_population": 1000000,
        "prevalence": {"2GB_or_less_ram": 0.40},
        "default_failure_probability": 0.80,
        "reproducibility": 0.90
    }
    impact = ImpactAnalyzer.calculate_impact(sample_failure, assumptions)
    assert impact["target_population"] == 1000000
    # Expected affected = 1,000,000 * 0.40 * 0.80 = 320,000
    assert impact["estimated_affected_users"] == 320000
    assert impact["priority_score"] >= 80.0
    assert impact["action_badge"] == "danger"

def test_deterministic_simulation_rules():
    """Verify simulated failure generation produces expected OOM when RAM is constrained."""
    budget_profile = {
        "name": "BharatPhone Lite",
        "ram_category": "2GB RAM",
        "android_version": "Android 10 Go",
        "storage": "16GB (450MB available)"
    }
    conditions = {
        "network_condition": "Slow connection",
        "storage_level": "Low (Under 500MB)",
        "memory_pressure": "High",
        "battery_saver": "Enabled",
        "background_interruption": "Incoming Call"
    }
    failures = generate_simulated_failures(budget_profile, conditions, "RUN_TEST_001")
    assert len(failures) >= 3

    categories = [f["category"] for f in failures]
    assert "Application crash" in categories
    assert "Network timeout" in categories
    assert "Storage write failure" in categories

def test_report_generation():
    """Verify markdown and JSON exports produce valid non-empty structured strings."""
    mock_run = {
        "id": "RUN_999",
        "app_name": "KisanApp",
        "mode": "Demo Simulation",
        "status": "Failed",
        "timestamp": "2026-10-19 12:00:00",
        "device_profile": {"name": "Test Phone", "ram_category": "2GB"},
        "conditions_summary": {"network_condition": "Slow 2G"},
        "failures": [
            {
                "id": "F1",
                "title": "Crash",
                "category": "Application crash",
                "severity": "Critical",
                "feature": {"name": "Catalog"},
                "confidence": "High",
                "reproduction_recipe": {
                    "steps": ["Step 1", "Step 2"],
                    "preconditions": "Precon",
                    "device_config": "2GB RAM",
                    "network_storage": "Slow",
                    "debug_direction": "Fix LRU cache"
                },
                "evidence": [{"type": "Logcat", "content": "Fatal error", "timestamp": "12:00"}]
            }
        ]
    }
    md = ReportGenerator.generate_markdown_report(mock_run)
    assert "# CheapPhone Lab" in md
    assert "KisanApp" in md
    assert "Reproduction Recipe" in md

    js = ReportGenerator.generate_json_report(mock_run)
    assert '"id": "RUN_999"' in js

def test_adb_graceful_missing_behavior():
    """Verify ADB commands don't crash when ADB binary is absent or devices are disconnected."""
    devices = ADBManager.list_connected_devices()
    assert isinstance(devices, list)

def test_neo4j_client_offline_graceful():
    """Verify Neo4j client reports offline mode without raising uncaught exceptions."""
    client = Neo4jClient()
    status = client.get_status()
    assert "connected" in status
    assert "mode" in status
