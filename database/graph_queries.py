import logging
from typing import Dict, Any, List, Optional
from .neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

def sync_test_run_to_graph(client: Neo4jClient, run_data: Dict[str, Any]) -> bool:
    """
    Persists a test run, device profile, conditions, failures, evidence,
    and reproduction recipes to Neo4j using MERGE statements to prevent duplication.
    """
    if not client.is_connected:
        return False

    cypher = """
    // 1. Merge Application
    MERGE (app:Application {name: $app_name})
    ON CREATE SET app.created_at = datetime()

    // 2. Merge Device Profile
    MERGE (dev:DeviceProfile {id: $device_id})
    SET dev.name = $device_name,
        dev.android_version = $device_android,
        dev.ram_category = $device_ram,
        dev.storage = $device_storage,
        dev.screen = $device_screen,
        dev.battery_saver = $device_battery

    // 3. Merge TestRun
    MERGE (tr:TestRun {id: $run_id})
    SET tr.timestamp = $timestamp,
        tr.mode = $run_mode,
        tr.status = $status,
        tr.iterations = $iterations,
        tr.description = $description

    // 4. Create relationships
    MERGE (tr)-[:TESTED]->(app)
    MERGE (tr)-[:USED_DEVICE]->(dev)

    // 5. Merge Conditions
    WITH tr, app, dev
    UNWIND $conditions AS cond_item
    MERGE (c:Condition {name: cond_item.name})
    SET c.category = cond_item.category,
        c.description = cond_item.description
    MERGE (tr)-[:USED_CONDITION]->(c)

    // Optional link Condition to UserSegment
    FOREACH (seg IN cond_item.segments |
        MERGE (s:UserSegment {name: seg.name})
        SET s.estimated_population = seg.population,
            s.description = seg.description
        MERGE (c)-[:COMMON_IN]->(s)
    )
    RETURN count(tr) as count
    """

    device = run_data.get("device_profile", {})
    conditions = run_data.get("conditions", [])

    params = {
        "app_name": run_data.get("app_name", "Unknown App"),
        "device_id": device.get("id", "unknown_device"),
        "device_name": device.get("name", "Generic Android"),
        "device_android": device.get("android_version", "Android 10"),
        "device_ram": device.get("ram_category", "2GB"),
        "device_storage": device.get("storage", "16GB"),
        "device_screen": device.get("screen", "720x1520"),
        "device_battery": device.get("battery_saver", "Enabled"),
        "run_id": run_data.get("id"),
        "timestamp": run_data.get("timestamp"),
        "run_mode": run_data.get("mode", "simulation"),
        "status": run_data.get("status", "completed"),
        "iterations": run_data.get("iterations", 1),
        "description": run_data.get("description", ""),
        "conditions": conditions
    }

    try:
        client.query(cypher, params)

        # Sync each failure
        for failure in run_data.get("failures", []):
            sync_failure_to_graph(client, run_data.get("id"), run_data.get("app_name"), failure)

        return True
    except Exception as e:
        logger.error("Failed to sync test run %s to graph: %s", run_data.get("id"), e)
        return False

