/**
 * CrimeGraph AI — Frontend Data Service & Adapter Layer
 * Architected for SIH 2026.
 *
 * Supports both dataset-driven graph data and manual entity / relationship CRUD.
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
                { id: "CASE_101", name: "Operation Midnight Shadow", type: "CASE", confidence: 1.0, details: "Logistics Yard Cargo Hijack", origin: "DATASET" },
                { id: "CASE_204", name: "Operation Golden Falcon", type: "CASE", confidence: 1.0, details: "Zaveri Bazaar Fencing Syndicate", origin: "DATASET" },
                { id: "CASE_102", name: "Operation Silver Shield", type: "CASE", confidence: 1.0, details: "Cyber Financial Fraud Ring", origin: "DATASET" },
                { id: "CASE_305", name: "Operation Falcon Eye", type: "CASE", confidence: 1.0, details: "Cross-Border Hawala Network", origin: "DATASET" },

                { id: "PERSON_017", name: "Aarav Verma", type: "PERSON", confidence: 0.96, details: "Logistics Dispatch Supervisor", origin: "DATASET" },
                { id: "PERSON_089", name: "Vikram Malhotra", type: "PERSON", confidence: 0.94, details: "Bullion Receiver & Fencer", origin: "DATASET" },
                { id: "PERSON_044", name: "Devansh Mehta", type: "PERSON", confidence: 0.91, details: "Warehouse Gate Keeper", origin: "DATASET" },
                { id: "PERSON_056", name: "Karan Shah", type: "PERSON", confidence: 0.88, details: "Hawala Courier Operator", origin: "DATASET" },

                { id: "PHONE_042", name: "+91-9876543210", type: "PHONE", confidence: 0.95, details: "Encrypted Burner Line", origin: "DATASET" },
                { id: "PHONE_017", name: "+91-9820011223", type: "PHONE", confidence: 0.92, details: "Personal Cell", origin: "DATASET" },
                { id: "PHONE_089", name: "+91-9811099887", type: "PHONE", confidence: 0.90, details: "Shop Landline", origin: "DATASET" },

                { id: "VEHICLE_042", name: "MH-01-AB-1234", type: "VEHICLE", confidence: 0.94, details: "Black SUV", origin: "DATASET" },
                { id: "VEHICLE_017", name: "MH-04-XY-9999", type: "VEHICLE", confidence: 0.89, details: "Commercial Delivery Van", origin: "DATASET" },

                { id: "LOC_001", name: "Nhava Sheva Hub", type: "LOCATION", confidence: 1.0, details: "Logistics Transit Yard", origin: "DATASET" },
                { id: "LOC_003", name: "Zaveri Bazaar", type: "LOCATION", confidence: 1.0, details: "Bullion Trading Vault", origin: "DATASET" },
                { id: "LOC_007", name: "Tower 14 Relay", type: "LOCATION", confidence: 1.0, details: "Cellular Base Station", origin: "DATASET" },

                { id: "ACC_001", name: "ACC_AXIS_9941", type: "ACCOUNT", confidence: 0.93, details: "Escrow Bank Account", origin: "DATASET" }
            ],

            edges: [
                { id: "REL_101_017", source: "CASE_101", target: "PERSON_017", relationship: "INVOLVED_IN", confidence: 0.97, evidence_id: "EVID_101_01", origin: "DATASET" },
                { id: "REL_017_042", source: "PERSON_017", target: "PHONE_042", relationship: "USES", confidence: 0.95, evidence_id: "EVID_042_01", origin: "DATASET" },
                { id: "REL_042_089", source: "PHONE_042", target: "PERSON_089", relationship: "USES", confidence: 0.93, evidence_id: "EVID_042_02", origin: "DATASET" },
                { id: "REL_089_204", source: "PERSON_089", target: "CASE_204", relationship: "INVOLVED_IN", confidence: 0.96, evidence_id: "EVID_204_01", origin: "DATASET" },

                { id: "REL_017_V042", source: "PERSON_017", target: "VEHICLE_042", relationship: "USES", confidence: 0.94, evidence_id: "EVID_V042_01", origin: "DATASET" },
                { id: "REL_V042_L001", source: "VEHICLE_042", target: "LOC_001", relationship: "SEEN_AT", confidence: 0.92, evidence_id: "EVID_L001_01", origin: "DATASET" },
                { id: "REL_089_L003", source: "PERSON_089", target: "LOC_003", relationship: "VISITED", confidence: 0.95, evidence_id: "EVID_L003_01", origin: "DATASET" },
                { id: "REL_044_101", source: "PERSON_044", target: "CASE_101", relationship: "INVOLVED_IN", confidence: 0.89, evidence_id: "EVID_044_01", origin: "DATASET" },
                { id: "REL_056_305", source: "PERSON_056", target: "CASE_305", relationship: "INVOLVED_IN", confidence: 0.91, evidence_id: "EVID_056_01", origin: "DATASET" },
                { id: "REL_089_ACC", source: "PERSON_089", target: "ACC_001", relationship: "OWNED_BY", confidence: 0.93, evidence_id: "EVID_ACC_01", origin: "DATASET" }
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
                    source_document: "DOC_CASE_101_SURVEILLANCE_LOG.pdf",
                    page_number: 1,
                    source_text: "Field surveillance logged Aarav Verma operating black SUV MH-01-AB-1234 on transit corridor.",
                    timestamp: "2026-08-10T22:00:00Z",
                    extraction_method: "SURVEILLANCE",
                    confidence: 0.94,
                    relationship: "PERSON_017 --USES--> VEHICLE_042"
                },
                "EVID_L001_01": {
                    evidence_id: "EVID_L001_01",
                    source_document: "DOC_CASE_101_ANPR_LOGS.pdf",
                    page_number: 4,
                    source_text: "Automatic Number Plate Recognition camera registered MH-01-AB-1234 entering Nhava Sheva Hub terminal gates.",
                    timestamp: "2026-08-10T17:45:00Z",
                    extraction_method: "ANPR",
                    confidence: 0.92,
                    relationship: "VEHICLE_042 --SEEN_AT--> LOC_001"
                },
                "EVID_L003_01": {
                    evidence_id: "EVID_L003_01",
                    source_document: "DOC_CASE_204_CCTV_TIMELINE.pdf",
                    page_number: 8,
                    source_text: "Commercial CCTV surveillance captured Vikram Malhotra entering private bullion vault at Zaveri Bazaar.",
                    timestamp: "2026-08-13T16:20:00Z",
                    extraction_method: "CCTV_ANALYTICS",
                    confidence: 0.95,
                    relationship: "PERSON_089 --VISITED--> LOC_003"
                },
                "EVID_044_01": {
                    evidence_id: "EVID_044_01",
                    source_document: "DOC_CASE_101_SECURITY_LOG.pdf",
                    page_number: 3,
                    source_text: "Devansh Mehta signed security clearance gate log admitting unmanifested freight container.",
                    timestamp: "2026-08-10T18:00:00Z",
                    extraction_method: "DOCUMENT_OCR",
                    confidence: 0.89,
                    relationship: "PERSON_044 --INVOLVED_IN--> CASE_101"
                },
                "EVID_056_01": {
                    evidence_id: "EVID_056_01",
                    source_document: "DOC_CASE_305_HAWALA_LEDGER.pdf",
                    page_number: 5,
                    source_text: "Seized encrypted ledger cross-references Karan Shah with Hawala transaction batch #8841.",
                    timestamp: "2026-08-17T14:10:00Z",
                    extraction_method: "FINANCIAL_INTELLIGENCE",
                    confidence: 0.91,
                    relationship: "PERSON_056 --INVOLVED_IN--> CASE_305"
                },
                "EVID_ACC_01": {
                    evidence_id: "EVID_ACC_01",
                    source_document: "DOC_CASE_204_BANK_KYC.pdf",
                    page_number: 1,
                    source_text: "Axis Bank KYC mandate documents show Vikram Malhotra as beneficial owner of escrow account ACC_AXIS_9941.",
                    timestamp: "2026-08-14T10:00:00Z",
                    extraction_method: "BANK_RECORDS",
                    confidence: 0.93,
                    relationship: "PERSON_089 --OWNED_BY--> ACC_001"
                }
            }
        };
    }

    async createCase(caseData) {
        const id = caseData.id || `CASE_${Date.now().toString().slice(-3)}`;
        const title = caseData.title || `Operation Case ${id}`;
        const newCase = {
            id: id,
            title: title,
            date: caseData.incident_date || new Date().toISOString().split("T")[0],
            status: (caseData.status || "ACTIVE").toUpperCase(),
            location: caseData.location_id || "LOC_001",
            entities_count: 1,
            evidence_count: 1,
            description: caseData.description || "",
            origin: "MANUAL",
            ...caseData
        };
        this.dataset.cases.push(newCase);
        this.dataset.nodes.push({
            id: id,
            name: title,
            type: "CASE",
            confidence: 1.0,
            details: newCase.description,
            origin: "MANUAL"
        });
        return newCase;
    }

    async getCases() {
        return this.dataset.cases;
    }

    async getCaseGraph(caseId) {
        if (caseId === "ALL") {
            return {
                nodes: this.dataset.nodes.map(n => ({
                    id: n.id,
                    label: n.name,
                    name: n.name,
                    type: n.type,
                    confidence: n.confidence,
                    details: n.details,
                    origin: n.origin || "DATASET"
                })),
                edges: this.dataset.edges.map(e => ({
                    id: e.id,
                    source: e.source,
                    target: e.target,
                    relationship: e.relationship,
                    confidence: e.confidence,
                    evidence_id: e.evidence_id,
                    origin: e.origin || "DATASET"
                }))
            };
        }

        const primaryCaseNode = this.dataset.nodes.find(n => n.id === caseId);
        if (!primaryCaseNode) {
            return { nodes: [], edges: [] };
        }

        const directEdges = this.dataset.edges.filter(e => e.source === caseId || e.target === caseId);
        const directConnectedIds = new Set();
        directConnectedIds.add(caseId);

        directEdges.forEach(e => {
            directConnectedIds.add(e.source);
            directConnectedIds.add(e.target);
        });

        const extendedEdges = this.dataset.edges.filter(e => {
            const isSourceConnected = directConnectedIds.has(e.source) && !e.source.startsWith("CASE_");
            const isTargetConnected = directConnectedIds.has(e.target) && !e.target.startsWith("CASE_");
            return isSourceConnected || isTargetConnected;
        });

        const connectedIds = new Set(directConnectedIds);
        extendedEdges.forEach(e => {
            if (!e.source.startsWith("CASE_") || e.source === caseId) connectedIds.add(e.source);
            if (!e.target.startsWith("CASE_") || e.target === caseId) connectedIds.add(e.target);
        });

        const nodes = this.dataset.nodes.filter(n => connectedIds.has(n.id)).map(n => ({
            id: n.id,
            label: n.name,
            name: n.name,
            type: n.type,
            confidence: n.confidence,
            details: n.details,
            origin: n.origin || "DATASET"
        }));

        const edges = this.dataset.edges.filter(e => connectedIds.has(e.source) && connectedIds.has(e.target)).map(e => ({
            id: e.id,
            source: e.source,
            target: e.target,
            relationship: e.relationship,
            confidence: e.confidence,
            evidence_id: e.evidence_id,
            origin: e.origin || "DATASET"
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
            origin: ent.origin || "DATASET",
            relationships: rels,
            cases: Array.from(cases),
            evidence: evidenceItems
        };
    }

    async createEntity(entityData) {
        const type = (entityData.entity_type || entityData.type || "PERSON").toUpperCase();
        const id = entityData.id || `MANUAL_${type}_${Date.now().toString().slice(-4)}`;
        const name = entityData.name || entityData.title || entityData.phone_number || entityData.registration_number || id;
        
        const newNode = {
            id: id,
            name: name,
            type: type,
            confidence: entityData.confidence !== undefined ? parseFloat(entityData.confidence) : 1.0,
            details: entityData.details || entityData.description || "Manually Added Entity",
            origin: "MANUAL",
            ...entityData
        };
        this.dataset.nodes.push(newNode);
        return newNode;
    }

    async updateEntity(entityId, updateData) {
        const idx = this.dataset.nodes.findIndex(n => n.id === entityId);
        if (idx === -1) throw new Error(`Entity ${entityId} not found`);
        this.dataset.nodes[idx] = { ...this.dataset.nodes[idx], ...updateData };
        return this.dataset.nodes[idx];
    }

    async deleteEntity(entityId) {
        const ent = this.dataset.nodes.find(n => n.id === entityId);
        if (!ent) throw new Error(`Entity ${entityId} not found`);
        if (ent.origin === "DATASET") throw new Error("Protected dataset entity cannot be deleted.");
        this.dataset.nodes = this.dataset.nodes.filter(n => n.id !== entityId);
        this.dataset.edges = this.dataset.edges.filter(e => e.source !== entityId && e.target !== entityId);
        return { status: "deleted", id: entityId };
    }

    async createRelationship(relData) {
        const id = relData.id || `REL_MANUAL_${Date.now().toString().slice(-4)}`;
        const newEdge = {
            id: id,
            source: relData.source_id || relData.source,
            target: relData.target_id || relData.target,
            relationship: (relData.relationship || "ASSOCIATED_WITH").toUpperCase(),
            confidence: relData.confidence !== undefined ? parseFloat(relData.confidence) : 1.0,
            evidence_id: (relData.evidence_ids && relData.evidence_ids[0]) || null,
            origin: "MANUAL"
        };
        this.dataset.edges.push(newEdge);
        return newEdge;
    }

    async deleteRelationship(relId) {
        const edge = this.dataset.edges.find(e => e.id === relId);
        if (!edge) throw new Error(`Relationship ${relId} not found`);
        if (edge.origin === "DATASET") throw new Error("Protected dataset relationship cannot be deleted.");
        this.dataset.edges = this.dataset.edges.filter(e => e.id !== relId);
        return { status: "deleted", id: relId };
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

    async getEvidenceList() {
        return Object.values(this.dataset.evidence);
    }

    async generateReport(caseId) {
        const targetCase = this.dataset.cases.find(c => c.id === caseId) || { id: caseId, title: "Cargo Hijack Investigation", status: "ACTIVE" };
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

    async generateComprehensiveReport(options = {}) {
        const caseId = options.case_id || (options.case_ids && options.case_ids[0]) || "CASE_101";
        const basic = await this.generateReport(caseId);
        return {
            ...basic,
            report_id: `REPORT_COMP_${caseId}_DEMO`,
            case_ids: options.case_ids || [caseId],
            title: `Investigation Intelligence Report: ${caseId}`,
            investigation_question: options.question || "Cross-case network analysis",
            executive_summary: basic.content,
            entities: this.dataset.nodes.slice(0, 10),
            relationships: this.dataset.edges.slice(0, 10),
            evidence: Object.values(this.dataset.evidence).slice(0, 5),
            cross_case_connections: [
                {
                    path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                    shared_entities: ["PHONE_042"],
                    confidence: 0.93,
                    evidence_ids: ["EVID_042_01", "EVID_042_02", "EVID_101_01", "EVID_204_01"]
                }
            ],
            confidence: 0.93,
            confidence_tier: "HIGH",
            disclaimer: "CrimeGraph AI reports are algorithmic investigative intelligence summaries and do not establish legal guilt."
        };
    }

    async exportReport(reportId, format = "JSON") {
        return {
            report_id: reportId,
            format: format,
            exported_at: new Date().toISOString(),
            status: "exported"
        };
    }

    async evaluateResolution(payload) {
        return {
            entity_type: payload.entity_type || "PERSON",
            matches_count: 1,
            matches: [
                {
                    match_id: "MATCH_MOCK_01",
                    source_entity_id: "RECORD_NEW",
                    target_entity_id: "PERSON_017",
                    entity_type: "PERSON",
                    confidence_score: 0.95,
                    match_tier: "HIGH",
                    matched_attributes: ["name", "phone_number"],
                    explanation: "Exact primary name match corroborated by shared phone association: PHONE_042",
                    has_conflicts: false
                }
            ],
            disclaimer: "Identity resolution scores indicate algorithmic correlation and do not establish legal guilt."
        };
    }

    async getResolutionCandidates(entityId, minConfidence = 0.50) {
        return {
            entity_id: entityId,
            entity_type: "PERSON",
            matches_count: 1,
            candidates: [
                {
                    match_id: "MATCH_MOCK_02",
                    source_entity_id: entityId,
                    target_entity_id: "PERSON_017",
                    entity_type: "PERSON",
                    confidence_score: 0.92,
                    match_tier: "HIGH",
                    matched_attributes: ["aliases", "phone_ids"],
                    explanation: "Corroborated by shared known alias and device association.",
                    has_conflicts: false
                }
            ],
            disclaimer: "Identity resolution scores indicate algorithmic correlation and do not establish legal guilt."
        };
    }

    async mergeEntities(payload) {
        return {
            canonical_entity_id: payload.canonical_entity_id,
            merged_entity_id: payload.merge_entity_id,
            aliases_retained: ["Alias A", "Alias B"],
            relationships_migrated: 2,
            evidence_migrated: 1,
            provenance_records_retained: 2,
            status: "MERGED",
            explanation: `Successfully merged '${payload.merge_entity_id}' into canonical entity '${payload.canonical_entity_id}'.`
        };
    }

    async getIdentityConflicts(status = null) {
        return {
            conflicts_count: 0,
            conflicts: [],
            disclaimer: "Identity conflicts highlight contradictory source assertions requiring officer review."
        };
    }

    async getCommunities(params = {}) {
        return {
            total_communities: 1,
            total_clustered_entities: 4,
            communities: [
                {
                    community_id: "COMM_MOCK_01",
                    classification: "CROSS_CASE_COMMUNITY",
                    member_entity_ids: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                    member_count: 5,
                    density_score: 0.65,
                    group_risk_score: 0.85,
                    confidence: 0.93,
                    confidence_tier: "HIGH",
                    central_entity_ids: ["PERSON_017", "PHONE_042"],
                    bridge_entity_ids: ["PHONE_042"],
                    shared_infrastructure_ids: ["PHONE_042"],
                    linked_case_ids: ["CASE_101", "CASE_204"],
                    supporting_evidence_ids: ["EVID_042_01", "EVID_042_02"],
                    investigative_leads: ["Cross-case bridge coordination via shared communication device."],
                    disclaimer: "Community detection identifies algorithmic graph clustering and shared infrastructure. It does not establish legal guilt."
                }
            ],
            disclaimer: "CrimeGraph AI community detection identifies graph topological patterns. Human verification is required."
        };
    }

    async getCommunityDetail(communityId) {
        const comms = (await this.getCommunities()).communities;
        return comms.find(c => c.community_id === communityId) || comms[0];
    }

    async getCaseCommunities(caseId, minClusterSize = 2) {
        const summary = await this.getCommunities();
        summary.case_id = caseId;
        return summary;
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

    async getAuditLogs(params = {}) {
        return {
            total_count: 3,
            filtered_count: 3,
            events: [
                {
                    event_id: "AUDIT_MOCK_001",
                    timestamp: new Date().toISOString(),
                    actor_id: "analyst",
                    actor_type: "USER",
                    action: "AUTH_LOGIN_SUCCESS",
                    resource_type: "AUTH",
                    status: "SUCCESS",
                    details: { role: "ANALYST" }
                },
                {
                    event_id: "AUDIT_MOCK_002",
                    timestamp: new Date().toISOString(),
                    actor_id: "analyst",
                    actor_type: "USER",
                    action: "CASE_VIEW",
                    resource_type: "CASE",
                    resource_id: "CASE_101",
                    case_id: "CASE_101",
                    status: "SUCCESS"
                },
                {
                    event_id: "AUDIT_MOCK_003",
                    timestamp: new Date().toISOString(),
                    actor_id: "analyst",
                    actor_type: "AI",
                    action: "INVESTIGATION_QUERY",
                    resource_type: "INVESTIGATION",
                    status: "SUCCESS",
                    details: { query_type: "CROSS_CASE_PATH" }
                }
            ]
        };
    }

    async queryAIInvestigator(question) {
        const q = (question || "").toLowerCase();
        let answer = "";
        let path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"];

        if (q.includes("guilt") || q.includes("guilty")) {
            answer = `### Safety Protocol Refusal — Non-Guilt Guarantee\n\n` +
                `CrimeGraph AI strictly refrains from making legal declarations of guilt or criminal liability. ` +
                `The platform provides evidence-grounded entity associations and graph traversals solely to assist authorized human investigators.\n\n` +
                `**Associated Entities in CASE_101**:\n` +
                `- Aarav Verma (PERSON_017) — Logistics Dispatch Supervisor\n` +
                `- Devansh Mehta (PERSON_044) — Gate Keeper\n\n` +
                `*Safety Protocol: Output represents investigative association leads only and does not establish legal guilt. Mandatory human verification required.*`;
            return {
                query: question,
                answer: answer,
                query_type: "SAFETY_REFUSAL",
                path: [],
                entities: [
                    { id: "PERSON_017", name: "Aarav Verma", type: "PERSON" },
                    { id: "PERSON_044", name: "Devansh Mehta", type: "PERSON" }
                ],
                confidence: 0.0,
                confidence_tier: "LOW",
                evidence_ids: ["EVID_101_01"],
                is_safe: true,
                disclaimer: "Safety refusal enforced: AI outputs represent investigative associations only and do not establish guilt.",
                investigative_lead: "Corroborate witness accounts and forensic evidence through authorized judicial process."
            };
        }

        if ((q.includes("101") && q.includes("204")) || q.includes("aarav") || q.includes("vikram")) {
            answer = `### Automated Multi-Hop Graph Discovery\n\n` +
                `Graph traversal cross-referenced encrypted burner communication **PHONE_042** (+91-9876543210) recovered from **Aarav Verma** (PERSON_017) to bullion receiver **Vikram Malhotra** (PERSON_089) in **CASE_204** (Zaveri Bazaar Syndicate).\n\n` +
                `**Traversed Path**:\n` +
                `\`CASE_101 (Cargo Hijack)\` → \`PERSON_017 (Aarav Verma)\` → \`PHONE_042 (Burner)\` → \`PERSON_089 (Vikram Malhotra)\` → \`CASE_204 (Zaveri Bazaar)\`\n\n` +
                `**Supporting Evidence**:\n` +
                `- \`EVID_042_01\`: Digital triage of physical SIM recovered at Nhava Sheva.\n` +
                `- \`EVID_042_02\`: Encrypted signal tower telemetry to Zaveri Bazaar relay.\n\n` +
                `*Safety Protocol: Output represents investigative association leads only and does not establish legal guilt.*`;
        } else {
            answer = `### Investigation Analysis for: "${question}"\n\n` +
                `Knowledge graph indexed **34 entities**, **24 relationships**, and **19 evidence items** across active cases. ` +
                `Cross-referencing entities against FIR records and digital forensics highlights active syndicate operations between Nhava Sheva (CASE_101) and Zaveri Bazaar (CASE_204).\n\n` +
                `*Safety Protocol: Output represents investigative association leads only and does not establish legal guilt.*`;
        }

        return {
            query: question,
            answer: answer,
            path: path,
            entities: [
                { id: "PERSON_017", name: "Aarav Verma", type: "PERSON" },
                { id: "PHONE_042", name: "+91-9876543210", type: "PHONE" },
                { id: "PERSON_089", name: "Vikram Malhotra", type: "PERSON" }
            ],
            confidence: 0.95,
            confidence_tier: "HIGH",
            evidence_ids: ["EVID_042_01", "EVID_042_02"],
            investigative_lead: "Intercept burner communication indicates coordinated cargo routing to Zaveri Bazaar fencers."
        };
    }

    async getInfluencers(caseId, entityType = "ALL", limit = 10) {
        return {
            case_id: caseId || "CASE_101",
            entity_type_filter: entityType,
            total_entities_analyzed: 10,
            results_count: 2,
            results: [
                {
                    entity_id: "PERSON_017",
                    entity_name: "Aarav Verma",
                    entity_type: "PERSON",
                    rank: 1,
                    influence_score: 0.9219,
                    connected_cases: ["CASE_101", "CASE_102"],
                    metrics: { direct_connections: 9, degree_score: 0.9, betweenness_score: 1.0, cross_case_score: 0.7 },
                    reasons: ["Highly connected within network with 9 direct entity associations", "Pivotal communication bridge"]
                },
                {
                    entity_id: "PHONE_042",
                    entity_name: "+91-9876543210",
                    entity_type: "PHONE",
                    rank: 2,
                    influence_score: 0.5204,
                    connected_cases: ["CASE_101", "CASE_204"],
                    metrics: { direct_connections: 2, degree_score: 0.2, betweenness_score: 0.677, cross_case_score: 1.0 },
                    reasons: ["Pivotal communication bridge", "Acts as a cross-case linkage across 2 distinct cases"]
                }
            ]
        };
    }

    async getKeyPlayers(params = {}) {
        return {
            scope: params.case_id ? `CASE:${params.case_id}` : "GLOBAL",
            case_id: params.case_id || null,
            filter_role: params.role || null,
            filter_entity_type: params.entity_type || null,
            total_entities_analyzed: 10,
            key_players_count: 2,
            key_players: [
                {
                    rank: 1,
                    entity_id: "PERSON_017",
                    entity_name: "Aarav Verma",
                    entity_type: "PERSON",
                    score: 0.9219,
                    influence_role: "CROSS_CASE_INFLUENCER",
                    metrics: {
                        degree_score: 0.9,
                        betweenness_score: 1.0,
                        closeness_score: 0.8,
                        pagerank_score: 0.85,
                        cross_case_score: 0.7,
                        community_reach_score: 0.66,
                        bridge_score: 0.85,
                        direct_connections: 9,
                        raw_betweenness: 12.0,
                        case_count: 2,
                        community_reach_count: 2,
                        evidence_count: 2,
                        average_edge_confidence: 0.95
                    },
                    connected_case_ids: ["CASE_101", "CASE_204"],
                    connected_entity_count: 9,
                    bridge_count: 12,
                    supporting_evidence_ids: ["EVID_042_01"],
                    provenance: "DATASET",
                    explanation: "Aarav Verma is classified as a Cross Case Influencer across 2 cases.",
                    reasons: ["Highly connected within network with 9 direct entity associations"],
                    confidence: 0.95
                }
            ],
            safety_notice: "Network influence metrics quantify graph topology. They do NOT establish legal guilt."
        };
    }

    async analyzePaths(params = {}) {
        return {
            source_id: params.source_id || "CASE_101",
            target_id: params.target_id || "CASE_204",
            max_depth: params.max_depth || 5,
            total_paths_found: 1,
            paths: [
                {
                    path_id: "PATH_MOCK_01",
                    source_id: params.source_id || "CASE_101",
                    target_id: params.target_id || "CASE_204",
                    path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                    hop_count: 4,
                    path_score: 0.8125,
                    confidence: 0.94,
                    average_edge_confidence: 0.95,
                    evidence_ids: ["EVID_042_01", "EVID_101_01"],
                    provenance_sources: ["DATASET"],
                    steps: [],
                    shared_entities: ["PERSON_017", "PHONE_042", "PERSON_089"],
                    temporal_alignment: "CHRONOLOGICAL",
                    explanation: "Discovered 4-hop path connecting CASE_101 to CASE_204 via PHONE_042 burner line.",
                    scoring_factors: { hop_count_factor: 0.25, edge_confidence_avg: 0.95 }
                }
            ],
            safety_notice: "Path analysis quantifies topological connectivity. It does NOT establish legal guilt."
        };
    }

    async getPatterns(params = {}) {
        return {
            patterns: [
                {
                    pattern_id: "PAT_MOCK_01",
                    pattern_type: "SHARED_DEVICE_CROSS_CASE",
                    title: "Shared Cross-Case Device (PHONE_042)",
                    severity: "HIGH",
                    involved_entities: ["PERSON_017", "PERSON_089", "PHONE_042"],
                    involved_entity_ids: ["PERSON_017", "PERSON_089", "PHONE_042"],
                    involved_cases: ["CASE_101", "CASE_204"],
                    involved_case_ids: ["CASE_101", "CASE_204"],
                    explanation: "Device PHONE_042 is linked across CASE_101 and CASE_204.",
                    confidence: 0.95,
                    anomaly_score: 0.81,
                    investigative_lead: "Prioritize investigation of shared burner hardware.",
                    disclaimer: "Investigative pattern discovery only. Does not establish legal culpability or criminal intent."
                }
            ],
            total_count: 1,
            disclaimer: "Investigative pattern discovery only. Does not establish legal culpability."
        };
    }

    async detectPatterns(params = {}) {
        return await this.getPatterns(params);
    }

    async getDashboard(params = {}) {
        return {
            case_filter: params.case_id || null,
            summary: {
                total_cases: 2,
                active_cases: 2,
                high_priority_cases: 1,
                total_entities: 34,
                total_relationships: 24,
                total_evidence_count: 19,
                suspicious_patterns_count: 8,
                unresolved_leads_count: 10
            },
            cases: [
                {
                    case_id: "CASE_101",
                    title: "Operation Cyber Shield",
                    status: "ACTIVE",
                    priority: "HIGH",
                    location: "Jurisdiction Alpha",
                    risk_indicator: "CRITICAL",
                    entity_count: 12,
                    relationship_count: 15,
                    evidence_count: 10,
                    suspicious_pattern_count: 5,
                    last_activity: "2026-08-30T18:00:00Z"
                }
            ],
            key_entities: [
                {
                    entity_id: "PERSON_017",
                    name: "Aarav Verma",
                    entity_type: "PERSON",
                    investigation_score: 0.9219,
                    influence_role: "CORE_HUB",
                    connection_count: 5,
                    involved_cases: ["CASE_101", "CASE_204"],
                    supporting_evidence_ids: ["EVID_101_01"],
                    confidence: 0.95
                }
            ],
            suspicious_patterns: [],
            cross_case_connections: [],
            investigation_paths: [],
            recent_events: [],
            ai_insights: [],
            command_actions: [],
            safety_notice: "Dashboard metrics quantify graph topology. They do NOT establish legal guilt."
        };
    }

    async getCorrelations(params = {}) {
        return {
            correlations: [
                {
                    correlation_id: "CORR_MOCK_01",
                    correlation_type: "ENTITY_CORRELATION",
                    title: "Multi-Source Entity Correlation (Aarav Verma)",
                    severity: "HIGH",
                    confidence: 0.95,
                    correlation_score: 0.88,
                    primary_entity_id: "PERSON_017",
                    involved_entities: ["PERSON_017"],
                    involved_entity_ids: ["PERSON_017"],
                    involved_cases: ["CASE_101", "CASE_204"],
                    involved_case_ids: ["CASE_101", "CASE_204"],
                    supporting_evidence: ["EVID_101_01", "EVID_042_01"],
                    evidence_ids: ["EVID_101_01", "EVID_042_01"],
                    explanation: "Entity Aarav Verma is corroborated across independent datasets and evidence files.",
                    investigative_lead: "Cross-verify records for Aarav Verma across independent systems.",
                    provenance_sources: ["DATASET", "EVIDENCE"],
                    disclaimer: "Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap."
                }
            ],
            total_count: 1,
            disclaimer: "Investigative correlation lead only. Does not establish legal guilt."
        };
    }

    async analyzeCorrelations(params = {}) {
        return await this.getCorrelations(params);
    }

    async getRiskScore(entityId) {
        return {
            entity_id: entityId || "PERSON_017",
            entity_name: "Aarav Verma",
            entity_type: "PERSON",
            risk_score: 78.5,
            risk_level: "HIGH",
            confidence: 0.95,
            features: {
                entity_id: entityId || "PERSON_017",
                entity_type: "PERSON",
                degree: 8,
                weighted_degree: 7.6,
                case_count: 2,
                community_count: 1,
                cross_case_count: 2,
                centrality_score: 0.92,
                anomaly_score: 0.85,
                pattern_count: 3,
                correlation_score: 0.77,
                cross_source_count: 3,
                evidence_count: 5
            },
            signals: [
                {
                    signal_type: "CROSS_CASE_HUB",
                    description: "Entity bridges 2 independent investigation cases.",
                    weight: 0.25,
                    score_contribution: 25.0,
                    evidence_ids: ["CASE_101", "CASE_204"]
                }
            ],
            involved_cases: ["CASE_101", "CASE_204"],
            evidence_ids: ["EVID_101_01"],
            source_records: ["DATASET"],
            explanation: "Entity Aarav Verma has a HIGH investigative priority score of 78.5/100.",
            investigative_lead: "Prioritize investigative verification for Aarav Verma.",
            disclaimer: "Investigative priority score quantifies graph topology. It does NOT indicate legal guilt."
        };
    }

    async getCaseRiskScore(caseId) {
        return {
            case_id: caseId || "CASE_101",
            case_title: "Financial Scam Investigation",
            risk_score: 82.0,
            risk_level: "HIGH",
            confidence: 0.95,
            total_entities: 9,
            high_risk_entity_count: 2,
            cross_case_link_count: 2,
            pattern_count: 3,
            correlation_count: 2,
            top_risk_entities: [],
            signals: [],
            explanation: "Case CASE_101 has an Investigation Risk Score of 82.0/100.",
            investigative_lead: "Focus analytical resource allocation on top risk entities in CASE_101.",
            disclaimer: "Investigative priority score quantifies graph topology. It does NOT indicate legal guilt."
        };
    }

    async getInvestigationPriorities(params = {}) {
        return {
            case_filter: params.case_id || null,
            min_score: params.min_score || 0.0,
            total_count: 1,
            priorities: [
                {
                    rank: 1,
                    entity_id: "PERSON_017",
                    entity_name: "Aarav Verma",
                    entity_type: "PERSON",
                    risk_score: 78.5,
                    risk_level: "HIGH",
                    primary_signal_type: "CROSS_CASE_HUB",
                    involved_cases: ["CASE_101", "CASE_204"],
                    evidence_ids: ["EVID_101_01"],
                    explanation: "Entity Aarav Verma has a HIGH investigative priority score of 78.5/100.",
                    investigative_lead: "Prioritize investigative verification for Aarav Verma."
                }
            ],
            disclaimer: "Investigative priority score quantifies graph topology. It does NOT indicate legal guilt."
        };
    }

    async analyzeRisk(params = {}) {
        return await this.getInvestigationPriorities(params);
    }

    async getNetworkIntelligence(caseId) {
        return {
            case_id: caseId || "CASE_101",
            network_summary: {
                total_nodes: 9,
                total_edges: 10,
                bridge_entities_count: 1,
                cross_case_connectors_count: 2,
                high_influence_entities_count: 1
            },
            key_individuals: [
                { entity_id: "PERSON_017", entity_name: "Aarav Verma", rank: 1, influence_score: 0.9219 }
            ],
            top_influencers: [
                { entity_id: "PERSON_017", rank: 1, influence_score: 0.9219 },
                { entity_id: "PHONE_042", rank: 2, influence_score: 0.5204 }
            ],
            bridge_entities: [
                { entity_id: "PERSON_017", entity_name: "Aarav Verma", influence_score: 0.9219 }
            ],
            cross_case_connectors: [
                { entity_id: "PERSON_017", entity_name: "Aarav Verma", influence_score: 0.9219 },
                { entity_id: "PHONE_042", entity_name: "+91-9876543210", influence_score: 0.5204 }
            ],
            safety_notice: "Network influence metrics indicate structural connectivity and do not establish legal guilt."
        };
    }

    async getPatterns(params = {}) {
        return {
            patterns: [
                {
                    pattern_id: "PAT_DEV_PHONE_042",
                    pattern_type: "SHARED_DEVICE_CROSS_CASE",
                    title: "Shared Cross-Case Device (+91-9876543210)",
                    severity: "HIGH",
                    involved_entities: ["PERSON_017", "PERSON_089", "PHONE_042"],
                    involved_cases: ["CASE_101", "CASE_102", "CASE_204"],
                    relationships: [
                        { relationship_id: "REL_002", source: "PERSON_017", target: "PHONE_042", relationship: "USES", confidence: 0.95 },
                        { relationship_id: "REL_003", source: "PERSON_089", target: "PHONE_042", relationship: "USES", confidence: 0.95 }
                    ],
                    supporting_evidence: ["EVID_042_01", "EVID_042_02"],
                    explanation: "Device '+91-9876543210' (PHONE_042 | PHONE) is linked to multiple individuals [Aarav Verma (PERSON_017), Vikram Malhotra (PERSON_089)] across distinct cases [CASE_101, CASE_102, CASE_204].",
                    confidence: 0.95,
                    confidence_tier: "HIGH",
                    investigative_significance: "Indicates potential operational overlap or burner line sharing between separate syndicates.",
                    limitations: "Device sharing may indicate relay infrastructure or co-location rather than direct conspiracy.",
                    disclaimer: "CrimeGraph AI suspicious patterns are algorithmic investigative leads only and do not establish legal guilt."
                },
                {
                    pattern_id: "PAT_BRIDGE_CASE_101_CASE_204_1",
                    pattern_type: "CROSS_CASE_BRIDGE_PATH",
                    title: "Cross-Case Bridge (CASE_101 -> CASE_204)",
                    severity: "HIGH",
                    involved_entities: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                    involved_cases: ["CASE_101", "CASE_204"],
                    relationships: [
                        { relationship_id: "REL_101_017", source: "CASE_101", target: "PERSON_017", relationship: "INVOLVED_IN", confidence: 0.97 },
                        { relationship_id: "REL_017_042", source: "PERSON_017", target: "PHONE_042", relationship: "USES", confidence: 0.95 },
                        { relationship_id: "REL_042_089", source: "PHONE_042", target: "PERSON_089", relationship: "USES", confidence: 0.93 },
                        { relationship_id: "REL_089_204", source: "PERSON_089", target: "CASE_204", relationship: "INVOLVED_IN", confidence: 0.96 }
                    ],
                    supporting_evidence: ["EVID_101_01", "EVID_042_01", "EVID_042_02", "EVID_204_01"],
                    explanation: "Identified multi-hop bridge path connecting CASE_101 to CASE_204 via intermediaries: CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204.",
                    confidence: 0.93,
                    confidence_tier: "HIGH",
                    investigative_significance: "Reveals cross-case connectivity between separate criminal investigations.",
                    limitations: "Path indicates structural graph connection. Corroborating temporal evidence required.",
                    disclaimer: "CrimeGraph AI suspicious patterns are algorithmic investigative leads only and do not establish legal guilt."
                }
            ],
            total_count: 2,
            limit: 50,
            disclaimer: "CrimeGraph AI suspicious patterns are algorithmic investigative leads only and do not establish legal guilt."
        };
    }

    async getCasePatterns(caseId, params = {}) {
        const all = await this.getPatterns(params);
        const filtered = all.patterns.filter(p => p.involved_cases.includes(caseId));
        return {
            case_id: caseId,
            patterns: filtered,
            total_count: filtered.length,
            disclaimer: "CrimeGraph AI suspicious patterns are algorithmic investigative leads only and do not establish legal guilt."
        };
    }

    async getSources() {
        return {
            sources: [
                { source_id: "SRC_SYNTHETIC_DATASET", source_type: "SYNTHETIC_DATASET", source_name: "Core SIH 2026 Synthetic Dataset", confidence: 1.0, is_active: true, entity_count: 34, relationship_count: 24, evidence_count: 19 },
                { source_id: "SRC_MANUAL_ENTRY", source_type: "MANUAL_ENTRY", source_name: "Investigator Manual Entry", confidence: 0.95, is_active: true, entity_count: 2, relationship_count: 1, evidence_count: 1 }
            ],
            total_count: 2
        };
    }

    async getSourceDetail(sourceId) {
        return {
            source: {
                source_id: sourceId,
                source_type: "SYNTHETIC_DATASET",
                source_name: "Core SIH 2026 Synthetic Dataset",
                confidence: 1.0,
                is_active: true
            },
            entity_count: 34,
            relationship_count: 24,
            evidence_count: 19,
            entities: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        };
    }

    async getEntitySources(entityId) {
        return {
            entity_id: entityId,
            provenance: [
                { provenance_id: `PROV_${entityId}_SYN`, source_id: "SRC_SYNTHETIC_DATASET", source_type: "SYNTHETIC_DATASET", source_name: "Synthetic Investigation Dataset", confidence: 1.0 }
            ],
            total_sources: 1,
            conflicts: []
        };
    }

    async getRelationshipSources(relationshipId) {
        return {
            relationship_id: relationshipId,
            provenance: [
                { provenance_id: `PROV_${relationshipId}_SYN`, source_id: "SRC_SYNTHETIC_DATASET", source_type: "SYNTHETIC_DATASET", source_name: "Synthetic Investigation Dataset", confidence: 0.95 }
            ],
            total_sources: 1
        };
    }

    async getSourceConflicts(params = {}) {
        return {
            conflicts: [],
            total_count: 0
        };
    }

    async getPathProvenance(nodes = []) {
        return {
            path: nodes,
            total_steps: Math.max(0, nodes.length - 1),
            steps: []
        };
    }

    async extractIntelligence(text, sourceDocumentId = "DOC_MOCK_EXTRACTION", caseId = null) {
        return {
            source_document_id: sourceDocumentId,
            case_id: caseId,
            entities: [
                {
                    id: "PERSON_017",
                    entity_type: "PERSON",
                    raw_value: "Vikram Malhotra",
                    canonical_value: "Vikram Malhotra",
                    confidence_tier: "MEDIUM",
                    confidence: 0.75,
                    extraction_method: "PATTERN_NAME",
                    resolved_id: "PERSON_017",
                    is_new: false
                },
                {
                    id: "PHONE_042",
                    entity_type: "PHONE",
                    raw_value: "+91-9876543210",
                    canonical_value: "+91-9876543210",
                    confidence_tier: "HIGH",
                    confidence: 0.92,
                    extraction_method: "REGEX_PHONE",
                    resolved_id: "PHONE_042",
                    is_new: false
                }
            ],
            relationships: [
                {
                    id: "REL_EXT_MOCK_1",
                    source_entity_id: "PERSON_017",
                    target_entity_id: "PHONE_042",
                    relationship_type: "USES",
                    confidence_tier: "MEDIUM",
                    confidence: 0.75,
                    extraction_method: "PATTERN_RELATIONSHIP",
                    supporting_text: text
                }
            ],
            events: [],
            evidence: [
                {
                    evidence_id: "EVID_EXT_MOCK_1",
                    source_document_id: sourceDocumentId,
                    source_text: text,
                    page_number: 1,
                    extraction_method: "NLP_PIPELINE",
                    confidence: 0.85
                }
            ],
            provenance: [
                {
                    provenance_id: "XPROV_MOCK_1",
                    source_document_id: sourceDocumentId,
                    source_type: "NLP_EXTRACT",
                    source_name: "NLP Extraction Pipeline",
                    extraction_method: "REGEX_PHONE",
                    confidence_tier: "HIGH",
                    confidence: 0.92,
                    source_snippet: text,
                    entity_id: "PHONE_042"
                }
            ],
            conflicts: [],
            graph_integration: {
                nlp_source_id: `SRC_NLP_${sourceDocumentId}`,
                entities_added: 0,
                entities_matched: 2,
                relationships_added: 1
            },
            extraction_status: "SUCCESS",
            disclaimer: "CrimeGraph AI NLP extraction produces investigative leads only. Extracted entities and relationships are NOT proof of criminal guilt."
        };
    }
}


// --- 2. HTTP ADAPTER (Real FastAPI Endpoint Integration) ---
class HttpCrimeGraphAdapter {
    constructor(baseUrl) {
        this.baseUrl = (baseUrl || this.resolveBaseUrl()).replace(/\/$/, "");
        this.token = this.getStoredToken();
    }

    getStoredToken() {
        if (typeof window !== "undefined") {
            try {
                return sessionStorage.getItem("CRIMEGRAPH_AUTH_TOKEN") || localStorage.getItem("CRIMEGRAPH_AUTH_TOKEN");
            } catch (_) {}
        }
        return null;
    }

    setToken(token) {
        this.token = token;
        if (typeof window !== "undefined") {
            try {
                if (token) {
                    sessionStorage.setItem("CRIMEGRAPH_AUTH_TOKEN", token);
                    localStorage.setItem("CRIMEGRAPH_AUTH_TOKEN", token);
                } else {
                    sessionStorage.removeItem("CRIMEGRAPH_AUTH_TOKEN");
                    localStorage.removeItem("CRIMEGRAPH_AUTH_TOKEN");
                }
            } catch (_) {}
        }
    }

    async login(username, password) {
        const res = await this.fetchJson("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        if (res && res.access_token) {
            this.setToken(res.access_token);
        }
        return res;
    }

    async getMe() {
        return await this.fetchJson("/api/auth/me");
    }

    logout() {
        this.setToken(null);
    }

    resolveBaseUrl() {
        if (typeof window !== "undefined") {
            if (window.CRIMEGRAPH_API_URL) return window.CRIMEGRAPH_API_URL;
            try {
                const stored = localStorage.getItem("CRIMEGRAPH_API_URL");
                if (stored) return stored;
            } catch (_) {}
            if (window.location && window.location.search) {
                const params = new URLSearchParams(window.location.search);
                const queryApi = params.get("api") || params.get("apiUrl");
                if (queryApi) return queryApi;
            }
            if (window.location && window.location.hostname && (window.location.hostname.includes("netlify.app") || (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" && window.location.hostname !== ""))) {
                return "https://crimegraph-api.onrender.com";
            }
        }
        return "http://localhost:8000";
    }

    async fetchJson(endpoint, options = {}) {
        const headers = { ...(options.headers || {}) };
        if (this.token && !headers["Authorization"]) {
            headers["Authorization"] = `Bearer ${this.token}`;
        }
        const fetchOptions = { ...options, headers };

        const response = await fetch(`${this.baseUrl}${endpoint}`, fetchOptions);
        if (!response.ok) {
            let errMsg = `HTTP ${response.status}: ${response.statusText}`;
            let retryAfter = response.headers.get("Retry-After");
            try {
                const errData = await response.json();
                if (errData.detail) errMsg = errData.detail;
                if (errData.retry_after) retryAfter = errData.retry_after;
            } catch (_) {}
            const error = new Error(errMsg);
            error.status = response.status;
            if (retryAfter) error.retryAfter = parseInt(retryAfter, 10) || retryAfter;
            throw error;
        }
        return await response.json();
    }

    async createCase(caseData) {
        return await this.fetchJson("/api/cases", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(caseData)
        });
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
            details: n.description || n.type || "Graph Entity",
            origin: n.origin || "DATASET"
        }));

        const edges = (raw.edges || []).map(e => ({
            id: e.id,
            source: e.source || e.source_id,
            target: e.target || e.target_id,
            relationship: e.relationship,
            confidence: e.confidence !== undefined ? e.confidence : 1.0,
            evidence_id: (e.evidence_ids && e.evidence_ids.length > 0) ? e.evidence_ids[0] : (e.evidence_id || "EVID_001"),
            origin: e.origin || "DATASET"
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
            origin: (raw.details && raw.details.origin) || raw.origin || "DATASET",
            relationships: (raw.relationships || []).map(r => ({
                id: r.id,
                source: r.source_id || r.source,
                target: r.target_id || r.target,
                relationship: r.relationship,
                confidence: r.confidence !== undefined ? r.confidence : 0.9,
                evidence_id: (r.evidence_ids && r.evidence_ids.length > 0) ? r.evidence_ids[0] : "EVID_001",
                origin: r.origin || "DATASET"
            })),
            cases: raw.cases || [],
            evidence: raw.evidence || []
        };
    }

    async createEntity(entityData) {
        return await this.fetchJson("/api/entities", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(entityData)
        });
    }

    async updateEntity(entityId, updateData) {
        return await this.fetchJson(`/api/entities/${entityId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updateData)
        });
    }

    async deleteEntity(entityId) {
        return await this.fetchJson(`/api/entities/${entityId}`, {
            method: "DELETE"
        });
    }

    async createRelationship(relData) {
        return await this.fetchJson("/api/relationships", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(relData)
        });
    }

    async deleteRelationship(relId) {
        return await this.fetchJson(`/api/relationships/${relId}`, {
            method: "DELETE"
        });
    }

    async getInvestigationDashboard() {
        try {
            return await this.fetchJson("/api/dashboard");
        } catch (err) {
            const mockAdapter = new MockCrimeGraphAdapter();
            return await mockAdapter.getInvestigationDashboard();
        }
    }

    async getKeyPlayers(params = {}) {
        try {
            return await this.fetchJson("/api/key-players");
        } catch (err) {
            const mockAdapter = new MockCrimeGraphAdapter();
            return await mockAdapter.getKeyPlayers(params);
        }
    }

    async findPaths(sourceId, targetId, maxDepth = 6, params = {}) {
        if (!sourceId || !targetId) {
            return { source_id: sourceId, target_id: targetId, path_count: 0, paths: [] };
        }
        const query = new URLSearchParams({
            source_id: sourceId,
            target_id: targetId,
            max_depth: maxDepth
        });
        if (params.directed !== undefined && params.directed !== null) {
            query.append("directed", params.directed);
        }

        try {
            const data = await this.fetchJson(`/api/paths?${query.toString()}`);
            if (data && Array.isArray(data.paths)) {
                return data;
            }
        } catch (e) {
            console.warn("API /api/paths query failed, attempting cross-case connections fallback", e);
        }

        if (sourceId.toUpperCase().startsWith("CASE_") && targetId.toUpperCase().startsWith("CASE_")) {
            try {
                const connData = await this.fetchJson(`/api/cases/connections?case_a=${encodeURIComponent(sourceId)}&case_b=${encodeURIComponent(targetId)}`);
                if (connData && Array.isArray(connData.connections) && connData.connections.length > 0) {
                    return {
                        source_id: sourceId,
                        target_id: targetId,
                        path_count: connData.connections.length,
                        paths: connData.connections.map(c => ({
                            source_id: sourceId,
                            target_id: targetId,
                            path: c.path,
                            shared_entities: c.shared_entities,
                            confidence: c.confidence,
                            evidence_ids: c.evidence_ids || [],
                            steps: (c.path || []).slice(0, -1).map((node, idx) => ({
                                from: node,
                                to: c.path[idx + 1],
                                relationship: "CONNECTED_TO",
                                confidence: c.confidence,
                                evidence_ids: c.evidence_ids || []
                            })),
                            hop_count: Math.max(1, (c.path || []).length - 1),
                            path_score: c.confidence
                        }))
                    };
                }
            } catch (err) {
                console.warn("Fallback /api/cases/connections failed", err);
            }
        }

        return { source_id: sourceId, target_id: targetId, path_count: 0, paths: [] };
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
            entities_count: c.entities_count !== undefined ? c.entities_count : 8,
            entity_count: c.entities_count !== undefined ? c.entities_count : 8,
            evidence_count: c.evidence_count !== undefined ? c.evidence_count : 5
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

        const nodes = (raw.nodes || []).map(n => {
            const detailsObj = (typeof n.details === "object" && n.details) ? n.details : n;
            const phoneNo = detailsObj.phone_number || n.phone_number;
            const regNo = detailsObj.registration_number || n.registration_number;
            const titleOrName = (phoneNo ? `${phoneNo}` : (regNo ? `${regNo}` : (n.name || n.title || n.label || n.id)));
            return {
                id: n.id,
                label: titleOrName,
                name: titleOrName,
                type: (n.type || n.entity_type || "ENTITY").toUpperCase(),
                confidence: n.confidence !== undefined ? n.confidence : 1.0,
                details: this.formatEntityDetails(n.details || n),
                source: n.source || (n.is_manual ? "Manual" : "Dataset"),
                is_manual: n.is_manual || n.source === "Manual"
            };
        });

        const edges = (raw.edges || []).map(e => ({
            id: e.id,
            source: e.source || e.source_id,
            target: e.target || e.target_id,
            relationship: e.relationship,
            confidence: e.confidence !== undefined ? e.confidence : 1.0,
            evidence_id: (e.evidence_ids && Array.isArray(e.evidence_ids) && e.evidence_ids.length > 0) ? e.evidence_ids[0] : (e.evidence_id || null),
            source_type: e.source_type || (e.is_manual ? "Manual" : "Dataset"),
            is_manual: e.is_manual || e.source_type === "Manual"
        }));

        return { nodes, edges };
    }

    async getEntityDetails(entityId) {
        try {
            const raw = await this.fetchJson(`/api/entities/${encodeURIComponent(entityId)}`);
            if (!raw) return null;

            const detailsObj = (typeof raw.details === "object" && raw.details) ? raw.details : raw;
            const phoneNo = detailsObj.phone_number || raw.phone_number;
            const regNo = detailsObj.registration_number || raw.registration_number;
            let displayName = raw.name || raw.title || raw.id;
            if (phoneNo && (displayName === raw.id || raw.type === "PHONE")) {
                displayName = phoneNo;
            } else if (regNo && (displayName === raw.id || raw.type === "VEHICLE")) {
                displayName = regNo;
            }

            return {
                id: raw.id,
                type: (raw.type || raw.entity_type || "ENTITY").toUpperCase(),
                name: displayName,
                details: this.formatEntityDetails(raw.details || raw),
                confidence: raw.confidence !== undefined ? raw.confidence : 0.95,
                source: raw.source || (raw.is_manual ? "Manual" : "Dataset"),
                is_manual: raw.is_manual || raw.source === "Manual",
                raw_data: raw.details || raw,
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
            const targetCase = caseId || "CASE_101";
            const raw = await this.fetchJson(`/api/cases/${encodeURIComponent(targetCase)}/timeline`);
            const rawEvents = raw.events || (Array.isArray(raw) ? raw : []);
            const events = rawEvents.map(e => ({
                ...e,
                case_id: e.case_id || targetCase,
                event_type: e.event_type || e.type || "EVENT",
                type: e.type || e.event_type || "EVENT",
                title: e.title || `${e.event_type || e.type || 'Event'} (${e.id})`,
                location_name: e.location_name || e.location_id || "N/A"
            }));
            return { events };
        } catch (err) {
            if (err.status === 404 || (err.message && err.message.toLowerCase().includes("not found"))) {
                return { events: [] };
            }
            throw err;
        }
    }

    async getEvidence(evidenceId) {
        try {
            const ev = await this.fetchJson(`/api/evidence/${evidenceId}`);
            return {
                evidence_id: ev.evidence_id || evidenceId,
                source_document: ev.source_document_id || ev.source_document || "DOC_EXTRACTION",
                page_number: ev.page_number || 1,
                source_text: ev.source_text || "Recorded evidence finding.",
                timestamp: ev.timestamp || "2026-08-11T09:30:00Z",
                extraction_method: ev.extraction_method || "AI_NER",
                confidence: ev.confidence !== undefined ? ev.confidence : 0.95,
                relationship: ev.relationship || "Verified Relationship Edge"
            };
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getEvidence(evidenceId);
        }
    }

    async getEvidenceList() {
        try {
            const raw = await this.fetchJson("/api/evidence");
            return raw.map(ev => ({
                evidence_id: ev.evidence_id || ev.id,
                source_document: ev.source_document_id || ev.source_document || "DOC_EXTRACTION",
                page_number: ev.page_number || 1,
                source_text: ev.source_text || "Recorded evidence finding.",
                timestamp: ev.timestamp || "2026-08-11T09:30:00Z",
                extraction_method: ev.extraction_method || "AI_NER",
                confidence: ev.confidence !== undefined ? ev.confidence : 0.95,
                relationship: ev.relationship || "Verified Edge"
            }));
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getEvidenceList();
        }
    }

    async generateReport(caseId) {
        return await this.fetchJson("/api/reports", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ case_id: caseId })
        });
    }

    async generateComprehensiveReport(options = {}) {
        return await this.fetchJson("/api/reports/investigation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(options)
        });
    }

    async exportReport(caseId, format = "json") {
        try {
            const token = this.getToken();
            const headers = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;

            const response = await fetch(`${this.baseUrl}/api/reports/export`, {
                method: "POST",
                headers: headers,
                body: JSON.stringify({ case_id: caseId, format: format })
            });

            if (response.ok) {
                const fmt = (format || "json").toLowerCase();
                if (fmt === "json") {
                    const text = await response.text();
                    return {
                        format: "json",
                        filename: `crimegraph_report_${caseId}.json`,
                        content: text,
                        blob: new Blob([text], { type: "application/json" })
                    };
                } else if (fmt === "pdf") {
                    const blob = await response.blob();
                    return {
                        format: "pdf",
                        filename: `crimegraph_report_${caseId}.pdf`,
                        blob: blob
                    };
                } else {
                    const text = await response.text();
                    return {
                        format: "markdown",
                        filename: `crimegraph_report_${caseId}.md`,
                        content: text,
                        blob: new Blob([text], { type: "text/markdown" })
                    };
                }
            }
        } catch (_) { }

        // Fallback: Generate via generateReport
        const rep = await this.generateReport(caseId);
        const text = rep.content || JSON.stringify(rep, null, 2);
        return {
            format: format || "markdown",
            filename: `crimegraph_report_${caseId}.${format === "json" ? "json" : "md"}`,
            content: text,
            blob: new Blob([text], { type: format === "json" ? "application/json" : "text/markdown" })
        };
    }

    async search(query, filters = {}) {
        try {
            const raw = await this.fetchJson(`/api/entities?type=${filters.type || ''}`);
            const q = (query || "").toLowerCase().trim();
            return raw.filter(n => (n.id && n.id.toLowerCase().includes(q)) || (n.name && n.name.toLowerCase().includes(q))).map(n => ({
                id: n.id,
                name: n.name || n.id,
                type: n.entity_type || "ENTITY",
                confidence: n.confidence || 0.95,
                origin: n.origin || "DATASET"
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

    async analyzePaths(params = {}) {
        try {
            return await this.fetchJson("/api/paths/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(params)
            });
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.analyzePaths(params);
        }
    }

    async getDashboard(params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.case_id) query.set("case_id", params.case_id);
            if (params.limit) query.set("limit", params.limit);
            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/investigation/dashboard${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getDashboard(params);
        }
    }

    async getPatterns(params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.case_id) query.set("case_id", params.case_id);
            if (params.entity_id) query.set("entity_id", params.entity_id);
            if (params.pattern_type) query.set("pattern_type", params.pattern_type);
            if (params.min_severity) query.set("min_severity", params.min_severity);
            if (params.min_score) query.set("min_score", params.min_score);
            if (params.limit) query.set("limit", params.limit);
            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/patterns${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getPatterns(params);
        }
    }

    async compareEntities(entityA, entityB) {
        try {
            return await this.fetchJson(`/api/entity-resolution/compare?entity_a=${encodeURIComponent(entityA)}&entity_b=${encodeURIComponent(entityB)}`);
        } catch (err) {
            const pending = await this.getPendingEntityResolutions().catch(() => ({ candidates: [] }));
            const candidate = (pending.candidates || []).find(c => 
                (c.entity_a === entityA && c.entity_b === entityB) ||
                (c.entity_a === entityB && c.entity_b === entityA)
            );
            if (candidate) return candidate;

            const [entA, entB] = await Promise.all([
                this.getEntityDetails(entityA).catch(() => null),
                this.getEntityDetails(entityB).catch(() => null)
            ]);

            return {
                entity_a: entityA,
                name_a: entA ? entA.name : entityA,
                entity_b: entityB,
                name_b: entB ? entB.name : entityB,
                similarity: 0.85,
                reasons: ["Topological graph co-location", "Shared evidence document context"],
                status: "PENDING_REVIEW"
            };
        }
    }

    async getCommunities(filters = {}) {
        try {
            let params = [];
            if (filters.case_id) params.push(`case_id=${encodeURIComponent(filters.case_id)}`);
            if (filters.classification && filters.classification !== "ALL") params.push(`classification=${encodeURIComponent(filters.classification)}`);
            if (filters.confidence_tier && filters.confidence_tier !== "ALL") params.push(`confidence_tier=${encodeURIComponent(filters.confidence_tier)}`);
            if (filters.cross_case === true) params.push(`cross_case=true`);
            const queryStr = params.length > 0 ? `?${params.join("&")}` : "";
            return await this.fetchJson(`/api/communities${queryStr}`);
        } catch (err) {
            const mockAdapter = new MockCrimeGraphAdapter();
            return await mockAdapter.getCommunities(filters);
        }
    }

    async getCommunityDetails(communityId) {
        try {
            return await this.fetchJson(`/api/communities/${encodeURIComponent(communityId)}`);
        } catch (err) {
            const mockAdapter = new MockCrimeGraphAdapter();
            return await mockAdapter.getCommunityDetails(communityId);
        }
    }

    async detectPatterns(params = {}) {
        try {
            return await this.fetchJson("/api/patterns/detect", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(params)
            });
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.detectPatterns(params);
        }
    }

    async getCorrelations(params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.case_id) query.set("case_id", params.case_id);
            if (params.entity_id) query.set("entity_id", params.entity_id);
            if (params.correlation_type) query.set("correlation_type", params.correlation_type);
            if (params.min_score) query.set("min_score", params.min_score);
            if (params.limit) query.set("limit", params.limit);
            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/correlations${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getCorrelations(params);
        }
    }

    async analyzeCorrelations(params = {}) {
        try {
            return await this.fetchJson("/api/correlations/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(params)
            });
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.analyzeCorrelations(params);
        }
    }

    async getRiskScore(entityId) {
        try {
            return await this.fetchJson(`/api/risk/entities/${entityId}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getRiskScore(entityId);
        }
    }

    async getCaseRiskScore(caseId) {
        try {
            return await this.fetchJson(`/api/risk/cases/${caseId}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getCaseRiskScore(caseId);
        }
    }

    async getInvestigationPriorities(params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.case_id) query.set("case_id", params.case_id);
            if (params.min_score) query.set("min_score", params.min_score);
            if (params.risk_level) query.set("risk_level", params.risk_level);
            if (params.limit) query.set("limit", params.limit);
            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/risk/priorities${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getInvestigationPriorities(params);
        }
    }

    async analyzeRisk(params = {}) {
        try {
            return await this.fetchJson("/api/risk/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(params)
            });
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.analyzeRisk(params);
        }
    }

    async getAuditLogs(params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.actor_id) query.set("actor_id", params.actor_id);
            if (params.action) query.set("action", params.action);
            if (params.resource_type) query.set("resource_type", params.resource_type);
            if (params.case_id) query.set("case_id", params.case_id);
            if (params.status) query.set("status", params.status);
            if (params.limit) query.set("limit", params.limit);
            if (params.offset) query.set("offset", params.offset);

            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/audit${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getAuditLogs(params);
        }
    }

    async getKeyPlayers(params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.case_id) query.set("case_id", params.case_id);
            if (params.role) query.set("role", params.role);
            if (params.entity_type) query.set("entity_type", params.entity_type);
            if (params.limit) query.set("limit", params.limit);
            if (params.min_score) query.set("min_score", params.min_score);

            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/intelligence/key-players${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getKeyPlayers(params);
        }
    }

    async getInfluencers(caseId, entityType = null, limit = 10) {
        try {
            const params = new URLSearchParams();
            if (entityType && entityType !== "ALL") params.set("entity_type", entityType);
            if (limit) params.set("limit", limit);
            const qs = params.toString() ? `?${params.toString()}` : "";
            
            const endpoint = caseId ? `/api/cases/${caseId}/influencers${qs}` : `/api/graph/influencers${qs}`;
            return await this.fetchJson(endpoint);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getInfluencers(caseId, entityType, limit);
        }
    }

    async getNetworkIntelligence(caseId) {
        try {
            const endpoint = caseId ? `/api/cases/${caseId}/network-intelligence` : `/api/graph/network-intelligence`;
            return await this.fetchJson(endpoint);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getNetworkIntelligence(caseId);
        }
    }

    async getPatterns(params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.case_id) query.set("case_id", params.case_id);
            if (params.entity_id) query.set("entity_id", params.entity_id);
            if (params.pattern_type) query.set("pattern_type", params.pattern_type);
            if (params.min_severity) query.set("min_severity", params.min_severity);
            if (params.min_confidence) query.set("min_confidence", params.min_confidence);
            if (params.limit) query.set("limit", params.limit);

            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/patterns${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getPatterns(params);
        }
    }

    async getCasePatterns(caseId, params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.min_severity) query.set("min_severity", params.min_severity);
            if (params.min_confidence) query.set("min_confidence", params.min_confidence);

            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/cases/${caseId}/patterns${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getPatterns({ case_id: caseId, ...params });
        }
    }

    async getSources() {
        try {
            return await this.fetchJson("/api/sources");
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getSources();
        }
    }

    async getSourceDetail(sourceId) {
        try {
            return await this.fetchJson(`/api/sources/${sourceId}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getSourceDetail(sourceId);
        }
    }

    async getEntitySources(entityId) {
        try {
            return await this.fetchJson(`/api/entities/${entityId}/sources`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getEntitySources(entityId);
        }
    }

    async getRelationshipSources(relationshipId) {
        try {
            return await this.fetchJson(`/api/relationships/${relationshipId}/sources`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getRelationshipSources(relationshipId);
        }
    }

    async getSourceConflicts(params = {}) {
        try {
            const query = new URLSearchParams();
            if (params.target_id) query.set("target_id", params.target_id);
            if (params.status) query.set("status", params.status);
            const qs = query.toString() ? `?${query.toString()}` : "";
            return await this.fetchJson(`/api/sources/conflicts${qs}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getSourceConflicts(params);
        }
    }

    async resolveSourceConflict(conflictId, resolveData) {
        return await this.fetchJson(`/api/sources/conflicts/${conflictId}/resolve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(resolveData)
        });
    }

    async getPathProvenance(nodes = []) {
        try {
            const nodeStr = Array.isArray(nodes) ? nodes.join(",") : nodes;
            return await this.fetchJson(`/api/graph/path-provenance?nodes=${nodeStr}`);
        } catch (err) {
            const mock = new MockCrimeGraphAdapter();
            return await mock.getPathProvenance(nodes);
        }
    }

    async ingestSourceBatch(sourceId, batchData) {
        return await this.fetchJson(`/api/sources/${sourceId}/ingest`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(batchData)
        });
    }

    async extractIntelligence(text, sourceDocumentId = "DOC_EXTRACTION", caseId = null) {
        return await this.fetchJson("/api/extract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: text,
                source_document_id: sourceDocumentId,
                case_id: caseId
            })
        });
    }

    async getCrossCaseTimeline(cases = ["CASE_101", "CASE_204"]) {
        const caseParam = Array.isArray(cases) ? cases.join(",") : cases;
        return await this.fetchJson(`/api/timeline/cross-case?cases=${caseParam}`);
    }

    async getEvents(params = {}) {
        let url = "/api/events";
        const queryParams = new URLSearchParams();
        if (params.case_id) queryParams.append("case_id", params.case_id);
        if (params.event_type) queryParams.append("event_type", params.event_type);
        const qStr = queryParams.toString();
        if (qStr) url += `?${qStr}`;
        return await this.fetchJson(url);
    }

    async getCorrelations(params = {}) {
        let url = "/api/timeline/correlations";
        if (typeof params === "string") {
            url += `?case_id=${params}`;
        } else if (params && params.case_id) {
            url += `?case_id=${params.case_id}`;
        }
        return await this.fetchJson(url);
    }

    async getTemporalConflicts() {
        return await this.fetchJson("/api/timeline/conflicts");
    }

    async evaluateResolution(payload) {
        return await this.fetchJson("/api/resolution/evaluate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    }

    async getResolutionCandidates(entityId, minConfidence = 0.50) {
        return await this.fetchJson(`/api/resolution/candidates/${entityId}?min_confidence=${minConfidence}`);
    }

    async mergeEntities(payload) {
        return await this.fetchJson("/api/resolution/merge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    }

    async getIdentityConflicts(status = null) {
        let url = "/api/resolution/conflicts";
        if (status) url += `?status=${status}`;
        return await this.fetchJson(url);
    }

    async getCommunities(params = {}) {
        let url = "/api/communities";
        const queryParams = new URLSearchParams();
        if (params.min_cluster_size) queryParams.append("min_cluster_size", params.min_cluster_size);
        if (params.case_id) queryParams.append("case_id", params.case_id);
        const qStr = queryParams.toString();
        if (qStr) url += `?${qStr}`;
        return await this.fetchJson(url);
    }

    async getCommunityDetail(communityId) {
        return await this.fetchJson(`/api/communities/${communityId}`);
    }

    async getCaseCommunities(caseId, minClusterSize = 2) {
        return await this.fetchJson(`/api/cases/${caseId}/communities?min_cluster_size=${minClusterSize}`);
    }

    async getRiskScores(caseId = null, minScore = 0) {
        try {
            let url = "/api/risk";
            const params = new URLSearchParams();
            if (caseId) params.append("case_id", caseId);
            if (minScore) params.append("min_score", minScore);
            const queryStr = params.toString();
            if (queryStr) url += `?${queryStr}`;
            return await this.fetchJson(url);
        } catch (err) {
            const mockAdapter = new MockCrimeGraphAdapter();
            return await mockAdapter.getRiskScores(caseId, minScore);
        }
    }

    async getAuditLogs(limit = 50) {
        try {
            return await this.fetchJson(`/api/audit?limit=${limit}`);
        } catch (err) {
            return [];
        }
    }

    async getInvestigationDashboard() {
        try {
            return await this.fetchJson("/api/dashboard");
        } catch (err) {
            const mockAdapter = new MockCrimeGraphAdapter();
            return await mockAdapter.getInvestigationDashboard();
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
        const targetUrl = this.httpAdapter.baseUrl || "http://localhost:8000";
        try {
            const res = await fetch(`${targetUrl}/`, { method: "GET" });
            if (res.ok) {
                this.activeAdapter = this.httpAdapter;
                this.adapterName = "HttpCrimeGraphAdapter";
                this.isBackendOnline = true;
                console.log(`Connected to live FastAPI backend at ${targetUrl} (HttpCrimeGraphAdapter active).`);
                this.notifyAdapterStatus(true);
                return;
            }
        } catch (err) {
            if (!targetUrl.includes("127.0.0.1") && !targetUrl.includes("localhost")) {
                try {
                    const fallbackRes = await fetch("http://127.0.0.1:8000/", { method: "GET" });
                    if (fallbackRes.ok) {
                        this.httpAdapter.baseUrl = "http://127.0.0.1:8000";
                        this.activeAdapter = this.httpAdapter;
                        this.adapterName = "HttpCrimeGraphAdapter";
                        this.isBackendOnline = true;
                        this.notifyAdapterStatus(true);
                        return;
                    }
                } catch (_) {}
            }
        }
        this.activeAdapter = this.mockAdapter;
        this.adapterName = "MockCrimeGraphAdapter";
        this.isBackendOnline = false;
        console.log("FastAPI backend offline. Active adapter: MockCrimeGraphAdapter.");
        this.notifyAdapterStatus(false);
    }

    notifyAdapterStatus(isHttp) {
        if (typeof document !== "undefined") {
            const badge = document.getElementById("adapter-status-badge");
            if (badge) {
                badge.innerText = isHttp ? "API Mode (HttpCrimeGraphAdapter)" : "Backend Offline — Demo Mode";
                badge.className = isHttp 
                    ? "px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800"
                    : "px-2 py-0.5 text-[10px] font-bold rounded bg-slate-900 text-slate-300 border border-slate-700";
            }
        }
    }

    async login(username, password) {
        if (this.httpAdapter && typeof this.httpAdapter.login === "function") {
            const res = await this.httpAdapter.login(username, password);
            return res;
        }
        return { access_token: "mock-token", user: { username, role: "ANALYST" } };
    }

    logout() {
        if (this.httpAdapter && typeof this.httpAdapter.logout === "function") {
            this.httpAdapter.logout();
        }
    }

    async getMe() {
        if (this.httpAdapter && typeof this.httpAdapter.getMe === "function") {
            return await this.httpAdapter.getMe();
        }
        return { username: "analyst", role: "ANALYST" };
    }

    async createCase(caseData) {
        try {
            return await this.activeAdapter.createCase(caseData);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.createCase(caseData);
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

    async createEntity(entityData) {
        try {
            return await this.activeAdapter.createEntity(entityData);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.createEntity(entityData);
        }
    }

    async updateEntity(entityId, updateData) {
        try {
            return await this.activeAdapter.updateEntity(entityId, updateData);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.updateEntity(entityId, updateData);
        }
    }

    async deleteEntity(entityId) {
        try {
            return await this.activeAdapter.deleteEntity(entityId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.deleteEntity(entityId);
        }
    }

    async createRelationship(relData) {
        try {
            return await this.activeAdapter.createRelationship(relData);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.createRelationship(relData);
        }
    }

    async deleteRelationship(relId) {
        try {
            return await this.activeAdapter.deleteRelationship(relId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.deleteRelationship(relId);
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

    async getEvidenceList() {
        try {
            return await this.activeAdapter.getEvidenceList();
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getEvidenceList();
        }
    }

    async generateReport(caseId) {
        try {
            return await this.activeAdapter.generateReport(caseId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.generateReport(caseId);
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

    async getAuditLogs(params = {}) {
        try {
            return await this.activeAdapter.getAuditLogs(params);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getAuditLogs(params);
        }
    }

    async getInfluencers(caseId, entityType = null, limit = 10) {
        try {
            return await this.activeAdapter.getInfluencers(caseId, entityType, limit);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getInfluencers(caseId, entityType, limit);
        }
    }

    async getNetworkIntelligence(caseId) {
        try {
            return await this.activeAdapter.getNetworkIntelligence(caseId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getNetworkIntelligence(caseId);
        }
    }

    async getPatterns(params = {}) {
        try {
            return await this.activeAdapter.getPatterns(params);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getPatterns(params);
        }
    }

    async getCasePatterns(caseId, params = {}) {
        try {
            return await this.activeAdapter.getCasePatterns(caseId, params);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getPatterns({ case_id: caseId, ...params });
        }
    }

    async getSources() {
        try {
            return await this.activeAdapter.getSources();
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getSources();
        }
    }

    async getSourceDetail(sourceId) {
        try {
            return await this.activeAdapter.getSourceDetail(sourceId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getSourceDetail(sourceId);
        }
    }

    async getEntitySources(entityId) {
        try {
            return await this.activeAdapter.getEntitySources(entityId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getEntitySources(entityId);
        }
    }

    async getRelationshipSources(relationshipId) {
        try {
            return await this.activeAdapter.getRelationshipSources(relationshipId);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getRelationshipSources(relationshipId);
        }
    }

    async getSourceConflicts(params = {}) {
        try {
            return await this.activeAdapter.getSourceConflicts(params);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getSourceConflicts(params);
        }
    }

    async resolveSourceConflict(conflictId, resolveData) {
        try {
            return await this.activeAdapter.resolveSourceConflict(conflictId, resolveData);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.resolveSourceConflict(conflictId, resolveData);
        }
    }

    async getPatterns(params = {}) {
        try {
            return await this.activeAdapter.getPatterns(params);
        } catch (err) {
            console.warn("HTTP getPatterns failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getPatterns(params);
        }
    }

    async getDashboard(params = {}) {
        try {
            return await this.activeAdapter.getDashboard(params);
        } catch (err) {
            console.warn("HTTP getDashboard failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getDashboard(params);
        }
    }

    async detectPatterns(params = {}) {
        try {
            return await this.activeAdapter.detectPatterns(params);
        } catch (err) {
            console.warn("HTTP detectPatterns failed, falling back to mock adapter:", err);
            return await this.mockAdapter.detectPatterns(params);
        }
    }

    async getCorrelations(params = {}) {
        try {
            return await this.activeAdapter.getCorrelations(params);
        } catch (err) {
            console.warn("HTTP getCorrelations failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getCorrelations(params);
        }
    }

    async analyzeCorrelations(params = {}) {
        try {
            return await this.activeAdapter.analyzeCorrelations(params);
        } catch (err) {
            console.warn("HTTP analyzeCorrelations failed, falling back to mock adapter:", err);
            return await this.mockAdapter.analyzeCorrelations(params);
        }
    }

    async getRiskScore(entityId) {
        try {
            return await this.activeAdapter.getRiskScore(entityId);
        } catch (err) {
            console.warn("HTTP getRiskScore failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getRiskScore(entityId);
        }
    }

    async getCaseRiskScore(caseId) {
        try {
            return await this.activeAdapter.getCaseRiskScore(caseId);
        } catch (err) {
            console.warn("HTTP getCaseRiskScore failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getCaseRiskScore(caseId);
        }
    }

    async getInvestigationPriorities(params = {}) {
        try {
            return await this.activeAdapter.getInvestigationPriorities(params);
        } catch (err) {
            console.warn("HTTP getInvestigationPriorities failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getInvestigationPriorities(params);
        }
    }

    async analyzeRisk(params = {}) {
        try {
            return await this.activeAdapter.analyzeRisk(params);
        } catch (err) {
            console.warn("HTTP analyzeRisk failed, falling back to mock adapter:", err);
            return await this.mockAdapter.analyzeRisk(params);
        }
    }

    async getPathProvenance(nodes = []) {
        try {
            return await this.activeAdapter.getPathProvenance(nodes);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.getPathProvenance(nodes);
        }
    }

    async analyzePaths(params = {}) {
        try {
            return await this.activeAdapter.analyzePaths(params);
        } catch (err) {
            console.warn("HTTP path analysis failed, falling back to mock adapter:", err);
            return await this.mockAdapter.analyzePaths(params);
        }
    }

    async ingestSourceBatch(sourceId, batchData) {
        try {
            return await this.activeAdapter.ingestSourceBatch(sourceId, batchData);
        } catch (err) {
            console.warn("HTTP call failed, falling back to mock adapter:", err);
            return await this.mockAdapter.ingestSourceBatch(sourceId, batchData);
        }
    }

    async extractIntelligence(text, sourceDocumentId = "DOC_EXTRACTION", caseId = null) {
        try {
            return await this.activeAdapter.extractIntelligence(text, sourceDocumentId, caseId);
        } catch (err) {
            console.warn("HTTP extraction failed, falling back to mock adapter:", err);
            return await this.mockAdapter.extractIntelligence(text, sourceDocumentId, caseId);
        }
    }

    async getCrossCaseTimeline(cases = ["CASE_101", "CASE_204"]) {
        try {
            return await this.activeAdapter.getCrossCaseTimeline(cases);
        } catch (err) {
            console.warn("HTTP cross-case timeline failed, falling back to mock:", err);
            return await this.mockAdapter.getCrossCaseTimeline(cases);
        }
    }

    async getKeyPlayers(params = {}) {
        try {
            return await this.activeAdapter.getKeyPlayers(params);
        } catch (err) {
            console.warn("HTTP key players failed, falling back to mock:", err);
            return await this.mockAdapter.getKeyPlayers(params);
        }
    }

    async getEvents(params = {}) {
        try {
            return await this.activeAdapter.getEvents(params);
        } catch (err) {
            console.warn("HTTP events list failed, falling back to mock:", err);
            return await this.mockAdapter.getEvents(params);
        }
    }

    async getCorrelations(params = {}) {
        try {
            return await this.activeAdapter.getCorrelations(params);
        } catch (err) {
            console.warn("HTTP correlations failed, falling back to mock:", err);
            return await this.mockAdapter.getCorrelations(params);
        }
    }

    async getTemporalConflicts() {
        try {
            return await this.activeAdapter.getTemporalConflicts();
        } catch (err) {
            console.warn("HTTP temporal conflicts failed, falling back to mock:", err);
            return await this.mockAdapter.getTemporalConflicts();
        }
    }

    async generateComprehensiveReport(options = {}) {
        try {
            return await this.activeAdapter.generateComprehensiveReport(options);
        } catch (err) {
            console.warn("HTTP comprehensive report failed, falling back to basic report:", err);
            return await this.mockAdapter.generateReport(options.case_id || "CASE_101");
        }
    }

    async exportReport(reportId, format = "JSON") {
        try {
            return await this.activeAdapter.exportReport(reportId, format);
        } catch (err) {
            console.warn("HTTP export report failed:", err);
            return { error: "Export failed", reportId };
        }
    }

    async evaluateResolution(payload) {
        try {
            return await this.activeAdapter.evaluateResolution(payload);
        } catch (err) {
            console.warn("HTTP resolution evaluate failed:", err);
            return { entity_type: payload.entity_type, matches_count: 0, matches: [] };
        }
    }

    async getResolutionCandidates(entityId, minConfidence = 0.50) {
        try {
            return await this.activeAdapter.getResolutionCandidates(entityId, minConfidence);
        } catch (err) {
            console.warn("HTTP resolution candidates failed:", err);
            return { entity_id: entityId, matches_count: 0, candidates: [] };
        }
    }

    async mergeEntities(payload) {
        try {
            return await this.activeAdapter.mergeEntities(payload);
        } catch (err) {
            console.warn("HTTP merge entities failed:", err);
            throw err;
        }
    }

    async getIdentityConflicts(status = null) {
        try {
            return await this.activeAdapter.getIdentityConflicts(status);
        } catch (err) {
            console.warn("HTTP identity conflicts failed:", err);
            return { conflicts_count: 0, conflicts: [] };
        }
    }

    async getCommunities(params = {}) {
        try {
            return await this.activeAdapter.getCommunities(params);
        } catch (err) {
            console.warn("HTTP communities list failed:", err);
            return { total_communities: 0, total_clustered_entities: 0, communities: [] };
        }
    }

    async getCommunityDetail(communityId) {
        try {
            return await this.activeAdapter.getCommunityDetail(communityId);
        } catch (err) {
            console.warn("HTTP community detail failed:", err);
            return null;
        }
    }

    async getCaseCommunities(caseId) {
        try {
            return await this.activeAdapter.getCaseCommunities(caseId);
        } catch (err) {
            console.warn("HTTP case communities failed:", err);
            return { total_communities: 0, total_clustered_entities: 0, case_id: caseId, communities: [] };
        }
    }
}

// Global DataService Instance
if (typeof window !== "undefined") {
    window.dataService = new CrimeGraphDataService();
}
if (typeof module !== "undefined" && module.exports) {
    module.exports = { MockCrimeGraphAdapter, HttpCrimeGraphAdapter, CrimeGraphDataService };
}
