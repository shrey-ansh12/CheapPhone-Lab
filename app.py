import os
import json
import logging
from typing import Dict, Any, List
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, Response, send_from_directory
)
from dotenv import load_dotenv

from database.neo4j_client import Neo4jClient
from database.graph_schema import init_neo4j_schema
from database.graph_queries import (
    get_graph_overview, query_failure_subgraph, query_related_failures_by_condition
)
from core.test_runner import TestRunner
from core.impact_analyzer import ImpactAnalyzer
from core.failure_detector import FailureDetector
from testing.adb_manager import ADBManager
from reports.report_generator import ReportGenerator

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CheapPhoneLab")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cheapphone-lab-secret-2026")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024 # 64MB max APK upload

# Initialize services
runner = TestRunner()
neo4j = Neo4jClient()
if neo4j.is_connected:
    init_neo4j_schema(neo4j)

# Seed realistic demo test run if storage is empty so dashboard is immediately rich & demonstrable
def ensure_seed_data():
    runs = runner.load_runs()
    if not runs:
        logger.info("Initializing baseline demo simulation run for HackFront presentation...")
        runner.execute_simulation(
            app_name="KisanBazaar Rural Grocery App",
            description="Baseline Stress Test across Indian 2G/EDGE Transit & 2GB RAM Devices",
            profile_id="budget_1",
            network_condition="Slow connection",
            storage_level="Low (Under 500MB)",
            memory_pressure="High",
            battery_saver="Enabled",
            background_interruption="Incoming Call",
            iterations=3
        )
        runner.execute_simulation(
            app_name="BharatPay UPI Lite",
            description="Payment Gateway Timeout & Duplicate Submission Audit under Intermittent Network",
            profile_id="budget_2",
            network_condition="Intermittent connectivity",
            storage_level="Adequate (Over 2GB)",
            memory_pressure="Normal",
            battery_saver="Disabled",
            background_interruption="None",
            iterations=2
        )

ensure_seed_data()

# Inject common context (Neo4j status) to all templates
@app.context_processor
def inject_global_status():
    return {
        "neo4j_status": neo4j.get_status(),
        "adb_installed": ADBManager.is_adb_installed(),
        "adb_version": ADBManager.get_adb_version()
    }

# ----------------- 1. DASHBOARD -----------------
@app.route("/")
def dashboard():
    runs = runner.load_runs()
    all_failures = runner.get_all_failures()

    total_runs = len(runs)
    passed_runs = sum(1 for r in runs if r.get("status") == "Passed")
    failed_runs = sum(1 for r in runs if r.get("status") == "Failed")
    simulated_runs = sum(1 for r in runs if r.get("is_simulation", True))
    real_runs = total_runs - simulated_runs

    # Failures by category
    category_counts = {}
    for f in all_failures:
        c = f.get("category", "Other")
        category_counts[c] = category_counts.get(c, 0) + 1

    # Failures by severity
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in all_failures:
        s = f.get("severity", "Medium")
        if s in severity_counts:
            severity_counts[s] += 1

    # Most affected features
    feature_counts = {}
    for f in all_failures:
        fname = f.get("feature", {}).get("name", "Core")
        feature_counts[fname] = feature_counts.get(fname, 0) + 1
    top_features = dict(sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:5])

    # Top priority issues (Critical & High)
    top_issues = [f for f in all_failures if f.get("severity") in ["Critical", "High"]][:6]

    stats = {
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "simulated_runs": simulated_runs,
        "real_runs": real_runs,
        "critical_high_count": severity_counts["Critical"] + severity_counts["High"]
    }

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        stats=stats,
        recent_runs=runs[:5],
        top_issues=top_issues,
        top_features=top_features,
        category_chart_data=category_counts,
        severity_chart_data=severity_counts
    )

# ----------------- 2. TEST LAB -----------------
@app.route("/test-lab")
def test_lab():
    profiles = runner.load_profiles()
    connected_devices = ADBManager.list_connected_devices()
    return render_template(
        "test_lab.html",
        active_page="test_lab",
        profiles=profiles,
        connected_devices=connected_devices
    )

