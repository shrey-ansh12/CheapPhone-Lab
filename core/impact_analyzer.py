from typing import Dict, Any, List

class ImpactAnalyzer:
    """
    Computes transparent user impact estimates and priority scores for discovered failures.

    Formula:
    Estimated affected users = Target User Population × Prevalence of Condition × Failure Probability under Condition

    Priority Score:
    Score = (Severity Weight × 0.40) + (User Reach Factor × 0.30) + (Reproducibility Factor × 0.20) + (Confidence Factor × 0.10)
    Normalized to a 0-100 scale.
    """

    SEVERITY_WEIGHTS = {
        "Critical": 1.0,
        "High": 0.75,
        "Medium": 0.45,
        "Low": 0.20
    }

    CONFIDENCE_WEIGHTS = {
        "Deterministic (High)": 1.0,
        "High": 0.9,
        "High (Simulated 2G/EDGE RTT)": 0.85,
        "High (Direct Logcat match)": 0.95,
        "Medium": 0.65,
        "Medium (Log signature match)": 0.60,
        "Low": 0.35
    }

    # Default illustrative assumptions for India Tier 2/3 and budget mobile base
    DEFAULT_ASSUMPTIONS = {
        "target_user_population": 5000000, # 5 Million illustrative MAUs
        "prevalence": {
            "2GB_or_less_ram": 0.38, # 38% of active devices in target segment
            "slow_intermittent_network": 0.42, # 42% travel or low-coverage time
            "low_storage_under_500mb": 0.29, # 29% devices with full storage cache
            "battery_saver_active": 0.35 # 35% time battery saver turned on
        },
        "default_failure_probability": 0.85,
        "reproducibility": 0.90
    }

    @classmethod
    def calculate_impact(cls, failure: Dict[str, Any], user_assumptions: Dict[str, Any] = None) -> Dict[str, Any]:
        assumptions = cls.DEFAULT_ASSUMPTIONS.copy()
        if user_assumptions:
            assumptions.update(user_assumptions)

        pop = assumptions.get("target_user_population", 5000000)
        category = failure.get("category", "")
        severity = failure.get("severity", "Medium")
        confidence = failure.get("confidence", "Medium")

        # Map condition prevalence based on failure category
        prev_map = assumptions.get("prevalence", cls.DEFAULT_ASSUMPTIONS["prevalence"])
        if category in ["Application crash", "Unresponsive UI"]:
            prevalence = prev_map.get("2GB_or_less_ram", 0.38)
            condition_name = "Budget Hardware / <= 2GB RAM Devices"
        elif category in ["Network timeout", "Failed network request", "Duplicate form submission"]:
            prevalence = prev_map.get("slow_intermittent_network", 0.42)
            condition_name = "Intermittent 2G/4G Network or Commute Blindspots"
        elif category in ["Storage write failure"]:
            prevalence = prev_map.get("low_storage_under_500mb", 0.29)
            condition_name = "Constrained Flash Storage (< 500MB Free)"
        elif category in ["Application not responding (ANR)", "Lost application state after process interruption"]:
            prevalence = prev_map.get("battery_saver_active", 0.35)
            condition_name = "Battery Saver CPU Throttling or Aggressive LMK"
        else:
            prevalence = 0.25
            condition_name = "Combined Edge Condition"

        fail_prob = assumptions.get("default_failure_probability", 0.85)
        reproducibility = assumptions.get("reproducibility", 0.90)

        # Transparent affected users estimate
        estimated_affected_users = int(pop * prevalence * fail_prob)

        # Severity Factor (0 to 100)
        sev_factor = cls.SEVERITY_WEIGHTS.get(severity, 0.45) * 100

        # Reach Factor (log scaled or normalized up to population)
        reach_factor = min(100.0, (estimated_affected_users / (pop * 0.5)) * 100)

        # Repro Factor
        repro_factor = reproducibility * 100

        # Confidence Factor
        conf_weight = cls.CONFIDENCE_WEIGHTS.get(confidence, 0.70)
        conf_factor = conf_weight * 100

        # Priority calculation:
        # 40% Severity, 30% Reach, 20% Reproducibility, 10% Confidence
        priority_score = (sev_factor * 0.40) + (reach_factor * 0.30) + (repro_factor * 0.20) + (conf_factor * 0.10)
        priority_score = round(min(100.0, max(0.0, priority_score)), 1)

        # Action recommendation
        if priority_score >= 80:
            recommended_action = "P0: Immediate Release Blocker — Hotfix required before rollout."
            action_badge = "danger"
        elif priority_score >= 60:
            recommended_action = "P1: Sprint Priority — Refactor memory/network handling this sprint."
            action_badge = "warning"
        elif priority_score >= 40:
            recommended_action = "P2: Scheduled Improvement — Optimize view layout & cache pruning."
            action_badge = "info"
        else:
            recommended_action = "P3: Minor Polish — Monitor telemetry in next release."
            action_badge = "secondary"

        return {
            "failure_id": failure.get("id"),
            "title": failure.get("title"),
            "category": category,
            "severity": severity,
            "condition_name": condition_name,
            "prevalence_rate": round(prevalence * 100, 1),
            "target_population": pop,
            "estimated_affected_users": estimated_affected_users,
            "confidence": confidence,
            "priority_score": priority_score,
            "recommended_action": recommended_action,
            "action_badge": action_badge,
            "formula_explanation": (
                f"{pop:,} (Target Users) × {prevalence:.2f} ({condition_name}) × {fail_prob:.2f} (Failure Prob) "
                f"= {estimated_affected_users:,} estimated affected users"
            )
        }

    @classmethod
    def rank_failures(cls, failures: List[Dict[str, Any]], user_assumptions: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        ranked = [cls.calculate_impact(f, user_assumptions) for f in failures]
        ranked.sort(key=lambda x: x["priority_score"], reverse=True)
        for idx, item in enumerate(ranked):
            item["rank"] = idx + 1
        return ranked
