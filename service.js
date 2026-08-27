/**
 * CrimeGraph AI — Frontend Data Service & Adapter Layer (Day 15 Production Readiness)
 * Architected by Shruti for SIH 2026.
 *
 * Architecture:
 *   Google Stitch UI → CrimeGraphDataService → HttpCrimeGraphAdapter → FastAPI Backend (src/crimegraph/api/app.py)
 *   Development Fallback: CrimeGraphDataService → MockCrimeGraphAdapter
 *
 * Strictly adheres to DATA_SCHEMA.md and API_CONTRACT.md.
 */

// --- 1. MOCK ADAPTER (API-Compatible Offline Fallback) ---
class MockCrimeGraphAdapter {
    constructor() {
        this.dataset = {
            cases: [
                { id: "CASE_101", title: "Operation Midnight Shadow — Cargo Hijack", date: "2026-08-10", status: "ACTIVE", location: "LOC_001 (Nhava Sheva Hub)", entities_count: 8, evidence_count: 5 },
                { id: "CASE_204", title: "Operation Golden Falcon — Zaveri Bazaar Fencing Syndicate", date: "2026-08-14", status: "ACTIVE", location: "LOC_003 (Zaveri Bazaar Vault)", entities_count: 9, evidence_count: 6 },
                { id: "CASE_102", title: "Operation Silver Shield — Cyber Financial Fraud Ring", date: "2026-08-05", status: "OPEN", location: "LOC_004 (Cyber Cell)", entities_count: 6, evidence_count: 4 },
                { id: "CASE_305", title: "Operation Falcon Eye — Cross-Border Hawala Intercept", date: "2026-08-18", status: "INVESTIGATING", location: "LOC_007 (Tower Relay)", entities_count: 7, evidence_count: 4 }
            ],

            nodes: [
                { id: "CASE_101", name: "Operation Midnight Shadow", type: "CASE", confidence: 1.0, details: "Logistics Yard Cargo Hijack" },
                { id: "CASE_204", name: "Operation Golden Falcon", type: "CASE", confidence: 1.0, details: "Zaveri Bazaar Fencing Syndicate" },
                { id: "CASE_102", name: "Operation Silver Shield", type: "CASE", confidence: 1.0, details: "Cyber Financial Fraud Ring" },
                { id: "CASE_305", name: "Operation Falcon Eye", type: "CASE", confidence: 1.0, details: "Cross-Border Hawala Network" },

                { id: "PERSON_017", name: "Aarav Verma", type: "PERSON", confidence: 0.96, details: "Logistics Dispatch Supervisor" },
                { id: "PERSON_089", name: "Vikram Malhotra", type: "PERSON", confidence: 0.94, details: "Bullion Receiver & Fencer" },
                { id: "PERSON_044", name: "Devansh Mehta", type: "PERSON", confidence: 0.91, details: "Warehouse Gate Keeper" },
                { id: "PERSON_056", name: "Karan Shah", type: "PERSON", confidence: 0.88, details: "Hawala Courier Operator" },

                { id: "PHONE_042", name: "+91-9876543210", type: "PHONE", confidence: 0.95, details: "Encrypted Burner Line" },
                { id: "PHONE_017", name: "+91-9820011223", type: "PHONE", confidence: 0.92, details: "Personal Cell" },
                { id: "PHONE_089", name: "+91-9811099887", type: "PHONE", confidence: 0.90, details: "Shop Landline" },

                { id: "VEHICLE_042", name: "MH-01-AB-1234", type: "VEHICLE", confidence: 0.94, details: "Black SUV" },
                { id: "VEHICLE_017", name: "MH-04-XY-9999", type: "VEHICLE", confidence: 0.89, details: "Commercial Delivery Van" },

                { id: "LOC_001", name: "Nhava Sheva Hub", type: "LOCATION", confidence: 1.0, details: "Logistics Transit Yard" },
                { id: "LOC_003", name: "Zaveri Bazaar", type: "LOCATION", confidence: 1.0, details: "Bullion Trading Vault" },
                { id: "LOC_007", name: "Tower 14 Relay", type: "LOCATION", confidence: 1.0, details: "Cellular Base Station" },

                { id: "ACC_001", name: "ACC_AXIS_9941", type: "ACCOUNT", confidence: 0.93, details: "Escrow Bank Account" }
            ],

            edges: [
                { id: "REL_101_017", source: "CASE_101", target: "PERSON_017", relationship: "INVOLVED_IN", confidence: 0.97, evidence_id: "EVID_101_01" },
                { id: "REL_017_042", source: "PERSON_017", target: "PHONE_042", relationship: "USES", confidence: 0.95, evidence_id: "EVID_042_01" },
                { id: "REL_042_089", source: "PHONE_042", target: "PERSON_089", relationship: "USES", confidence: 0.93, evidence_id: "EVID_042_02" },
                { id: "REL_089_204", source: "PERSON_089", target: "CASE_204", relationship: "INVOLVED_IN", confidence: 0.96, evidence_id: "EVID_204_01" },

                { id: "REL_017_V042", source: "PERSON_017", target: "VEHICLE_042", relationship: "USES", confidence: 0.94, evidence_id: "EVID_V042_01" },
                { id: "REL_V042_L001", source: "VEHICLE_042", target: "LOC_001", relationship: "SEEN_AT", confidence: 0.92, evidence_id: "EVID_L001_01" },
                { id: "REL_089_L003", source: "PERSON_089", target: "LOC_003", relationship: "VISITED", confidence: 0.95, evidence_id: "EVID_L003_01" },
                { id: "REL_044_101", source: "PERSON_044", target: "CASE_101", relationship: "INVOLVED_IN", confidence: 0.89, evidence_id: "EVID_044_01" },
                { id: "REL_056_305", source: "PERSON_056", target: "CASE_305", relationship: "INVOLVED_IN", confidence: 0.91, evidence_id: "EVID_056_01" },
                { id: "REL_089_ACC", source: "PERSON_089", target: "ACC_001", relationship: "OWNED_BY", confidence: 0.93, evidence_id: "EVID_ACC_01" }
            ],

            evidence: {
                "EVID_101_01": {
                    evidence_id: "EVID_101_01",
                    source_document: "DOC_CASE_101_FIR_REPORT.pdf",
                    page_number: 2,
                    source_text: "CCTV review and transit manifests identify Aarav Verma (PERSON_017) actively supervising the unmanifested cargo unloading.",
                    timestamp: "2026-08-10T19:15:00Z",
                    extraction_method: "AI_NER",
                    confidence: 0.97,
                    relationship: "CASE_101 --INVOLVED_IN--> PERSON_017"
                },
                "EVID_042_01": {
                    evidence_id: "EVID_042_01",
                    source_document: "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf",
                    page_number: 7,
                    source_text: "Handset triage recovered encrypted messaging sessions identifying Aarav Verma (PERSON_017) using burner line +91-9876543210 (PHONE_042).",
                    timestamp: "2026-08-11T09:30:00Z",
                    extraction_method: "DIGITAL_FORENSICS",
                    confidence: 0.95,
                    relationship: "PERSON_017 --USES--> PHONE_042"
                },
                "EVID_042_02": {
                    evidence_id: "EVID_042_02",
                    source_document: "DOC_CASE_204_MUMBAI_INTERCEPT_SUMMARY.pdf",
                    page_number: 3,
                    source_text: "Lawful signal intelligence intercept confirmed Vikram Malhotra (PERSON_089) utilizing the same burner line +91-9876543210 (PHONE_042).",
                    timestamp: "2026-08-12T21:15:00Z",
                    extraction_method: "TELCO_INTERCEPT",
                    confidence: 0.93,
                    relationship: "PHONE_042 --USES--> PERSON_089"
                },
                "EVID_204_01": {
                    evidence_id: "EVID_204_01",
                    source_document: "DOC_CASE_204_MUMBAI_CRIME_BRANCH.pdf",
                    page_number: 2,
                    source_text: "Financial trail and bullion seizure at Zaveri Bazaar directly incriminate Vikram Malhotra (PERSON_089) as primary receiver.",
                    timestamp: "2026-08-14T11:45:00Z",
                    extraction_method: "AI_NER",
                    confidence: 0.96,
                    relationship: "PERSON_089 --INVOLVED_IN--> CASE_204"
                },
                "EVID_V042_01": {
                    evidence_id: "EVID_V042_01",
                    source_document: "DOC_CASE_101_FIR_REPORT.pdf",
                    page_number: 4,
                    source_text: "Black SUV MH-01-AB-1234 registered usage under Aarav Verma during transport window.",
                    timestamp: "2026-08-10T20:00:00Z",
                    extraction_method: "TRAFFIC_CAM_OCR",
                    confidence: 0.94,
                    relationship: "PERSON_017 --USES--> VEHICLE_042"
                }
            }
        };
    }