@app.route("/test-lab/simulate", methods=["POST"])
def start_simulation():
    app_name = request.form.get("app_name", "Demo Application").strip()
    description = request.form.get("description", "").strip()
    profile_id = request.form.get("profile_id", "budget_1")
    network_condition = request.form.get("network_condition", "Slow connection")
    storage_level = request.form.get("storage_level", "Low (Under 500MB)")
    memory_pressure = request.form.get("memory_pressure", "High")
    battery_saver = request.form.get("battery_saver", "Enabled")
    background_interruption = request.form.get("background_interruption", "None")
    iterations = int(request.form.get("iterations", 1))

    run = runner.execute_simulation(
        app_name=app_name,
        description=description,
        profile_id=profile_id,
        network_condition=network_condition,
        storage_level=storage_level,
        memory_pressure=memory_pressure,
        battery_saver=battery_saver,
        background_interruption=background_interruption,
        iterations=iterations
    )

    flash(f"Simulation run {run['id']} completed! Discovered {run['failure_count']} failure pattern(s).", "info")
    return redirect(url_for("run_detail", run_id=run["id"]))

@app.route("/test-lab/real", methods=["POST"])
def start_real_test():
    app_name = request.form.get("app_name", "").strip()
    device_serial = request.form.get("device_serial", "").strip()
    description = request.form.get("description", "").strip()

    if not app_name or not device_serial:
        flash("Application name and target device serial are required.", "danger")
        return redirect(url_for("test_lab"))

    apk_file = request.files.get("apk_file")
    saved_apk_path = None
    if apk_file and apk_file.filename.endswith(".apk"):
        safe_name = f"app_{uuid.uuid4().hex[:8]}.apk"
        saved_apk_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
        apk_file.save(saved_apk_path)

    try:
        run = runner.execute_real_emulator_test(
            app_name=app_name,
            description=description,
            device_serial=device_serial,
            apk_path=saved_apk_path,
            iterations=1
        )
        flash(f"Real ADB test {run['id']} completed on {device_serial}!", "success")
        return redirect(url_for("run_detail", run_id=run["id"]))
    except Exception as e:
        flash(f"Real test failed: {str(e)}", "danger")
        return redirect(url_for("test_lab"))

# ----------------- 3. TEST RUNS -----------------
@app.route("/runs")
def test_runs():
    runs = runner.load_runs()
    return render_template("test_runs.html", active_page="test_runs", runs=runs)

@app.route("/runs/<run_id>")
def run_detail(run_id):
    run = runner.get_run_by_id(run_id)
    if not run:
        flash(f"Test run {run_id} not found.", "danger")
        return redirect(url_for("test_runs"))
    return render_template("run_detail.html", active_page="test_runs", run=run)

# ----------------- 4. FAILURE EXPLORER -----------------
@app.route("/failures")
def failure_explorer():
    failures = runner.get_all_failures()

    category = request.args.get("category", "").strip()
    severity = request.args.get("severity", "").strip()
    mode = request.args.get("mode", "").strip()

    filtered = failures
    if category:
        filtered = [f for f in filtered if f.get("category") == category]
    if severity:
        filtered = [f for f in filtered if f.get("severity") == severity]
    if mode:
        filtered = [f for f in filtered if mode.lower() in f.get("mode", "").lower()]

    return render_template(
        "failure_explorer.html",
        active_page="failure_explorer",
        failures=filtered,
        categories=FailureDetector.CATEGORIES,
        selected_category=category,
        selected_severity=severity,
        selected_mode=mode
    )

@app.route("/failures/<failure_id>")
def failure_detail(failure_id):
    f = runner.get_failure_by_id(failure_id)
    if not f:
        flash(f"Failure record {failure_id} not found.", "danger")
        return redirect(url_for("failure_explorer"))
    return render_template("failure_detail.html", active_page="failure_explorer", failure=f)

