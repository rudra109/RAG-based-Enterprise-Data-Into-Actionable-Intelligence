"""
EnterpriseIQ ML — Knowledge Graph Extraction Engine
Month 6 deliverable.

Pipeline:
  1. Cloud Natural Language API → basic entity extraction
  2. Gemini Pro → rich relationship extraction (nodes + edges)
  3. Merge + entity resolution (deduplicate similar entities)
  4. Write to Spanner Graph + BigQuery
  5. NL-to-GQL query conversion
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog
import vertexai
from google.cloud import language_v2
from google.cloud import spanner
from vertexai.generative_models import GenerationConfig, GenerativeModel

from shared.bigquery_client import BigQueryClient
from shared.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class KGNode:
    node_id: str
    entity_type: str   # PERSON | ORG | PRODUCT | CONCEPT | LOCATION | EVENT
    entity_name: str
    properties: dict = field(default_factory=dict)
    source_doc_id: str = ""
    confidence: float = 1.0
    graph_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class KGEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    properties: dict = field(default_factory=dict)
    source_doc_id: str = ""
    confidence: float = 1.0
    graph_id: str = ""


@dataclass
class KGExtraction:
    nodes: list[KGNode]
    edges: list[KGEdge]
    doc_id: str
    graph_id: str
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


@dataclass
class GraphQueryResult:
    gql: str
    nodes: list[dict]
    edges: list[dict]
    row_count: int


class KnowledgeGraphExtractor:
    """
    Knowledge Graph extraction and query engine.
    Developer B Month 6.
    """

    # Cloud NLP → our canonical entity type mapping
    NLP_TYPE_MAP = {
        "PERSON": "PERSON",
        "ORGANIZATION": "ORG",
        "LOCATION": "LOCATION",
        "EVENT": "EVENT",
        "WORK_OF_ART": "CONCEPT",
        "CONSUMER_GOOD": "PRODUCT",
        "OTHER": "CONCEPT",
        "UNKNOWN": "CONCEPT",
    }

    def __init__(self) -> None:
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)
        self._gemini_pro = GenerativeModel(settings.gemini_pro_model)
        self._gemini_flash = GenerativeModel(settings.gemini_flash_model)
        self._nl_client = language_v2.LanguageServiceClient()
        self._bq = BigQueryClient()

        # Spanner client (for graph writes + queries)
        try:
            self._spanner_client = spanner.Client(project=settings.gcp_project_id)
            self._spanner_instance = self._spanner_client.instance(settings.spanner_instance_id)
            self._spanner_db = self._spanner_instance.database(settings.spanner_database_id)
            self._spanner_available = True
        except Exception as e:
            logger.warning("Spanner not available", error=str(e))
            self._spanner_available = False

        logger.info("KnowledgeGraphExtractor initialised")

    # ── Step 1: Cloud NLP Extraction ──────────────────────────────────────────

    def _extract_with_nlp_api(self, text: str, doc_id: str,
                               graph_id: str) -> list[KGNode]:
        """Extract entities using Cloud Natural Language API."""
        document = language_v2.Document(
            content=text[:1_000_000],  # 1MB limit
            type_=language_v2.Document.Type.PLAIN_TEXT,
        )

        try:
            response = self._nl_client.analyze_entities(
                request={"document": document}
            )
        except Exception as e:
            logger.warning("Cloud NLP API failed", error=str(e))
            return []

        nodes: list[KGNode] = []
        for entity in response.entities:
            entity_type = self.NLP_TYPE_MAP.get(
                language_v2.Entity.Type(entity.type_).name, "CONCEPT"
            )
            nodes.append(KGNode(
                node_id=str(uuid.uuid4()),
                entity_type=entity_type,
                entity_name=entity.name,
                properties={
                    "salience": round(entity.salience, 4),
                    "mentions": len(entity.mentions),
                    "metadata": dict(entity.metadata),
                },
                source_doc_id=doc_id,
                confidence=round(entity.salience, 4),
                graph_id=graph_id,
            ))

        return nodes

    # ── Step 2: Gemini Pro Extraction ─────────────────────────────────────────

    def _extract_with_gemini(self, text: str, doc_id: str,
                              graph_id: str) -> tuple[list[KGNode], list[KGEdge]]:
        """Extract rich entities and relationships using Gemini Pro."""

        prompt = f"""Extract all entities and relationships from this document.