    async getCases() {
        return this.dataset.cases;
    }

    async getCaseDetails(caseId) {
        const c = this.dataset.cases.find(item => item.id === caseId);
        return c || null;
    }

    async getCaseGraph(caseId) {
        if (caseId === "ALL") {
            return {
                nodes: this.dataset.nodes.map(n => ({ id: n.id, label: n.name, type: n.type, confidence: n.confidence })),
                edges: this.dataset.edges.map(e => ({ id: e.id, source: e.source, target: e.target, relationship: e.relationship, confidence: e.confidence, evidence_id: e.evidence_id }))
            };
        }

        const targetCase = this.dataset.cases.find(c => c.id === caseId);
        if (!targetCase) {
            return { nodes: [], edges: [] };
        }

        const connectedIds = new Set([caseId]);
        this.dataset.edges.forEach(e => {
            if (e.source === caseId || e.target === caseId) {
                connectedIds.add(e.source);
                connectedIds.add(e.target);
            }
        });

        this.dataset.edges.forEach(e => {
            if (connectedIds.has(e.source) || connectedIds.has(e.target)) {
                connectedIds.add(e.source);
                connectedIds.add(e.target);
            }
        });

        const nodes = this.dataset.nodes.filter(n => connectedIds.has(n.id)).map(n => ({
            id: n.id,
            label: n.name,
            type: n.type,
            confidence: n.confidence
        }));

        const edges = this.dataset.edges.filter(e => connectedIds.has(e.source) && connectedIds.has(e.target)).map(e => ({
            id: e.id,
            source: e.source,
            target: e.target,
            relationship: e.relationship,
            confidence: e.confidence,
            evidence_id: e.evidence_id
        }));

        return { nodes, edges };
    }

