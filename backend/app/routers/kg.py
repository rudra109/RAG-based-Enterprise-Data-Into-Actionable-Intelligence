"""
EnterpriseIQ Backend — Knowledge Graph Router
/v1/kg/* endpoints
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import FirebaseUser, get_current_user
from app.core.clients import BigQueryClient, CacheClient, get_bq, get_cache, get_firestore, FirestoreClient
from app.core.ml_client import MLServiceClient, get_ml_client

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/kg", tags=["Knowledge Graph"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class KGExtractRequest(BaseModel):
    document_ids: List[str]
    graph_id: str


class KGExtractResponse(BaseModel):
    job_id: str
    graph_id: str
    status: str
    document_count: int
    message: str


class KGQueryRequest(BaseModel):
    graph_id: str
    query: str
    query_type: str = "natural_language"  # natural_language | gql


class KGNode(BaseModel):
    node_id: str
    entity_type: str
    entity_name: str
    properties: dict = {}
    confidence: float


class KGEdge(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    properties: dict = {}
    confidence: float


class KGQueryResponse(BaseModel):
    graph_id: str
    query: str
    nodes: List[KGNode]
    edges: List[KGEdge]
    explanation: str
    result_count: int


class KGSubgraphResponse(BaseModel):
    entity_id: str
    depth: int
    nodes: List[KGNode]
    edges: List[KGEdge]
    total_nodes: int
    total_edges: int


class GraphCreate(BaseModel):
    graph_id: str
    name: str
    description: str = ""


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/graphs", status_code=201, summary="Create a new knowledge graph")
async def create_graph(
    body: GraphCreate,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    graph = {
        "graph_id": body.graph_id,
        "name": body.name,
        "description": body.description,
        "owner_uid": user.uid,
        "created_at": datetime.utcnow().isoformat(),
        "node_count": 0,
        "edge_count": 0,
    }
    fs.set_document("knowledge_graphs", body.graph_id, graph)
    logger.info("Knowledge graph created", graph_id=body.graph_id)
    return graph


@router.get("/graphs", summary="List knowledge graphs")
async def list_graphs(
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    graphs = fs.list_documents("knowledge_graphs", filters=[("owner_uid", "==", user.uid)])
    return {"graphs": graphs, "total": len(graphs)}


@router.post("/extract", response_model=KGExtractResponse, summary="Extract knowledge graph from documents")
async def extract_kg(
    body: KGExtractRequest,
    user: FirebaseUser = Depends(get_current_user),
    ml: MLServiceClient = Depends(get_ml_client),
    bq: BigQueryClient = Depends(get_bq),
):
    job_id = str(uuid.uuid4())

    # Trigger Developer B's KG extraction pipeline
    try:
        result = await ml.kg_extract(body.document_ids, body.graph_id)
    except Exception as e:
        logger.error("KG extraction service error", error=str(e))
        raise HTTPException(status_code=503, detail=f"KG service unavailable: {e}")

    # Persist nodes and edges returned immediately (if any)
    nodes = result.get("nodes", [])
    edges = result.get("edges", [])

    if nodes:
        try:
            bq_nodes = [
                {
                    "node_id": n.get("node_id", str(uuid.uuid4())),
                    "graph_id": body.graph_id,
                    "entity_type": n.get("entity_type", ""),
                    "entity_name": n.get("entity_name", ""),
                    "properties": str(n.get("properties", {})),
                    "source_doc_id": n.get("source_doc_id", ""),
                    "confidence": float(n.get("confidence", 0.9)),
                    "created_at": datetime.utcnow().isoformat(),
                }
                for n in nodes
            ]
            bq.insert_rows("kg_nodes", bq_nodes)
        except Exception as e:
            logger.warning("Failed to persist KG nodes to BQ", error=str(e))

    if edges:
        try:
            bq_edges = [
                {
                    "edge_id": e.get("edge_id", str(uuid.uuid4())),
                    "graph_id": body.graph_id,
                    "source_node_id": e.get("source_node_id", ""),
                    "target_node_id": e.get("target_node_id", ""),
                    "relationship_type": e.get("relationship_type", ""),
                    "properties": str(e.get("properties", {})),
                    "source_doc_id": e.get("source_doc_id", ""),
                    "confidence": float(e.get("confidence", 0.9)),
                }
                for e in edges
            ]
            bq.insert_rows("kg_edges", bq_edges)
        except Exception as e:
            logger.warning("Failed to persist KG edges to BQ", error=str(e))

    logger.info("KG extraction triggered", graph_id=body.graph_id, docs=len(body.document_ids))
    return KGExtractResponse(
        job_id=job_id,
        graph_id=body.graph_id,
        status=result.get("status", "processing"),
        document_count=len(body.document_ids),
        message="Knowledge graph extraction in progress",
    )


@router.post("/query", response_model=KGQueryResponse, summary="Query the knowledge graph")
async def query_kg(
    body: KGQueryRequest,
    user: FirebaseUser = Depends(get_current_user),
    ml: MLServiceClient = Depends(get_ml_client),
    cache: CacheClient = Depends(get_cache),
):
    cache_key = f"kg:query:{body.graph_id}:{hash(body.query)}:{body.query_type}"
    cached = cache.get(cache_key)
    if cached:
        return KGQueryResponse(**cached)

    try:
        result = await ml.kg_query(body.graph_id, body.query, body.query_type)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"KG service unavailable: {e}")

    nodes = [KGNode(**n) for n in result.get("nodes", [])]
    edges = [KGEdge(**e) for e in result.get("edges", [])]

    response = KGQueryResponse(
        graph_id=body.graph_id,
        query=body.query,
        nodes=nodes,
        edges=edges,
        explanation=result.get("explanation", ""),
        result_count=len(nodes),
    )
    cache.set(cache_key, response.model_dump(), ttl=1800)
    return response


@router.get("/subgraph", response_model=KGSubgraphResponse, summary="Get a subgraph centred on an entity")
async def get_subgraph(
    entity_id: str,
    depth: int = 2,
    user: FirebaseUser = Depends(get_current_user),
    ml: MLServiceClient = Depends(get_ml_client),
    cache: CacheClient = Depends(get_cache),
):
    cache_key = f"kg:subgraph:{entity_id}:{depth}"
    cached = cache.get(cache_key)
    if cached:
        return KGSubgraphResponse(**cached)

    try:
        result = await ml.kg_subgraph(entity_id, depth)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"KG service unavailable: {e}")

    nodes = [KGNode(**n) for n in result.get("nodes", [])]
    edges = [KGEdge(**e) for e in result.get("edges", [])]

    response = KGSubgraphResponse(
        entity_id=entity_id,
        depth=depth,
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )
    cache.set(cache_key, response.model_dump(), ttl=1800)
    return response
