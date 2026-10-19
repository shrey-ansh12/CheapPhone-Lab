import os
import json
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Neo4jClient:
    """
    Manages connection to Neo4j AuraDB with graceful fallback to local storage
    if credentials are not provided or connection fails.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.uri = os.getenv("NEO4J_URI", "").strip()
        self.username = os.getenv("NEO4J_USERNAME", "").strip()
        self.password = os.getenv("NEO4J_PASSWORD", "").strip()
        self.driver = None
        self.is_connected = False
        self.connection_error = None
        self._connect()
        self._initialized = True

    def _connect(self):
        if not self.uri or not self.password:
            self.is_connected = False
            self.connection_error = "Neo4j AuraDB credentials not configured in environment variables."
            return

        try:
            from neo4j import GraphDatabase, basic_auth
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=basic_auth(self.username, self.password),
                connection_timeout=5.0,
                max_connection_lifetime=300
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            self.is_connected = True
            self.connection_error = None
            logger.info("Successfully connected to Neo4j AuraDB: %s", self.uri)
        except Exception as e:
            self.is_connected = False
            self.connection_error = f"Neo4j Connection Failed: {str(e)}"
            logger.warning("Neo4j AuraDB connection failed. Running in standalone local mode. Error: %s", e)

    def close(self):
        if self.driver:
            try:
                self.driver.close()
            except Exception:
                pass
            self.is_connected = False

    def query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a Cypher query using parameterized statements.
        Returns a list of dicts.
        """
        if not self.is_connected or not self.driver:
            raise ConnectionError(self.connection_error or "Neo4j is not connected.")

        parameters = parameters or {}
        try:
            with self.driver.session() as session:
                result = session.run(cypher, parameters)
                return [record.data() for record in result]
        except Exception as e:
            logger.error("Error executing Cypher query: %s | Params: %s | Error: %s", cypher, parameters, e)
            raise e

    def execute_write(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes a write transaction query.
        """
        if not self.is_connected or not self.driver:
            raise ConnectionError(self.connection_error or "Neo4j is not connected.")

        parameters = parameters or {}
        def _tx(tx):
            res = tx.run(cypher, parameters)
            return [record.data() for record in res]

        try:
            with self.driver.session() as session:
                return session.execute_write(_tx)
        except Exception as e:
            logger.error("Error executing write transaction: %s | Params: %s | Error: %s", cypher, parameters, e)
            raise e

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "uri": self.uri if self.is_connected else (self.uri[:15] + "..." if self.uri else "None"),
            "username": self.username if self.is_connected else "None",
            "error": self.connection_error,
            "mode": "Neo4j AuraDB (Live)" if self.is_connected else "Local File Store (AuraDB Disconnected)"
        }
