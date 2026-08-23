/**
 * CrimeGraph AI — Frontend Application Logic
 * Day 1 Foundation (Shruti — Frontend, Data & Integration Lead)
 * Strictly compatible with DATA_SCHEMA.md and API_CONTRACT.md
 */

let networkInstance = null;
let currentGraphNodes = [];
let currentGraphEdges = [];

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initCaseExplorer();
    initGraphWorkspace();
    initAIInvestigator();
    initTimeline();
    initEvidenceExplorer();
});

/* ----------------------------------------------------
   1. NAVIGATION & TAB ROUTING
---------------------------------------------------- */
function initNavigation() {
    const navButtons = document.querySelectorAll(".nav-item");
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetPane = btn.getAttribute("data-tab");
            switchTab(targetPane);
        });
    });

    const headerCaseSelect = document.getElementById("header-case-select");
    if (headerCaseSelect) {
        headerCaseSelect.addEventListener("change", (e) => {
            renderGraph(e.target.value);
        });
    }
}

function switchTab(paneId) {
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    const activeBtn = document.querySelector(`.nav-item[data-tab="${paneId}"]`);
    if (activeBtn) activeBtn.classList.add("active");

    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.add("hidden");
        pane.classList.remove("active");
    });

    const target = document.getElementById(paneId);
    if (target) {
        target.classList.remove("hidden");
        target.classList.add("active");
    }

    if (paneId === "pane-graph" && networkInstance) {
        setTimeout(() => networkInstance.fit(), 100);
    }
}

/* ----------------------------------------------------
   2. SYNTHETIC GRAPH DATA (DATA_SCHEMA.md Compatible)
---------------------------------------------------- */
const SYNTHETIC_GRAPH_DATA = {
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
        }
    }
};

/* ----------------------------------------------------
   3. NETWORK GRAPH WORKSPACE & VIS.JS ENGINE
---------------------------------------------------- */
function initGraphWorkspace() {
    renderGraph("CASE_101");

    // Controls
    document.getElementById("graph-zoom-in")?.addEventListener("click", () => {
        if (networkInstance) {
            const scale = networkInstance.getScale();
            networkInstance.moveTo({ scale: scale * 1.25 });
        }
    });

    document.getElementById("graph-zoom-out")?.addEventListener("click", () => {
        if (networkInstance) {
            const scale = networkInstance.getScale();
            networkInstance.moveTo({ scale: scale * 0.8 });
        }
    });

    document.getElementById("graph-reset")?.addEventListener("click", () => {
        if (networkInstance) networkInstance.fit();
    });

    document.getElementById("graph-highlight-path")?.addEventListener("click", highlightDemoPath);
}

function renderGraph(caseId = "CASE_101") {
    const container = document.getElementById("graph-canvas");
    if (!container) return;

    let filteredNodes = SYNTHETIC_GRAPH_DATA.nodes;
    let filteredEdges = SYNTHETIC_GRAPH_DATA.edges;

    if (caseId !== "ALL") {
        // Find connected node IDs
        const connectedNodeIds = new Set([caseId]);
        SYNTHETIC_GRAPH_DATA.edges.forEach(e => {
            if (e.source === caseId || e.target === caseId) {
                connectedNodeIds.add(e.source);
                connectedNodeIds.add(e.target);
            }
        });

        // 2nd degree
        SYNTHETIC_GRAPH_DATA.edges.forEach(e => {
            if (connectedNodeIds.has(e.source) || connectedNodeIds.has(e.target)) {
                connectedNodeIds.add(e.source);
                connectedNodeIds.add(e.target);
            }
        });

        filteredNodes = SYNTHETIC_GRAPH_DATA.nodes.filter(n => connectedNodeIds.has(n.id));
        filteredEdges = SYNTHETIC_GRAPH_DATA.edges.filter(e => connectedNodeIds.has(e.source) && connectedNodeIds.has(e.target));
    }

    const nodeColors = {
        "PERSON": { background: "#3b82f6", border: "#1d4ed8" },
        "PHONE": { background: "#10b981", border: "#047857" },
        "VEHICLE": { background: "#f59e0b", border: "#b45309" },
        "LOCATION": { background: "#8b5cf6", border: "#6d28d9" },
        "CASE": { background: "#ef4444", border: "#b91c1c" },
        "ACCOUNT": { background: "#06b6d4", border: "#0e7490" }
    };

    const visNodes = filteredNodes.map(n => ({
        id: n.id,
        label: `${n.name}\n[${n.id}]`,
        shape: n.type === "CASE" ? "diamond" : "box",
        color: nodeColors[n.type] || { background: "#64748b", border: "#334155" },
        font: { color: "#ffffff", size: 11, face: "Inter" },
        margin: 8,
        nodeObj: n
    }));

    const visEdges = filteredEdges.map(e => ({
        id: e.id,
        from: e.source,
        to: e.target,
        label: e.relationship,
        font: { color: "#8c90a1", size: 9, align: "horizontal" },
        color: { color: "#424656", highlight: "#b3c5ff" },
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        edgeObj: e
    }));

    const data = {
        nodes: new vis.DataSet(visNodes),
        edges: new vis.DataSet(visEdges)
    };

    const options = {
        nodes: { borderWidth: 2, shadow: true },
        edges: { smooth: { type: "continuous" } },
        physics: { barnesHut: { springLength: 100, gravitationalConstant: -2000 } }
    };

    networkInstance = new vis.Network(container, data, options);

    // Node click -> Open Entity Details Panel
    networkInstance.on("selectNode", (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const nodeData = SYNTHETIC_GRAPH_DATA.nodes.find(n => n.id === nodeId);
            if (nodeData) openEntityDetailsPanel(nodeData);
        }
    });

    // Edge click -> Open Evidence Panel
    networkInstance.on("selectEdge", (params) => {
        if (params.edges.length > 0 && params.nodes.length === 0) {
            const edgeId = params.edges[0];
            const edgeData = SYNTHETIC_GRAPH_DATA.edges.find(e => e.id === edgeId);
            if (edgeData) openEvidencePanel(edgeData);
        }
    });
}