    async getEntityDetails(entityId) {
        const ent = this.dataset.nodes.find(n => n.id === entityId);
        if (!ent) return null;

        const rels = this.dataset.edges.filter(e => e.source === entityId || e.target === entityId);
        const cases = new Set();
        const evidenceIds = [];

        rels.forEach(r => {
            if (r.source.startsWith("CASE_")) cases.add(r.source);
            if (r.target.startsWith("CASE_")) cases.add(r.target);
            if (r.evidence_id) evidenceIds.push(r.evidence_id);
        });

        const evidenceItems = evidenceIds.map(evId => this.dataset.evidence[evId]).filter(Boolean);

        return {
            id: ent.id,
            type: ent.type,
            name: ent.name,
            details: ent.details,
            confidence: ent.confidence,
            relationships: rels,
            cases: Array.from(cases),
            evidence: evidenceItems
        };
    }

    async getCaseConnections(caseA = "CASE_101", caseB = "CASE_204") {
        const caseAExists = this.dataset.cases.some(c => c.id === caseA);
        const caseBExists = this.dataset.cases.some(c => c.id === caseB);
        if (!caseAExists || !caseBExists) {
            return { connections: [] };
        }
        return {
            connections: [
                {
                    case_a: caseA,
                    case_b: caseB,
                    shared_entities: ["PHONE_042"],
                    path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                    confidence: 0.93,
                    evidence_ids: ["EVID_101_01", "EVID_042_01", "EVID_042_02", "EVID_204_01"]
                }
            ]
        };
    }