Return ONLY valid JSON in exactly this format (no markdown, no explanation):
{{
  "nodes": [
    {{
      "id": "unique_id_string",
      "type": "PERSON|ORG|PRODUCT|CONCEPT|LOCATION|EVENT",
      "name": "entity name",
      "properties": {{"description": "optional description"}}
    }}
  ],
  "edges": [
    {{
      "source": "node_id",
      "target": "node_id",
      "type": "RELATIONSHIP_TYPE_IN_CAPS",
      "properties": {{"weight": 1.0}}
    }}
  ]
}}

Important:
- Use CAPS_WITH_UNDERSCORES for relationship types (e.g., WORKS_FOR, FOUNDED, ACQUIRED)
- Only include confident relationships with clear textual evidence
- node IDs must be unique alphanumeric strings

Document text (first 4000 chars):
{text[:4000]}"""

        try:
            response = self._gemini_pro.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.0, max_output_tokens=4096),
            )
            raw = response.text.strip()

            # Strip markdown code blocks if present
            raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw)

            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Gemini KG JSON parse failed", error=str(e))
            return [], []
        except Exception as e:
            logger.error("Gemini KG extraction failed", error=str(e))
            return [], []

        id_to_node_id: dict[str, str] = {}
        nodes: list[KGNode] = []

        for n in data.get("nodes", []):
            node_id = str(uuid.uuid4())
            id_to_node_id[n.get("id", "")] = node_id
            nodes.append(KGNode(
                node_id=node_id,
                entity_type=n.get("type", "CONCEPT"),
                entity_name=n.get("name", ""),
                properties=n.get("properties", {}),
                source_doc_id=doc_id,
                confidence=0.9,
                graph_id=graph_id,
            ))

        edges: list[KGEdge] = []
        for e in data.get("edges", []):
            src_id = id_to_node_id.get(e.get("source", ""))
            tgt_id = id_to_node_id.get(e.get("target", ""))
            if src_id and tgt_id:
                edges.append(KGEdge(
                    edge_id=str(uuid.uuid4()),
                    source_node_id=src_id,
                    target_node_id=tgt_id,
                    relationship_type=e.get("type", "RELATED_TO"),
                    properties=e.get("properties", {}),
                    source_doc_id=doc_id,
                    confidence=0.9,
                    graph_id=graph_id,
                ))

        return nodes, edges

    # ── Step 3: Entity Resolution ─────────────────────────────────────────────

    def _resolve_entities(self, nodes: list[KGNode]) -> tuple[list[KGNode], dict[str, str]]:
        """
        Deduplicate entities with the same canonical name.
        Returns (deduplicated_nodes, old_id → canonical_id mapping).
        """
        canonical: dict[str, KGNode] = {}  # normalized name → canonical node
        id_map: dict[str, str] = {}

        for node in nodes:
            # Normalize: lowercase, strip whitespace, remove punctuation
            normalized = re.sub(r"[^\w\s]", "", node.entity_name.lower()).strip()

            if normalized in canonical:
                # Map to existing canonical node
                id_map[node.node_id] = canonical[normalized].node_id
                # Merge properties
                canonical[normalized].properties.update(node.properties)
                # Boost confidence
                canonical[normalized].confidence = min(
                    canonical[normalized].confidence + 0.05, 1.0
                )
            else:
                canonical[normalized] = node
                id_map[node.node_id] = node.node_id

        return list(canonical.values()), id_map

    def _merge_extractions(self, nlp_nodes: list[KGNode],
                            gemini_nodes: list[KGNode],
                            gemini_edges: list[KGEdge]) -> tuple[list[KGNode], list[KGEdge]]:
        """Merge NLP + Gemini extractions, preferring Gemini for richer data."""
        all_nodes = gemini_nodes + [
            n for n in nlp_nodes
            if not any(g.entity_name.lower() == n.entity_name.lower()
                       for g in gemini_nodes)
        ]
        return all_nodes, gemini_edges

    # ── Step 4: Write to Spanner Graph ────────────────────────────────────────

    def _write_to_spanner_graph(self, nodes: list[KGNode],
                                 edges: list[KGEdge]) -> None:
        """Upsert nodes and edges into Cloud Spanner Graph."""
        if not self._spanner_available:
            return

        try:
            with self._spanner_db.batch() as batch:
                # Upsert nodes
                batch.insert_or_update(
                    table="KGNodes",
                    columns=["NodeId", "GraphId", "EntityType", "EntityName", "Properties"],
                    values=[
                        [n.node_id, n.graph_id, n.entity_type, n.entity_name,
                         json.dumps(n.properties)]
                        for n in nodes
                    ],
                )
                # Upsert edges
                if edges:
                    batch.insert_or_update(
                        table="KGEdges",
                        columns=["EdgeId", "GraphId", "SourceNodeId", "TargetNodeId",
                                 "RelationshipType", "Properties"],
                        values=[
                            [e.edge_id, e.graph_id, e.source_node_id, e.target_node_id,
                             e.relationship_type, json.dumps(e.properties)]
                            for e in edges
                        ],
                    )
            logger.debug("Spanner Graph write complete",
                         nodes=len(nodes), edges=len(edges))
        except Exception as e:
            logger.error("Spanner write failed", error=str(e))

    # ── Step 5: Write to BigQuery ─────────────────────────────────────────────

    def _write_to_bigquery(self, nodes: list[KGNode], edges: list[KGEdge]) -> None:
        try:
            bq_nodes = [
                {
                    "node_id": n.node_id,
                    "graph_id": n.graph_id,
                    "entity_type": n.entity_type,
                    "entity_name": n.entity_name,
                    "properties": json.dumps(n.properties),
                    "source_doc_id": n.source_doc_id,
                    "confidence": n.confidence,
                    "created_at": n.created_at.isoformat(),
                }
                for n in nodes
            ]
            bq_edges = [
                {
                    "edge_id": e.edge_id,
                    "graph_id": e.graph_id,
                    "source_node_id": e.source_node_id,
                    "target_node_id": e.target_node_id,
                    "relationship_type": e.relationship_type,
                    "properties": json.dumps(e.properties),
                    "source_doc_id": e.source_doc_id,
                    "confidence": e.confidence,
                }
                for e in edges
            ]
            if bq_nodes:
                self._bq.write_kg_nodes(bq_nodes)
            if bq_edges:
                self._bq.write_kg_edges(bq_edges)
        except Exception as e:
            logger.error("BigQuery KG write failed", error=str(e))

    def _extract_from_csv_structure(self, text: str, doc_id: str, graph_id: str) -> tuple[list[KGNode], list[KGEdge]]:
        """Simple structural extraction for CSV files to ensure the graph isn't empty."""
        lines = text.strip().split('\n')
        if not lines or ',' not in lines[0]:
            return [], []
        
        headers = [h.strip() for h in lines[0].split(',') if h.strip()]
        nodes: list[KGNode] = []
        edges: list[KGEdge] = []
        
        # Dataset Node
        dataset_id = str(uuid.uuid4())
        nodes.append(KGNode(
            node_id=dataset_id,
            entity_type="PRODUCT",
            entity_name=f"Dataset Source",
            properties={"type": "CSV", "column_count": len(headers)},
            source_doc_id=doc_id,
            graph_id=graph_id
        ))
        
        # Column Nodes
        for h in headers:
            col_id = str(uuid.uuid4())
            nodes.append(KGNode(
                node_id=col_id,
                entity_type="CONCEPT",
                entity_name=h,
                properties={"context": "Data Metric"},
                source_doc_id=doc_id,
                graph_id=graph_id
            ))
            edges.append(KGEdge(
                edge_id=str(uuid.uuid4()),
                source_node_id=dataset_id,
                target_node_id=col_id,
                relationship_type="CONTAINS_METRIC",
                graph_id=graph_id
            ))
            
        return nodes, edges

    # ── Main Extraction Entry Point ───────────────────────────────────────────

    def extract_from_document(self, doc_text: str, doc_id: str,
                               graph_id: str) -> KGExtraction:
        """
        Full KG extraction pipeline for a single document.
        Called by Person A's backend via /internal/kg/extract.
        """
        logger.info("KG extraction started", doc_id=doc_id, graph_id=graph_id)

        # Step 1: Cloud NLP
        nlp_nodes = self._extract_with_nlp_api(doc_text, doc_id, graph_id)

        # Step 2: Gemini Pro
        gemini_nodes, gemini_edges = self._extract_with_gemini(doc_text, doc_id, graph_id)

        # Step 3: CSV Structure Fallback (if it's a CSV)
        csv_nodes, csv_edges = self._extract_from_csv_structure(doc_text, doc_id, graph_id)

        # Step 4: Merge
        merged_nodes, merged_edges = self._merge_extractions(
            nlp_nodes + csv_nodes, gemini_nodes, gemini_edges + csv_edges
        )

        # Step 5: Entity resolution
        resolved_nodes, id_map = self._resolve_entities(merged_nodes)

        # Remap edge IDs after resolution
        resolved_edges = [
            KGEdge(
                edge_id=e.edge_id,
                source_node_id=id_map.get(e.source_node_id, e.source_node_id),
                target_node_id=id_map.get(e.target_node_id, e.target_node_id),
                relationship_type=e.relationship_type,
                properties=e.properties,
                source_doc_id=e.source_doc_id,
                confidence=e.confidence,
                graph_id=e.graph_id,
            )
            for e in merged_edges
        ]

        # Remove self-loops
        resolved_edges = [
            e for e in resolved_edges if e.source_node_id != e.target_node_id
        ]

        # Step 6: Persist
        self._write_to_spanner_graph(resolved_nodes, resolved_edges)
        self._write_to_bigquery(resolved_nodes, resolved_edges)

        extraction = KGExtraction(
            nodes=resolved_nodes,
            edges=resolved_edges,
            doc_id=doc_id,
            graph_id=graph_id,
        )

        logger.info("KG extraction complete",
                    nodes=extraction.node_count, edges=extraction.edge_count)
        return extraction

    # ── NL-to-GQL Query ──────────────────────────────────────────────────────

    def query_graph_nl(self, question: str, graph_id: str) -> GraphQueryResult:
        """
        Convert natural language question to Spanner GQL and execute.
        """
        # Get graph schema summary
        try:
            schema_rows = self._bq.query(f"""
                SELECT DISTINCT entity_type, COUNT(*) as count
                FROM `{self._bq._table_ref("kg_nodes")}`
                WHERE graph_id = @graph_id
                GROUP BY entity_type
            """, [("graph_id", "STRING", graph_id)])

            rel_rows = self._bq.query(f"""
                SELECT DISTINCT relationship_type, COUNT(*) as count
                FROM `{self._bq._table_ref("kg_edges")}`
                WHERE graph_id = @graph_id
                GROUP BY relationship_type
            """, [("graph_id", "STRING", graph_id)])

            schema_text = (
                f"Node types: {[r['entity_type'] for r in schema_rows]}\n"
                f"Relationship types: {[r['relationship_type'] for r in rel_rows]}"
            )
        except Exception:
            schema_text = "Node types: PERSON, ORG, PRODUCT, CONCEPT, LOCATION, EVENT"

        prompt = f"""Convert this natural language question to a Spanner Graph Query Language (GQL) query.

Graph Schema:
{schema_text}

The graph has two tables:
- KGNodes(NodeId, GraphId, EntityType, EntityName, Properties)  
- KGEdges(EdgeId, GraphId, SourceNodeId, TargetNodeId, RelationshipType, Properties)

Always filter by: WHERE n.GraphId = '{graph_id}'

Question: {question}

Return ONLY the GQL query, no explanation:"""

        try:
            response = self._gemini_flash.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.0, max_output_tokens=500),
            )
            gql = response.text.strip()
            gql = re.sub(r"```(?:sql|gql)?\s*|\s*```", "", gql).strip()
        except Exception as e:
            logger.error("GQL generation failed", error=str(e))
            gql = f"SELECT * FROM KGNodes WHERE GraphId = '{graph_id}' LIMIT 20"

        # Execute GQL via Spanner
        nodes: list[dict] = []
        edges: list[dict] = []

        if self._spanner_available:
            try:
                with self._spanner_db.snapshot() as snapshot:
                    results = snapshot.execute_sql(gql)
                    rows = [dict(zip([col.name for col in results.fields], row))
                            for row in results]
                    nodes = [r for r in rows if "NodeId" in r]
                    edges = [r for r in rows if "EdgeId" in r]
            except Exception as e:
                logger.warning("GQL execution failed, falling back to BQ", error=str(e))
                # Fallback: BigQuery query on kg_nodes table
                try:
                    bq_rows = self._bq.query(f"""
                        SELECT node_id, entity_type, entity_name, properties
                        FROM `{self._bq._table_ref("kg_nodes")}`
                        WHERE graph_id = '{graph_id}'
                        LIMIT 50
                    """)
                    nodes = bq_rows
                except Exception:
                    pass

        return GraphQueryResult(
            gql=gql,
            nodes=nodes,
            edges=edges,
            row_count=len(nodes) + len(edges),
        )

    def get_subgraph(self, entity_id: str, graph_id: str, depth: int = 2) -> GraphQueryResult:
        """Return subgraph centered on a node up to `depth` hops."""
        try:
            nodes_rows = self._bq.query(f"""
                SELECT node_id, entity_type, entity_name, properties
                FROM `{self._bq._table_ref("kg_nodes")}`
                WHERE graph_id = '{graph_id}'
                  AND node_id = '{entity_id}'
            """)

            edges_rows = self._bq.query(f"""
                SELECT edge_id, source_node_id, target_node_id, relationship_type
                FROM `{self._bq._table_ref("kg_edges")}`
                WHERE graph_id = '{graph_id}'
                  AND (source_node_id = '{entity_id}' OR target_node_id = '{entity_id}')
                LIMIT 50
            """)

            # Get neighbor nodes
            neighbor_ids = set()
            for e in edges_rows:
                neighbor_ids.add(e["source_node_id"])
                neighbor_ids.add(e["target_node_id"])
            neighbor_ids.discard(entity_id)

            if neighbor_ids:
                ids_str = ", ".join(f"'{nid}'" for nid in list(neighbor_ids)[:20])
                neighbor_rows = self._bq.query(f"""
                    SELECT node_id, entity_type, entity_name, properties
                    FROM `{self._bq._table_ref("kg_nodes")}`
                    WHERE graph_id = '{graph_id}' AND node_id IN ({ids_str})
                """)
                all_nodes = nodes_rows + neighbor_rows
            else:
                all_nodes = nodes_rows

            return GraphQueryResult(
                gql="",
                nodes=all_nodes,
                edges=edges_rows,
                row_count=len(all_nodes) + len(edges_rows),
            )
        except Exception as e:
            logger.error("Subgraph query failed", error=str(e))
            return GraphQueryResult(gql="", nodes=[], edges=[], row_count=0)