function highlightDemoPath() {
    if (!networkInstance) return;
    const demoNodes = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"];
    networkInstance.selectNodes(demoNodes);
    alert("Highlighted Central Demo Chain: CASE_101 → PERSON_017 → PHONE_042 → PERSON_089 → CASE_204");
}

/* ----------------------------------------------------
   4. REUSABLE ENTITY DETAILS PANEL (SECTION 6)
---------------------------------------------------- */
function openEntityDetailsPanel(entity) {
    const drawer = document.getElementById("inspector-drawer");
    if (!drawer) return;

    // Find relationships for entity
    const rels = SYNTHETIC_GRAPH_DATA.edges.filter(e => e.source === entity.id || e.target === entity.id);
    const connectedCases = new Set();
    rels.forEach(r => {
        if (r.source.startswith ? r.source.startswith("CASE_") : r.source.indexOf("CASE_") === 0) connectedCases.add(r.source);
        if (r.target.startswith ? r.target.startswith("CASE_") : r.target.indexOf("CASE_") === 0) connectedCases.add(r.target);
    });

    const badgeClass = `badge-${entity.type.toLowerCase()}`;

    drawer.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                <span class="font-mono text-xs font-bold text-primary px-2 py-0.5 rounded bg-surface-container-highest border border-outline-variant">${entity.id}</span>
                <span class="px-2 py-0.5 text-[10px] font-bold rounded ${badgeClass}">${entity.type}</span>
            </div>

            <h3 class="text-sm font-bold text-white">${entity.name}</h3>
            <p class="text-xs text-on-surface-variant">${entity.details}</p>

            <div class="text-[11px] font-mono text-tertiary">
                Extraction Confidence: <strong>${(entity.confidence * 100).toFixed(0)}%</strong>
            </div>

            <!-- Connected Cases -->
            <div class="border-t border-surface-container-high pt-2 space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Linked Cases (${connectedCases.size})</div>
                <div class="flex flex-wrap gap-1">
                    ${Array.from(connectedCases).map(c => `<span class="px-1.5 py-0.5 rounded bg-error-container/30 text-error border border-error/30 text-[10px] font-mono font-bold">${c}</span>`).join("")}
                </div>
            </div>

            <!-- Relationships List -->
            <div class="border-t border-surface-container-high pt-2 space-y-1.5">
                <div class="text-[10px] font-bold uppercase text-outline">Relationships (${rels.length})</div>
                ${rels.map(r => `
                    <div class="bg-surface-container-lowest p-2 rounded text-[11px] space-y-0.5 border border-surface-container-high">
                        <div class="text-primary font-mono font-semibold">${r.source} --${r.relationship}--> ${r.target}</div>
                        <div class="text-[10px] text-on-surface-variant">Confidence: ${(r.confidence * 100).toFixed(0)}% | Evidence: ${r.evidence_id}</div>
                    </div>
                `).join("")}
            </div>

            <!-- Action -->
            <button onclick="askAIAboutEntity('${entity.id}')" class="w-full py-2 bg-primary-container text-white text-xs font-semibold rounded shadow flex items-center justify-center gap-1 mt-2">
                <span class="material-symbols-outlined text-sm">auto_awesome</span> Query Entity in AI Investigator
            </button>
        </div>
    `;
}

/* ----------------------------------------------------
   5. REUSABLE EVIDENCE PANEL (SECTION 7)
---------------------------------------------------- */
function openEvidencePanel(edge) {
    const drawer = document.getElementById("inspector-drawer");
    if (!drawer) return;

    const evid = SYNTHETIC_GRAPH_DATA.evidence[edge.evidence_id] || {
        evidence_id: edge.evidence_id,
        source_document: "DOC_INVESTIGATION_LOG.pdf",
        page_number: 3,
        source_text: `Observed relationship: ${edge.source} ${edge.relationship} ${edge.target}.`,
        timestamp: "2026-08-11T12:00:00Z",
        extraction_method: "AI_NER",
        confidence: edge.confidence,
        relationship: `${edge.source} --${edge.relationship}--> ${edge.target}`
    };

    drawer.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                <span class="font-mono text-xs font-bold text-tertiary px-2 py-0.5 rounded bg-tertiary-container/20 border border-tertiary/30">${evid.evidence_id}</span>
                <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-primary-container/30 text-primary border border-primary/40">EVIDENCE</span>
            </div>

            <div class="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/40 p-1.5 rounded border border-amber-800/40">
                <span class="material-symbols-outlined text-sm">lightbulb</span>
                <span class="text-[11px]"><strong>Classification:</strong> Potential Investigative Lead</span>
            </div>

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Supported Relationship</div>
                <div class="font-mono text-xs text-white font-bold bg-surface-container-lowest p-2 rounded border border-surface-container-high">${evid.relationship}</div>
            </div>

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Source Text Snippet</div>
                <p class="text-xs text-on-surface italic bg-surface-container-lowest p-2.5 rounded border border-surface-container-high leading-relaxed">"${evid.source_text}"</p>
            </div>

            <div class="grid grid-cols-2 gap-2 text-[11px] pt-1 font-mono">
                <div>Source Doc: <span class="text-primary font-bold">${evid.source_document}</span></div>
                <div>Page Ref: <span class="text-white font-bold">Pg. ${evid.page_number}</span></div>
                <div>Timestamp: <span class="text-white font-bold">${evid.timestamp}</span></div>
                <div>Confidence: <span class="text-tertiary font-bold">${(evid.confidence * 100).toFixed(0)}%</span></div>
            </div>
        </div>
    `;
}

