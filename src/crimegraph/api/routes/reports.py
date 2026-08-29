"""Investigation Report Generation API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md Section 8 and PROJECT_SPEC.md Safety Principles.
"""

import uuid
from typing import Any, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Header, HTTPException, Request
from crimegraph.api.routes.auth import verify_bearer_token, verify_case_access

router = APIRouter(prefix="/api/reports", tags=["Reports"])


class ReportRequest(BaseModel):
    case_id: str = Field(..., description="Case ID to generate report for")


@router.post("", response_model=Dict[str, Any])
def generate_report(
    request: Request,
    payload: ReportRequest,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Generate an evidence-linked investigation report summary for a case."""
    if authorization:
        user = verify_bearer_token(authorization)
        verify_case_access(user, payload.case_id)

    graph = request.app.state.graph
    case_id = payload.case_id

    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in knowledge graph")

    case = graph.get_entity(case_id)
    subgraph = graph.get_case_subgraph(case_id)

    nodes = subgraph.get("nodes", [])
    edges = subgraph.get("edges", [])

    involved_people = [n["name"] for n in nodes if n.get("entity_type") == "PERSON"]
    involved_phones = [n.get("phone_number", n["id"]) for n in nodes if n.get("entity_type") == "PHONE"]
    involved_vehicles = [n.get("registration_number", n["id"]) for n in nodes if n.get("entity_type") == "VEHICLE"]

    report_content = (
        f"# CRIMEGRAPH AI — INVESTIGATION SUMMARY REPORT\n\n"
        f"**Case Reference**: {getattr(case, 'case_number', case_id)} — {getattr(case, 'title', 'Untitled')}\n"
        f"**Status**: {getattr(case, 'status', 'ACTIVE')}\n"
        f"**Incident Date**: {getattr(case, 'incident_date', 'N/A')}\n\n"
        f"## 1. Executive Summary\n"
        f"{getattr(case, 'description', 'No description available.')}\n\n"
        f"## 2. Identified Key Entities\n"
        f"- **Persons**: {', '.join(involved_people) if involved_people else 'None'}\n"
        f"- **Phones**: {', '.join(involved_phones) if involved_phones else 'None'}\n"
        f"- **Vehicles**: {', '.join(involved_vehicles) if involved_vehicles else 'None'}\n\n"
        f"## 3. Relationship Network\n"
        f"Total connected graph entities: {len(nodes)}\n"
        f"Total verified relationship edges: {len(edges)}\n\n"
        f"## 4. LEGAL & SAFETY DISCLAIMER\n"
        f"CrimeGraph AI provides investigative leads and association mappings based solely on ingested documents. "
        f"This output does NOT declare guilt, make legal judgments, or represent conclusive criminal proof. "
        f"All generated leads require mandatory human verification by authorized case officers."
    )

    report_id = f"REPORT_{uuid.uuid4().hex[:8].upper()}"

    return {
        "report_id": report_id,
        "case_id": case_id,
        "status": "generated",
        "content": report_content
    }
