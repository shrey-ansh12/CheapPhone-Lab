import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FailureDetector:
    """
    Standardizes failure representation, assigns confidence metrics,
    and supports multi-category classification.
    """

    CATEGORIES = [
        "Application crash",
        "Application not responding (ANR)",
        "Network timeout",
        "Failed network request",
        "Content or image loading failure",
        "Unresponsive UI",
        "Lost application state after process interruption",
        "Storage write failure",
        "Duplicate form submission",
        "Excessive loading",
        "Layout or usability issue",
        "Failed test assertion"
    ]

    SEVERITIES = ["Critical", "High", "Medium", "Low"]

    @staticmethod
    def create_failure_record(
        failure_id: str,
        title: str,
        description: str,
        category: str,
        severity: str,
        feature: Dict[str, str],
        test_run_id: str,
        device_profile: Dict[str, Any],
        conditions: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        recipe: Dict[str, Any],
        confidence: str = "High",
        mode: str = "simulation",
        expected_behavior: str = "",
        observed_behavior: str = "",
        suggested_debugging: str = ""
    ) -> Dict[str, Any]:
        return {
            "id": failure_id,
            "title": title,
            "description": description,
            "category": category if category in FailureDetector.CATEGORIES else "Failed test assertion",
            "severity": severity if severity in FailureDetector.SEVERITIES else "Medium",
            "feature": feature,
            "test_run_id": test_run_id,
            "device_profile": device_profile,
            "conditions": conditions,
            "evidence": evidence,
            "reproduction_recipe": recipe,
            "confidence": confidence,
            "mode": mode,
            "expected_behavior": expected_behavior,
            "observed_behavior": observed_behavior,
            "suggested_debugging": suggested_debugging,
            "created_at": datetime.now().isoformat()
        }