def sync_failure_to_graph(client: Neo4jClient, run_id: str, app_name: str, failure: Dict[str, Any]) -> bool:
    """
    Persists a single Failure node along with affected AppFeature, Evidence, and ReproductionRecipe.
    """
    if not client.is_connected:
        return False

    cypher = """
    MATCH (tr:TestRun {id: $run_id})
    MATCH (app:Application {name: $app_name})

    // 1. Merge Failure
    MERGE (f:Failure {id: $failure_id})
    SET f.title = $title,
        f.description = $description,
        f.category = $category,
        f.severity = $severity,
        f.confidence = $confidence,
        f.mode = $mode,
        f.expected_behavior = $expected_behavior,
        f.observed_behavior = $observed_behavior,
        f.suggested_debugging = $suggested_debugging

    MERGE (tr)-[:DISCOVERED]->(f)

    // 2. Feature & Application linkage
    MERGE (feat:AppFeature {id: $feature_id})
    SET feat.name = $feature_name
    MERGE (app)-[:HAS_FEATURE]->(feat)
    MERGE (f)-[:AFFECTS]->(feat)

    // 3. Evidence
    WITH f
    UNWIND $evidence_list AS ev
    MERGE (e:Evidence {id: ev.id})
    SET e.type = ev.type,
        e.content = ev.content,
        e.timestamp = ev.timestamp
    MERGE (f)-[:SUPPORTED_BY]->(e)

    // 4. Recipe
    WITH f
    MERGE (r:ReproductionRecipe {id: $recipe.id})
    SET r.preconditions = $recipe.preconditions,
        r.device_config = $recipe.device_config,
        r.network_storage = $recipe.network_storage,
        r.steps = $recipe.steps,
        r.expected = $recipe.expected,
        r.observed = $recipe.observed,
        r.debug_direction = $recipe.debug_direction
    MERGE (f)-[:HAS_RECIPE]->(r)

    RETURN f.id as id
    """

    feature = failure.get("feature", {})
    recipe = failure.get("reproduction_recipe", {})
    evidence_list = failure.get("evidence", [])

    params = {
        "run_id": run_id,
        "app_name": app_name,
        "failure_id": failure.get("id"),
        "title": failure.get("title"),
        "description": failure.get("description"),
        "category": failure.get("category"),
        "severity": failure.get("severity"),
        "confidence": failure.get("confidence", "High"),
        "mode": failure.get("mode", "simulation"),
        "expected_behavior": failure.get("expected_behavior", ""),
        "observed_behavior": failure.get("observed_behavior", ""),
        "suggested_debugging": failure.get("suggested_debugging", ""),
        "feature_id": feature.get("id", "general"),
        "feature_name": feature.get("name", "Core Navigation"),
        "evidence_list": evidence_list,
        "recipe": {
            "id": recipe.get("id", f"recipe_{failure.get('id')}"),
            "preconditions": recipe.get("preconditions", ""),
            "device_config": recipe.get("device_config", ""),
            "network_storage": recipe.get("network_storage", ""),
            "steps": recipe.get("steps", []),
            "expected": recipe.get("expected", ""),
            "observed": recipe.get("observed", ""),
            "debug_direction": recipe.get("debug_direction", "")
        }
    }

    try:
        client.query(cypher, params)
        return True
    except Exception as e:
        logger.error("Failed to sync failure %s to graph: %s", failure.get("id"), e)
        return False