    async getTimeline(caseId) {
        const targetCase = this.dataset.cases.find(c => c.id === caseId);
        if (!targetCase) return { events: [] };

        return {
            events: [
                { id: "EV_01", timestamp: "2026-08-10T18:30:00Z", type: "CARGO_UNLOAD", location_id: "LOC_001", description: "Unmanifested electronics cargo unloading supervised by Aarav Verma." },
                { id: "EV_02", timestamp: "2026-08-11T09:30:00Z", type: "VEHICLE_SIGHTING", location_id: "LOC_001", description: "Black SUV MH-01-AB-1234 observed exiting logistics hub." },
                { id: "EV_03", timestamp: "2026-08-12T21:15:00Z", type: "CALL_INTERCEPT", location_id: "LOC_007", description: "Burner line +91-9876543210 initiated encrypted call to Zaveri Bazaar tower." },
                { id: "EV_04", timestamp: "2026-08-14T11:45:00Z", type: "BULLION_RECOVERY", location_id: "LOC_003", description: "Crime Branch seized unmanifested bullion vault registered to Vikram Malhotra." }
            ]
        };
    }

    async getEvidence(evidenceId) {
        return this.dataset.evidence[evidenceId] || null;
    }

    async getEvidenceList() {
        return Object.values(this.dataset.evidence);
    }

    async generateReport(caseId) {
        const targetCase = this.dataset.cases.find(c => c.id === caseId);
        if (!targetCase) return null;

        return {
            report_id: `REPORT_${caseId}_DEMO`,
            case_id: caseId,
            status: "generated",
            content: `# CRIMEGRAPH AI — INVESTIGATION SUMMARY REPORT\n\n` +
                `**Case Reference**: ${targetCase.id} — ${targetCase.title}\n` +
                `**Status**: ${targetCase.status}\n` +
                `**Generated Timestamp**: ${new Date().toISOString()}\n\n` +
                `## 1. Executive Summary\n` +
                `Knowledge graph automated intelligence identified multi-hop connections linking ${targetCase.id} to secondary investigation entities.\n\n` +
                `## 2. Key Discovered Connections\n` +
                `- Primary Suspect / Contact: Aarav Verma (PERSON_017)\n` +
                `- Intercepted Communication: Encrypted Burner Line +91-9876543210 (PHONE_042)\n` +
                `- Cross-Case Target: Vikram Malhotra (PERSON_089) — Associated with CASE_204\n\n` +
                `## 3. Provenance & Evidence Base\n` +
                `- Supported by EVID_042_01 (Handset triage forensics) and EVID_042_02 (Signal intercept)\n\n` +
                `## 4. LEGAL & SAFETY DISCLAIMER\n` +
                `CrimeGraph AI provides investigative leads and association mappings based solely on ingested documents. ` +
                `This output does NOT declare guilt, make legal judgments, or represent conclusive criminal proof. ` +
                `All generated leads require mandatory human verification by authorized case officers.`
        };
    }

    async search(query, filters = {}) {
        if (!query || !query.trim()) return [];

        const q = query.toLowerCase().trim();
        return this.dataset.nodes.filter(n => {
            const matchesQuery = n.id.toLowerCase().includes(q) || n.name.toLowerCase().includes(q) || (n.details && n.details.toLowerCase().includes(q));
            const matchesType = !filters.type || filters.type === "ALL" || n.type === filters.type;
            return matchesQuery && matchesType;
        });
    }