/* ----------------------------------------------------
   6. AI INVESTIGATOR UI (SECTION 8 - MOCK INTERFACE)
---------------------------------------------------- */
function initAIInvestigator() {
    document.querySelectorAll(".ai-preset-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const queryText = btn.innerText.replace(/"/g, "").trim();
            runAIQueryMock(queryText);
        });
    });

    document.getElementById("ai-submit-btn")?.addEventListener("click", () => {
        const input = document.getElementById("ai-input-text");
        if (input && input.value.trim()) {
            runAIQueryMock(input.value.trim());
        }
    });
}

function runAIQueryMock(queryText) {
    const container = document.getElementById("ai-response-container");
    if (!container) return;

    let mockResponse = {
        question: queryText,
        answer: "Automated graph analysis surfaced a 4-hop relationship chain linking CASE_101 and CASE_204 through shared burner line PHONE_042 (+91-9876543210).",
        path: ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
        confidence: "0.93 (High)",
        evidence: "Supported by EVID_042_01 (Phone extraction) and EVID_042_02 (Telco signal intercept).",
        lead: "Investigative Lead: Inspect bullion transactions linked to Vikram Malhotra (PERSON_089) at Zaveri Bazaar."
    };

    container.innerHTML = `
        <div class="space-y-4">
            <div class="border-b border-surface-container-high pb-2">
                <div class="text-[10px] font-bold uppercase text-outline">User Query</div>
                <div class="text-sm font-bold text-primary">${mockResponse.question}</div>
            </div>

            <div class="space-y-2">
                <div class="text-[10px] font-bold uppercase text-outline">Answer Summary</div>
                <div class="text-xs text-white leading-relaxed font-sans">${mockResponse.answer}</div>
            </div>

            <div class="space-y-2">
                <div class="text-[10px] font-bold uppercase text-outline">Discovered Connection Path</div>
                <div class="flex flex-wrap items-center gap-1.5 font-mono text-xs">
                    ${mockResponse.path.map((p, idx) => `
                        <span class="px-2 py-0.5 rounded bg-surface-container-high text-tertiary border border-tertiary/30 font-bold">${p}</span>
                        ${idx < mockResponse.path.length - 1 ? '<span class="material-symbols-outlined text-xs text-outline">arrow_forward</span>' : ''}
                    `).join("")}
                </div>
            </div>

            <div class="grid grid-cols-2 gap-3 pt-2">
                <div class="bg-surface-container-low p-2.5 rounded border border-surface-container-high">
                    <div class="text-[10px] font-bold uppercase text-outline">Confidence Score</div>
                    <div class="text-xs text-tertiary font-bold">${mockResponse.confidence}</div>
                </div>
                <div class="bg-surface-container-low p-2.5 rounded border border-surface-container-high">
                    <div class="text-[10px] font-bold uppercase text-outline">Evidence Citations</div>
                    <div class="text-[11px] text-on-surface-variant">${mockResponse.evidence}</div>
                </div>
            </div>

            <div class="p-3 bg-amber-950/40 border border-amber-800/40 rounded text-amber-300 text-xs">
                <i class="material-symbols-outlined text-xs text-amber-400">lightbulb</i>
                <strong>AI Lead:</strong> ${mockResponse.lead}
            </div>
        </div>
    `;
}

