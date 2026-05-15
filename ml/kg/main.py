"""
EnterpriseIQ ML — Knowledge Graph FastAPI Service
Internal endpoints for KG extraction and querying.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, "../")

from shared.logging_setup import configure_logging
from kg.extractor import KnowledgeGraphExtractor, KGExtraction, GraphQueryResult

configure_logging("ml-kg-service")
logger = structlog.get_logger(__name__)


class ExtractRequest(BaseModel):
    doc_text: str = Field(..., min_length=10)
    doc_id: str
    graph_id: str


class NLQueryRequest(BaseModel):
    question: str
    graph_id: str


class SubgraphRequest(BaseModel):
    entity_id: str
    graph_id: str
    depth: int = Field(default=2, ge=1, le=4)


class NodeOut(BaseModel):
    node_id: str
    entity_type: str
    entity_name: str
    confidence: float


class EdgeOut(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str


class ExtractResponse(BaseModel):
    doc_id: str
    graph_id: str
    node_count: int
    edge_count: int
    nodes: list[NodeOut]
    edges: list[EdgeOut]
    extracted_at: datetime


class GraphQueryResponse(BaseModel):
    gql: str
    nodes: list[dict]
    edges: list[dict]
    row_count: int


class HealthResponse(BaseModel):
    status: str
    service: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("KG service starting up")
    app.state.extractor = KnowledgeGraphExtractor()
    yield


app = FastAPI(title="EnterpriseIQ KG Service", version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="ml-kg-service")


@app.post("/internal/kg/extract", response_model=ExtractResponse)
async def extract(req: ExtractRequest):
    try:
        extractor: KnowledgeGraphExtractor = app.state.extractor
        result: KGExtraction = extractor.extract_from_document(
            doc_text=req.doc_text,
            doc_id=req.doc_id,
            graph_id=req.graph_id,
        )
        return ExtractResponse(
            doc_id=result.doc_id,
            graph_id=result.graph_id,
            node_count=result.node_count,
            edge_count=result.edge_count,
            nodes=[
                NodeOut(node_id=n.node_id, entity_type=n.entity_type,
                        entity_name=n.entity_name, confidence=n.confidence)
                for n in result.nodes
            ],
            edges=[
                EdgeOut(edge_id=e.edge_id, source_node_id=e.source_node_id,
                        target_node_id=e.target_node_id, relationship_type=e.relationship_type)
                for e in result.edges
            ],
            extracted_at=result.extracted_at,
        )
    except Exception as e:
        logger.error("KG extraction failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/kg/query", response_model=GraphQueryResponse)
async def query_graph(req: NLQueryRequest):
    try:
        extractor: KnowledgeGraphExtractor = app.state.extractor
        result: GraphQueryResult = extractor.query_graph_nl(req.question, req.graph_id)
        return GraphQueryResponse(gql=result.gql, nodes=result.nodes,
                                   edges=result.edges, row_count=result.row_count)
    except Exception as e:
        logger.error("KG query failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/kg/subgraph", response_model=GraphQueryResponse)
async def get_subgraph(req: SubgraphRequest):
    try:
        extractor: KnowledgeGraphExtractor = app.state.extractor
        result: GraphQueryResult = extractor.get_subgraph(
            req.entity_id, req.graph_id, req.depth
        )
        return GraphQueryResponse(gql=result.gql, nodes=result.nodes,
                                   edges=result.edges, row_count=result.row_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
