import re
from typing import List, Dict, Any

class LogcatCollector:
    """
    Parses real Logcat streams to detect crash stacktraces, ANRs, and OOM indicators.
    Labels unverified or partial findings appropriately.
    """

    CRASH_REGEX = re.compile(r"FATAL EXCEPTION:\s*(.+)|AndroidRuntime:\s*FATAL EXCEPTION|Fatal signal \d+", re.IGNORECASE)
    ANR_REGEX = re.compile(r"ANR in\s+([a-zA-Z0-9_\.]+)|Input dispatching timed out", re.IGNORECASE)
    OOM_REGEX = re.compile(r"OutOfMemoryError|lowmemorykiller|art::GC::DumpForSigQuit", re.IGNORECASE)

    @classmethod
    def analyze_logcat_output(cls, logcat_text: str) -> List[Dict[str, Any]]:
        findings = []

        if not logcat_text:
            return findings

        # Check for Fatal Crash
        crash_matches = cls.CRASH_REGEX.findall(logcat_text)
        if crash_matches:
            findings.append({
                "category": "Application crash",
                "title": "Uncaught Exception / Fatal Crash Detected in Logcat",
                "severity": "Critical",
                "confidence": "High (Direct Logcat match)",
                "evidence": logcat_text[:1200]
            })

        # Check for ANR
        anr_matches = cls.ANR_REGEX.findall(logcat_text)
        if anr_matches:
            findings.append({
                "category": "Application not responding (ANR)",
                "title": "Application ANR Event Detected in Logcat",
                "severity": "Critical",
                "confidence": "High (Direct Logcat match)",
                "evidence": logcat_text[:1000]
            })

        # Check for OOM / Low Memory Killer
        oom_matches = cls.OOM_REGEX.findall(logcat_text)
        if oom_matches:
            findings.append({
                "category": "Lost application state after process interruption",
                "title": "Low Memory Killer Event or OutOfMemory in Logcat",
                "severity": "High",
                "confidence": "Medium (Log signature match)",
                "evidence": logcat_text[:800]
            })

        return findings