# ----------------- 5. IMPACT ANALYSIS -----------------
@app.route("/impact-analysis", methods=["GET", "POST"])
def impact_analysis():
    assumptions = ImpactAnalyzer.DEFAULT_ASSUMPTIONS.copy()

    if request.method == "POST":
        try:
            pop = int(request.form.get("population", 5000000))
            ram_prev = float(request.form.get("ram_prev", 38)) / 100.0
            net_prev = float(request.form.get("net_prev", 42)) / 100.0

            assumptions["target_user_population"] = pop
            assumptions["prevalence"]["2GB_or_less_ram"] = ram_prev
            assumptions["prevalence"]["slow_intermittent_network"] = net_prev
        except Exception as e:
            flash(f"Error parsing demographic inputs: {e}", "warning")

    failures = runner.get_all_failures()
    ranked = ImpactAnalyzer.rank_failures(failures, assumptions)

    return render_template(
        "impact_analysis.html",
        active_page="impact_analysis",
        ranked_failures=ranked,
        assumptions=assumptions
    )

# ----------------- 6. GRAPH EXPLORER -----------------
@app.route("/graph-explorer")
def graph_explorer():
    return _render_graph_view(None)

@app.route("/graph-explorer/query/<failure_id>")
def graph_explorer_query(failure_id):
    return _render_graph_view(failure_id)

def _render_graph_view(target_failure_id: str = None):
    # Fetch from live Neo4j if available, or build deterministic connected graph from saved runs
    graph_data = {"nodes": [], "edges": []}
    condition_correlations = []

    if neo4j.is_connected:
        try:
            if target_failure_id:
                graph_data = query_failure_subgraph(neo4j, target_failure_id)
            else:
                graph_data = get_graph_overview(neo4j)
        except Exception as e:
            logger.error("Error querying Neo4j graph: %s", e)

    # Fallback or supplementary visualization from local runs
    if not graph_data.get("nodes"):
        runs = runner.load_runs()
        nodes_dict = {}
        edges_list = []

        for r in runs[:4]:
            run_node_id = f"Run_{r['id'][-6:]}"
            nodes_dict[run_node_id] = {"id": run_node_id, "label": f"TestRun\n{r['app_name'][:12]}", "group": "TestRun", "title": r["id"]}
            
            # App node
            app_node_id = f"App_{r['app_name']}"
            nodes_dict[app_node_id] = {"id": app_node_id, "label": f"App\n{r['app_name'][:14]}", "group": "Application", "title": r["app_name"]}
            edges_list.append({"from": run_node_id, "to": app_node_id, "label": "TESTED"})

            # Device node
            dev = r.get("device_profile", {})
            dev_node_id = f"Dev_{dev.get('id', 'dev')}"
            nodes_dict[dev_node_id] = {"id": dev_node_id, "label": f"Device\n{dev.get('name', 'Android')[:14]}", "group": "DeviceProfile", "title": dev.get('name')}
            edges_list.append({"from": run_node_id, "to": dev_node_id, "label": "USED_DEVICE"})

            # Condition node
            net_cond = r.get("conditions_summary", {}).get("network_condition", "2G Network")
            cond_node_id = f"Cond_{net_cond}"
            nodes_dict[cond_node_id] = {"id": cond_node_id, "label": f"Condition\n{net_cond[:14]}", "group": "Condition", "title": net_cond}
            edges_list.append({"from": run_node_id, "to": cond_node_id, "label": "USED_CONDITION"})

            # Failures
            for f in r.get("failures", []):
                f_node_id = f"Fail_{f['id'][-6:]}"
                nodes_dict[f_node_id] = {"id": f_node_id, "label": f"Failure\n{f['category'][:14]}", "group": "Failure", "title": f["title"]}
                edges_list.append({"from": run_node_id, "to": f_node_id, "label": "DISCOVERED"})

                feat = f.get("feature", {})
                feat_node_id = f"Feat_{feat.get('id', 'core')}"
                nodes_dict[feat_node_id] = {"id": feat_node_id, "label": f"Feature\n{feat.get('name', 'Feature')[:14]}", "group": "AppFeature", "title": feat.get('name')}
                edges_list.append({"from": f_node_id, "to": feat_node_id, "label": "AFFECTS"})

                condition_correlations.append({
                    "condition": net_cond,
                    "failure_title": f["title"],
                    "feature": feat.get("name", "Core"),
                    "severity": f["severity"],
                    "run_id": r["id"]
                })

        graph_data = {"nodes": list(nodes_dict.values()), "edges": edges_list}

    return render_template(
        "graph_explorer.html",
        active_page="graph_explorer",
        graph_data=graph_data,
        condition_correlations=condition_correlations[:10],
        target_failure_id=target_failure_id
    )

