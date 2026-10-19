import logging
from .neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

SCHEMA_CONSTRAINTS = [
    "CREATE CONSTRAINT app_name_unique IF NOT EXISTS FOR (a:Application) REQUIRE a.name IS UNIQUE",
    "CREATE CONSTRAINT feature_id_unique IF NOT EXISTS FOR (f:AppFeature) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT device_id_unique IF NOT EXISTS FOR (d:DeviceProfile) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT condition_name_unique IF NOT EXISTS FOR (c:Condition) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT segment_name_unique IF NOT EXISTS FOR (s:UserSegment) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT testrun_id_unique IF NOT EXISTS FOR (t:TestRun) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT failure_id_unique IF NOT EXISTS FOR (f:Failure) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT recipe_id_unique IF NOT EXISTS FOR (r:ReproductionRecipe) REQUIRE r.id IS UNIQUE"
]

def init_neo4j_schema(client: Neo4jClient) -> bool:
    """
    Initializes uniqueness constraints and base indexes on Neo4j AuraDB.
    Returns True if successfully initialized, False otherwise.
    """
    if not client.is_connected:
        logger.info("Neo4j client not connected. Skipping constraint creation.")
        return False

    try:
        for cypher in SCHEMA_CONSTRAINTS:
            client.query(cypher)
        logger.info("Neo4j AuraDB schema constraints initialized successfully.")
        return True
    except Exception as e:
        logger.error("Failed to initialize Neo4j schema: %s", e)
        return False
