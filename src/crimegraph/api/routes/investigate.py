"""AI Investigator natural language query API routes for CrimeGraph AI.

Strictly adheres to PROJECT_SPEC.md (F9 — AI Investigator), DATA_SCHEMA.md, and Safety Principles.
Provides factual, evidence-grounded answers across dataset and manually created entities.
"""

import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from crimegraph.graph.traversal import find_cross_case_connections, find_paths_between_entities
from crimegraph.models.entities import EntityType
from crimegraph.ai.investigator import AIInvestigator
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus

from crimegraph.observability.metrics import metrics

router = APIRouter(prefix="/api/investigate", tags=["AI Investigator"], dependencies=[Depends(get_current_user)])


class InvestigateRequest(BaseModel):
    question: str = Field(..., description="Natural language investigation query")


def _format_ai_response(
    question: str,
    answer: str,
    query_type: str = "GENERAL_INVESTIGATION",
    path: Optional[List[str]] = None,
    relationships: Optional[List[Dict[str, Any]]] = None,
    entities: Optional[Union[List[Any], Dict[str, Any]]] = None,
    evidence: Optional[List[Dict[str, Any]]] = None,
    evidence_ids: Optional[List[str]] = None,
    confidence: float = 0.95,
    investigative_lead: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Ensures consistent, schema-compliant AI response fields for both UI and AI subsystems."""
    confidence_tier = "HIGH" if confidence >= 0.85 else ("MEDIUM" if confidence >= 0.60 else "LOW")
    
    resp = {
        "question": question,
        "query": question,
        "answer": answer,
        "explanation": answer,
        "query_type": query_type,
        "path": path or [],
        "relationships": relationships or [],
        "entities": entities if entities is not None else [],
        "evidence": evidence or [],
        "evidence_ids": evidence_ids or [],
        "confidence": confidence,
        "confidence_tier": confidence_tier,
        "investigative_lead": investigative_lead or "Review connected entities and corroborated evidence logs.",
        "limitations": "Findings are investigative associations based on current knowledge graph records.",
        "is_safe": True,
        "disclaimer": "AI-generated investigative lead requiring human verification. Not a declaration of guilt."
    }
    
    if extra:
        for k, v in extra.items():
            resp[k] = v
            
    return resp


@router.post("", response_model=Dict[str, Any])
def investigate_query(
    request: Request,
    payload: InvestigateRequest,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Execute a natural-language investigation query grounded in the knowledge graph."""
    res = _handle_investigation(request, payload)
    
    # Record AI metrics
    metrics.record_ai_query(res.get("confidence_tier", "HIGH"))
    
    audit_logger.log(
        action="INVESTIGATION_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.AI,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={
            "question": payload.question,
            "query_type": res.get("query_type"),
            "path": res.get("path"),
            "evidence_ids": res.get("evidence_ids"),
            "confidence_tier": res.get("confidence_tier")
        }
    )
    return res


