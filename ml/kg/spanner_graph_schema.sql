-- ============================================================
-- EnterpriseIQ — Spanner Graph DDL
-- Knowledge Graph schema for Cloud Spanner
-- Developer B — Month 6 deliverable
-- ============================================================

-- ── Node table ────────────────────────────────────────────────────────────────

CREATE TABLE KGNodes (
  NodeId     STRING(MAX)  NOT NULL,
  GraphId    STRING(MAX)  NOT NULL,
  EntityType STRING(100),            -- PERSON | ORG | PRODUCT | CONCEPT | LOCATION | EVENT
  EntityName STRING(MAX),
  Properties JSON,                   -- Flexible properties (role, sector, etc.)
  SourceDocId STRING(MAX),           -- Which document this entity came from
  Confidence FLOAT64,                -- Extraction confidence (0.0–1.0)
  CreatedAt  TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP())
) PRIMARY KEY (GraphId, NodeId);

-- ── Edge table (interleaved for performance) ──────────────────────────────────

CREATE TABLE KGEdges (
  EdgeId           STRING(MAX)  NOT NULL,
  GraphId          STRING(MAX)  NOT NULL,
  SourceNodeId     STRING(MAX)  NOT NULL,
  TargetNodeId     STRING(MAX)  NOT NULL,
  RelationshipType STRING(100),
  Properties       JSON,
  SourceDocId      STRING(MAX),
  Confidence       FLOAT64,
  CreatedAt        TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP())
) PRIMARY KEY (GraphId, EdgeId);

-- ── Secondary indexes for fast queries ──────────────────────────────────────

CREATE INDEX NodesByType ON KGNodes (GraphId, EntityType);
CREATE INDEX NodesByName ON KGNodes (GraphId, EntityName);
CREATE INDEX EdgesBySource ON KGEdges (GraphId, SourceNodeId);
CREATE INDEX EdgesByTarget ON KGEdges (GraphId, TargetNodeId);
CREATE INDEX EdgesByType ON KGEdges (GraphId, RelationshipType);

-- ── Property Graph definition ─────────────────────────────────────────────────

CREATE PROPERTY GRAPH EnterpriseKG
  NODE TABLES (
    KGNodes
      KEY (NodeId)
      LABEL Entity
      PROPERTIES (EntityType AS type, EntityName AS name,
                  Confidence AS confidence, Properties AS props)
  )
  EDGE TABLES (
    KGEdges
      KEY (EdgeId)
      SOURCE KEY (SourceNodeId) REFERENCES KGNodes (NodeId)
      DESTINATION KEY (TargetNodeId) REFERENCES KGNodes (NodeId)
      LABEL Relationship
      PROPERTIES (RelationshipType AS type, Confidence AS confidence)
  );

-- ============================================================
-- Example GQL Queries
-- ============================================================

-- 1. Find all entities of type PERSON in a graph
/*
GRAPH EnterpriseKG
MATCH (n:Entity {type: 'PERSON', GraphId: 'graph_001'})
RETURN n.name, n.confidence
ORDER BY n.confidence DESC
LIMIT 20
*/

-- 2. Find all relationships for a specific entity
/*
GRAPH EnterpriseKG
MATCH (n:Entity)-[r:Relationship]->(m:Entity)
WHERE n.NodeId = 'node_uuid_here'
RETURN n.name, r.type, m.name, r.confidence
*/

-- 3. Find shortest path between two entities
/*
GRAPH EnterpriseKG
MATCH PATH p = ANY SHORTEST (a:Entity)-[:Relationship]->+(b:Entity)
WHERE a.NodeId = 'node_a' AND b.NodeId = 'node_b'
RETURN NODES(p) AS path_nodes, EDGES(p) AS path_edges
*/

-- 4. Find all organisations connected to a person within 2 hops
/*
GRAPH EnterpriseKG
MATCH (p:Entity {type: 'PERSON'})-[:Relationship]->{1,2}(o:Entity {type: 'ORG'})
WHERE p.name = 'John Smith'
RETURN o.name, o.confidence
ORDER BY o.confidence DESC
*/