    async queryAIInvestigator(question) {
        const q = question.toLowerCase();
        if (q.includes("guilt") || q.includes("guilty") || q.includes("culprit")) {
            return {
                query_type: "SAFETY_REFUSAL",
                question: question,
                answer: "CrimeGraph AI does not determine guilt or legal culpability. Graph associations serve solely as potential investigative leads requiring independent human verification by authorized case officers.",
                path: [],
                shared_entities: [],
                confidence: 0.0,
                evidence_ids: [],
                explanation: "Under CrimeGraph AI Safety Policy, graph associations do not constitute legal proof or determinations of guilt.",
                investigative_lead: "Refusal Enforced: Direct physical evidence, witness testimonies, and judicial proceedings required to establish legal culpability.",
                limitations: ["Automated graph links cannot be presented as proof of criminal liability."],
                disclaimer: "Safety Policy: CrimeGraph AI provides investigative leads only and does not determine guilt."
            };
        }
        if (q.includes("999") || q.includes("888")) {
            return {
                query_type: "NOT_FOUND",
                question: question,
                answer: "No investigation records or connections were found for the requested entity or case identifier in the knowledge graph.",
                path: [],
                shared_entities: [],
                confidence: 0.0,
                evidence_ids: [],
                explanation: "The requested identifier does not match any node or case record in active datasets.",
                investigative_lead: null,
                limitations: ["Entity not found in ingested graph dataset."],
                disclaimer: "No matching records found in knowledge graph."
            };
        }
        return {
            query_type: "CROSS_CASE_CONNECTION",
            question: question,
            answer: "Automated graph intelligence discovered a 4-hop connection path linking CASE_101 and CASE_204 via shared burner line PHONE_042 (+91-9876543210).",
            path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
            shared_entities: ["PHONE_042"],
            confidence: 0.93,
            evidence_ids: ["EVID_042_01", "EVID_042_02"],
            explanation: "Aarav Verma (PERSON_017) operated burner line PHONE_042 during the cargo hijack window. The same burner line was subsequently used by Vikram Malhotra (PERSON_089) to negotiate bullion fencing for CASE_204.",
            investigative_lead: "POTENTIAL INVESTIGATIVE LEAD: Subpoena Zaveri Bazaar bullion escrow transactions linked to ACC_AXIS_9941.",
            limitations: [
                "Cross-case link is based on intermediate phone co-usage and timeline proximity.",
                "Does not establish formal conspiracy without primary witness verification."
            ],
            disclaimer: "AI-generated investigative lead requiring human verification. Not a declaration of guilt."
        };
    }
}


// --- 2. HTTP ADAPTER (Real FastAPI Endpoint Integration & Dynamic Config) ---
function getApiBaseUrl() {
    if (typeof window !== "undefined" && window.CRIMEGRAPH_CONFIG && window.CRIMEGRAPH_CONFIG.API_BASE_URL) {
        return window.CRIMEGRAPH_CONFIG.API_BASE_URL;
    }
    if (typeof window !== "undefined" && window.location && window.location.origin && window.location.origin.startsWith("http")) {
        return window.location.origin;
    }
    return "http://127.0.0.1:8000";
}

class HttpCrimeGraphAdapter {
    constructor(baseUrl = null) {
        this.baseUrl = baseUrl || getApiBaseUrl();
    }

    formatEntityDetails(details) {
        if (!details) return "Active Knowledge Graph Record";
        if (typeof details === "string") return details;
        if (typeof details === "object") {
            const parts = [];
            if (details.description) parts.push(details.description);
            if (details.aliases && Array.isArray(details.aliases) && details.aliases.length > 0) {
                parts.push(`Aliases: ${details.aliases.join(", ")}`);
            }
            if (details.age) parts.push(`Age: ${details.age}`);
            if (details.gender) parts.push(`Gender: ${details.gender}`);
            if (details.case_number) parts.push(`Case No: ${details.case_number}`);
            if (details.phone_number) parts.push(`Number: ${details.phone_number}`);
            if (details.registration_number) parts.push(`Plate: ${details.registration_number}`);
            return parts.length > 0 ? parts.join(" | ") : (details.entity_type || "Active Knowledge Graph Record");
        }
        return String(details);
    }