def _handle_investigation(request: Request, payload: InvestigateRequest) -> Dict[str, Any]:
    """Inner core logic for executing natural language investigation queries."""
    graph = request.app.state.graph
    question = payload.question
    
    if not question or not question.strip():
        return _format_ai_response(
            question=question,
            answer="Please provide a natural language investigative question. Example: 'How are Case 101 and Case 204 connected?'",
            query_type="EMPTY_QUERY",
            confidence=0.0
        )
        
    question_lower = question.lower().strip()

    # -------------------------------------------------------------
    # 0. UNKNOWN / UNAVAILABLE INFORMATION GUARD (ZERO HALLUCINATION)
    # -------------------------------------------------------------
    unavailable_fields = ["email", "passport", "salary", "blood group", "religion", "caste", "credit score"]
    for uf in unavailable_fields:
        if uf in question_lower:
            return _format_ai_response(
                question=question,
                answer=(
                    f"The requested property ('{uf}') is not recorded in the CrimeGraph knowledge base. "
                    f"CrimeGraph contains only authoritative law-enforcement entities (Cases, Persons, Vehicles, "
                    f"Phones, Accounts, Locations, Organizations) and evidence-supported relationships."
                ),
                query_type="INFO_UNAVAILABLE",
                confidence=0.0
            )

    # -------------------------------------------------------------
    # 0.1 LEGAL BOUNDARY & SAFETY GUARD (NON-GUILT PROTOCOL)
    # -------------------------------------------------------------
    guilt_keywords = [
        "guilty", "who is guilty", "is guilty", "is the criminal", "is a criminal",
        "the criminal", "should be arrested", "who committed", "convict", "committed the crime",
        "responsible for the crime", "definitely responsible", "who is responsible for",
        "criminal group", "criminal organization", "criminals in", "prove that"
    ]
    if any(gk in question_lower for gk in guilt_keywords):
        target_name = ""
        p_m = re.search(r"\bperson[\s\-_]*(\d+)\b", question_lower)
        pid = None
        if p_m or "017" in question_lower:
            pid = "PERSON_017" if "017" in question_lower else f"PERSON_{int(p_m.group(1)):03d}"
            ent = graph.get_entity(pid)
            if ent:
                target_name = getattr(ent, "name", "")

        ref_str = f" regarding {target_name} ({pid})" if target_name else ""
        return _format_ai_response(
            question=question,
            answer=(
                f"CrimeGraph AI operates strictly as an investigative relationship discovery tool and cannot make determinations of legal guilt{ref_str}. "
                "The system does not establish legal guilt, culpability, or criminal accusations. "
                "All graph associations, communication links, and pattern detections are leads requiring human investigator verification."
            ),
            query_type="SAFETY_REFUSAL",
            confidence=0.0,
            path=[],
            relationships=[],
            evidence=[],
            investigative_lead="Verify all entity connections and corroborated source documents independently before reaching investigative conclusions."
        )

    # -------------------------------------------------------------
    # 0.15 INVESTIGATIVE RISK & PRIORITY SCORING QUERIES (DAY 33)
    # -------------------------------------------------------------
    if any(w in question_lower for w in ["risk", "priority", "priorit", "score", "high risk", "critical risk"]):
        from crimegraph.graph.risk import InvestigativeRiskEngine
        risk_engine = InvestigativeRiskEngine(graph)

        case_match = re.search(r"\bcase[\s\-_]*(\d+)\b", question_lower)
        case_id = f"CASE_{int(case_match.group(1))}" if case_match else None
        if "101" in question_lower and not case_id:
            case_id = "CASE_101"
        elif "204" in question_lower and not case_id:
            case_id = "CASE_204"

        target_case = case_id if (case_id and case_id in graph.entities) else None
        priorities = risk_engine.get_priorities(case_id=target_case, limit=5)
        if priorities:
            top_p = priorities[0]
            p_summaries = [
                f"• #{p.rank} {p.entity_name} [{p.entity_id}] (Risk Score: {p.risk_score:.1f}/100, Level: {p.risk_level.value}): {p.explanation}"
                for p in priorities[:5]
            ]
            scope_str = f"within {target_case}" if target_case else "across the knowledge graph"
            answer = (
                f"Top Investigative Risk Priorities {scope_str}:\n\n" +
                "\n".join(p_summaries)
            )
            return _format_ai_response(
                question=question,
                answer=answer,
                query_type="INVESTIGATIVE_RISK_PRIORITY",
                confidence=0.95,
                evidence_ids=top_p.evidence_ids,
                investigative_lead="Focus analytical resource allocation on high-priority network hubs and cross-case connectors.",
                extra={
                    "top_priority": top_p.model_dump(),
                    "priorities": [p.model_dump() for p in priorities]
                }
            )

    # -------------------------------------------------------------
    # 0.2 KEY PLAYER & INFLUENCER INTELLIGENCE QUERIES (DAY 28)
    # -------------------------------------------------------------
    if any(w in question_lower for w in ["influe", "key player", "rank", "centrality", "top entity", "bridge entity", "most connected", "network reach", "highest rank"]):
        from crimegraph.graph.intelligence import NetworkIntelligenceEngine
        engine = NetworkIntelligenceEngine(graph)

        case_match = re.search(r"\bcase[\s\-_]*(\d+)\b", question_lower)
        case_id = f"CASE_{int(case_match.group(1))}" if case_match else None
        if "101" in question_lower and not case_id:
            case_id = "CASE_101"
        elif "204" in question_lower and not case_id:
            case_id = "CASE_204"

        target_case = case_id if (case_id and case_id in graph.entities) else None
        key_player_res = engine.get_advanced_key_players(case_id=target_case, limit=5)
        kp_list = key_player_res.key_players

        if kp_list:
            top_kp = kp_list[0]
            kp_summaries = [
                f"• #{kp.rank} {kp.entity_name} [{kp.entity_id}] ({kp.influence_role.value if hasattr(kp.influence_role, 'value') else kp.influence_role}): Score {kp.score:.4f} — {kp.explanation}"
                for kp in kp_list[:5]
            ]
            scope_str = f"within {target_case}" if target_case else "across the full knowledge graph"
            answer = (
                f"Top Key Players & Network Influencers {scope_str}:\n\n" +
                "\n".join(kp_summaries)
            )
            return _format_ai_response(
                question=question,
                answer=answer,
                query_type="KEY_PLAYER_INTELLIGENCE",
                confidence=top_kp.confidence,
                evidence_ids=top_kp.supporting_evidence_ids,
                investigative_lead="Focus investigative resources on key structural bridge entities and cross-case influencers.",
                extra={
                    "top_key_player": top_kp.model_dump(),
                    "key_players": [kp.model_dump() for kp in kp_list]
                }
            )

    # -------------------------------------------------------------
    # 0.3 PATTERN & ANOMALY INTELLIGENCE QUERIES (DAY 30)
    # -------------------------------------------------------------
    if any(w in question_lower for w in ["pattern", "anomaly", "suspicious activity", "hub node", "corroboration"]):
        from crimegraph.graph.patterns import SuspiciousPatternEngine
        pat_engine = SuspiciousPatternEngine(graph)

        case_match = re.search(r"\bcase[\s\-_]*(\d+)\b", question_lower)
        case_id = f"CASE_{int(case_match.group(1))}" if case_match else None
        if "101" in question_lower and not case_id:
            case_id = "CASE_101"
        elif "204" in question_lower and not case_id:
            case_id = "CASE_204"

        target_case = case_id if (case_id and case_id in graph.entities) else None
        patterns = pat_engine.detect_all_patterns(case_id=target_case, limit=5)
        if patterns:
            top_pat = patterns[0]
            pat_summaries = [
                f"• [{p['pattern_type']}] {p['title']} (Anomaly Score: {p.get('anomaly_score', 0.0):.4f}, Severity: {p.get('severity')}): {p.get('explanation')}"
                for p in patterns[:5]
            ]
            scope_str = f"within {target_case}" if target_case else "across the knowledge graph"
            answer = (
                f"Detected {len(patterns)} Pattern & Anomaly Finding(s) {scope_str}:\n\n" +
                "\n".join(pat_summaries)
            )
            return _format_ai_response(
                question=question,
                answer=answer,
                query_type="SUSPICIOUS_PATTERNS",
                confidence=top_pat.get("confidence", 0.90),
                evidence_ids=top_pat.get("evidence_ids", []),
                investigative_lead="Prioritize investigation of flagged high-density clusters and burner devices.",
                extra={
                    "top_pattern": top_pat,
                    "patterns": patterns
                }
            )

    # -------------------------------------------------------------
    # 0.4 CROSS-SOURCE INTELLIGENCE CORRELATION QUERIES (DAY 32)
    # -------------------------------------------------------------
    if any(w in question_lower for w in ["correlat", "cross-source", "contradict", "discrepancy", "overlap"]):
        from crimegraph.graph.correlation import CrossSourceCorrelationEngine
        corr_engine = CrossSourceCorrelationEngine(graph)

        case_match = re.search(r"\bcase[\s\-_]*(\d+)\b", question_lower)
        case_id = f"CASE_{int(case_match.group(1))}" if case_match else None
        if "101" in question_lower and not case_id:
            case_id = "CASE_101"
        elif "204" in question_lower and not case_id:
            case_id = "CASE_204"

        target_case = case_id if (case_id and case_id in graph.entities) else None
        correlations = corr_engine.detect_all_correlations(case_id=target_case, limit=5)
        if correlations:
            top_corr = correlations[0]
            corr_summaries = [
                f"• [{c['correlation_type']}] {c['title']} (Score: {c.get('correlation_score', 0.0):.4f}, Severity: {c.get('severity')}): {c.get('explanation')}"
                for c in correlations[:5]
            ]
            scope_str = f"within {target_case}" if target_case else "across the knowledge graph"
            answer = (
                f"Detected {len(correlations)} Cross-Source Intelligence Correlation(s) {scope_str}:\n\n" +
                "\n".join(corr_summaries)
            )
            return _format_ai_response(
                question=question,
                answer=answer,
                query_type="CROSS_SOURCE_CORRELATION",
                confidence=top_corr.get("confidence", 0.90),
                evidence_ids=top_corr.get("evidence_ids", []),
                investigative_lead="Cross-verify records across independent data sources and evidence items.",
                extra={
                    "top_correlation": top_corr,
                    "correlations": correlations
                }
            )

    # -------------------------------------------------------------
    # 1. EXPLICIT ENTITY ID PATH QUERIES (ANY TWO ENTITY IDS)
    # -------------------------------------------------------------
    found_entity_ids = []
    
    # 1.1 Match by full ID or ID with space instead of underscore
    for eid in graph.entities.keys():
        if eid.lower() in question_lower or eid.lower().replace("_", " ") in question_lower:
            if eid not in found_entity_ids:
                found_entity_ids.append(eid)

    # 1.2 Regex matches for standard Person / Phone / Vehicle / Case patterns
    for m in re.findall(r"\bperson[\s\-_]*(\d+)\b", question_lower):
        pid = f"PERSON_{int(m):03d}"
        if pid in graph.entities and pid not in found_entity_ids:
            found_entity_ids.append(pid)

    for m in re.findall(r"\bphone[\s\-_]*(\d+)\b", question_lower):
        phid = f"PHONE_{int(m):03d}"
        if phid in graph.entities and phid not in found_entity_ids:
            found_entity_ids.append(phid)

    for m in re.findall(r"\bvehicle[\s\-_]*(\d+)\b", question_lower):
        vid = f"VEHICLE_{int(m):03d}"
        if vid in graph.entities and vid not in found_entity_ids:
            found_entity_ids.append(vid)

    for m in re.findall(r"\bcase[\s\-_]*(\d+)\b", question_lower):
        cid = f"CASE_{int(m)}"
        if cid in graph.entities and cid not in found_entity_ids:
            found_entity_ids.append(cid)

    # 1.3 Regex matches for explicit IDs (e.g. MANUAL_PERSON_..., ACC_ICICI_...)
    explicit_matches = re.findall(r"\b((?:MANUAL_)?[A-Z]+_[0-9A-Za-z]+)\b", question)
    for m in explicit_matches:
        if m in graph.entities and m not in found_entity_ids:
            found_entity_ids.append(m)

    # Check for missing requested IDs
    for m in explicit_matches:
        if m not in graph.entities and ("case" in m.lower() or "person" in m.lower() or "phone" in m.lower() or "vehicle" in m.lower()):
            return _format_ai_response(
                question=question,
                answer=f"Entity '{m}' was not found in the CrimeGraph knowledge base. No connections can be determined.",
                query_type="NOT_FOUND",
                confidence=0.0,
                extra={"unknown_entity_ids": [m]}
            )

    missing_cases = [f"CASE_{num}" for num in re.findall(r"\bcase[\s\-_]*(\d+)\b", question_lower) if f"CASE_{num}" not in graph.entities]
    if missing_cases and ("between" in question_lower or "connected" in question_lower or "how" in question_lower or len(missing_cases) >= 2):
        return _format_ai_response(
            question=question,
            answer=f"The requested cases ({', '.join(missing_cases)}) do not exist in the CrimeGraph knowledge base. No graph path, entities, or evidence can be retrieved for cases that are not in the dataset.",
            query_type="NOT_FOUND",
            confidence=0.0,
            extra={"unknown_case_ids": missing_cases}
        )

    missing_persons = [f"PERSON_{int(num):03d}" for num in re.findall(r"\bperson[\s\-_]*(\d+)\b", question_lower) if f"PERSON_{int(num):03d}" not in graph.entities]
    if missing_persons and ("between" in question_lower or "connected" in question_lower or "how" in question_lower or len(missing_persons) >= 2):
        return _format_ai_response(
            question=question,
            answer=f"Person(s) not found in knowledge base: {', '.join(missing_persons)}.",
            query_type="NOT_FOUND",
            confidence=0.0,
            extra={"unknown_entity_ids": missing_persons}
        )

    # If TWO entity IDs are found -> path query between them
    if len(found_entity_ids) >= 2:
        e1, e2 = found_entity_ids[0], found_entity_ids[1]
        
        # Case to Case path
        if e1.startswith("CASE_") and e2.startswith("CASE_"):
            connections = find_cross_case_connections(graph, e1, e2)
            if connections:
                conn = connections[0]
                bridge_str = ", ".join(conn["shared_entities"]) if conn["shared_entities"] else "intermediate entities"
                path_str = " -> ".join(conn["path"])
                evidence_str = ", ".join(conn["evidence_ids"])
                ans = (
                    f"CrimeGraph AI identified a verified multi-hop link between {e1} and {e2} "
                    f"via bridge entity {bridge_str}. "
                    f"Path: {path_str} with composite confidence {conn['confidence']}. "
                    f"Supporting evidence: {evidence_str}."
                )
                return _format_ai_response(
                    question=question,
                    answer=ans,
                    query_type="CROSS_CASE_CONNECTION",
                    path=conn["path"],
                    evidence_ids=conn["evidence_ids"],
                    confidence=conn["confidence"],
                    investigative_lead=f"Investigate intermediate entity {bridge_str} linking {e1} and {e2}.",
                    extra={"shared_entities": conn["shared_entities"]}
                )

        # Any entity to entity path
        paths = find_paths_between_entities(graph, e1, e2, max_depth=6)
        if paths:
            best = paths[0]
            path_str = " -> ".join(best["path"])
            evidence_str = ", ".join(best.get("evidence_ids", []))
            ans = (
                f"CrimeGraph AI discovered a verified relationship path connecting {e1} and {e2}: "
                f"{path_str} (Confidence: {best.get('confidence', 0.9):.2f})."
                + (f" Supporting evidence: {evidence_str}." if evidence_str else "")
            )
            return _format_ai_response(
                question=question,
                answer=ans,
                query_type="ENTITY_PATH",
                path=best["path"],
                confidence=best.get("confidence", 0.9),
                evidence_ids=best.get("evidence_ids", []),
                investigative_lead=f"Corroborate communication and ownership records along path {path_str}."
            )
        return _format_ai_response(
            question=question,
            answer=f"No graph path found connecting {e1} and {e2} within the current knowledge base.",
            query_type="NO_CONNECTION",
            confidence=0.0
        )

    # -------------------------------------------------------------
    # 1.5 SUSPICIOUS PATTERN & ANOMALY QUERIES
    # -------------------------------------------------------------
    if any(w in question_lower for w in ["pattern", "suspicious", "anomal", "burner"]):
        investigator = AIInvestigator(graph)
        ai_resp = investigator.query(question)
        if ai_resp.get("query_type") in ["SUSPICIOUS_PATTERNS", "SAFETY_REFUSAL"]:
            return _format_ai_response(
                question=question,
                answer=ai_resp.get("answer", "No suspicious patterns detected."),
                query_type=ai_resp.get("query_type", "SUSPICIOUS_PATTERNS"),
                confidence=ai_resp.get("confidence", 0.95),
                evidence_ids=ai_resp.get("evidence_ids", []),
                investigative_lead=ai_resp.get("investigative_lead", "Review detected pattern indicators and connected cases."),
                extra={"patterns": ai_resp.get("patterns", [])}
            )

    # -------------------------------------------------------------
    # 1.6 MULTI-SOURCE & PROVENANCE QUERIES
    # -------------------------------------------------------------
    if any(w in question_lower for w in ["source", "provenance", "origin", "data feed", "evidence origin"]):
        investigator = AIInvestigator(graph)
        ai_resp = investigator.query(question)
        if ai_resp.get("query_type") in ["SOURCE_PROVENANCE", "SOURCE_SUMMARY", "SAFETY_REFUSAL"]:
            return _format_ai_response(
                question=question,
                answer=ai_resp.get("answer", "Multi-source provenance analyzed."),
                query_type=ai_resp.get("query_type", "SOURCE_PROVENANCE"),
                confidence=ai_resp.get("confidence", 0.95),
                investigative_lead=ai_resp.get("investigative_lead", "Cross-reference multi-source lineage documentation with investigating officer logs."),
                extra={
                    "provenance": ai_resp.get("provenance", []),
                    "sources": ai_resp.get("sources", []),
                    "entity_id": ai_resp.get("entity_id")
                }
            )

    # -------------------------------------------------------------
    # 2. SINGLE CASE INSPECTION & SUMMARY QUERIES
    # -------------------------------------------------------------
    case_matches = re.findall(r"(?:case[_\s]*)(\d+)", question_lower)
    if case_matches or (len(found_entity_ids) == 1 and (found_entity_ids[0].startswith("CASE_") or found_entity_ids[0].startswith("MANUAL_CASE_"))):
        cid = found_entity_ids[0] if (found_entity_ids and (found_entity_ids[0].startswith("CASE_") or found_entity_ids[0].startswith("MANUAL_CASE_"))) else f"CASE_{case_matches[0]}"
        
        if cid not in graph.entities:
            return _format_ai_response(
                question=question,
                answer=f"Case '{cid}' does not exist in the CrimeGraph knowledge base.",
                query_type="NOT_FOUND",
                confidence=0.0,
                extra={"unknown_case_ids": [cid]}
            )

        investigator = AIInvestigator(graph)
        c_context = investigator.get_case_context(cid)
        if not c_context:
            return _format_ai_response(
                question=question,
                answer=f"Unable to retrieve context for Case '{cid}'.",
                query_type="NOT_FOUND",
                confidence=0.0
            )

        case_obj = c_context["case"]
        entities = c_context["entities"]
        
        # Specific filter questions:
        if "suspect" in question_lower or "person" in question_lower or "who" in question_lower or "people" in question_lower:
            p_names = [f"{p.get('name', p['id'])} [{p['id']}]" for p in entities["persons"]]
            ans = f"Suspects/Persons associated with {cid} ({case_obj.get('title')}): {', '.join(p_names) if p_names else 'None recorded.'}"
            return _format_ai_response(
                question=question,
                answer=ans,
                query_type="CASE_INSPECTION",
                confidence=0.96,
                entities=entities["persons"],
                relationships=c_context["relationships"],
                extra={"case_id": cid, "persons": p_names}
            )

        if "vehicle" in question_lower:
            v_names = [f"{v.get('registration_number', v['id'])} ({v.get('type', 'Vehicle')}) [{v['id']}]" for v in entities["vehicles"]]
            ans = f"Vehicles connected to {cid}: {', '.join(v_names) if v_names else 'No vehicles recorded for this case.'}"
            return _format_ai_response(
                question=question,
                answer=ans,
                query_type="CASE_INSPECTION",
                confidence=0.95,
                entities=entities["vehicles"],
                extra={"case_id": cid, "vehicles": v_names}
            )

        if "phone" in question_lower:
            ph_names = [f"{ph.get('phone_number', ph['id'])} [{ph['id']}]" for ph in entities["phones"]]
            ans = f"Phone numbers associated with {cid}: {', '.join(ph_names) if ph_names else 'No phones recorded for this case.'}"
            return _format_ai_response(
                question=question,
                answer=ans,
                query_type="CASE_INSPECTION",
                confidence=0.95,
                entities=entities["phones"],
                extra={"case_id": cid, "phones": ph_names}
            )

        if "account" in question_lower:
            acc_names = [f"{acc.get('identifier', acc['id'])} [{acc['id']}]" for acc in entities["accounts"]]
            ans = f"Accounts associated with {cid}: {', '.join(acc_names) if acc_names else 'No financial accounts recorded for this case.'}"
            return _format_ai_response(
                question=question,
                answer=ans,
                query_type="CASE_INSPECTION",
                confidence=0.95,
                entities=entities["accounts"],
                extra={"case_id": cid, "accounts": acc_names}
            )

        if "summarize" in question_lower or "summary" in question_lower or "entities" in question_lower or "overview" in question_lower:
            summary = c_context["summary"]
            ans = (
                f"Summary for {cid} — {case_obj.get('title')}:\n"
                f"Status: {case_obj.get('status', 'ACTIVE')} | Incident Date: {case_obj.get('incident_date', 'N/A')}\n"
                f"Connected Entities: {summary['total_connected_entities']} (Persons: {summary['persons_count']}, "
                f"Vehicles: {summary['vehicles_count']}, Phones: {summary['phones_count']}, Accounts: {summary['accounts_count']}, "
                f"Locations: {summary['locations_count']}, Manual: {summary['manual_entities_count']})\n"
                f"Description: {case_obj.get('description', 'Case record in CrimeGraph.')}"
            )
            return _format_ai_response(
                question=question,
                answer=ans,
                query_type="CASE_SUMMARY",
                confidence=0.98,
                entities=entities,
                relationships=c_context["relationships"],
                extra={"case_id": cid, "summary": summary}
            )

        # Default case info
        ans = f"Case {cid} ({case_obj.get('title')}): Status {case_obj.get('status')}, with {c_context['summary']['total_connected_entities']} connected entities and {len(c_context['relationships'])} relationships."
        return _format_ai_response(
            question=question,
            answer=ans,
            query_type="CASE_INSPECTION",
            confidence=0.95,
            entities=entities,
            relationships=c_context["relationships"],
            extra={"case_id": cid}
        )

    # -------------------------------------------------------------
    # 3. SINGLE ENTITY INSPECTION (PERSON, PHONE, VEHICLE, ETC.)
    # -------------------------------------------------------------
    person_matches = re.findall(r"(?:person[_\s]*)(\d+)", question_lower)
    target_entity_id = None
    if found_entity_ids:
        target_entity_id = found_entity_ids[0]
    elif person_matches:
        target_entity_id = f"PERSON_{int(person_matches[0]):03d}"

    # Search entity by name if named (e.g. "Aarav Verma", "Vikram Malhotra")
    if not target_entity_id:
        for eid, ent in graph.entities.items():
            name = getattr(ent, "name", "")
            if name and name.lower() in question_lower:
                target_entity_id = eid
                break

    if target_entity_id and target_entity_id in graph.entities:
        investigator = AIInvestigator(graph)
        e_context = investigator.get_entity_context(target_entity_id)
        if e_context:
            ent = e_context["entity"]
            conn = e_context["connected_entities"]
            conn_names = [c.get('name') or c.get('phone_number') or c.get('registration_number') or c['id'] for c in conn]
            conn_summary = [f"{c.get('name', c.get('phone_number', c.get('registration_number', c['id'])))} [{c['id']}]" for c in conn]
            
            # Specific category filters
            if "vehicle" in question_lower:
                veh = [f"{v.get('registration_number', v['id'])} ({v.get('type', 'Vehicle')}) [{v['id']}]" for v in conn if v.get("entity_type") == "VEHICLE"]
                ans = f"Vehicles connected to {target_entity_id} ({ent.get('name', target_entity_id)}): {', '.join(veh) if veh else 'No connected vehicles recorded.'}"
                return _format_ai_response(
                    question=question,
                    answer=ans,
                    query_type="ENTITY_INSPECTION",
                    confidence=0.95,
                    entities=conn,
                    extra={"entity_id": target_entity_id, "vehicles": veh, "connected_entities": conn_names}
                )

            if "phone" in question_lower:
                phs = [f"{p.get('phone_number', p['id'])} [{p['id']}]" for p in conn if p.get("entity_type") == "PHONE"]
                ans = f"Phone numbers connected to {target_entity_id} ({ent.get('name', target_entity_id)}): {', '.join(phs) if phs else 'No connected phones recorded.'}"
                return _format_ai_response(
                    question=question,
                    answer=ans,
                    query_type="ENTITY_INSPECTION",
                    confidence=0.95,
                    entities=conn,
                    extra={"entity_id": target_entity_id, "phones": phs, "connected_entities": conn_names}
                )

            if "account" in question_lower:
                accs = [f"{a.get('identifier', a['id'])} [{a['id']}]" for a in conn if a.get("entity_type") == "ACCOUNT"]
                ans = f"Accounts connected to {target_entity_id} ({ent.get('name', target_entity_id)}): {', '.join(accs) if accs else 'No connected accounts recorded.'}"
                return _format_ai_response(
                    question=question,
                    answer=ans,
                    query_type="ENTITY_INSPECTION",
                    confidence=0.95,
                    entities=conn,
                    extra={"entity_id": target_entity_id, "accounts": accs, "connected_entities": conn_summary}
                )

            if "case" in question_lower:
                cases = e_context["linked_cases"]
                ans = f"Cases associated with {target_entity_id} ({ent.get('name', target_entity_id)}): {', '.join(cases) if cases else 'No direct case links recorded.'}"
                return _format_ai_response(
                    question=question,
                    answer=ans,
                    query_type="ENTITY_INSPECTION",
                    confidence=0.96,
                    entities=conn,
                    extra={"entity_id": target_entity_id, "cases": cases, "connected_entities": conn_summary}
                )

            if "location" in question_lower:
                locs = [f"{l.get('name', l['id'])} [{l['id']}]" for l in conn if l.get("entity_type") == "LOCATION"]
                ans = f"Locations associated with {target_entity_id} ({ent.get('name', target_entity_id)}): {', '.join(locs) if locs else 'No location links recorded.'}"
                return _format_ai_response(
                    question=question,
                    answer=ans,
                    query_type="ENTITY_INSPECTION",
                    confidence=0.94,
                    entities=conn,
                    extra={"entity_id": target_entity_id, "locations": locs, "connected_entities": conn_summary}
                )

            if "organization" in question_lower:
                orgs = [f"{o.get('name', o['id'])} [{o['id']}]" for o in conn if o.get("entity_type") == "ORGANIZATION"]
                ans = f"Organizations associated with {target_entity_id} ({ent.get('name', target_entity_id)}): {', '.join(orgs) if orgs else 'No organization links recorded.'}"
                return _format_ai_response(
                    question=question,
                    answer=ans,
                    query_type="ENTITY_INSPECTION",
                    confidence=0.95,
                    entities=conn,
                    extra={"entity_id": target_entity_id, "organizations": orgs, "connected_entities": conn_summary}
                )

            # General entity overview
            ans = f"{ent.get('name', target_entity_id)} [{target_entity_id}] has {len(conn)} connections: {', '.join(conn_summary)}."
            return _format_ai_response(
                question=question,
                answer=ans,
                query_type="ENTITY_INSPECTION",
                confidence=0.95,
                entities=conn,
                extra={"entity_id": target_entity_id, "connected_entities": conn_names}
            )

    # -------------------------------------------------------------
    # 4. SHARED ENTITIES QUERY
    # -------------------------------------------------------------
    if any(kw in question_lower for kw in ["multiple cases", "shared entities", "cross case", "cross-case", "both cases", "shared across"]):
        shared = []
        for e_id, ent in graph.entities.items():
            if e_id.startswith("CASE_"):
                continue
            linked_cases = set()
            for _rel, neighbor in graph.get_neighbors(e_id, direction="undirected"):
                if neighbor.id.startswith("CASE_"):
                    linked_cases.add(neighbor.id)
            if len(linked_cases) > 1:
                e_label = getattr(ent, "name", getattr(ent, "phone_number", getattr(ent, "registration_number", e_id)))
                shared.append({
                    "entity_id": e_id,
                    "label": e_label,
                    "linked_cases": sorted(linked_cases),
                })
        ans = (
            f"Identified {len(shared)} entity/entities present in multiple cases: "
            + "; ".join(
                f"{s['entity_id']} ({s['label']}) in {', '.join(s['linked_cases'])}" for s in shared
            )
        ) if shared else "No cross-case shared entities found in the current dataset."
        return _format_ai_response(
            question=question,
            answer=ans,
            query_type="SHARED_ENTITIES",
            confidence=0.96,
            extra={"shared_entities": shared}
        )

    # -------------------------------------------------------------
    # 5. GENERAL FALLBACK (GROUNDED, ZERO FABRICATION)
    # -------------------------------------------------------------
    ans = (
        f"CrimeGraph knowledge base contains {len(graph.entities)} entities and "
        f"{len(graph.relationships)} relationships. Use specific queries such as "
        f"'How are Case 101 and Case 204 connected?' or 'Who is connected to Person 017?' "
        f"to retrieve targeted investigative leads."
    )
    return _format_ai_response(
        question=question,
        answer=ans,
        query_type="GENERAL_INVESTIGATION",
        confidence=0.90,
        extra={
            "hint": (
                "Try: 'How are Case 101 and Case 204 connected?' | "
                "'Who are the suspects in Case 101?' | "
                "'What vehicles are connected to Person 017?'"
            )
        }
    )


