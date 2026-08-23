/**
 * CrimeGraph AI — Frontend Data Service & Adapter Layer (Day 3 Real API Integration)
 * Architected by Shruti for SIH 2026.
 *
 * Architecture:
 *   Google Stitch UI → CrimeGraphDataService → HttpCrimeGraphAdapter → FastAPI Backend (src/crimegraph/api/app.py)
 *   Development Fallback: CrimeGraphDataService → MockCrimeGraphAdapter
 *
 * Strictly adheres to DATA_SCHEMA.md and API_CONTRACT.md.
 */

// --- 1. MOCK ADAPTER (API-Compatible Fallback) ---
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

    async getCaseGraph(caseId) {
        if (caseId === "ALL") {
            return {
                nodes: this.dataset.nodes.map(n => ({ id: n.id, label: n.name, type: n.type, confidence: n.confidence })),
                edges: this.dataset.edges.map(e => ({ id: e.id, source: e.source, target: e.target, relationship: e.relationship, confidence: e.confidence, evidence_id: e.evidence_id }))
            };
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
        return {
            question: question,
            answer: "Automated graph intelligence discovered a 4-hop connection path linking CASE_101 and CASE_204 via shared burner line PHONE_042 (+91-9876543210).",
            path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
            confidence: "0.93 (High)",
            evidence: "Supported by EVID_042_01 (Phone extraction) and EVID_042_02 (Telco signal intercept).",
            explanation: "Aarav Verma (PERSON_017) operated burner line PHONE_042 during the cargo hijack window. The same burner line was subsequently used by Vikram Malhotra (PERSON_089) to negotiate bullion fencing for CASE_204.",
            lead: "Potential Investigative Lead: Subpoena Zaveri Bazaar bullion escrow transactions linked to ACC_AXIS_9941."
        };
    }
}


// --- 2. HTTP ADAPTER (Real FastAPI Endpoint Integration) ---
class HttpCrimeGraphAdapter {
    constructor(baseUrl = "http://localhost:8000") {
        this.baseUrl = baseUrl;
    }

    async fetchJson(endpoint, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, options);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }

    async getCases() {
        const raw = await this.fetchJson("/api/cases");
        return raw.map(c => ({
            id: c.id,
            title: c.title || c.id,
            date: c.incident_date || c.date || "2026-08-10",
            status: c.status || "ACTIVE",
            location: c.location_id || c.location || "LOC_001",
            entities_count: c.entities_count || 8,
            evidence_count: c.evidence_count || 5
        }));
    }

    async getCaseGraph(caseId) {
        const endpoint = caseId === "ALL" ? "/api/graph" : `/api/cases/${caseId}/graph`;
        const raw = await this.fetchJson(endpoint);

        const nodes = (raw.nodes || []).map(n => ({
            id: n.id,
            label: n.label || n.name || n.title || n.phone_number || n.registration_number || n.id,
            name: n.name || n.title || n.phone_number || n.registration_number || n.id,
            type: n.type || n.entity_type || "ENTITY",
            confidence: n.confidence !== undefined ? n.confidence : 1.0,
            details: n.description || n.type || "Graph Entity"
        }));

        const edges = (raw.edges || []).map(e => ({
            id: e.id,
            source: e.source || e.source_id,
            target: e.target || e.target_id,
            relationship: e.relationship,
            confidence: e.confidence !== undefined ? e.confidence : 1.0,
            evidence_id: (e.evidence_ids && e.evidence_ids.length > 0) ? e.evidence_ids[0] : (e.evidence_id || "EVID_001")
        }));

        return { nodes, edges };
    }

    async getEntityDetails(entityId) {
        const raw = await this.fetchJson(`/api/entities/${entityId}`);
        if (!raw) return null;

        return {
            id: raw.id,
            type: raw.type || raw.entity_type || "ENTITY",
            name: raw.name || raw.title || raw.phone_number || raw.registration_number || raw.id,
            details: (raw.details && raw.details.description) ? raw.details.description : (raw.entity_type || "Knowledge Graph Record"),
            confidence: raw.confidence !== undefined ? raw.confidence : 0.95,
            relationships: (raw.relationships || []).map(r => ({
                id: r.id,
                source: r.source_id || r.source,
                target: r.target_id || r.target,
                relationship: r.relationship,
                confidence: r.confidence !== undefined ? r.confidence : 0.9,
                evidence_id: (r.evidence_ids && r.evidence_ids.length > 0) ? r.evidence_ids[0] : "EVID_001"
            })),
            cases: raw.cases || [],
            evidence: raw.evidence || []
        };
    }

    async getCaseConnections(caseA = "CASE_101", caseB = "CASE_204") {
        return await this.fetchJson(`/api/cases/connections?case_a=${caseA}&case_b=${caseB}`);
    }

    async getTimeline(caseId) {
        return await this.fetchJson(`/api/cases/${caseId}/timeline`);
    }

    async getEvidence(evidenceId) {
        try {
            return await this.fetchJson(`/api/evidence/${evidenceId}`);
        } catch (err) {
            // Fallback lookup if single evidence endpoint unavailable
            const mock = new MockCrimeGraphAdapter();
            return await mock.getEvidence(evidenceId);
        }
    }

    async search(query, filters = {}) {
        try {
            const raw = await this.fetchJson(`/api/entities?type=${filters.type || ''}`);
            const q = (query || "").toLowerCase().trim();
            return raw.filter(n => (n.id && n.id.toLowerCase().includes(q)) || (n.name && n.name.toLowerCase().includes(q))).map(n => ({
                id: n.id,
                name: n.name || n.id,
                type: n.entity_type || "ENTITY",
                confidence: n.confidence || 0.95
            }));
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.search(query, filters);
        }
    }

    async queryAIInvestigator(question) {
        try {
            return await this.fetchJson("/api/investigate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.queryAIInvestigator(question);
        }
    }
}