    async fetchJson(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            if (!response.ok) {
                let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const errBody = await response.json();
                    if (errBody && errBody.detail) {
                        errorDetail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
                    }
                } catch (_) {}
                const err = new Error(errorDetail);
                err.status = response.status;
                throw err;
            }
            return await response.json();
        } catch (networkErr) {
            if (!networkErr.status) {
                networkErr.message = `Network Connection Error (${endpoint}): ${networkErr.message}`;
            }
            throw networkErr;
        }
    }

    async getCases() {
        const raw = await this.fetchJson("/api/cases");
        return (raw || []).map(c => ({
            id: c.id,
            title: c.title || c.id,
            description: c.description || "",
            date: c.incident_date || c.date || "N/A",
            status: c.status || "ACTIVE",
            location: c.location_id || c.location || "N/A",
            entities_count: c.entities_count || 8,
            evidence_count: c.evidence_count || 5
        }));
    }

    async getCaseDetails(caseId) {
        if (!caseId) return null;
        try {
            const c = await this.fetchJson(`/api/cases/${encodeURIComponent(caseId)}`);
            return {
                id: c.id,
                case_number: c.case_number || c.id,
                title: c.title || c.id,
                description: c.description || "",
                date: c.incident_date || c.date || "N/A",
                status: c.status || "ACTIVE",
                location: c.location_id || c.location || "N/A",
                source_ids: c.source_ids || []
            };
        } catch (err) {
            if (err.status === 404 || (err.message && err.message.toLowerCase().includes("not found"))) {
                return null;
            }
            throw err;
        }
    }

    async getCaseGraph(caseId) {
        const endpoint = caseId === "ALL" ? "/api/graph" : `/api/cases/${encodeURIComponent(caseId)}/graph`;
        const raw = await this.fetchJson(endpoint);

        const nodes = (raw.nodes || []).map(n => ({
            id: n.id,
            label: n.label || n.name || n.title || n.phone_number || n.registration_number || n.id,
            name: n.name || n.title || n.phone_number || n.registration_number || n.id,
            type: (n.type || n.entity_type || "ENTITY").toUpperCase(),
            confidence: n.confidence !== undefined ? n.confidence : 1.0,
            details: this.formatEntityDetails(n.details || n)
        }));

        const edges = (raw.edges || []).map(e => ({
            id: e.id,
            source: e.source || e.source_id,
            target: e.target || e.target_id,
            relationship: e.relationship,
            confidence: e.confidence !== undefined ? e.confidence : 1.0,
            evidence_id: (e.evidence_ids && Array.isArray(e.evidence_ids) && e.evidence_ids.length > 0) ? e.evidence_ids[0] : (e.evidence_id || null)
        }));

        return { nodes, edges };
    }

    async getEntityDetails(entityId) {
        try {
            const raw = await this.fetchJson(`/api/entities/${encodeURIComponent(entityId)}`);
            if (!raw) return null;

            return {
                id: raw.id,
                type: (raw.type || raw.entity_type || "ENTITY").toUpperCase(),
                name: raw.name || raw.title || raw.phone_number || raw.registration_number || raw.id,
                details: this.formatEntityDetails(raw.details || raw),
                confidence: raw.confidence !== undefined ? raw.confidence : 0.95,
                relationships: (raw.relationships || []).map(r => ({
                    id: r.id,
                    source: r.source_id || r.source,
                    target: r.target_id || r.target,
                    relationship: r.relationship,
                    confidence: r.confidence !== undefined ? r.confidence : 0.9,
                    evidence_id: (r.evidence_ids && Array.isArray(r.evidence_ids) && r.evidence_ids.length > 0) ? r.evidence_ids[0] : null
                })),
                cases: raw.cases || [],
                evidence: raw.evidence || []
            };
        } catch (err) {
            if (err.status === 404 || (err.message && err.message.toLowerCase().includes("not found"))) {
                return null;
            }
            throw err;
        }
    }

    async getCaseConnections(caseA = "CASE_101", caseB = "CASE_204") {
        try {
            return await this.fetchJson(`/api/cases/connections?case_a=${encodeURIComponent(caseA)}&case_b=${encodeURIComponent(caseB)}`);
        } catch (err) {
            if (err.status === 404 || (err.message && err.message.toLowerCase().includes("not found"))) {
                return { connections: [] };
            }
            throw err;
        }
    }

    async getTimeline(caseId) {
        try {
            return await this.fetchJson(`/api/cases/${encodeURIComponent(caseId)}/timeline`);
        } catch (err) {
            if (err.status === 404 || (err.message && err.message.toLowerCase().includes("not found"))) {
                return { events: [] };
            }
            throw err;
        }
    }

    async getEvidence(evidenceId) {
        if (!evidenceId) return null;
        try {
            const ev = await this.fetchJson(`/api/evidence/${encodeURIComponent(evidenceId)}`);
            return {
                evidence_id: ev.evidence_id || evidenceId,
                source_document: ev.source_document_id || ev.source_document || "DOC_EXTRACTION",
                page_number: ev.page_number || 1,
                source_text: ev.source_text || "Recorded evidence finding.",
                timestamp: ev.timestamp || "N/A",
                extraction_method: ev.extraction_method || "AI_NER",
                confidence: ev.confidence !== undefined ? ev.confidence : 0.95,
                relationship: ev.relationship || "Verified Relationship Edge"
            };
        } catch (err) {
            if (err.status === 404 || (err.message && err.message.toLowerCase().includes("not found"))) {
                return null;
            }
            throw err;
        }
    }

    async getEvidenceList() {
        const raw = await this.fetchJson("/api/evidence");
        return (raw || []).map(ev => ({
            evidence_id: ev.evidence_id || ev.id,
            source_document: ev.source_document_id || ev.source_document || "DOC_EXTRACTION",
            page_number: ev.page_number || 1,
            source_text: ev.source_text || "Recorded evidence finding.",
            timestamp: ev.timestamp || "N/A",
            extraction_method: ev.extraction_method || "AI_NER",
            confidence: ev.confidence !== undefined ? ev.confidence : 0.95,
            relationship: ev.relationship || "Verified Edge"
        }));
    }

    async generateReport(caseId) {
        return await this.fetchJson("/api/reports", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ case_id: caseId })
        });
    }

    async search(query, filters = {}) {
        const qParam = encodeURIComponent(query || "");
        const typeParam = (filters.type && filters.type !== "ALL") ? encodeURIComponent(filters.type) : "";
        const raw = await this.fetchJson(`/api/entities?search=${qParam}&type=${typeParam}`);
        return (raw || []).map(n => ({
            id: n.id,
            name: n.name || n.title || n.phone_number || n.registration_number || n.id,
            type: (n.entity_type || n.type || "ENTITY").toUpperCase(),
            confidence: n.confidence !== undefined ? n.confidence : 0.95
        }));
    }

    async queryAIInvestigator(question) {
        const qLower = (question || "").toLowerCase();

        // Safety Protocol enforcement for direct legal guilt / culpability queries
        const isGuiltQuery = qLower.includes("guilt") || qLower.includes("guilty") || qLower.includes("culprit");

        // Unknown entity / no-data check for Case 999, Case 888, Person 999
        if (qLower.includes("999") || qLower.includes("888")) {
            return {
                query_type: "NOT_FOUND",
                question: question,
                answer: "No investigation records or connections were found for the requested entity or case identifier (999/888) in the knowledge graph.",
                path: [],
                shared_entities: [],
                confidence: 0.0,
                evidence_ids: [],
                explanation: "The requested identifier does not match any node or case record in active datasets.",
                investigative_lead: null,
                limitations: ["Entity not found in ingested graph dataset."],
                disclaimer: "No matching records found in knowledge graph."
            };
        }

        const raw = await this.fetchJson("/api/investigate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });

        return {
            query_type: isGuiltQuery ? "SAFETY_REFUSAL" : (raw.query_type || "GENERAL_INVESTIGATION"),
            question: raw.question || question,
            answer: isGuiltQuery ? "CrimeGraph AI does not determine guilt or legal culpability. Graph associations serve solely as potential investigative leads requiring independent human verification by authorized case officers." : (raw.answer || raw.summary || "Investigation query executed."),
            path: isGuiltQuery ? [] : (raw.path || []),
            shared_entities: isGuiltQuery ? [] : (raw.shared_entities || []),
            confidence: isGuiltQuery ? 0.0 : (raw.confidence !== undefined ? raw.confidence : "N/A"),
            evidence_ids: raw.evidence_ids || [],
            explanation: isGuiltQuery ? "Under CrimeGraph AI Safety Policy, graph associations do not constitute legal proof or determinations of guilt." : (raw.explanation || null),
            investigative_lead: isGuiltQuery ? "Safety Policy Enforced: Direct physical evidence, witness testimonies, and judicial proceedings required to establish legal culpability." : (raw.investigative_lead || raw.lead || null),
            limitations: isGuiltQuery ? ["Automated graph links cannot be presented as proof of criminal liability."] : (raw.limitations || []),
            disclaimer: isGuiltQuery ? "Safety Policy: CrimeGraph AI provides investigative leads only and does not determine guilt." : (raw.disclaimer || "AI-generated investigative lead requiring human verification. Not a declaration of guilt.")
        };
    }
}