def get_graph_overview(client: Neo4jClient) -> Dict[str, Any]:
    """
    Retrieves summary stats and nodes/relationships for graph visualization.
    """
    if not client.is_connected:
        return {"connected": False, "nodes": [], "edges": [], "stats": {}}

    try:
        # Get counts
        counts_cypher = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        """
        counts_res = client.query(counts_cypher)
        counts = {r["label"]: r["count"] for r in counts_res if r["label"]}

        # Query recent nodes and relationships (limit 150 for clean visualization)
        graph_cypher = """
        MATCH (a)-[r]->(b)
        RETURN
            id(a) as source_id,
            labels(a)[0] as source_label,
            coalesce(a.name, a.title, a.id, 'Node') as source_name,
            id(b) as target_id,
            labels(b)[0] as target_label,
            coalesce(b.name, b.title, b.id, 'Node') as target_name,
            type(r) as rel_type
        LIMIT 100
        """
        records = client.query(graph_cypher)

        nodes_dict = {}
        edges = []

        for row in records:
            s_id = str(row["source_id"])
            t_id = str(row["target_id"])

            if s_id not in nodes_dict:
                nodes_dict[s_id] = {
                    "id": s_id,
                    "label": f"{row['source_label']}\n{row['source_name'][:18]}",
                    "group": row["source_label"],
                    "title": f"{row['source_label']}: {row['source_name']}"
                }
            if t_id not in nodes_dict:
                nodes_dict[t_id] = {
                    "id": t_id,
                    "label": f"{row['target_label']}\n{row['target_name'][:18]}",
                    "group": row["target_label"],
                    "title": f"{row['target_label']}: {row['target_name']}"
                }

            edges.append({
                "from": s_id,
                "to": t_id,
                "label": row["rel_type"],
                "arrows": "to"
            })

        return {
            "connected": True,
            "nodes": list(nodes_dict.values()),
            "edges": edges,
            "stats": counts
        }
    except Exception as e:
        logger.error("Error fetching graph overview: %s", e)
        return {"connected": False, "error": str(e), "nodes": [], "edges": [], "stats": {}}

def query_failure_subgraph(client: Neo4jClient, failure_id: str) -> Dict[str, Any]:
    """
    Retrieves the complete graph neighborhood of a specific failure:
    TestRun -> DISCOVERED -> Failure -> AFFECTS -> AppFeature
    Failure -> SUPPORTED_BY -> Evidence
    Failure -> HAS_RECIPE -> ReproductionRecipe
    TestRun -> USED_CONDITION -> Condition -> COMMON_IN -> UserSegment
    """
    if not client.is_connected:
        return {"connected": False, "nodes": [], "edges": [], "details": {}}

    cypher = """
    MATCH (f:Failure {id: $failure_id})
    OPTIONAL MATCH (tr:TestRun)-[r1:DISCOVERED]->(f)
    OPTIONAL MATCH (f)-[r2:AFFECTS]->(feat:AppFeature)
    OPTIONAL MATCH (f)-[r3:SUPPORTED_BY]->(ev:Evidence)
    OPTIONAL MATCH (f)-[r4:HAS_RECIPE]->(recipe:ReproductionRecipe)
    OPTIONAL MATCH (tr)-[r5:USED_CONDITION]->(c:Condition)
    OPTIONAL MATCH (c)-[r6:COMMON_IN]->(seg:UserSegment)
    OPTIONAL MATCH (tr)-[r7:USED_DEVICE]->(dev:DeviceProfile)
    RETURN f, tr, feat, ev, recipe, c, seg, dev
    """
    try:
        rows = client.query(cypher, {"failure_id": failure_id})
        nodes_dict = {}
        edges = []
        failure_details = {}

        for row in rows:
            if not failure_details and row.get("f"):
                failure_details = row["f"]

            # Helper to add node & edge
            def add_n(node_obj, label_fallback):
                if not node_obj:
                    return None
                n_id = str(node_obj.get("id") or node_obj.get("name") or id(node_obj))
                label = node_obj.get("title") or node_obj.get("name") or n_id
                nodes_dict[n_id] = {
                    "id": n_id,
                    "label": f"{label_fallback}\n{label[:20]}",
                    "group": label_fallback,
                    "title": str(node_obj)
                }
                return n_id

            fid = add_n(row.get("f"), "Failure")
            trid = add_n(row.get("tr"), "TestRun")
            featid = add_n(row.get("feat"), "AppFeature")
            evid = add_n(row.get("ev"), "Evidence")
            recid = add_n(row.get("recipe"), "ReproductionRecipe")
            cid = add_n(row.get("c"), "Condition")
            segid = add_n(row.get("seg"), "UserSegment")
            devid = add_n(row.get("dev"), "DeviceProfile")

            if trid and fid:
                edges.append({"from": trid, "to": fid, "label": "DISCOVERED", "arrows": "to"})
            if fid and featid:
                edges.append({"from": fid, "to": featid, "label": "AFFECTS", "arrows": "to"})
            if fid and evid:
                edges.append({"from": fid, "to": evid, "label": "SUPPORTED_BY", "arrows": "to"})
            if fid and recid:
                edges.append({"from": fid, "to": recid, "label": "HAS_RECIPE", "arrows": "to"})
            if trid and cid:
                edges.append({"from": trid, "to": cid, "label": "USED_CONDITION", "arrows": "to"})
            if cid and segid:
                edges.append({"from": cid, "to": segid, "label": "COMMON_IN", "arrows": "to"})
            if trid and devid:
                edges.append({"from": trid, "to": devid, "label": "USED_DEVICE", "arrows": "to"})

        return {
            "connected": True,
            "nodes": list(nodes_dict.values()),
            "edges": edges,
            "details": failure_details
        }
    except Exception as e:
        logger.error("Failed to query subgraph for %s: %s", failure_id, e)
        return {"connected": False, "nodes": [], "edges": [], "error": str(e)}

def query_related_failures_by_condition(client: Neo4jClient, condition_name: str) -> List[Dict[str, Any]]:
    """
    Finds failures that occur under identical network/storage conditions across multiple test runs.
    Demonstrates graph pattern matching power.
    """
    if not client.is_connected:
        return []

    cypher = """
    MATCH (c:Condition {name: $condition_name})<-[:USED_CONDITION]-(tr:TestRun)-[:DISCOVERED]->(f:Failure)
    OPTIONAL MATCH (f)-[:AFFECTS]->(feat:AppFeature)
    RETURN DISTINCT
        f.id as failure_id,
        f.title as title,
        f.severity as severity,
        f.category as category,
        feat.name as feature_name,
        tr.id as test_run_id,
        tr.timestamp as timestamp
    LIMIT 20
    """
    try:
        return client.query(cypher, {"condition_name": condition_name})
    except Exception as e:
        logger.error("Error querying related failures: %s", e)
        return []
