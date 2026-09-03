"""Investigation Report Generation and Export API routes for CrimeGraph AI (Day 24).

Strictly adheres to API_CONTRACT.md Section 8, DATA_SCHEMA.md, and Safety Principles.
Provides:
- POST /api/reports: Legacy backward-compatible report summary generation
- POST /api/reports/investigation: Comprehensive multi-source investigation report synthesis
- GET /api/reports/{report_id}: Retrieve generated report record
- GET /api/reports/{report_id}/export: Export investigation report in JSON, Markdown, HTML, or PDF-ready formats
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.reports.exporter import ReportExporter
from crimegraph.reports.generator import InvestigationReportGenerator
from crimegraph.reports.models import (
    InvestigationReport,
    ReportExportFormat,
    ReportRequest,
)

router = APIRouter(prefix="/api/reports", tags=["Reports"], dependencies=[Depends(get_current_user)])


def get_report_generator(request: Request) -> InvestigationReportGenerator:
    """Helper to initialize and access the InvestigationReportGenerator on app state."""
    graph = request.app.state.graph
    timeline_engine = getattr(request.app.state, "timeline_engine", None)
    if not hasattr(request.app.state, "report_generator") or request.app.state.report_generator is None:
        request.app.state.report_generator = InvestigationReportGenerator(graph_store=graph, timeline_engine=timeline_engine)
    return request.app.state.report_generator


def get_report_cache(request: Request) -> Dict[str, InvestigationReport]:
    """In-memory cache for generated investigation reports."""
    if not hasattr(request.app.state, "reports_cache") or request.app.state.reports_cache is None:
        request.app.state.reports_cache = {}
    return request.app.state.reports_cache


@router.post("", response_model=Dict[str, Any])
def generate_report_legacy(
    request: Request,
    payload: ReportRequest,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Legacy investigation report generation (API_CONTRACT.md Section 8 compatible)."""
    graph = request.app.state.graph
    case_id = payload.case_id

    if not case_id or case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in knowledge graph")

    generator = get_report_generator(request)
    report = generator.generate_investigation_report(payload, actor_id=current_user.username)
    report_cache = get_report_cache(request)
    report_cache[report.report_id] = report

    # Generate markdown content
    md_content = ReportExporter.to_markdown(report)
    report.content = md_content

    audit_logger.log(
        action="REPORT_GENERATE",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        resource_id=report.report_id,
        case_id=case_id,
        status=AuditStatus.SUCCESS
    )

    return {
        "report_id": report.report_id,
        "case_id": case_id,
        "status": "generated",
        "content": md_content,
        "report": report.model_dump()
    }


@router.post("/investigation", response_model=InvestigationReport)
def generate_comprehensive_report(
    request: Request,
    payload: ReportRequest,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> InvestigationReport:
    """Generates a complete multi-source, evidence-grounded investigation report."""
    graph = request.app.state.graph
    case_ids = payload.case_ids or ([payload.case_id] if payload.case_id else [])

    for cid in case_ids:
        if cid not in graph.entities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{cid}' not found in knowledge graph."
            )

    generator = get_report_generator(request)
    report = generator.generate_investigation_report(payload, actor_id=current_user.username)
    report.content = ReportExporter.to_markdown(report)

    report_cache = get_report_cache(request)
    report_cache[report.report_id] = report

    audit_logger.log(
        action="INVESTIGATION_REPORT_GENERATE",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        resource_id=report.report_id,
        status=AuditStatus.SUCCESS,
        details={"case_ids": case_ids, "entities_count": len(report.entities), "evidence_count": len(report.evidence)}
    )

    return report


@router.get("/{report_id}", response_model=InvestigationReport)
def get_report_by_id(
    report_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> InvestigationReport:
    """Retrieves an existing investigation report by ID."""
    report_id = report_id.strip()
    report_cache = get_report_cache(request)
    report = report_cache.get(report_id)

    if not report:
        # If not cached, check if report_id has a case_id prefix or fallback to regenerating
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found."
        )

    audit_logger.log(
        action="REPORT_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        resource_id=report_id,
        status=AuditStatus.SUCCESS
    )

    return report


@router.get("/{report_id}/export")
def export_report(
    report_id: str,
    request: Request,
    format: ReportExportFormat = Query(ReportExportFormat.JSON, description="Export format: JSON, PDF, HTML, MARKDOWN"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Response:
    """Exports an investigation report in requested presentation format (JSON, Markdown, HTML, PDF)."""
    report_id = report_id.strip()
    report_cache = get_report_cache(request)
    report = report_cache.get(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found for export."
        )

    audit_logger.log(
        action="REPORT_EXPORT",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        resource_id=report_id,
        status=AuditStatus.SUCCESS,
        details={"format": format.value}
    )

    if format == ReportExportFormat.JSON:
        json_content = ReportExporter.to_json(report)
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={report_id}.json"}
        )
    elif format == ReportExportFormat.MARKDOWN:
        md_content = ReportExporter.to_markdown(report)
        return PlainTextResponse(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={report_id}.md"}
        )
    elif format in (ReportExportFormat.HTML, ReportExportFormat.PDF):
        html_content = ReportExporter.to_html(report)
        # Printable HTML is compatible with browser PDF saving / printing
        return HTMLResponse(
            content=html_content,
            media_type="text/html",
            headers={"Content-Disposition": f"inline; filename={report_id}.html"}
        )

    raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