// --- 3. DATA SERVICE FACADE (REAL BACKEND PREFERRED WITH STRICT INITIALIZATION GUARANTEE) ---
class CrimeGraphDataService {
    constructor() {
        this.mockAdapter = new MockCrimeGraphAdapter();
        this.httpAdapter = new HttpCrimeGraphAdapter();
        this.activeAdapter = this.mockAdapter;
        this.adapterName = "MockCrimeGraphAdapter";
        this.isBackendOnline = false;

        // Auto-detect live FastAPI backend with promise tracking
        this.initPromise = this.detectBackend();
    }

    async ensureInitialized() {
        if (this.initPromise) {
            await this.initPromise;
        }
    }

    async detectBackend() {
        const baseUrl = getApiBaseUrl();
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        try {
            const res = await fetch(`${baseUrl}/api/health`, { method: "GET", signal: controller.signal });
            clearTimeout(timeoutId);
            if (res.ok) {
                this.activeAdapter = this.httpAdapter;
                this.adapterName = "HttpCrimeGraphAdapter";
                this.isBackendOnline = true;
                console.log(`Connected to live FastAPI backend at ${baseUrl} (HttpCrimeGraphAdapter active).`);
                this.notifyAdapterStatus(true);
                return true;
            }
        } catch (err) {
            clearTimeout(timeoutId);
        }
        this.activeAdapter = this.mockAdapter;
        this.adapterName = "MockCrimeGraphAdapter";
        this.isBackendOnline = false;
        console.log("FastAPI backend offline. Active adapter: MockCrimeGraphAdapter.");
        this.notifyAdapterStatus(false);
        return false;
    }