# ----------------- 7. DEVICE PROFILES -----------------
@app.route("/device-profiles")
def device_profiles():
    profiles = runner.load_profiles()
    return render_template("device_profiles.html", active_page="device_profiles", profiles=profiles)

@app.route("/device-profiles/create", methods=["POST"])
def create_profile():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Profile name is required.", "danger")
        return redirect(url_for("device_profiles"))

    profile_data = {
        "name": name,
        "android_version": request.form.get("android_version", "Android 10"),
        "ram_category": request.form.get("ram_category", "2GB"),
        "storage": request.form.get("storage", "16GB"),
        "screen": request.form.get("screen", "720x1520"),
        "network_config": request.form.get("network_config", "4G / 2G commute drops"),
        "battery_saver": request.form.get("battery_saver", "Enabled"),
        "description": request.form.get("description", "Custom profile"),
        "is_demo_profile": True
    }
    runner.save_profile(profile_data)
    flash(f"Device profile '{name}' saved successfully.", "success")
    return redirect(url_for("device_profiles"))

# ----------------- 8. REPORTS -----------------
@app.route("/reports")
def reports_view():
    runs = runner.load_runs()
    return render_template("reports.html", active_page="reports", runs=runs)

@app.route("/reports/export/<run_id>/<fmt>")
def export_report(run_id, fmt):
    run = runner.get_run_by_id(run_id)
    if not run:
        flash(f"Run {run_id} not found.", "danger")
        return redirect(url_for("reports_view"))

    if fmt == "json":
        data = ReportGenerator.generate_json_report(run)
        return Response(
            data,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename=cheapphone_report_{run_id}.json"}
        )
    else:
        data = ReportGenerator.generate_markdown_report(run)
        return Response(
            data,
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment;filename=cheapphone_report_{run_id}.md"}
        )

# ----------------- 9. SETTINGS -----------------
@app.route("/settings")
def settings_view():
    return render_template("settings.html", active_page="settings")

@app.route("/settings/update", methods=["POST"])
def update_settings():
    stype = request.form.get("setting_type")
    if stype == "neo4j":
        uri = request.form.get("neo4j_uri", "").strip()
        username = request.form.get("neo4j_username", "").strip()
        password = request.form.get("neo4j_password", "").strip()

        # Update environment variables
        os.environ["NEO4J_URI"] = uri
        os.environ["NEO4J_USERNAME"] = username
        os.environ["NEO4J_PASSWORD"] = password

        # Re-initialize client
        global neo4j
        neo4j._initialized = False
        neo4j._connect()
        if neo4j.is_connected:
            init_neo4j_schema(neo4j)
            flash("Neo4j AuraDB connected and schema initialized successfully!", "success")
        else:
            flash(f"Could not connect to Neo4j: {neo4j.connection_error}", "warning")

    return redirect(url_for("settings_view"))

# ----------------- API ENDPOINTS -----------------
@app.route("/api/runs")
def api_runs():
    return jsonify(runner.load_runs())

@app.route("/api/failures")
def api_failures():
    return jsonify(runner.get_all_failures())

@app.route("/api/graph")
def api_graph():
    return jsonify(get_graph_overview(neo4j))

@app.route("/api/status")
def api_status():
    return jsonify({
        "status": "online",
        "neo4j": neo4j.get_status(),
        "adb": {
            "installed": ADBManager.is_adb_installed(),
            "version": ADBManager.get_adb_version()
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
