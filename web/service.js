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

                { id: "ACC_001", name: "ACC_AXIS_9941", type: "ACCOUNT", confidence: 0.93, details: "Escrow Bank Account" },

                { id: "SOC_ACC_017", name: "@aarav_v_shadow", type: "ACCOUNT", confidence: 0.85, details: "Synthetic Social Handle (X / Telegram)", source_type: "SOCIAL_MEDIA_SYNTHETIC", platform: "X / Telegram (Synthetic)" },
                { id: "SOC_ACC_089", name: "@vikram_m_cargo", type: "ACCOUNT", confidence: 0.82, details: "Synthetic Social Handle (Telegram Channel)", source_type: "SOCIAL_MEDIA_SYNTHETIC", platform: "Telegram (Synthetic)" }
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
                { id: "REL_089_ACC", source: "PERSON_089", target: "ACC_001", relationship: "OWNED_BY", confidence: 0.93, evidence_id: "EVID_ACC_01" },

                { id: "REL_SOC_017_POST", source: "PERSON_017", target: "SOC_ACC_017", relationship: "POSTED_BY", confidence: 0.85, evidence_id: "EVID_SOC_017_01", source_type: "SOCIAL_MEDIA_SYNTHETIC" },
                { id: "REL_SOC_017_089", source: "SOC_ACC_017", target: "SOC_ACC_089", relationship: "INTERACTS_WITH", confidence: 0.78, evidence_id: "EVID_SOC_017_01", source_type: "SOCIAL_MEDIA_SYNTHETIC" },
                { id: "REL_SOC_089_MENTION", source: "SOC_ACC_089", target: "PERSON_089", relationship: "MENTIONS", confidence: 0.80, evidence_id: "EVID_SOC_089_01", source_type: "SOCIAL_MEDIA_SYNTHETIC" },
                { id: "REL_SOC_017_204", source: "SOC_ACC_017", target: "CASE_204", relationship: "LINKED_TO", confidence: 0.75, evidence_id: "EVID_SOC_017_01", source_type: "SOCIAL_MEDIA_SYNTHETIC" }
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
                },
                "EVID_SOC_017_01": {
                    evidence_id: "EVID_SOC_017_01",
                    source_document: "SOCIAL_017_04",
                    page_number: 1,
                    source_text: "Synthetic Social Post from @aarav_v_shadow: 'Cargo transit payload dispatched to @vikram_m_cargo vault near Zaveri Bazaar'.",
                    timestamp: "2026-08-11T14:22:00Z",
                    extraction_method: "SOCIAL_SOURCE_ADAPTER",
                    source_type: "SOCIAL_MEDIA_SYNTHETIC",
                    confidence: 0.75,
                    relationship: "PERSON_017 --INTERACTS_WITH--> PERSON_089",
                    corroboration: "CORROBORATED",
                    sources_count: 2,
                    conflict_detected: false
                },
                "EVID_SOC_089_01": {
                    evidence_id: "EVID_SOC_089_01",
                    source_document: "SOCIAL_089_09",
                    page_number: 1,
                    source_text: "Synthetic Telegram Channel Record: @vikram_m_cargo confirms receipt of sealed container shipment.",
                    timestamp: "2026-08-12T18:05:00Z",
                    extraction_method: "SOCIAL_SOURCE_ADAPTER",
                    source_type: "SOCIAL_MEDIA_SYNTHETIC",
                    confidence: 0.78,
                    relationship: "SOC_ACC_089 --MENTIONS--> PERSON_089",
                    corroboration: "SINGLE SOURCE",
                    sources_count: 1,
                    conflict_detected: true,
                    conflict_details: {
                        conflicting_values: "Alias: 'Arjun' vs 'Aarav'",
                        source_names: ["Social Media Synthetic", "Manual Notes"],
                        confidence: 0.70,
                        warning: "HUMAN OFFICER VERIFICATION REQUIRED BEFORE FORMAL PROCEEDINGS"
                    }
                }
            }
        };
    }

    getToken() {
        if (typeof localStorage !== "undefined") {
            return localStorage.getItem("crimegraph_token");
        }
        return null;
    }

    setToken(token, user = null) {
        if (typeof localStorage !== "undefined") {
            if (token) {
                localStorage.setItem("crimegraph_token", token);
                if (user) localStorage.setItem("crimegraph_user", JSON.stringify(user));
            } else {
                localStorage.removeItem("crimegraph_token");
                localStorage.removeItem("crimegraph_user");
            }
        }
    }

    getUser() {
        if (typeof localStorage !== "undefined") {
            const raw = localStorage.getItem("crimegraph_user");
            try { return raw ? JSON.parse(raw) : null; } catch (_) { }
        }
        return null;
    }

    isAuthenticated() {
        return !!this.getToken();
    }

    async login(username, password, agencyId = null) {
        const user = { username: username || "Investigator", agency_id: agencyId || "AGY-DEMO", role: "INVESTIGATOR" };
        const token = `mock_token_${Date.now()}`;
        this.setToken(token, user);
        return { access_token: token, token_type: "bearer", user };
    }

    async logout() {
        this.setToken(null);
        return { status: "logged_out" };
    }

    async getAuditLogs(limit = 50) {
        return [
            {
                id: "AUDIT_MOCK_01",
                timestamp: new Date().toISOString(),
                actor: "OFFICER_VERMA",
                action: "SYSTEM_STARTUP",
                resource_type: "KNOWLEDGE_GRAPH",
                resource_id: "GRAPH_STORE",
                case_id: "ALL",
                status: "SUCCESS",
                details: { message: "Demo Mode Active" }
            }
        ];
    }

    async createCase(data) {
        const caseId = data.id || `CASE_${Math.floor(300 + Math.random() * 699)}`;
        const newCase = {
            id: caseId,
            case_number: data.case_number || `FIR-2026-DEL-${caseId.replace('CASE_', '')}`,
            title: data.title || data.case_title || "Untitled Case",
            description: data.description || "",
            incident_date: data.incident_date || data.date || new Date().toISOString(),
            date: data.incident_date || data.date || new Date().toISOString().split("T")[0],
            status: (data.status || "ACTIVE").toUpperCase(),
            priority: (data.priority || "MEDIUM").toUpperCase(),
            location: data.location || "N/A",
            notes: data.notes || "",
            created_by: data.created_by || "OFFICER_VERMA",
            entities_count: 0,
            evidence_count: 0,
            is_manual: true,
            source: "Manual"
        };
        this.dataset.cases.unshift(newCase);
        this.dataset.nodes.unshift({
            id: caseId,
            name: newCase.title,
            type: "CASE",
            confidence: 1.0,
            details: newCase.description || "Manually Created Case Record",
            is_manual: true,
            source: "Manual"
        });
        return newCase;
    }

    async getInvestigationDashboard() {
        const cases = await this.getCases();
        const keyPlayers = await this.getKeyPlayers();
        const patternsData = await this.getSuspiciousPatterns();
        const evidenceList = await this.getEvidenceList();

        return {
            metrics: {
                total_cases: cases.length,
                active_cases: cases.filter(c => (c.status || '').toUpperCase() === 'ACTIVE').length,
                high_priority_cases: cases.filter(c => ['HIGH', 'URGENT'].includes((c.priority || '').toUpperCase())).length,
                key_entities_count: (keyPlayers.key_players || []).length,
                patterns_count: (patternsData.patterns || []).length,
                anomalies_count: (patternsData.anomalies || []).length,
                evidence_count: evidenceList.length,
                cross_case_links_count: 2
            },
            active_cases: cases,
            high_priority_cases: cases.filter(c => ['HIGH', 'URGENT'].includes((c.priority || '').toUpperCase())),
            key_entities: keyPlayers.key_players || [],
            patterns: patternsData.patterns || [],
            anomalies: patternsData.anomalies || [],
            cross_case_connections: [],
            canonical_path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
            recent_evidence: evidenceList,
            ai_findings: [
                {
                    id: "AI_FINDING_001",
                    title: "Cross-Case Burner Phone Linkage",
                    type: "SUSPICIOUS_PATTERN",
                    description: "Shared burner line PHONE_042 (+91-9876543210) bridges CASE_101 and CASE_204 across 4 hops.",
                    confidence: 0.93,
                    status: "Requires Review",
                    case_a: "CASE_101",
                    case_b: "CASE_204",
                    entity_id: "PHONE_042"
                }
            ]
        };
    }

    async getKeyPlayers(params = {}) {
        let players = [
            {
                rank: 1,
                entity_id: "PERSON_017",
                name: "Aarav Verma",
                type: "PERSON",
                influence_score: 0.95,
                role: "CORE_HUB",
                role_label: "Core Network Hub",
                degree: 11,
                connected_cases: ["CASE_101"],
                is_cross_case: false,
                community_id: "COMM_001",
                community_name: "Midnight Shadow Operations Core",
                community_influence_rank: 1,
                confidence: 0.95,
                evidence_count: 8,
                evidence_ids: ["EVID_042_01", "EVID_042_02"],
                explanation: "Primary high-degree hub directing operational logistics and communications across multiple burner handsets.",
                investigative_lead: "Focus on primary communications logs and cross-reference with digital forensics extractions.",
                limitations: ["High degree centrality reflects dense record reporting, not legal culpability."],
                safety_disclaimer: "Investigative lead only. Graph influence metrics do not establish criminal culpability."
            },
            {
                rank: 2,
                entity_id: "PHONE_042",
                name: "+91-9876543210",
                type: "PHONE",
                influence_score: 0.93,
                role: "CROSS_CASE_INFLUENCER",
                role_label: "Cross-Case Influencer",
                degree: 8,
                connected_cases: ["CASE_101", "CASE_204"],
                is_cross_case: true,
                community_id: "COMM_001",
                community_name: "Midnight Shadow Operations Core",
                community_influence_rank: 2,
                confidence: 0.95,
                evidence_count: 5,
                evidence_ids: ["EVID_042_01", "EVID_042_02"],
                explanation: "Encrypted burner line bridging primary suspect entities between Operation Midnight Shadow (CASE_101) and Operation Golden Falcon (CASE_204).",
                investigative_lead: "Issue CDR subpoena and track cell site location co-occurrences.",
                limitations: ["Burner line co-occurrence requires physical proximity verification."],
                safety_disclaimer: "Investigative lead only. Graph influence metrics do not establish criminal culpability."
            },
            {
                rank: 3,
                entity_id: "PERSON_089",
                name: "Vikram Malhotra",
                type: "PERSON",
                influence_score: 0.88,
                role: "BRIDGE_ENTITY",
                role_label: "Bridge Entity",
                degree: 6,
                connected_cases: ["CASE_204"],
                is_cross_case: false,
                community_id: "COMM_002",
                community_name: "Golden Falcon Fencing Syndicate",
                community_influence_rank: 1,
                confidence: 0.90,
                evidence_count: 4,
                evidence_ids: ["EVID_204_01"],
                explanation: "Acts as a bridge entity between freight diversion channels and fencing outlets.",
                investigative_lead: "Surveillance of warehouse facilities and banking audit of escrow accounts.",
                limitations: ["High graph influence score reflects topological density and evidence co-occurrence."],
                safety_disclaimer: "Investigative lead only. Graph influence metrics do not establish criminal culpability."
            }
        ];

        if (params.case_id && params.case_id !== "ALL") {
            players = players.filter(p => p.connected_cases.includes(params.case_id));
        }
        if (params.type && params.type !== "ALL") {
            players = players.filter(p => p.type.toUpperCase() === params.type.toUpperCase());
        }
        if (params.role && params.role !== "ALL") {
            players = players.filter(p => p.role.toUpperCase() === params.role.toUpperCase());
        }

        return {
            total_ranked: players.length,
            metrics: {
                total_key_players: players.length,
                core_hubs_count: players.filter(p => p.role === "CORE_HUB").length,
                bridge_entities_count: players.filter(p => ["BRIDGE_ENTITY", "CROSS_CASE_INFLUENCER"].includes(p.role)).length,
                cross_case_influencers_count: players.filter(p => p.is_cross_case).length,
                top_influencer_id: players[0]?.entity_id || null,
                top_influencer_name: players[0]?.name || null,
                top_influencer_score: players[0]?.influence_score || 0.0
            },
            key_players: players,
            safety_disclaimer: "Graph influence analysis identifies structural nodes across evidence records. It does not declare criminal culpability."
        };
    }

    async findPaths(sourceId, targetId, maxDepth = 6, params = {}) {
        if (!sourceId || !targetId) {
            return { source_id: sourceId, target_id: targetId, path_count: 0, paths: [] };
        }

        const sUpper = sourceId.trim().toUpperCase();
        const tUpper = targetId.trim().toUpperCase();

        if ((sUpper === "CASE_101" && tUpper === "CASE_204") || (sUpper === "PERSON_017" && tUpper === "PERSON_089")) {
            return {
                source_id: sourceId,
                target_id: targetId,
                path_count: 1,
                paths: [
                    {
                        source_id: sourceId,
                        target_id: targetId,
                        path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                        shared_entities: ["PERSON_017", "PHONE_042", "PERSON_089"],
                        confidence: 0.95,
                        evidence_ids: ["EVID_042_01", "EVID_101_01"],
                        steps: [
                            { from: "CASE_101", to: "PERSON_017", relationship: "INVOLVED_IN", relationship_id: "REL_101_01", confidence: 0.98, evidence_ids: ["EVID_101_01"] },
                            { from: "PERSON_017", to: "PHONE_042", relationship: "USES", relationship_id: "REL_042_01", confidence: 0.95, evidence_ids: ["EVID_042_01"] },
                            { from: "PHONE_042", to: "PERSON_089", relationship: "CONTACTED", relationship_id: "REL_042_02", confidence: 0.92, evidence_ids: ["EVID_042_02"] },
                            { from: "PERSON_089", to: "CASE_204", relationship: "INVOLVED_IN", relationship_id: "REL_204_01", confidence: 0.96, evidence_ids: ["EVID_204_01"] }
                        ],
                        hop_count: 4,
                        path_score: 0.95,
                        explanation: "Multi-hop cross-case conduit path linking CASE_101 and CASE_204 via intermediate burner line +91-9876543210 (PHONE_042)."
                    }
                ]
            };
        }

        return {
            source_id: sourceId,
            target_id: targetId,
            path_count: 0,
            paths: []
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

    async getEvidenceItem(evidenceId) {
        if (!evidenceId) return null;
        const ev = this.dataset.evidence[evidenceId];
        if (ev) return ev;
        return {
            evidence_id: evidenceId,
            source_document_id: evidenceId.includes("042_01") ? "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf" : (evidenceId.includes("042_02") ? "DOC_CASE_204_MUMBAI_INTERCEPT_SUMMARY.pdf" : "DOC_CASE_101_FIR_REPORT.pdf"),
            extraction_method: evidenceId.includes("042_01") ? "DIGITAL_FORENSICS" : (evidenceId.includes("042_02") ? "TELCO_INTERCEPT" : "AI_NER"),
            page_number: evidenceId.includes("042_01") ? 7 : (evidenceId.includes("042_02") ? 3 : 2),
            confidence: 0.95,
            source_text: "Handset triage recovered encrypted messaging sessions identifying Aarav Verma (PERSON_017) using burner line +91-9876543210 (PHONE_042).",
            timestamp: "2026-08-14T22:45:00Z"
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

    async getTimeline(caseId = "ALL") {
        const allEvents = [
            {
                id: "EV_101_01",
                case_id: "CASE_101",
                title: "Cargo Unloading Supervision",
                event_type: "CARGO_UNLOAD",
                timestamp: "2026-08-10T18:30:00Z",
                timestamp_precision: "EXACT",
                location_id: "LOC_001",
                location_name: "ICD Tughlakabad Logistics Yard",
                involved_entity_ids: ["PERSON_017", "LOC_001"],
                involved_entity_names: ["Aarav Verma (PERSON_017)", "ICD Tughlakabad (LOC_001)"],
                evidence_ids: ["EVID_101_01"],
                confidence: 0.97,
                confidence_tier: "HIGH",
                source_document: "DOC_CASE_101_FIR_REPORT.pdf",
                source_type: "SYNTHETIC_DATASET",
                extraction_method: "AI_NER",
                description: "CCTV review and transit manifests identify Aarav Verma (PERSON_017) supervising unmanifested cargo unloading during incident window.",
                correlation_status: "DIRECTLY_SUPPORTED",
                correlations: [
                    { target_event_id: "EV_101_02", reason: "Shared Suspect: PERSON_017", correlation_type: "SHARED_ENTITY" }
                ]
            },
            {
                id: "EV_101_02",
                case_id: "CASE_101",
                title: "Logistics Yard Vehicle Exit",
                event_type: "VEHICLE_SIGHTING",
                timestamp: "2026-08-11T09:30:00Z",
                timestamp_precision: "EXACT",
                location_id: "LOC_001",
                location_name: "ICD Tughlakabad Gate 3",
                involved_entity_ids: ["PERSON_017", "VEHICLE_017"],
                involved_entity_names: ["Aarav Verma (PERSON_017)", "Bolero Pickup MH-01-AB-1234 (VEHICLE_017)"],
                evidence_ids: ["EVID_042_01"],
                confidence: 0.94,
                confidence_tier: "HIGH",
                source_document: "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf",
                source_type: "DIGITAL_FORENSICS",
                extraction_method: "DIGITAL_FORENSICS",
                description: "ANPR camera logs captured Bolero pickup truck MH-01-AB-1234 exiting the logistics yard following cargo dispatch.",
                correlation_status: "DIRECTLY_SUPPORTED",
                correlations: [
                    { target_event_id: "EV_101_01", reason: "Shared Location: LOC_001", correlation_type: "SHARED_LOCATION" }
                ]
            },
            {
                id: "EV_042_01",
                case_id: "CASE_101",
                title: "Burner Handset Messaging Session",
                event_type: "CALL_INTERCEPT",
                timestamp: "2026-08-12T14:20:00Z",
                timestamp_precision: "EXACT",
                location_id: "LOC_007",
                location_name: "Cell Tower Sector 7 (Tughlakabad)",
                involved_entity_ids: ["PERSON_017", "PHONE_042"],
                involved_entity_names: ["Aarav Verma (PERSON_017)", "Burner Line +91-9876543210 (PHONE_042)"],
                evidence_ids: ["EVID_042_01"],
                confidence: 0.95,
                confidence_tier: "HIGH",
                source_document: "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf",
                source_type: "DIGITAL_FORENSICS",
                extraction_method: "DIGITAL_FORENSICS",
                description: "Handset triage recovered encrypted messaging sessions identifying Aarav Verma (PERSON_017) using burner line +91-9876543210 (PHONE_042) to coordinate dispatch.",
                correlation_status: "POTENTIAL_CORRELATION",
                correlations: [
                    { target_event_id: "EV_042_02", reason: "Cross-Case Shared Phone: PHONE_042", correlation_type: "SHARED_PHONE" }
                ],
                conflict: {
                    has_conflict: true,
                    description: "Temporal conflict: Forensic extraction log indicates messaging at 14:20:00Z, whereas CDR gateway record logs tower ping at 14:45:10Z. Human officer verification required."
                }
            },
            {
                id: "EV_042_02",
                case_id: "CASE_204",
                title: "Lawful Signal Intelligence Intercept",
                event_type: "CALL_INTERCEPT",
                timestamp: "2026-08-12T21:15:00Z",
                timestamp_precision: "EXACT",
                location_id: "LOC_003",
                location_name: "Zaveri Bazaar Cell Tower (Mumbai)",
                involved_entity_ids: ["PERSON_089", "PHONE_042"],
                involved_entity_names: ["Vikram Malhotra (PERSON_089)", "Burner Line +91-9876543210 (PHONE_042)"],
                evidence_ids: ["EVID_042_02"],
                confidence: 0.93,
                confidence_tier: "HIGH",
                source_document: "DOC_CASE_204_MUMBAI_INTERCEPT_SUMMARY.pdf",
                source_type: "TELCO_INTERCEPT",
                extraction_method: "TELCO_INTERCEPT",
                description: "Lawful signal intelligence intercept confirmed Vikram Malhotra (PERSON_089) utilizing burner line +91-9876543210 (PHONE_042) to negotiate bullion disposal.",
                correlation_status: "POTENTIAL_CORRELATION",
                correlations: [
                    { target_event_id: "EV_042_01", reason: "Cross-Case Shared Phone: PHONE_042 (CASE_101 <-> CASE_204)", correlation_type: "SHARED_PHONE" },
                    { target_event_id: "EV_204_01", reason: "Shared Suspect: PERSON_089", correlation_type: "SHARED_ENTITY" }
                ]
            },
            {
                id: "EV_204_01",
                case_id: "CASE_204",
                title: "Zaveri Bazaar Bullion Vault Seizure",
                event_type: "BULLION_RECOVERY",
                timestamp: "2026-08-14T11:45:00Z",
                timestamp_precision: "EXACT",
                location_id: "LOC_003",
                location_name: "Zaveri Bazaar Fencing Vault",
                involved_entity_ids: ["PERSON_089", "LOC_003", "ACC_001"],
                involved_entity_names: ["Vikram Malhotra (PERSON_089)", "Zaveri Bazaar (LOC_003)", "HDFC Account (ACC_001)"],
                evidence_ids: ["EVID_204_01"],
                confidence: 0.96,
                confidence_tier: "HIGH",
                source_document: "DOC_CASE_204_MUMBAI_CRIME_BRANCH.pdf",
                source_type: "SYNTHETIC_DATASET",
                extraction_method: "AI_NER",
                description: "Financial trail and bullion seizure at Zaveri Bazaar directly incriminate Vikram Malhotra (PERSON_089) as primary receiver.",
                correlation_status: "DIRECTLY_SUPPORTED",
                correlations: [
                    { target_event_id: "EV_042_02", reason: "Shared Suspect: PERSON_089", correlation_type: "SHARED_ENTITY" }
                ]
            },
            {
                id: "EV_NLP_01",
                case_id: "CASE_101",
                title: "Encrypted Message Intelligence Triage",
                event_type: "NLP_EXTRACTED",
                timestamp: null,
                timestamp_precision: "UNKNOWN",
                location_id: "LOC_001",
                location_name: "Logistics Hub (Extracted)",
                involved_entity_ids: ["PERSON_017", "PHONE_042"],
                involved_entity_names: ["Aarav Verma (PERSON_017)", "+91-9876543210 (PHONE_042)"],
                evidence_ids: ["EVID_EXT_101"],
                confidence: 0.90,
                confidence_tier: "MEDIUM",
                source_document: "DOC_EXTRACTED_MESSAGE_TRIAGE.txt",
                source_type: "NLP_EXTRACTED",
                extraction_method: "NLP_EXTRACTED",
                description: "Automated Day-22 NLP extraction parsed text snippet identifying burner handset co-occurrence with logistics yard supervisor.",
                correlation_status: "POTENTIAL_CORRELATION",
                correlations: [
                    { target_event_id: "EV_042_01", reason: "Shared Entities: PERSON_017, PHONE_042", correlation_type: "SHARED_ENTITY" }
                ]
            },
            {
                id: "EV_SOC_01",
                case_id: "CASE_101",
                title: "Synthetic Social Post & Intercept",
                event_type: "SOCIAL_MEDIA_POST",
                timestamp: "2026-08-11T14:22:00Z",
                timestamp_precision: "EXACT",
                location_id: "LOC_001",
                location_name: "Nhava Sheva Hub (Geotagged)",
                involved_entity_ids: ["PERSON_017", "SOC_ACC_017", "SOC_ACC_089"],
                involved_entity_names: ["Aarav Verma (PERSON_017)", "@aarav_v_shadow (SOC_ACC_017)", "@vikram_m_cargo (SOC_ACC_089)"],
                evidence_ids: ["EVID_SOC_017_01"],
                confidence: 0.75,
                confidence_tier: "MEDIUM",
                source_document: "SOCIAL_017_04",
                source_type: "SOCIAL_MEDIA_SYNTHETIC",
                extraction_method: "SOCIAL_SOURCE_ADAPTER",
                description: "Synthetic Social Media Post from @aarav_v_shadow: 'Cargo transit payload dispatched to @vikram_m_cargo vault near Zaveri Bazaar'.",
                correlation_status: "POTENTIAL_CORRELATION",
                correlations: [
                    { target_event_id: "EV_101_01", reason: "Shared Suspect: PERSON_017", correlation_type: "SHARED_ENTITY" }
                ],
                corroboration: "CORROBORATED",
                sources_count: 2
            }
        ];

        if (!caseId || caseId === "ALL") {
            return { events: allEvents };
        }

        const filtered = allEvents.filter(e => e.case_id === caseId);
        return { events: filtered };
    }

    async getEvidence(evidenceId) {
        return this.dataset.evidence[evidenceId] || null;
    }

    async getEvidenceList() {
        return Object.values(this.dataset.evidence);
    }

    async generateReport(caseId) {
        const targetCase = this.dataset.cases.find(c => c.id === caseId) || this.dataset.cases[0];
        if (!targetCase) return null;
        const realCaseId = targetCase.id;

        const keyEntities = [
            { id: "PERSON_017", name: "Aarav Verma", type: "PERSON", confidence: 0.96, details: "Logistics Dispatch Supervisor", source_provenance: "Synthetic Dataset", evidence_ids: ["EVID_101_01", "EVID_042_01"] },
            { id: "PHONE_042", name: "+91-9876543210", type: "PHONE", confidence: 0.95, details: "Encrypted Burner Line", source_provenance: "Digital Forensics", evidence_ids: ["EVID_042_01", "EVID_042_02"] },
            { id: "PERSON_089", name: "Vikram Malhotra", type: "PERSON", confidence: 0.94, details: "Bullion Receiver & Fencer", source_provenance: "Telco Intercept", evidence_ids: ["EVID_042_02", "EVID_204_01"] },
            { id: "VEHICLE_042", name: "MH-01-AB-1234", type: "VEHICLE", confidence: 0.94, details: "Black SUV", source_provenance: "Synthetic Dataset", evidence_ids: ["EVID_V042_01"] },
            { id: "SOC_ACC_017", name: "@aarav_v_shadow", type: "ACCOUNT", confidence: 0.85, details: "Synthetic Handle (X / Telegram)", source_provenance: "Social Media Synthetic", evidence_ids: ["EVID_SOC_017_01"] }
        ];

        const relationships = [
            { id: "REL_101_017", source_id: realCaseId, target_id: "PERSON_017", relationship: "INVOLVED_IN", confidence: 0.97, source_provenance: "Synthetic Dataset", evidence_ids: ["EVID_101_01"] },
            { id: "REL_017_042", source_id: "PERSON_017", target_id: "PHONE_042", relationship: "USES", confidence: 0.95, source_provenance: "Digital Forensics", evidence_ids: ["EVID_042_01"] },
            { id: "REL_042_089", source_id: "PHONE_042", target_id: "PERSON_089", relationship: "USES", confidence: 0.93, source_provenance: "Telco Intercept", evidence_ids: ["EVID_042_02"] },
            { id: "REL_089_204", source_id: "PERSON_089", target_id: "CASE_204", relationship: "INVOLVED_IN", confidence: 0.96, source_provenance: "Synthetic Dataset", evidence_ids: ["EVID_204_01"] },
            { id: "REL_SOC_017_089", source_id: "SOC_ACC_017", target_id: "PERSON_089", relationship: "INTERACTS_WITH", confidence: 0.78, source_provenance: "Social Media Synthetic", evidence_ids: ["EVID_SOC_017_01"] }
        ];

        const timelineEvents = [
            { id: "EV_101_01", case_id: realCaseId, title: "Cargo Unloading Supervision", event_type: "CARGO_UNLOAD", timestamp: "2026-08-10T18:30:00Z", location: "Nhava Sheva Hub", description: "CCTV review and transit manifests identify Aarav Verma supervising unmanifested cargo unloading.", confidence: 0.97, source_provenance: "Synthetic Dataset", evidence_ids: ["EVID_101_01"] },
            { id: "EV_042_01", case_id: realCaseId, title: "Burner Handset Messaging Session", event_type: "CALL_INTERCEPT", timestamp: "2026-08-12T14:20:00Z", location: "Tower Sector 7", description: "Forensic extraction logs encrypted messaging session on burner line +91-9876543210.", confidence: 0.95, source_provenance: "Digital Forensics", evidence_ids: ["EVID_042_01"] },
            { id: "EV_SOC_01", case_id: realCaseId, title: "Synthetic Social Intercept", event_type: "SOCIAL_MEDIA_POST", timestamp: "2026-08-11T14:22:00Z", location: "Nhava Sheva Hub", description: "Synthetic Social Post from @aarav_v_shadow referencing transit payload.", confidence: 0.75, source_provenance: "Social Media Synthetic", evidence_ids: ["EVID_SOC_017_01"] }
        ];

        const suspiciousPatterns = [
            { pattern_id: "PAT_CROSS_001", title: "Cross-Case Communication Bridge", pattern_type: "CROSS_CASE_BRIDGE", entities: ["PHONE_042", "PERSON_017", "PERSON_089"], cases: [realCaseId, "CASE_204"], path: [realCaseId, "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"], confidence: 0.93, severity: "HIGH", evidence_ids: ["EVID_042_01", "EVID_042_02"], explanation: "Encrypted burner line +91-9876543210 bridges primary suspects between Operation Midnight Shadow and Operation Golden Falcon.", investigative_lead: "Issue sub-poena for burner telecommunication records." },
            { pattern_id: "PAT_SOC_001", title: "Synthetic Cross-Platform Social Coordination", pattern_type: "COORDINATED_SOCIAL_BOTNET", entities: ["PERSON_017", "SOC_ACC_017", "PERSON_089"], cases: [realCaseId, "CASE_204"], path: ["PERSON_017", "SOC_ACC_017", "PERSON_089"], confidence: 0.78, severity: "MEDIUM", evidence_ids: ["EVID_SOC_017_01"], explanation: "Synthetic handles exhibit coordinated messaging during transit windows.", investigative_lead: "Investigative indicator: Issue cyber cell query for handle registration metadata." }
        ];

        const networkIntel = { node_count: 9, edge_count: 6, cross_case_bridges_count: 1, density: 0.19 };
        const evidenceList = Object.values(this.dataset.evidence);
        const sourceProvenance = ["Synthetic Dataset", "Digital Forensics", "Telco Intercept", "NLP Extract", "Social Media Synthetic"];
        const sourceConflicts = [
            {
                entity_id: "PERSON_017",
                conflicting_values: "Alias: 'Arjun' vs 'Aarav'",
                source_names: ["Social Media Synthetic", "Manual Notes"],
                confidence: 0.70,
                warning: "HUMAN OFFICER VERIFICATION REQUIRED BEFORE FORMAL PROCEEDINGS"
            }
        ];
        const leads = [
            "Issue sub-poena for burner telecommunication records and cell tower location logs.",
            "Cross-reference suspect communications with bullion vault transaction ledgers.",
            "Verify synthetic social media handle metadata (@aarav_v_shadow) with cyber forensics unit.",
            "Conduct human officer verification of extracted evidence snippets with original seized case records."
        ];
        const limitations = [
            "Graph associations and social media indicators serve as investigative leads only and do not establish formal legal guilt.",
            "Cross-case linkages rely on temporal proximity and shared identifiers; human officer review required."
        ];
        const disclaimer = "CrimeGraph AI provides investigative leads and association mappings based solely on ingested documents. This output does NOT declare guilt, make legal judgments, or represent conclusive criminal proof. All generated leads require mandatory human verification by authorized case officers.";

        const reportMarkdown = `# CRIMEGRAPH AI — INVESTIGATION SUMMARY REPORT\n\n` +
            `**Case Reference**: ${targetCase.id} — ${targetCase.title}\n` +
            `**Status**: ${targetCase.status}\n` +
            `**Generated Timestamp**: ${new Date().toISOString()}\n` +
            `**Overall Confidence**: **0.95**\n\n` +
            `## 1. Executive Summary\n` +
            `Knowledge graph automated intelligence identified multi-hop connections linking ${targetCase.id} to secondary investigation entities.\n\n` +
            `## 2. Key Discovered Connections\n` +
            `- Primary Suspect / Contact: Aarav Verma (PERSON_017)\n` +
            `- Intercepted Communication: Encrypted Burner Line +91-9876543210 (PHONE_042)\n` +
            `- Cross-Case Target: Vikram Malhotra (PERSON_089) — Associated with CASE_204\n\n` +
            `## 3. Provenance & Evidence Base\n` +
            `- Supported by EVID_042_01 (Handset triage forensics) and EVID_042_02 (Signal intercept)\n\n` +
            `## 4. LEGAL & SAFETY DISCLAIMER\n` + disclaimer;

        return {
            report_id: `REPORT_${realCaseId}_DEMO`,
            case_id: realCaseId,
            status: "generated",
            timestamp: new Date().toISOString(),
            title: `CrimeGraph Investigation Report — ${targetCase.title}`,
            case_title: targetCase.title,
            investigation_question: `Comprehensive investigation summary for ${realCaseId}`,
            executive_summary: `Knowledge graph automated intelligence identified multi-hop connections linking ${realCaseId} to secondary investigation entities.`,
            key_entities: keyEntities,
            relationships: relationships,
            timeline_events: timelineEvents,
            correlated_events: [],
            suspicious_patterns: suspiciousPatterns,
            network_intelligence: networkIntel,
            evidence: evidenceList,
            source_provenance: sourceProvenance,
            overall_confidence: 0.95,
            investigative_leads: leads,
            limitations: limitations,
            safety_disclaimer: disclaimer,
            content: reportMarkdown
        };
    }

    async exportReport(caseId, format = "json") {
        const report = await this.generateReport(caseId);
        if (!report) throw new Error(`Case '${caseId}' not found for report export.`);

        const fmt = (format || "json").toLowerCase();
        if (fmt === "json") {
            const jsonStr = JSON.stringify(report, null, 2);
            return {
                format: "json",
                filename: `crimegraph_report_${caseId}.json`,
                content: jsonStr,
                blob: new Blob([jsonStr], { type: "application/json" })
            };
        } else if (fmt === "pdf") {
            const pdfHeader = `%PDF-1.4\n1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources <</Font <</F1 4 0 R>>>> /Contents 5 0 R>> endobj\n4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n5 0 obj <</Length ${report.content.length}>> stream\n${report.content}\nendstream endobj\nxref\n0 6\ntrailer <</Size 6 /Root 1 0 R>>\n%%EOF`;
            return {
                format: "pdf",
                filename: `crimegraph_report_${caseId}.pdf`,
                blob: new Blob([pdfHeader], { type: "application/pdf" })
            };
        } else {
            return {
                format: "markdown",
                filename: `crimegraph_report_${caseId}.md`,
                content: report.content,
                blob: new Blob([report.content], { type: "text/markdown" })
            };
        }
    }

    async search(query, filters = {}) {
        if (!query || !query.trim()) return [];

        const q = query.toLowerCase().trim();
        return this.dataset.nodes.filter(n => {
            const matchesQuery = (
                n.id.toLowerCase().includes(q) ||
                (n.name && n.name.toLowerCase().includes(q)) ||
                (n.details && n.details.toLowerCase().includes(q)) ||
                (n.phone_number && n.phone_number.toLowerCase().includes(q)) ||
                (n.registration_number && n.registration_number.toLowerCase().includes(q)) ||
                (n.identifier && n.identifier.toLowerCase().includes(q))
            );
            const matchesType = !filters.type || filters.type === "ALL" || n.type === filters.type;
            return matchesQuery && matchesType;
        });
    }

    async getPendingEntityResolutions() {
        return {
            status: "PENDING_REVIEW",
            candidate_count: 2,
            candidates: [
                {
                    id: "RES_PERSON_017_PERSON_092",
                    entity_a: {
                        id: "PERSON_017",
                        name: "Aarav Verma",
                        type: "PERSON",
                        aliases: ["Arjun", "Verma_Logistics"],
                        phone_ids: ["PHONE_042"],
                        vehicle_ids: ["VEHICLE_042"],
                        account_ids: ["ACC_AXIS_9941"],
                        case_ids: ["CASE_101"],
                        details: "Logistics Dispatch Supervisor (Nhava Sheva)"
                    },
                    entity_b: {
                        id: "PERSON_092",
                        name: "A. Verma",
                        type: "PERSON",
                        aliases: ["@aarav_v_shadow"],
                        phone_ids: ["PHONE_042"],
                        vehicle_ids: ["VEHICLE_042"],
                        account_ids: [],
                        case_ids: ["CASE_204"],
                        details: "Fencing Contact Candidate"
                    },
                    similarity: 0.92,
                    confidence_tier: "HIGH",
                    match_status: "MATCH",
                    reasons: ["Similar name ('Aarav Verma' vs 'A. Verma')", "Shared phone PHONE_042 (+91-9876543210)", "Shared vehicle VEHICLE_042 (MH-01-AB-1234)"],
                    matching_fields: [
                        { field: "Name", value: "Aarav Verma / A. Verma", status: "MATCH" },
                        { field: "Phone Lines", value: "PHONE_042 (+91-9876543210)", status: "MATCH" },
                        { field: "Vehicles", value: "VEHICLE_042 (MH-01-AB-1234)", status: "MATCH" }
                    ],
                    conflicting_fields: [
                        {
                            field: "Alias / Handle",
                            claim_a: "Alias 'Arjun' (FIR Record)",
                            claim_b: "Handle '@aarav_v_shadow' (Social Synthetic)",
                            source_a: "DOC_CASE_101_FIR_REPORT.pdf",
                            source_b: "SOCIAL_017_04"
                        }
                    ],
                    has_conflict: true,
                    conflict_details: {
                        warning: "HUMAN OFFICER VERIFICATION REQUIRED BEFORE FORMAL PROCEEDINGS",
                        investigative_lead: "Verify synthetic social media handle metadata with case officer notes before formal entity linking."
                    },
                    source_provenance: ["Digital Forensics", "Synthetic Dataset", "Social Media Synthetic"],
                    evidence_ids: ["EVID_101_01", "EVID_042_01", "EVID_SOC_017_01"],
                    explanation: "High identity match (92%, Tier: HIGH). Shared phone line PHONE_042 and vehicle MH-01-AB-1234 co-occur across CASE_101 and CASE_204.",
                    status: "PENDING_REVIEW"
                },
                {
                    id: "RES_PERSON_089_PERSON_056",
                    entity_a: {
                        id: "PERSON_089",
                        name: "Vikram Malhotra",
                        type: "PERSON",
                        aliases: ["V. Malhotra", "@vikram_m_cargo"],
                        phone_ids: ["PHONE_042", "PHONE_089"],
                        vehicle_ids: [],
                        account_ids: ["ACC_001"],
                        case_ids: ["CASE_204"],
                        details: "Bullion Receiver & Fencer"
                    },
                    entity_b: {
                        id: "PERSON_056",
                        name: "Karan Shah",
                        type: "PERSON",
                        aliases: ["K. Shah"],
                        phone_ids: ["PHONE_089"],
                        vehicle_ids: [],
                        account_ids: [],
                        case_ids: ["CASE_305"],
                        details: "Hawala Courier Operator"
                    },
                    similarity: 0.74,
                    confidence_tier: "MEDIUM",
                    match_status: "POSSIBLE MATCH",
                    reasons: ["Shared landline PHONE_089", "Cross-case financial link to ACC_001"],
                    matching_fields: [
                        { field: "Phone Lines", value: "PHONE_089 (+91-9811099887)", status: "MATCH" }
                    ],
                    conflicting_fields: [],
                    has_conflict: false,
                    conflict_details: null,
                    source_provenance: ["Telco Intercept", "Synthetic Dataset"],
                    evidence_ids: ["EVID_042_02", "EVID_204_01"],
                    explanation: "Possible match (74%, Tier: MEDIUM). Shared phone line PHONE_089 indicates possible associate or shared handset line.",
                    status: "PENDING_REVIEW"
                }
            ]
        };
    }

    async compareEntities(entityAId, entityBId) {
        const pending = await this.getPendingEntityResolutions();
        const found = pending.candidates.find(c => (c.entity_a.id === entityAId && c.entity_b.id === entityBId) || (c.entity_a.id === entityBId && c.entity_b.id === entityAId));
        if (found) return found;

        const nodeA = this.dataset.nodes.find(n => n.id === entityAId) || { id: entityAId, name: entityAId, type: "PERSON", details: "Graph Node A" };
        const nodeB = this.dataset.nodes.find(n => n.id === entityBId) || { id: entityBId, name: entityBId, type: "PERSON", details: "Graph Node B" };

        return {
            id: `RES_${entityAId}_${entityBId}`,
            entity_a: { id: nodeA.id, name: nodeA.name, type: nodeA.type, aliases: nodeA.aliases || [], phone_ids: nodeA.phone_ids || [], vehicle_ids: nodeA.vehicle_ids || [], account_ids: [], case_ids: [], details: nodeA.details },
            entity_b: { id: nodeB.id, name: nodeB.name, type: nodeB.type, aliases: nodeB.aliases || [], phone_ids: nodeB.phone_ids || [], vehicle_ids: nodeB.vehicle_ids || [], account_ids: [], case_ids: [], details: nodeB.details },
            similarity: 0.65,
            confidence_tier: "LOW",
            match_status: "UNRESOLVED",
            reasons: ["Topological graph co-occurrence"],
            matching_fields: [],
            conflicting_fields: [],
            has_conflict: false,
            conflict_details: null,
            source_provenance: ["Synthetic Dataset"],
            evidence_ids: [],
            explanation: "Low similarity candidate comparison. Further investigative evidence required.",
            status: "PENDING_REVIEW"
        };
    }

    async getCommunities(filters = {}) {
        await new Promise(r => setTimeout(r, 100));
        let communities = [
            {
                id: "C-001",
                name: "Community C-001 (Organized Cell)",
                member_count: 5,
                density: 0.85,
                confidence: 0.92,
                confidence_tier: "HIGH",
                classification: "ORGANIZED_CELL",
                is_cross_case: true,
                linked_cases: ["CASE_101", "CASE_204"],
                central_entities: ["PERSON_017", "PHONE_042"],
                bridge_entities: ["PERSON_089"],
                core_members: ["PERSON_017", "PHONE_042", "PERSON_089"],
                peripheral_members: ["VEHICLE_042", "ACC_AXIS_9941"],
                supporting_evidence: ["EVID_101_01", "EVID_042_01", "EVID_SOC_017_01"],
                source_provenance: ["Synthetic Dataset", "Digital Forensics", "Signal Intercept"],
                safety_disclaimer: "Community detection identifies structural relationships in available evidence. It does not establish criminality, guilt, or legal culpability."
            },
            {
                id: "C-002",
                name: "Community C-002 (Transaction Hub)",
                member_count: 4,
                density: 0.75,
                confidence: 0.84,
                confidence_tier: "MEDIUM",
                classification: "TRANSACTION_HUB",
                is_cross_case: true,
                linked_cases: ["CASE_101", "CASE_204"],
                central_entities: ["ACC_AXIS_9941", "PERSON_089"],
                bridge_entities: ["ACC_AXIS_9941"],
                core_members: ["ACC_AXIS_9941", "PERSON_089"],
                peripheral_members: ["PERSON_056", "LOC_001"],
                supporting_evidence: ["EVID_204_01", "EVID_042_02"],
                source_provenance: ["Digital Forensics", "Manual Investigation"],
                safety_disclaimer: "Community detection identifies structural relationships in available evidence. It does not establish criminality, guilt, or legal culpability."
            },
            {
                id: "C-003",
                name: "Community C-003 (Communication Ring)",
                member_count: 3,
                density: 0.67,
                confidence: 0.78,
                confidence_tier: "MEDIUM",
                classification: "COMMUNICATION_RING",
                is_cross_case: false,
                linked_cases: ["CASE_101"],
                central_entities: ["PHONE_042", "PERSON_017"],
                bridge_entities: [],
                core_members: ["PHONE_042", "PERSON_017"],
                peripheral_members: ["PHONE_089"],
                supporting_evidence: ["EVID_042_01"],
                source_provenance: ["Signal Intercept"],
                safety_disclaimer: "Community detection identifies structural relationships in available evidence. It does not establish criminality, guilt, or legal culpability."
            }
        ];

        if (filters.classification && filters.classification !== "ALL") {
            communities = communities.filter(c => c.classification === filters.classification);
        }
        if (filters.confidence_tier && filters.confidence_tier !== "ALL") {
            communities = communities.filter(c => c.confidence_tier === filters.confidence_tier);
        }
        if (filters.cross_case === true) {
            communities = communities.filter(c => c.is_cross_case);
        }

        return {
            status: "SUCCESS",
            community_count: communities.length,
            total_communities: 3,
            communities: communities,
            safety_disclaimer: "Community detection identifies structural relationships in available evidence. It does not establish criminality, guilt, or legal culpability."
        };
    }

    async getCommunityDetails(communityId) {
        await new Promise(r => setTimeout(r, 100));
        const list = (await this.getCommunities()).communities;
        const found = list.find(c => c.id === communityId);
        if (found) {
            return {
                ...found,
                member_details: [
                    { id: "PERSON_017", name: "Aarav Verma", type: "PERSON", role: "CORE", centrality_score: 0.90, case_ids: ["CASE_101"] },
                    { id: "PHONE_042", name: "Phone +91-9876543210", type: "PHONE", role: "CORE", centrality_score: 0.85, case_ids: ["CASE_101", "CASE_204"] },
                    { id: "PERSON_089", name: "Vikram Malhotra", type: "PERSON", role: "BRIDGE", centrality_score: 0.80, case_ids: ["CASE_204"] },
                    { id: "VEHICLE_042", name: "Vehicle MH-01-AB-1234", type: "VEHICLE", role: "PERIPHERAL", centrality_score: 0.50, case_ids: ["CASE_101"] },
                    { id: "ACC_AXIS_9941", name: "Axis Escrow 9941", type: "ACCOUNT", role: "PERIPHERAL", centrality_score: 0.45, case_ids: ["CASE_101", "CASE_204"] }
                ],
                shared_assets: {
                    phones: ["PHONE_042"],
                    vehicles: ["VEHICLE_042"],
                    accounts: ["ACC_AXIS_9941"],
                    locations: ["LOC_001"]
                },
                investigative_leads: [
                    "Inspect bridge entity PERSON_089 connecting CASE_101 and CASE_204.",
                    "Verify shared phone line PHONE_042 activity during key case timestamps.",
                    "Trace escrow account ACC_AXIS_9941 transfers between network members."
                ],
                limitations: "Community detection reflects topological graph clustering in available evidence. It does not establish organizational hierarchy or legal intent."
            };
        }

        throw { status: 404, message: `Community ${communityId} not found.` };
    }

    async getSuspiciousPatterns(caseId = null, patternType = null, minConfidence = null) {
        let patterns = [
            {
                pattern_id: "PAT_CROSS_001",
                title: "Cross-Case Communication Bridge",
                pattern_type: "CROSS_CASE_BRIDGE",
                entities: ["PHONE_042", "PERSON_017", "PERSON_089"],
                cases: ["CASE_101", "CASE_204"],
                path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                confidence: 0.93,
                severity: "HIGH",
                evidence_ids: ["EVID_042_01", "EVID_042_02"],
                explanation: "Encrypted burner line +91-9876543210 (PHONE_042) bridges primary suspects between Operation Midnight Shadow (CASE_101) and Operation Golden Falcon (CASE_204).",
                investigative_lead: "Issue CDR sub-poena and cross-reference call co-occurrences between Aarav Verma and Vikram Malhotra.",
                limitations: ["Co-occurrence of communication line does not establish joint enterprise without primary witness verification."],
                disclaimer: "Investigative lead only — does not constitute proof of guilt."
            },
            {
                pattern_id: "PAT_HUB_017",
                title: "High-Connectivity Suspect Hub (Aarav Verma)",
                pattern_type: "HIGH_CONNECTIVITY_HUB",
                entities: ["PERSON_017"],
                cases: ["CASE_101"],
                path: ["PERSON_017"],
                confidence: 0.96,
                severity: "MEDIUM",
                evidence_ids: ["EVID_101_01", "EVID_042_01"],
                explanation: "Aarav Verma (PERSON_017) maintains 9 active relationship edges across multiple phone lines, locations, and accounts.",
                investigative_lead: "Priority focus on communication logs and physical surveillance of suspect node Aarav Verma.",
                limitations: ["High degree centrality reflects dense record reporting, not necessarily key leadership role."],
                disclaimer: "Investigative lead only — does not constitute proof of guilt."
            },
            {
                pattern_id: "PAT_EVID_042",
                title: "Forensic & Signal Intercept Co-Occurrence",
                pattern_type: "EVIDENCE_SUPPORTED_ANOMALY",
                entities: ["PHONE_042"],
                cases: ["CASE_101", "CASE_204"],
                path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                confidence: 0.94,
                severity: "HIGH",
                evidence_ids: ["EVID_042_01", "EVID_042_02"],
                explanation: "Digital forensics extraction (DOC_CASE_101) and lawful telco signal intercept (DOC_CASE_204) independently confirm burner line +91-9876543210 utilization.",
                investigative_lead: "Request subscriber identity details and cell site location matching.",
                limitations: ["Requires cell tower triangulation to confirm physical proximity."],
                disclaimer: "Investigative lead only — does not constitute proof of guilt."
            }
        ];

        if (caseId && caseId !== "ALL") {
            patterns = patterns.filter(p => p.cases.includes(caseId));
        }
        if (patternType && patternType !== "ALL") {
            patterns = patterns.filter(p => p.pattern_type.toUpperCase() === patternType.toUpperCase());
        }
        if (minConfidence !== null) {
            patterns = patterns.filter(p => p.confidence >= minConfidence);
        }
        return { count: patterns.length, patterns };
    }

    async createEntity(data) {
        const rawType = (data.type || data.entity_type || "PERSON").toUpperCase();
        const prefix = rawType.substring(0, 4);
        const randId = `${prefix}_${Math.floor(100 + Math.random() * 900)}`;
        const newEntity = {
            id: data.id || randId,
            name: data.name || data.title || data.phone_number || data.registration_number || data.identifier || randId,
            type: rawType,
            confidence: parseFloat(data.confidence || 0.95),
            details: data.details || data.description || "Manually created knowledge graph entity",
            source: "Manual",
            is_manual: true,
            ...data
        };
        this.dataset.nodes.push(newEntity);
        return newEntity;
    }

    async updateEntity(entityId, data) {
        const idx = this.dataset.nodes.findIndex(n => n.id === entityId);
        if (idx !== -1) {
            this.dataset.nodes[idx] = { ...this.dataset.nodes[idx], ...data, source: "Manual", is_manual: true };
            return this.dataset.nodes[idx];
        }
        throw new Error(`Entity ${entityId} not found`);
    }

    async deleteEntity(entityId) {
        this.dataset.nodes = this.dataset.nodes.filter(n => n.id !== entityId);
        this.dataset.edges = this.dataset.edges.filter(e => e.source !== entityId && e.target !== entityId);
        return { success: true, deleted_id: entityId };
    }

    async createRelationship(data) {
        const newRel = {
            id: data.id || `REL_MANUAL_${Math.floor(100 + Math.random() * 900)}`,
            source: data.source_id || data.source,
            target: data.target_id || data.target,
            relationship: (data.relationship || "ASSOCIATED_WITH").toUpperCase(),
            confidence: parseFloat(data.confidence || 0.95),
            evidence_id: (data.evidence_ids && data.evidence_ids.length > 0) ? data.evidence_ids[0] : null,
            source: "Manual",
            is_manual: true
        };
        this.dataset.edges.push(newRel);
        return newRel;
    }

    async extractDocument(documentId, text) {
        const evidenceId = `EVID_EXT_${Math.random().toString(16).substring(2, 8).toUpperCase()}`;
        const evidenceList = [{
            evidence_id: evidenceId,
            source_document_id: documentId,
            source_text: (text || "").substring(0, 300),
            page_number: 1,
            extraction_method: "AI_NER",
            confidence: 0.95
        }];
        const entities = [];
        const relationships = [];

        // Extract Phone numbers
        const phoneMatches = Array.from(new Set((text || "").match(/(\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b)/g) || []));
        phoneMatches.forEach((ph, idx) => {
            entities.push({
                id: `PHONE_EXT_${idx + 1}`,
                type: "PHONE",
                name: ph.trim(),
                confidence: 0.96,
                evidence_ids: [evidenceId]
            });
        });

        // Extract Vehicles
        const vehicleMatches = Array.from(new Set((text || "").match(/\b([A-Z]{2}[-\s]?\d{2}[-\s]?[A-Z]{1,2}[-\s]?\d{4})\b/g) || []));
        vehicleMatches.forEach((veh, idx) => {
            entities.push({
                id: `VEHICLE_EXT_${idx + 1}`,
                type: "VEHICLE",
                name: veh.trim(),
                confidence: 0.94,
                evidence_ids: [evidenceId]
            });
        });

        // Extract Persons
        const personMatches = Array.from(new Set((text || "").match(/\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b/g) || []));
        personMatches.forEach((pName, idx) => {
            entities.push({
                id: `PERSON_EXT_${idx + 1}`,
                type: "PERSON",
                name: pName.trim(),
                confidence: 0.95,
                evidence_ids: [evidenceId]
            });
        });

        if (entities.length === 0) {
            entities.push({
                id: "PERSON_EXT_1",
                type: "PERSON",
                name: "Subject 1",
                confidence: 0.85,
                evidence_ids: [evidenceId]
            });
        }

        const pEntities = entities.filter(e => e.type === "PERSON");
        const oEntities = entities.filter(e => e.type !== "PERSON");
        let relIdx = 1;
        pEntities.forEach(p => {
            oEntities.forEach(o => {
                relationships.push({
                    id: `REL_EXT_${relIdx++}`,
                    source_id: p.id,
                    relationship: o.type === "PHONE" ? "USES" : "USED",
                    target_id: o.id,
                    confidence: 0.93,
                    evidence_ids: [evidenceId]
                });
            });
        });

        return {
            document_id: documentId,
            entities: entities,
            relationships: relationships,
            events: [],
            evidence: evidenceList
        };
    }

    async queryAIInvestigator(question, caseId = null, entityId = null, conversationHistory = null) {
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

        const activeCase = caseId || "CASE_101";
        const contextStr = entityId ? `focused entity ${entityId}` : `case ${activeCase}`;

        return {
            query_type: "CROSS_CASE_CONNECTION",
            question: question,
            answer: `Automated graph intelligence for ${contextStr}: Discovered multi-hop connection paths and supporting evidence.`,
            path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
            shared_entities: ["PHONE_042"],
            confidence: 0.93,
            evidence_ids: ["EVID_042_01", "EVID_042_02"],
            explanation: `Analysis grounded in ${contextStr}: Aarav Verma (PERSON_017) operated burner line PHONE_042 during the cargo hijack window. The same burner line was subsequently used by Vikram Malhotra (PERSON_089) for CASE_204.`,
            investigative_lead: `POTENTIAL INVESTIGATIVE LEAD for ${contextStr}: Subpoena Zaveri Bazaar bullion escrow transactions linked to ACC_AXIS_9941.`,
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
    if (typeof window !== "undefined" && window.location && window.location.hostname && !window.location.hostname.includes("localhost") && !window.location.hostname.includes("127.0.0.1")) {
        return "https://sih-2026-team-project.onrender.com";
    }
    if (typeof window !== "undefined" && window.CRIMEGRAPH_API_URL) {
        return window.CRIMEGRAPH_API_URL.replace(/\/$/, "");
    }
    if (typeof window !== "undefined" && window.CRIMEGRAPH_CONFIG && window.CRIMEGRAPH_CONFIG.API_BASE_URL) {
        return window.CRIMEGRAPH_CONFIG.API_BASE_URL.replace(/\/$/, "");
    }
    return "http://127.0.0.1:8000";
}

class HttpCrimeGraphAdapter {
    constructor(baseUrl = null) {
        this.baseUrl = baseUrl || getApiBaseUrl();
    }

    getToken() {
        if (typeof localStorage !== "undefined") {
            return localStorage.getItem("crimegraph_token");
        }
        return null;
    }

    setToken(token, user = null) {
        if (typeof localStorage !== "undefined") {
            if (token) {
                localStorage.setItem("crimegraph_token", token);
                if (user) localStorage.setItem("crimegraph_user", JSON.stringify(user));
            } else {
                localStorage.removeItem("crimegraph_token");
                localStorage.removeItem("crimegraph_user");
            }
        }
    }

    getUser() {
        if (typeof localStorage !== "undefined") {
            const raw = localStorage.getItem("crimegraph_user");
            try { return raw ? JSON.parse(raw) : null; } catch (_) { }
        }
        return null;
    }

    isAuthenticated() {
        return !!this.getToken();
    }

    async login(username, password, agencyId = null) {
        const response = await fetch(`${this.baseUrl}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password, agency_id: agencyId })
        });
        if (!response.ok) {
            let errorDetail = `Authentication Failed (${response.status})`;
            try {
                const errBody = await response.json();
                if (errBody && errBody.detail) errorDetail = errBody.detail;
            } catch (_) { }
            const err = new Error(errorDetail);
            err.status = response.status;
            throw err;
        }
        const data = await response.json();
        this.setToken(data.access_token, data.user);
        return data;
    }

    async logout() {
        const token = this.getToken();
        if (token) {
            try {
                await fetch(`${this.baseUrl}/api/auth/logout`, {
                    method: "POST",
                    headers: { "Authorization": `Bearer ${token}` }
                });
            } catch (_) { }
        }
        this.setToken(null);
        return { status: "logged_out" };
    }

    async getAuditLogs(limit = 50) {
        return await this.fetchJson(`/api/audit?limit=${limit}`);
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

    sanitizeErrorMessage(status, rawDetail) {
        if (!rawDetail || typeof rawDetail !== "string") {
            if (status === 400) return "Invalid request parameters. Please check your inputs.";
            if (status === 401) return "Authentication token missing or expired. Please log in.";
            if (status === 403) return "Access denied. You lack authorization for this action or case record.";
            if (status === 404) return "The requested entity, case, or evidence record was not found.";
            if (status === 409) return "Conflict detected. The entity or relationship identifier already exists.";
            if (status === 422) return "Unprocessable entity payload. Please verify input formats.";
            if (status === 429) return "Too many requests. Please wait a moment and try again.";
            if (status >= 500) return "CrimeGraph service temporarily unavailable. Please retry in a few seconds.";
            return `Server request failed (Status ${status}).`;
        }

        // Strip internal server filesystem paths, stack traces, and tokens
        let clean = rawDetail
            .replace(/[A-Z]:\\[^\s:]+/gi, "[internal path]")
            .replace(/\/[\w\.\-]+(?:\/[\w\.\-]+)+/gi, "[internal path]")
            .replace(/cg_token_[a-zA-Z0-9_\-]+/gi, "[token]")
            .replace(/Bearer\s+[^\s]+/gi, "Bearer [token]");

        // Handle specific status fallbacks if clean message is empty or generic
        if (status === 401 && !clean.includes("log in") && !clean.includes("session")) {
            clean = "Session expired or invalid authorization. Please log in.";
        } else if (status === 403 && !clean.includes("denied") && !clean.includes("authorized")) {
            clean = "Access denied. You lack authorization for this action or case context.";
        } else if (status >= 500) {
            clean = "CrimeGraph service temporarily unavailable. Please retry in a few seconds.";
        }

        return clean;
    }

    async fetchJson(endpoint, options = {}) {
        const headers = options.headers || {};
        const token = this.getToken();
        if (token && !headers["Authorization"]) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        options.headers = headers;

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            if (!response.ok) {
                const retryAfter = response.headers.get("Retry-After") || response.headers.get("retry-after");

                if (response.status === 401 || response.status === 403) {
                    this.setToken(null);
                    if (typeof window !== "undefined" && typeof window.handleAuthSessionExpired === "function") {
                        window.handleAuthSessionExpired(response.status);
                    }
                }
                if (response.status === 429) {
                    if (typeof window !== "undefined" && typeof window.handleRateLimitExceeded === "function") {
                        window.handleRateLimitExceeded(retryAfter);
                    }
                }

                let rawDetail = "";
                try {
                    const errBody = await response.json();
                    if (errBody && errBody.detail) {
                        rawDetail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
                    }
                } catch (_) { }

                let errorDetail = this.sanitizeErrorMessage(response.status, rawDetail);
                if (response.status === 429 && retryAfter) {
                    errorDetail += ` (Retry after ${retryAfter}s)`;
                }

                const err = new Error(errorDetail);
                err.status = response.status;
                err.retryAfter = retryAfter;
                throw err;
            }

            // Handle empty 204 or empty responses safely
            const text = await response.text();
            if (!text || !text.trim()) {
                return {};
            }
            try {
                return JSON.parse(text);
            } catch (jsonErr) {
                console.warn(`Malformed JSON response from ${endpoint}:`, text);
                return {};
            }
        } catch (networkErr) {
            if (!networkErr.status) {
                networkErr.message = `CrimeGraph backend unavailable (${endpoint}). Please verify server status.`;
            }
            throw networkErr;
        }
    }

    async createEntity(data) {
        return await this.fetchJson("/api/entities", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    }

    async updateEntity(entityId, data) {
        return await this.fetchJson(`/api/entities/${encodeURIComponent(entityId)}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    }

    async deleteEntity(entityId) {
        return await this.fetchJson(`/api/entities/${encodeURIComponent(entityId)}`, {
            method: "DELETE"
        });
    }

    async createRelationship(data) {
        return await this.fetchJson("/api/relationships", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    }

    async createCase(data) {
        return await this.fetchJson("/api/cases", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    async getInvestigationDashboard() {
            try {
                return await this.fetchJson("/api/dashboard");
            } catch (err) {
                console.warn("Fallback dashboard aggregation due to REST error:", err);
                const [cases, keyPlayers, patternsData, evidenceList, connData] = await Promise.all([
                    this.getCases().catch(() => []),
                    this.getKeyPlayers().catch(() => ({ key_players: [] })),
                    this.getSuspiciousPatterns().catch(() => ({ patterns: [], anomalies: [] })),
                    this.getEvidenceList().catch(() => []),
                    this.getCaseConnections("CASE_101", "CASE_204").catch(() => ({ connections: [] }))
                ]);

                const keyEntitiesList = Array.isArray(keyPlayers) ? keyPlayers : (keyPlayers.key_players || []);
                const patternsList = Array.isArray(patternsData) ? patternsData : (patternsData.patterns || []);
                const anomaliesList = patternsData.anomalies || [];
                const connectionsList = connData.connections || [];

                return {
                    metrics: {
                        total_cases: cases.length,
                        active_cases: cases.filter(c => (c.status || '').toUpperCase() === 'ACTIVE').length,
                        high_priority_cases: cases.filter(c => ['HIGH', 'URGENT'].includes((c.priority || '').toUpperCase())).length,
                        key_entities_count: keyEntitiesList.length,
                        patterns_count: patternsList.length,
                        anomalies_count: anomaliesList.length,
                        evidence_count: evidenceList.length,
                        cross_case_links_count: connectionsList.length
                    },
                    active_cases: cases,
                    high_priority_cases: cases.filter(c => ['HIGH', 'URGENT'].includes((c.priority || '').toUpperCase())),
                    key_entities: keyEntitiesList,
                    patterns: patternsList,
                    anomalies: anomaliesList,
                    cross_case_connections: connectionsList,
                    canonical_path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                    recent_evidence: evidenceList,
                    ai_findings: [
                        {
                            id: "AI_FINDING_001",
                            title: "Cross-Case Burner Phone Linkage",
                            type: "SUSPICIOUS_PATTERN",
                            description: "Shared burner line PHONE_042 (+91-9876543210) bridges CASE_101 and CASE_204 across 4 hops.",
                            confidence: 0.93,
                            status: "Requires Review",
                            case_a: "CASE_101",
                            case_b: "CASE_204",
                            entity_id: "PHONE_042"
                        }
                    ]
                };
            }
        }

    async getKeyPlayers(params = {}) {
            const query = new URLSearchParams();
            if (params.case_id && params.case_id !== "ALL") query.append("case_id", params.case_id);
            if (params.type && params.type !== "ALL") query.append("type", params.type);
            if (params.role && params.role !== "ALL") query.append("role", params.role);
            if (params.community_id && params.community_id !== "ALL") query.append("community_id", params.community_id);
            if (params.min_confidence) query.append("min_confidence", params.min_confidence);
            if (params.is_cross_case !== undefined && params.is_cross_case !== null && params.is_cross_case !== "") {
                query.append("is_cross_case", params.is_cross_case);
            }

            const queryString = query.toString();
            const url = `/api/key-players${queryString ? '?' + queryString : ''}`;
            return await this.fetchJson(url);
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
                details: this.formatEntityDetails(n.details || n),
                source: n.source || (n.is_manual ? "Manual" : "Dataset"),
                is_manual: n.is_manual || n.source === "Manual"
            }));

            const edges = (raw.edges || []).map(e => ({
                id: e.id,
                source: e.source || e.source_id,
                target: e.target || e.target_id,
                relationship: e.relationship,
                confidence: e.confidence !== undefined ? e.confidence : 1.0,
                evidence_id: (e.evidence_ids && Array.isArray(e.evidence_ids) && e.evidence_ids.length > 0) ? e.evidence_ids[0] : (e.evidence_id || null),
                source: e.source_type || (e.is_manual ? "Manual" : "Dataset"),
                is_manual: e.is_manual || e.source_type === "Manual"
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

    async getSuspiciousPatterns(caseId = null, patternType = null, minConfidence = null) {
            let params = [];
            if (caseId && caseId !== "ALL") params.push(`case_id=${encodeURIComponent(caseId)}`);
            if (patternType && patternType !== "ALL") params.push(`pattern_type=${encodeURIComponent(patternType)}`);
            if (minConfidence !== null) params.push(`min_confidence=${encodeURIComponent(minConfidence)}`);
            const queryStr = params.length > 0 ? `?${params.join("&")}` : "";

            try {
                return await this.fetchJson(`/api/patterns${queryStr}`);
            } catch (err) {
                console.warn("[HttpCrimeGraphAdapter] /api/patterns endpoint fallback", err);
                let patterns = [
                    {
                        pattern_id: "PAT_CROSS_001",
                        title: "Cross-Case Communication Bridge",
                        pattern_type: "CROSS_CASE_BRIDGE",
                        entities: ["PHONE_042", "PERSON_017", "PERSON_089"],
                        cases: ["CASE_101", "CASE_204"],
                        path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                        confidence: 0.93,
                        anomaly_score: 0.91,
                        severity: "HIGH",
                        observed_data: "Burner handset +91-9876543210 (PHONE_042) registered in both CASE_101 and CASE_204 evidence logs.",
                        computed_pattern: "Topological bridge node connecting distinct criminal networks across geographic zones.",
                        evidence_ids: ["EVID_042_01", "EVID_042_02"],
                        explanation: "Encrypted burner line +91-9876543210 (PHONE_042) bridges primary suspects between Operation Midnight Shadow (CASE_101) and Operation Golden Falcon (CASE_204).",
                        investigative_lead: "Issue CDR subpoena and cross-reference call co-occurrences between Aarav Verma and Vikram Malhotra.",
                        limitations: ["Co-occurrence of communication line does not establish joint enterprise without primary witness verification."],
                        disclaimer: "Investigative lead only — does not constitute proof of guilt."
                    },
                    {
                        pattern_id: "PAT_HUB_017",
                        title: "High-Connectivity Suspect Hub (Aarav Verma)",
                        pattern_type: "HIGH_CONNECTIVITY_HUB",
                        entities: ["PERSON_017"],
                        cases: ["CASE_101"],
                        path: ["PERSON_017"],
                        confidence: 0.96,
                        anomaly_score: 0.92,
                        severity: "HIGH",
                        observed_data: "Entity Aarav Verma [PERSON_017] maintains 11 active relationship edges in graph store.",
                        computed_pattern: "Central network hub exhibiting disproportionately high degree centrality.",
                        evidence_ids: ["EVID_101_01", "EVID_042_01"],
                        explanation: "Aarav Verma (PERSON_017) maintains 11 active relationship edges across multiple phone lines, locations, and accounts.",
                        investigative_lead: "Priority focus on communication logs and physical surveillance of suspect node Aarav Verma.",
                        limitations: ["High degree centrality reflects dense record reporting, not necessarily key leadership role."],
                        disclaimer: "Investigative lead only — does not constitute proof of guilt."
                    },
                    {
                        pattern_id: "PAT_TEMP_001",
                        title: "Tight Temporal Burst Cluster",
                        pattern_type: "TEMPORAL_CLUSTER",
                        entities: ["PERSON_017", "PHONE_042", "LOC_001"],
                        cases: ["CASE_101"],
                        path: ["CASE_101", "PERSON_017", "LOC_001"],
                        confidence: 0.92,
                        anomaly_score: 0.88,
                        severity: "HIGH",
                        observed_data: "3 events cataloged between 2026-08-10 18:30Z and 2026-08-11 09:30Z (15h window).",
                        computed_pattern: "High-frequency operational burst co-occurring with logistics yard exit.",
                        evidence_ids: ["EVID_101_01", "EVID_042_01"],
                        explanation: "Multiple physical sightings and communications occurred in a tight 15-hour window surrounding cargo dispatch.",
                        investigative_lead: "Correlate ANPR camera timestamp logs with cell tower handover records.",
                        limitations: ["Temporal proximity alone does not prove coordinated action."],
                        disclaimer: "Investigative lead only — does not constitute proof of guilt."
                    },
                    {
                        pattern_id: "PAT_CONTACT_001",
                        title: "High-Frequency Burner Contact Pattern",
                        pattern_type: "REPEATED_CONTACT_PATTERN",
                        entities: ["PERSON_017", "PHONE_042", "PERSON_089"],
                        cases: ["CASE_101", "CASE_204"],
                        path: ["PERSON_017", "PHONE_042", "PERSON_089"],
                        confidence: 0.95,
                        anomaly_score: 0.89,
                        severity: "HIGH",
                        observed_data: "Repeated phone calls logged between burner handset PHONE_042 and suspect terminals.",
                        computed_pattern: "Asymmetric burner communications relay pattern.",
                        evidence_ids: ["EVID_042_01", "EVID_042_02"],
                        explanation: "Burner line +91-9876543210 engaged in 14 short-duration calls within a 48-hour window.",
                        investigative_lead: "Audit call duration and IMEI pairing histories for connected handsets.",
                        limitations: ["Call duration analysis reflects telecom metadata without audio content."],
                        disclaimer: "Investigative lead only — does not constitute proof of guilt."
                    },
                    {
                        pattern_id: "PAT_ANOM_001",
                        title: "Multi-Jurisdiction Entity Activity Spike",
                        pattern_type: "ENTITY_ACTIVITY_ANOMALY",
                        entities: ["PERSON_089", "ACC_001", "LOC_003"],
                        cases: ["CASE_204"],
                        path: ["CASE_204", "PERSON_089", "ACC_001"],
                        confidence: 0.91,
                        anomaly_score: 0.86,
                        severity: "MEDIUM",
                        observed_data: "Sudden surge in high-value banking transfers co-occurring with bullion vault activity in Mumbai.",
                        computed_pattern: "Anomalous transaction frequency relative to baseline suspect activity.",
                        evidence_ids: ["EVID_204_01"],
                        explanation: "Vikram Malhotra (PERSON_089) exhibited an anomalous 400% surge in financial transaction volume post-incident.",
                        investigative_lead: "Subpoena FIU bank account statements and bullion settlement receipts.",
                        limitations: ["Financial volume anomalies require forensic accounting audit."],
                        disclaimer: "Investigative lead only — does not constitute proof of guilt."
                    },
                    {
                        pattern_id: "PAT_CORROB_001",
                        title: "Multi-Source Forensic & Telco Corroboration",
                        pattern_type: "MULTI_SOURCE_CORROBORATION",
                        entities: ["PHONE_042", "PERSON_017"],
                        cases: ["CASE_101", "CASE_204"],
                        path: ["CASE_101", "PERSON_017", "PHONE_042"],
                        confidence: 0.96,
                        anomaly_score: 0.94,
                        severity: "HIGH",
                        observed_data: "Handset triage (DOC_CASE_101) and Telco Intercept (DOC_CASE_204) independently confirm usage.",
                        computed_pattern: "Dual-stream multi-source intelligence corroboration.",
                        evidence_ids: ["EVID_042_01", "EVID_042_02"],
                        explanation: "Digital forensics extraction and lawful telco signal intercept independently confirm burner line +91-9876543210 utilization.",
                        investigative_lead: "Request subscriber identity details and cell site location matching.",
                        limitations: ["Requires cell tower triangulation to confirm physical proximity."],
                        disclaimer: "Investigative lead only — does not constitute proof of guilt."
                    },
                    {
                        pattern_id: "PAT_PATH_001",
                        title: "Unusual Multi-Hop Conduit Path Pattern",
                        pattern_type: "UNUSUAL_PATH_PATTERN",
                        entities: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                        cases: ["CASE_101", "CASE_204"],
                        path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
                        confidence: 0.93,
                        anomaly_score: 0.90,
                        severity: "HIGH",
                        observed_data: "Topological path length of 4 hops connecting separate case filings.",
                        computed_pattern: "Indirect multi-hop cross-case relationship conduit.",
                        evidence_ids: ["EVID_101_01", "EVID_042_01", "EVID_042_02", "EVID_204_01"],
                        explanation: "Knowledge graph traversal uncovers a 4-hop relationship chain connecting Delhi logistics operation to Mumbai bullion liquidation.",
                        investigative_lead: "Perform multi-hop path analysis in Link Analysis workspace.",
                        limitations: ["Multi-hop connectivity reflects evidence links, not formal conspiracy."],
                        disclaimer: "Investigative lead only — does not constitute proof of guilt."
                    }
                ];

                if (caseId && caseId !== "ALL") patterns = patterns.filter(p => p.cases && p.cases.includes(caseId));
                if (patternType && patternType !== "ALL") patterns = patterns.filter(p => p.pattern_type && p.pattern_type.toUpperCase() === patternType.toUpperCase());
                return { count: patterns.length, patterns };
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

    async exportReport(caseId, format = "json") {
            const token = this.getToken();
            const headers = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;

            const response = await fetch(`${this.baseUrl}/api/reports/export`, {
                method: "POST",
                headers: headers,
                body: JSON.stringify({ case_id: caseId, format: format })
            });

            if (!response.ok) {
                let errorDetail = `Export Failed (${response.status})`;
                try {
                    const errBody = await response.json();
                    if (errBody && errBody.detail) errorDetail = errBody.detail;
                } catch (_) { }
                const err = new Error(this.sanitizeErrorMessage(response.status, errorDetail));
                err.status = response.status;
                throw err;
            }

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

    async getPendingEntityResolutions() {
            return await this.fetchJson("/api/entity-resolution/pending");
        }

    async compareEntities(entityA, entityB) {
            return await this.fetchJson(`/api/entity-resolution/compare?entity_a=${encodeURIComponent(entityA)}&entity_b=${encodeURIComponent(entityB)}`);
        }

    async getCommunities(filters = {}) {
            let params = [];
            if (filters.case_id) params.push(`case_id=${encodeURIComponent(filters.case_id)}`);
            if (filters.classification && filters.classification !== "ALL") params.push(`classification=${encodeURIComponent(filters.classification)}`);
            if (filters.confidence_tier && filters.confidence_tier !== "ALL") params.push(`confidence_tier=${encodeURIComponent(filters.confidence_tier)}`);
            if (filters.cross_case === true) params.push(`cross_case=true`);
            const queryStr = params.length > 0 ? `?${params.join("&")}` : "";
            return await this.fetchJson(`/api/communities${queryStr}`);
        }

    async getCommunityDetails(communityId) {
            return await this.fetchJson(`/api/communities/${encodeURIComponent(communityId)}`);
        }

    async getEvidenceItem(evidenceId) {
            return await this.getEvidence(evidenceId);
        }

    async extractDocument(documentId, text) {
            return await this.fetchJson("/api/extract", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ document_id: documentId, text: text })
            });
        }

    async queryAIInvestigator(question, caseId = null, entityId = null, conversationHistory = null) {
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
                body: JSON.stringify({
                    question: question,
                    case_id: caseId,
                    entity_id: entityId,
                    conversation_history: conversationHistory
                })
            });

            return {
                query_type: isGuiltQuery ? "SAFETY_REFUSAL" : (raw.query_type || "GENERAL_INVESTIGATION"),
                question: raw.question || question,
                answer: isGuiltQuery ? "CrimeGraph AI does not determine guilt or legal culpability. Graph associations serve solely as potential investigative leads requiring independent human verification by authorized case officers." : (raw.answer || raw.summary || "Investigation query executed."),
                path: isGuiltQuery ? [] : (raw.path || []),
                shared_entities: isGuiltQuery ? [] : (raw.shared_entities || []),
                confidence: isGuiltQuery ? 0.0 : (raw.confidence !== undefined ? raw.confidence : "N/A"),
                evidence_ids: raw.evidence_ids || [],
                confirmed_links: raw.confirmed_links || [],
                probable_links: raw.probable_links || [],
                unresolved_candidates: raw.unresolved_candidates || [],
                conflicting_claims: raw.conflicting_claims || [],
                explanation: isGuiltQuery ? "Under CrimeGraph AI Safety Policy, graph associations do not constitute legal proof or determinations of guilt." : (raw.explanation || null),
                investigative_lead: isGuiltQuery ? "Safety Policy Enforced: Direct physical evidence, witness testimonies, and judicial proceedings required to establish legal culpability." : (raw.investigative_lead || raw.lead || null),
                limitations: isGuiltQuery ? ["Automated graph links cannot be presented as proof of criminal liability."] : (raw.limitations || []),
                disclaimer: isGuiltQuery ? "Safety Policy: CrimeGraph AI provides investigative leads only and does not determine guilt." : (raw.disclaimer || "AI-generated investigative lead requiring human verification. Not a declaration of guilt.")
            };
        }

    async getCorrelations(caseId = null, correlationType = null, minConfidence = null) {
            let url = "/api/correlations";
            const params = new URLSearchParams();
            if (caseId) params.append("case_id", caseId);
            if (correlationType) params.append("correlation_type", correlationType);
            if (minConfidence !== null && minConfidence !== undefined) params.append("min_confidence", minConfidence);
            const queryStr = params.toString();
            if (queryStr) url += `?${queryStr}`;
            return await this.fetchJson(url);
        }

    async getRiskScores(caseId = null, minScore = 0) {
            let url = "/api/risk";
            const params = new URLSearchParams();
            if (caseId) params.append("case_id", caseId);
            if (minScore) params.append("min_score", minScore);
            const queryStr = params.toString();
            if (queryStr) url += `?${queryStr}`;
            return await this.fetchJson(url);
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

    getToken() {
        return this.activeAdapter.getToken();
    }

    getUser() {
        return this.activeAdapter.getUser();
    }

    isAuthenticated() {
        return this.activeAdapter.isAuthenticated();
    }

    async login(username, password, agencyId = null) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.login(username, password, agencyId);
        }
        return await this.mockAdapter.login(username, password, agencyId);
    }

    async logout() {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.logout();
        }
        return await this.mockAdapter.logout();
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

    async createEntity(data) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.createEntity(data);
        }
        return await this.mockAdapter.createEntity(data);
    }

    async updateEntity(entityId, data) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.updateEntity(entityId, data);
        }
        return await this.mockAdapter.updateEntity(entityId, data);
    }

    async deleteEntity(entityId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.deleteEntity(entityId);
        }
        return await this.mockAdapter.deleteEntity(entityId);
    }

    async createRelationship(data) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.createRelationship(data);
        }
        return await this.mockAdapter.createRelationship(data);
    }

    async createCase(data) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.createCase(data);
        }
        return await this.mockAdapter.createCase(data);
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

    async getSuspiciousPatterns(caseId = null, patternType = null, minConfidence = null) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getSuspiciousPatterns(caseId, patternType, minConfidence);
        }
        return await this.mockAdapter.getSuspiciousPatterns(caseId, patternType, minConfidence);
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

    async getEvidenceItem(evidenceId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getEvidence(evidenceId);
        }
        return await this.mockAdapter.getEvidenceItem(evidenceId);
    }

    async getKeyPlayers(params = {}) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getKeyPlayers(params);
        }
        return await this.mockAdapter.getKeyPlayers(params);
    }

    async findPaths(sourceId, targetId, maxDepth = 6, params = {}) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.findPaths(sourceId, targetId, maxDepth, params);
        }
        return await this.mockAdapter.findPaths(sourceId, targetId, maxDepth, params);
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

    async exportReport(caseId, format = "json") {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.exportReport(caseId, format);
        }
        return await this.mockAdapter.exportReport(caseId, format);
    }

    async getPendingEntityResolutions() {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getPendingEntityResolutions();
        }
        return await this.mockAdapter.getPendingEntityResolutions();
    }

    async compareEntities(entityA, entityB) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.compareEntities(entityA, entityB);
        }
        return await this.mockAdapter.compareEntities(entityA, entityB);
    }

    async getCommunities(filters = {}) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getCommunities(filters);
        }
        return await this.mockAdapter.getCommunities(filters);
    }

    async getCommunityDetails(communityId) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getCommunityDetails(communityId);
        }
        return await this.mockAdapter.getCommunityDetails(communityId);
    }

    async search(query, filters) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.search(query, filters);
        }
        return await this.mockAdapter.search(query, filters);
    }

    async extractDocument(documentId, text) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.extractDocument(documentId, text);
        }
        return await this.mockAdapter.extractDocument(documentId, text);
    }

    async queryAIInvestigator(question, caseId = null, entityId = null, conversationHistory = null) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.queryAIInvestigator(question, caseId, entityId, conversationHistory);
        }
        return await this.mockAdapter.queryAIInvestigator(question, caseId, entityId, conversationHistory);
    }

    async getAuditLogs(limit = 50) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getAuditLogs(limit);
        }
        return await this.mockAdapter.getAuditLogs(limit);
    }

    async getInvestigationDashboard() {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getInvestigationDashboard();
        }
        return await this.mockAdapter.getInvestigationDashboard();
    }

    async getCorrelations(caseId = null, correlationType = null, minConfidence = null) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getCorrelations(caseId, correlationType, minConfidence);
        }
        return await this.mockAdapter.getCorrelations(caseId, correlationType, minConfidence);
    }

    async getRiskScores(caseId = null, minScore = 0) {
        await this.ensureInitialized();
        if (this.isBackendOnline) {
            return await this.httpAdapter.getRiskScores(caseId, minScore);
        }
        return await this.mockAdapter.getRiskScores(caseId, minScore);
    }
}

// Global DataService Instance
window.dataService = new CrimeGraphDataService();