// --- 3. DATA SERVICE FACADE (WITH AUTO FAILOVER) ---
class CrimeGraphDataService {
    constructor() {
        this.mockAdapter = new MockCrimeGraphAdapter();
        this.httpAdapter = new HttpCrimeGraphAdapter();
        this.activeAdapter = this.mockAdapter;
        this.adapterName = "MockCrimeGraphAdapter";
        this.isBackendOnline = false;

        // Auto-detect live FastAPI backend
        this.detectBackend();
    }

    async detectBackend() {
        try {
            const res = await fetch("http://127.0.0.1:8000/", { method: "GET" });
            if (res.ok) {
                this.activeAdapter = this.httpAdapter;
                this.adapterName = "HttpCrimeGraphAdapter";
                this.isBackendOnline = true;
                console.log("Connected to live FastAPI backend (HttpCrimeGraphAdapter active).");
                this.notifyAdapterStatus(true);
                return;
            }
        } catch (err) {
            // FastAPI backend offline
        }
        this.activeAdapter = this.mockAdapter;
        this.adapterName = "MockCrimeGraphAdapter";
        this.isBackendOnline = false;
        console.log("FastAPI backend offline. Active adapter: MockCrimeGraphAdapter.");
        this.notifyAdapterStatus(false);
    }

    notifyAdapterStatus(isHttp) {
        const badge = document.getElementById("adapter-status-badge");
        if (badge) {
            badge.innerText = isHttp ? "API Mode (HttpCrimeGraphAdapter)" : "Backend Offline — Demo Mode";
            badge.className = isHttp 
                ? "px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800"
                : "px-2 py-0.5 text-[10px] font-bold rounded bg-slate-900 text-slate-300 border border-slate-700";
        }
    }

    async getCases() {
        try {
            return await this.activeAdapter.getCases();
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getCases();
        }
    }

    async getCaseGraph(caseId) {
        try {
            return await this.activeAdapter.getCaseGraph(caseId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getCaseGraph(caseId);
        }
    }

    async getEntityDetails(entityId) {
        try {
            return await this.activeAdapter.getEntityDetails(entityId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getEntityDetails(entityId);
        }
    }

    async getCaseConnections(caseA, caseB) {
        try {
            return await this.activeAdapter.getCaseConnections(caseA, caseB);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getCaseConnections(caseA, caseB);
        }
    }

    async getTimeline(caseId) {
        try {
            return await this.activeAdapter.getTimeline(caseId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getTimeline(caseId);
        }
    }

    async getEvidence(evidenceId) {
        try {
            return await this.activeAdapter.getEvidence(evidenceId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getEvidence(evidenceId);
        }
    }

    async search(query, filters) {
        try {
            return await this.activeAdapter.search(query, filters);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.search(query, filters);
        }
    }

    async queryAIInvestigator(question) {
        try {
            return await this.activeAdapter.queryAIInvestigator(question);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.queryAIInvestigator(question);
        }
    }
}

// Global DataService Instance
window.dataService = new CrimeGraphDataService();