function askAIAboutEntity(entityId) {
    switchTab("pane-ai-investigator");
    runAIQueryMock(`What connects ${entityId} to active cases?`);
}

/* ----------------------------------------------------
   7. TIMELINE & CASE EXPLORER & REPORTS
---------------------------------------------------- */
function initCaseExplorer() {
    const tableBody = document.getElementById("cases-table-body");
    const dashContainer = document.getElementById("dashboard-cases-container");
    if (!tableBody && !dashContainer) return;

    const cases = [
        { id: "CASE_101", title: "Operation Midnight Shadow — Cargo Hijack", date: "2026-08-10", status: "ACTIVE", location: "LOC_001 (Nhava Sheva Hub)", entities: 8 },
        { id: "CASE_204", title: "Operation Golden Falcon — Zaveri Bazaar Fencing", date: "2026-08-14", status: "ACTIVE", location: "LOC_003 (Zaveri Bazaar Vault)", entities: 9 },
        { id: "CASE_102", title: "Operation Silver Shield — Cyber Fraud", date: "2026-08-05", status: "OPEN", location: "LOC_004 (Cyber Cell)", entities: 6 },
        { id: "CASE_305", title: "Operation Falcon Eye — Hawala Intercept", date: "2026-08-18", status: "INVESTIGATING", location: "LOC_007 (Tower Relay)", entities: 7 }
    ];

    if (tableBody) {
        tableBody.innerHTML = cases.map(c => `
            <tr class="hover:bg-surface-container transition">
                <td class="p-3 font-mono font-bold text-error">${c.id}</td>
                <td class="p-3 font-bold text-white">${c.title}</td>
                <td class="p-3 font-mono text-on-surface-variant">${c.date}</td>
                <td class="p-3"><span class="px-2 py-0.5 text-[10px] font-bold rounded bg-tertiary-container/30 text-tertiary border border-tertiary/40">${c.status}</span></td>
                <td class="p-3 text-on-surface-variant">${c.location}</td>
                <td class="p-3">
                    <button onclick="exploreCase('${c.id}')" class="px-2.5 py-1 bg-primary-container text-white text-[11px] font-semibold rounded flex items-center gap-1">
                        <span class="material-symbols-outlined text-xs">hub</span> View Graph
                    </button>
                </td>
            </tr>
        `).join("");
    }

    if (dashContainer) {
        dashContainer.innerHTML = cases.map(c => `
            <div class="stitch-card stitch-card-interactive space-y-2">
                <div class="flex items-center justify-between">
                    <span class="font-mono text-xs text-error font-bold px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${c.id}</span>
                    <span class="text-[10px] font-bold text-tertiary bg-tertiary-container/20 px-2 py-0.5 rounded">${c.status}</span>
                </div>
                <h4 class="text-xs font-bold text-white">${c.title}</h4>
                <div class="text-[11px] text-on-surface-variant">${c.location}</div>
                <div class="flex items-center justify-between pt-2 border-t border-surface-container-high text-[11px]">
                    <span class="text-outline font-mono">${c.date}</span>
                    <button onclick="exploreCase('${c.id}')" class="text-primary font-semibold flex items-center gap-0.5 hover:underline">
                        Investigate <span class="material-symbols-outlined text-xs">arrow_forward</span>
                    </button>
                </div>
            </div>
        `).join("");
    }
}