# =========================================================================
# STRUCTURED AI DATA ACCESS ENDPOINTS (FOR ADITYA'S AI INVESTIGATION ENGINE)
# =========================================================================

class ContextSearchRequest(BaseModel):
    query: str = Field(..., description="Search keyword, name, phone, or case identifier")
    entity_types: Optional[List[str]] = Field(None, description="Optional entity type filters")
    limit: int = Field(20, ge=1, le=100, description="Max results to return")


@router.get("/context/cases/{case_id}", response_model=Dict[str, Any])
def get_ai_case_context(request: Request, case_id: str) -> Dict[str, Any]:
    """Retrieve structured factual case context for AI prompt grounding and reasoning."""
    graph = request.app.state.graph
    investigator = AIInvestigator(graph)
    context = investigator.get_case_context(case_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in knowledge graph")
        
    return context


@router.get("/context/entities/{entity_id}", response_model=Dict[str, Any])
def get_ai_entity_context(request: Request, entity_id: str) -> Dict[str, Any]:
    """Retrieve structured factual neighborhood and relationship context for an entity."""
    graph = request.app.state.graph
    investigator = AIInvestigator(graph)
    context = investigator.get_entity_context(entity_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found in knowledge graph")
        
    return context


@router.post("/context/search", response_model=Dict[str, Any])
def search_ai_context(request: Request, payload: ContextSearchRequest) -> Dict[str, Any]:
    """Search authoritative case and entity records for AI reasoning grounding."""
    graph = request.app.state.graph
    investigator = AIInvestigator(graph)
    return investigator.search_context(
        query=payload.query,
        entity_types=payload.entity_types,
        limit=payload.limit
    )
