"""FastAPI Backend Server for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md endpoints and data schemas.
"""

from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.traversal import find_cross_case_connections
from crimegraph.ai.extractor import DocumentExtractor
from crimegraph.ai.resolution import EntityResolver
from crimegraph.ai.investigator import AIInvestigator
from crimegraph.reports.reporter import InvestigationReporter
from crimegraph.models.entities import EntityType


app = FastAPI(
    title="CrimeGraph AI API",
    description="Evidence-linked investigative intelligence API for SIH 2026",
    version="1.0.0"
)

# Enable CORS for web frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize in-memory Knowledge Graph Store & Engines
graph_store: KnowledgeGraphStore = load_dataset()
extractor = DocumentExtractor()
resolver = EntityResolver(graph_store)
investigator = AIInvestigator(graph_store)
reporter = InvestigationReporter(graph_store)


# --- Request Models ---

class ExtractRequest(BaseModel):
    document_id: str = Field(..., description="Source document identifier")
    text: str = Field(..., description="Investigation text to extract entities from")


class ReportRequest(BaseModel):
    case_id: str = Field(..., description="Target case ID for report generation")


class InvestigateRequest(BaseModel):
    question: str = Field(..., description="Natural language investigation query")
    case_id: Optional[str] = Field(None, description="Currently selected case ID context")
    entity_id: Optional[str] = Field(None, description="Currently focused entity ID context")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Prior conversation history")


# --- Endpoints ---


@app.get("/")
def root():
    return {
        "system": "CrimeGraph AI",
        "status": "ONLINE",
        "version": "1.0.0",
        "disclaimer": "Investigative intelligence platform. Output provides leads and does not determine guilt."
    }


@app.post("/api/extract")
def extract_document(req: ExtractRequest):
    """POST /api/extract - Extracts entities, relationships, events, and evidence from text per API_CONTRACT.md."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text field cannot be empty.")
    
    res = extractor.extract_from_document(req.document_id, req.text)
    return res


@app.get("/api/cases/{case_id}/graph")
def get_case_graph(case_id: str):
    """GET /api/cases/{case_id}/graph - Returns sub-graph nodes and edges for a specific case matching API_CONTRACT.md."""
    try:
        subgraph = graph_store.get_case_subgraph(case_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    formatted_nodes = []
    for n in subgraph["nodes"]:
        n_id = n["id"]
        n_type = n.get("entity_type", "ENTITY")
        n_label = n.get("name") or n.get("title") or n.get("phone_number") or n.get("registration_number") or n_id
        formatted_nodes.append({
            "id": n_id,
            "label": n_label,
            "type": n_type,
            "confidence": n.get("confidence", 1.0)
        })

    formatted_edges = []
    for e in subgraph["edges"]:
        formatted_edges.append({
            "id": e["id"],
            "source": e["source_id"],
            "target": e["target_id"],
            "relationship": e["relationship"],
            "confidence": e["confidence"],
            "evidence_ids": e.get("evidence_ids", [])
        })

    return {
        "nodes": formatted_nodes,
        "edges": formatted_edges
    }


@app.get("/api/entities/{entity_id}")
def get_entity_details(entity_id: str):
    """GET /api/entities/{entity_id} - Returns entity properties, relationships, connected cases, and evidence matching API_CONTRACT.md."""
    try:
        return graph_store.get_entity_details(entity_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found.")


@app.get("/api/cases/connections")
def get_case_connections(case_a: Optional[str] = Query(default="CASE_101"), case_b: Optional[str] = Query(default="CASE_204")):
    """GET /api/cases/connections - Discovers cross-case relationship chains matching API_CONTRACT.md."""
    conns = find_cross_case_connections(graph_store, case_a, case_b)
    return {"connections": conns}


@app.get("/api/cases/{case_id}/timeline")
def get_case_timeline(case_id: str):
    """GET /api/cases/{case_id}/timeline - Returns chronological event timeline for a case matching API_CONTRACT.md."""
    events = graph_store.get_entities_by_type(EntityType.EVENT)
    event_list = []

    for ev in events:
        event_list.append({
            "id": ev.id,
            "timestamp": getattr(ev, "timestamp", "2026-08-12T18:30:00Z"),
            "type": getattr(ev, "event_type", "EVENT"),
            "location_id": getattr(ev, "location_id", "LOC_001"),
            "description": getattr(ev, "description", "")
        })

    # Sort chronologically
    event_list.sort(key=lambda x: str(x.get("timestamp", "")))

    return {"events": event_list}


@app.post("/api/reports")
def create_investigation_report(req: ReportRequest):
    """POST /api/reports - Generates an evidence-backed investigation report matching API_CONTRACT.md."""
    report = reporter.generate_report(req.case_id)
    return report


@app.get("/api/entity-resolution/pending")
def get_pending_entity_resolutions():
    """GET /api/entity-resolution/pending - Candidate duplicate entity matches pending human review matching DATA_SCHEMA.md Section 5."""
    candidates = resolver.find_pending_matches()
    return {"candidates": candidates}


@app.post("/api/investigate")
def investigate_query(req: InvestigateRequest):
    """POST /api/investigate - Natural language AI investigator query endpoint matching PROJECT_SPEC.md F9 & F10."""
    res = investigator.query(
        question=req.question,
        case_id=req.case_id,
        entity_id=req.entity_id,
        conversation_history=req.conversation_history
    )
    return res