function exploreCase(caseId) {
    const select = document.getElementById("header-case-select");
    if (select) select.value = caseId;
    switchTab("pane-graph");
    renderGraph(caseId);
}

function initTimeline() {
    const container = document.getElementById("timeline-container");
    if (!container) return;

    const events = [
        { time: "2026-08-10 18:30:00 UTC", type: "CARGO_UNLOAD", location: "LOC_001 (Nhava Sheva)", entity: "PERSON_017 (Aarav Verma)", ref: "DOC_CASE_101_FIR_REPORT.pdf (Pg 2)", text: "Unmanifested cargo unloading supervised by Aarav Verma." },
        { time: "2026-08-11 09:30:00 UTC", type: "VEHICLE_SIGHTING", location: "LOC_001 (Exit Gate)", entity: "VEHICLE_042 (Black SUV)", ref: "DOC_CASE_101_FORENSIC.pdf (Pg 7)", text: "Black SUV MH-01-AB-1234 exited logistics yard following cargo dispatch." },
        { time: "2026-08-12 21:15:00 UTC", type: "CALL_INTERCEPT", location: "LOC_007 (Base Tower 14)", entity: "PHONE_042 (+91-9876543210)", ref: "DOC_CASE_204_INTERCEPT.pdf (Pg 3)", text: "180-second encrypted call session established with Zaveri Bazaar relay." },
        { time: "2026-08-14 11:45:00 UTC", type: "BULLION_RECOVERY", location: "LOC_003 (Zaveri Bazaar)", entity: "PERSON_089 (Vikram Malhotra)", ref: "DOC_CASE_204_CRIME_BRANCH.pdf (Pg 2)", text: "Bullion vault raid and recovery of unmanifested precious metals." }
    ];

    container.innerHTML = events.map(ev => `
        <div class="p-3 bg-surface-container-low border border-surface-container-high rounded space-y-1 text-xs">
            <div class="flex items-center justify-between text-[11px] font-mono">
                <span class="text-tertiary font-bold">${ev.time}</span>
                <span class="px-2 py-0.5 rounded bg-surface-container-highest text-primary font-bold">${ev.type}</span>
            </div>
            <p class="text-white font-medium">${ev.text}</p>
            <div class="flex items-center justify-between text-[10px] text-on-surface-variant pt-1">
                <span>Involved Entity: <strong class="text-white font-mono">${ev.entity}</strong></span>
                <span>Ref: <strong class="text-outline font-mono">${ev.ref}</strong></span>
            </div>
        </div>
    `).join("");
}

function initEvidenceExplorer() {
    const container = document.getElementById("evidence-grid-container");
    if (!container) return;

    const items = Object.values(SYNTHETIC_GRAPH_DATA.evidence);
    container.innerHTML = items.map(ev => `
        <div class="stitch-card space-y-2 text-xs">
            <div class="flex items-center justify-between font-mono">
                <span class="text-tertiary font-bold">${ev.evidence_id}</span>
                <span class="px-2 py-0.5 rounded bg-tertiary-container/30 text-tertiary text-[10px] font-bold">${(ev.confidence * 100).toFixed(0)}% Confidence</span>
            </div>
            <p class="text-white italic">"${ev.source_text}"</p>
            <div class="text-[10px] text-outline font-mono">Doc: ${ev.source_document} (Pg. ${ev.page_number})</div>
        </div>
    `).join("");
}

function generateReport(caseId) {
    const viewBox = document.getElementById("report-view-box");
    if (!viewBox) return;

    viewBox.innerHTML = `
        <div class="space-y-3">
            <div class="text-base font-bold text-white">CrimeGraph AI — Investigation Summary Report</div>
            <div>Case Identifier: <strong class="text-error font-mono">${caseId}</strong></div>
            <div>Generated: <strong>${new Date().toISOString()}</strong></div>
            <hr class="border-surface-container-high">
            <div class="text-amber-300 bg-amber-950/40 p-2 rounded border border-amber-800/40 text-[11px]">
                LEGAL DISCLAIMER: Provides evidence-linked investigative leads only. Does not declare guilt or replace human law enforcement judgment.
            </div>
            <div class="text-white">Summary Findings:</div>
            <div>- High confidence link established between Aarav Verma (PERSON_017) and Vikram Malhotra (PERSON_089).</div>
            <div>- Shared communication vector: Burner line PHONE_042 (+91-9876543210).</div>
            <div>- Cross-case path discovered between CASE_101 and CASE_204 with 0.93 composite confidence score.</div>
        </div>
    `;
}
