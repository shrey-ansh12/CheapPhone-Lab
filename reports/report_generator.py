import json
from typing import Dict, Any

class ReportGenerator:
    """
    Exports comprehensive test run and failure reports in clean JSON and Markdown formats.
    """

    @staticmethod
    def generate_json_report(run_data: Dict[str, Any]) -> str:
        return json.dumps(run_data, indent=2)

    @staticmethod
    def generate_markdown_report(run_data: Dict[str, Any]) -> str:
        app_name = run_data.get("app_name", "Application")
        run_id = run_data.get("id", "N/A")
        mode = run_data.get("mode", "Simulation")
        status = run_data.get("status", "Completed")
        timestamp = run_data.get("timestamp", "")
        profile = run_data.get("device_profile", {})
        failures = run_data.get("failures", [])

        md = []
        md.append(f"# CheapPhone Lab — Test Execution Report")
        md.append(f"**Tagline:** Test Beyond the Flagship | HackFront India 2026\n")
        md.append(f"| Metric | Details |")
        md.append(f"| :--- | :--- |")
        md.append(f"| **Application** | `{app_name}` |")
        md.append(f"| **Run ID** | `{run_id}` |")
        md.append(f"| **Execution Mode** | {mode} |")
        md.append(f"| **Status** | **{status}** |")
        md.append(f"| **Timestamp** | {timestamp} |")
        md.append(f"| **Failures Discovered** | {len(failures)} |")
        md.append(f"| **Device Profile** | {profile.get('name', 'N/A')} ({profile.get('ram_category', '')}) |")
        md.append(f"| **Android Version** | {profile.get('android_version', 'N/A')} |")
        md.append("")

        md.append("## 1. Environmental & Stress Conditions")
        cond = run_data.get("conditions_summary", {})
        for k, v in cond.items():
            formatted_key = k.replace("_", " ").title()
            md.append(f"- **{formatted_key}:** {v}")
        md.append("")

        md.append("## 2. Discovered Failures & Reproduction Recipes")
        if not failures:
            md.append("> *No failures were detected under this test execution.*")
        else:
            for idx, f in enumerate(failures, 1):
                md.append(f"### {idx}. [{f.get('severity', 'Medium')}] {f.get('title')}")
                md.append(f"- **Failure ID:** `{f.get('id')}`")
                md.append(f"- **Category:** {f.get('category')}")
                md.append(f"- **Feature Affected:** {f.get('feature', {}).get('name', 'Core')}")
                md.append(f"- **Confidence:** {f.get('confidence', 'High')}")
                md.append(f"- **Expected Behavior:** {f.get('expected_behavior')}")
                md.append(f"- **Observed Behavior:** {f.get('observed_behavior')}")
                md.append(f"- **Suggested Debugging:** {f.get('suggested_debugging')}\n")

                recipe = f.get("reproduction_recipe", {})
                md.append(f"#### Reproduction Recipe")
                md.append(f"- **Preconditions:** {recipe.get('preconditions')}")
                md.append(f"- **Hardware/OS Config:** {recipe.get('device_config')}")
                md.append(f"- **Network & Storage State:** {recipe.get('network_storage')}")
                md.append("##### Steps to Reproduce:")
                for step_idx, step in enumerate(recipe.get("steps", []), 1):
                    md.append(f"  {step_idx}. {step}")
                md.append("")

                md.append(f"#### Diagnostic Evidence")
                for ev in f.get("evidence", []):
                    md.append(f"```text\n// {ev.get('type')} ({ev.get('timestamp')})\n{ev.get('content')}\n```")
                md.append("---")

        md.append("\n## 3. Prioritization & Developer Guidance")
        md.append("Under typical Indian telecom and budget handset demographics, application failures caused by "
                  "low memory pressure or high latency degrade user retention significantly. Address critical OOM and ANR "
                  "blockers before advancing release trains.")

        return "\n".join(md)
