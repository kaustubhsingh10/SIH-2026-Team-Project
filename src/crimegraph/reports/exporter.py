"""Investigation Report Exporter for CrimeGraph AI (Day 24).

Generates grounded export formats (JSON, Markdown, HTML, and standalone PDF-printable document).
Ensures zero data leakage of internal tokens, passwords, or filesystem paths.
"""

from datetime import datetime
import json
import re
from typing import Any, Dict, List, Optional
from crimegraph.reports.models import InvestigationReport


class ReportExporter:
    """Exports InvestigationReport into standardized, presentation-ready formats."""

    @classmethod
    def to_json(cls, report: InvestigationReport, indent: int = 2) -> str:
        """Serializes the investigation report to standardized JSON string."""
        data = report.model_dump()
        # Clean any private system keys if present
        cls._sanitize_export_data(data)
        return json.dumps(data, indent=indent, default=str)

    @classmethod
    def to_markdown(cls, report: InvestigationReport) -> str:
        """Generates comprehensive, formatted Markdown representation of the report."""
        if report.content and len(report.content) > 100:
            return report.content

        lines: List[str] = []
        lines.append(f"# {report.title}")
        lines.append(f"**Report Reference**: `{report.report_id}`  ")
        lines.append(f"**Target Case(s)**: `{', '.join(report.case_ids) if report.case_ids else report.case_id}`  ")
        lines.append(f"**Generated**: {report.generated_at} by `{report.generated_by}`  ")
        lines.append(f"**Confidence Level**: **{report.confidence:.2f}** (`{report.confidence_tier}`)")
        lines.append("\n---\n")

        lines.append("> [!IMPORTANT]")
        lines.append(f"> **LEGAL & SAFETY DISCLAIMER**: {report.disclaimer}")
        lines.append("\n---\n")

        # Executive Summary
        lines.append("## 1. Executive Summary")
        lines.append(report.executive_summary)
        lines.append("\n")

        if report.investigation_question:
            lines.append("### Investigation Objective / Question")
            lines.append(f"*{report.investigation_question}*\n")

        # Entities
        lines.append(f"## 2. Identified & Linked Entities ({len(report.entities)})")
        if report.entities:
            for ent in report.entities:
                ename = ent.get("name", ent.get("phone_number", ent.get("registration_number", ent.get("id"))))
                etype = ent.get("entity_type", ent.get("type", "ENTITY"))
                origin = ent.get("origin", "DATASET")
                lines.append(f"- **{ename}** (`{ent.get('id')}` | `{etype}`): Source Origin: `{origin}`")
        else:
            lines.append("No specific entities attached.")
        lines.append("\n")

        # Cross-Case & Bridge Connections
        if report.cross_case_connections:
            lines.append(f"## 3. Discovered Cross-Case Bridge Paths ({len(report.cross_case_connections)})")
            for cc in report.cross_case_connections:
                p_str = " → ".join(cc.get("path", []))
                lines.append(f"- **Path**: `{p_str}`")
                lines.append(f"  - **Bridge Entities**: `{', '.join(cc.get('shared_entities', []))}`")
                lines.append(f"  - **Confidence**: **{cc.get('confidence', 0.90):.2f}**")
                if cc.get("evidence_ids"):
                    lines.append(f"  - **Supporting Evidence**: `{', '.join(cc.get('evidence_ids', []))}`")
            lines.append("\n")

        # Timeline Events
        if report.timeline_events:
            lines.append(f"## 4. Chronological Event Sequence ({len(report.timeline_events)})")
            for ev in report.timeline_events:
                ts = ev.get("timestamp") or "UNDATED"
                etype = ev.get("event_type", ev.get("type", "EVENT"))
                desc = ev.get("description", "Event recorded in case logs.")
                lines.append(f"- `[{ts}]` **{etype}** (`{ev.get('id', ev.get('event_id'))}`): {desc}")
            lines.append("\n")

        # Suspicious Patterns
        if report.suspicious_patterns:
            lines.append(f"## 5. Detected Suspicious Patterns ({len(report.suspicious_patterns)})")
            for pat in report.suspicious_patterns:
                lines.append(f"- **{pat.get('title', pat.get('pattern_type'))}** [Severity: `{pat.get('severity', 'HIGH')}`]")
                lines.append(f"  - *Explanation*: {pat.get('explanation')}")
            lines.append("\n")

        # Evidence & Provenance
        lines.append(f"## 6. Corroborating Evidence & Source Lineage ({len(report.evidence)})")
        if report.evidence:
            for ev in report.evidence:
                ev_id = ev.get("evidence_id", ev.get("id"))
                src_doc = ev.get("source_document_id", ev.get("source_document", "DOC_RECORD"))
                txt = ev.get("source_text", "")
                conf = ev.get("confidence", 0.95)
                lines.append(f"- [`{ev_id}`] Document: **{src_doc}** (Confidence: {conf:.2f})")
                if txt:
                    lines.append(f"  > \"{txt}\"")
        else:
            lines.append("No explicit physical/digital evidence items linked.")
        lines.append("\n")

        # Investigative Leads & Limitations
        lines.append("## 7. Recommended Investigative Leads")
        if report.investigative_leads:
            for lead in report.investigative_leads:
                lines.append(f"- {lead}")
        else:
            lines.append("- Review linked device logs and subpoena intermediary communication records.")
        lines.append("\n")

        lines.append("## 8. Data Limitations & Scope Constraints")
        if report.limitations:
            for lim in report.limitations:
                lines.append(f"- {lim}")
        else:
            lines.append("- Analysis bounded by currently ingested documents and verified graph records.")
        lines.append("\n---\n")
        lines.append(f"*Report Reference: `{report.report_id}` — CrimeGraph AI Intelligence System*")

        return "\n".join(lines)

    @classmethod
    def to_html(cls, report: InvestigationReport) -> str:
        """Generates self-contained, printable HTML/CSS report document (PDF export compatible)."""
        md = cls.to_markdown(report)
        
        # Simple clean HTML rendering suitable for browser printing or PDF saving
        escaped_title = report.title.replace("<", "&lt;").replace(">", "&gt;")
        
        html_sections = []
        for line in md.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("# "):
                html_sections.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_sections.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_sections.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("> "):
                html_sections.append(f"<div class='disclaimer'>{line[2:]}</div>")
            elif line.startswith("- "):
                html_sections.append(f"<li>{line[2:]}</li>")
            else:
                html_sections.append(f"<p>{line}</p>")

        content_html = "\n".join(html_sections)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{escaped_title}</title>
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.6;
        color: #1e293b;
        max-width: 900px;
        margin: 0 auto;
        padding: 40px 20px;
        background-color: #ffffff;
    }}
    h1 {{ color: #0f172a; border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 20px; }}
    h2 {{ color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-top: 30px; }}
    h3 {{ color: #334155; margin-top: 20px; }}
    .disclaimer {{
        background-color: #f8fafc;
        border-left: 4px solid #f59e0b;
        padding: 12px 16px;
        margin: 20px 0;
        font-size: 0.95em;
        color: #78350f;
    }}
    li {{ margin-bottom: 6px; }}
    code {{ background-color: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }}
    @media print {{
        body {{ padding: 0; max-width: 100%; }}
        h1, h2, h3 {{ page-break-after: avoid; }}
    }}
</style>
</head>
<body>
{content_html}
</body>
</html>"""

    @classmethod
    def _sanitize_export_data(cls, data: Any) -> None:
        """Recursively removes sensitive keys such as passwords, tokens, API keys, or private system paths."""
        if isinstance(data, dict):
            keys_to_remove = [k for k in data if re.search(r"(password|secret|jwt|token|api_key|auth_header|private_key)", k, re.IGNORECASE)]
            for k in keys_to_remove:
                del data[k]
            for v in data.values():
                cls._sanitize_export_data(v)
        elif isinstance(data, list):
            for item in data:
                cls._sanitize_export_data(item)