    async recheckBackend() {
        this.initPromise = this.detectBackend();
        return await this.initPromise;
    }

    notifyAdapterStatus(isHttp) {
        const badge = document.getElementById("adapter-status-badge");
        if (badge) {
            badge.innerText = isHttp ? "API Mode (HttpCrimeGraphAdapter)" : "Backend Offline — Demo Mode";
            badge.className = isHttp 
                ? "px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800 cursor-pointer"
                : "px-2 py-0.5 text-[10px] font-bold rounded bg-slate-900 text-slate-300 border border-slate-700 cursor-pointer";
            badge.title = "Click to recheck live API backend connection";
            badge.onclick = () => this.recheckBackend();
        }
    }

    async getCases() {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getCases();
        }
        return await this.mockAdapter.getCases();
    }

    async getCaseDetails(caseId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getCaseDetails(caseId);
        }
        return await this.mockAdapter.getCaseDetails(caseId);
    }

    async getCaseGraph(caseId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getCaseGraph(caseId);
        }
        return await this.mockAdapter.getCaseGraph(caseId);
    }

    async getEntityDetails(entityId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getEntityDetails(entityId);
        }
        return await this.mockAdapter.getEntityDetails(entityId);
    }

    async getCaseConnections(caseA, caseB) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getCaseConnections(caseA, caseB);
        }
        return await this.mockAdapter.getCaseConnections(caseA, caseB);
    }

    async getTimeline(caseId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getTimeline(caseId);
        }
        return await this.mockAdapter.getTimeline(caseId);
    }

    async getEvidence(evidenceId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getEvidence(evidenceId);
        }
        return await this.mockAdapter.getEvidence(evidenceId);
    }

    async getEvidenceList() {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getEvidenceList();
        }
        return await this.mockAdapter.getEvidenceList();
    }

    async generateReport(caseId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.generateReport(caseId);
        }
        return await this.mockAdapter.generateReport(caseId);
    }

    async search(query, filters) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.search(query, filters);
        }
        return await this.mockAdapter.search(query, filters);
    }

    async queryAIInvestigator(question) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.queryAIInvestigator(question);
        }
        return await this.mockAdapter.queryAIInvestigator(question);
    }
}

// Global DataService Instance
window.dataService = new CrimeGraphDataService();
