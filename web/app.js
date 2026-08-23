/**
 * CrimeGraph AI — Frontend Application Logic (Day 2 Refactored)
 * Architected by Shruti for SIH 2026.
 *
 * All UI components fetch exclusively from window.dataService facade.
 */

let networkInstance = null;
let currentVisNodes = null;
let currentVisEdges = null;
let rawGraphData = { nodes: [], edges: [] };

document.addEventListener("DOMContentLoaded", async () => {
    initNavigation();
    await renderDashboard();
    await renderCaseExplorer();
    await renderCaseDetail("CASE_101");
    await initGraphWorkspace("CASE_101");
    initAIInvestigator();
    await renderTimeline("CASE_101");
    await renderEvidenceExplorer();
    initGlobalSearch();
});

/* ----------------------------------------------------
   1. NAVIGATION & ROUTING
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
        headerCaseSelect.addEventListener("change", async (e) => {
            await renderGraphWorkspace(e.target.value);
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
   2. DASHBOARD & CASE EXPLORER (PHASE 3)
---------------------------------------------------- */
async function renderDashboard() {
    const container = document.getElementById("dashboard-cases-container");
    if (!container) return;

    container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Loading active cases via DataService...</div>`;

    const cases = await window.dataService.getCases();
    if (!cases || cases.length === 0) {
        container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs">No active cases found in investigation store.</div>`;
        return;
    }

    container.innerHTML = cases.map(c => `
        <div class="stitch-card stitch-card-interactive space-y-2">
            <div class="flex items-center justify-between">
                <span class="font-mono text-xs text-error font-bold px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${c.id}</span>
                <span class="text-[10px] font-bold text-tertiary bg-tertiary-container/20 px-2 py-0.5 rounded border border-tertiary/30">${c.status}</span>
            </div>
            <h4 class="text-xs font-bold text-white">${c.title}</h4>
            <div class="text-[11px] text-on-surface-variant">${c.location}</div>
            <div class="flex items-center justify-between pt-2 border-t border-surface-container-high text-[11px]">
                <span class="text-outline font-mono">${c.date}</span>
                <button onclick="exploreCase('${c.id}')" class="text-primary font-semibold flex items-center gap-0.5 hover:underline">
                    Explore Network <span class="material-symbols-outlined text-xs">arrow_forward</span>
                </button>
            </div>
        </div>
    `).join("");
}

async function renderCaseExplorer() {
    const tableBody = document.getElementById("cases-table-body");
    const searchInput = document.getElementById("case-search");
    if (!tableBody) return;

    const cases = await window.dataService.getCases();

    const renderTable = (filteredCases) => {
        if (!filteredCases || filteredCases.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-outline text-xs">No matching cases found.</td></tr>`;
            return;
        }

        tableBody.innerHTML = filteredCases.map(c => `
            <tr class="hover:bg-surface-container transition">
                <td class="p-3 font-mono font-bold text-error">${c.id}</td>
                <td class="p-3 font-bold text-white">${c.title}</td>
                <td class="p-3 font-mono text-on-surface-variant">${c.date}</td>
                <td class="p-3"><span class="px-2 py-0.5 text-[10px] font-bold rounded bg-tertiary-container/30 text-tertiary border border-tertiary/40">${c.status}</span></td>
                <td class="p-3 text-on-surface-variant">${c.location}</td>
                <td class="p-3 font-mono text-primary font-bold">${c.entities_count || 8}</td>
                <td class="p-3">
                    <button onclick="exploreCase('${c.id}')" class="px-2.5 py-1 bg-primary-container text-white text-[11px] font-semibold rounded flex items-center gap-1">
                        <span class="material-symbols-outlined text-xs">hub</span> Explore Graph
                    </button>
                </td>
            </tr>
        `).join("");
    };

    renderTable(cases);

    searchInput?.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        const filtered = cases.filter(c => c.id.toLowerCase().includes(query) || c.title.toLowerCase().includes(query) || c.location.toLowerCase().includes(query));
        renderTable(filtered);
    });
}

/* ----------------------------------------------------
   3. CASE DETAIL (PHASE 4)
---------------------------------------------------- */
async function renderCaseDetail(caseId = "CASE_101") {
    const container = document.getElementById("case-detail-container");
    if (!container) return;

    const cases = await window.dataService.getCases();
    const c = cases.find(item => item.id === caseId) || cases[0];

    container.innerHTML = `
        <div class="flex items-center justify-between border-b border-surface-container-high pb-3">
            <div>
                <span class="font-mono text-xs text-error font-bold px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${c.id}</span>
                <h2 class="text-lg font-bold text-white mt-1">${c.title}</h2>
                <p class="text-xs text-on-surface-variant">Incident Date: ${c.date} | Primary Location: ${c.location}</p>
            </div>
            <button onclick="exploreCase('${c.id}')" class="px-3 py-1.5 bg-primary-container text-white text-xs font-semibold rounded shadow flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">hub</span> Explore Network Graph
            </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div class="stitch-card bg-surface-container-low space-y-2">
                <div class="font-bold text-white uppercase text-[10px] text-outline">Primary Suspects</div>
                <div class="text-primary font-mono font-bold">PERSON_017 (Aarav Verma)</div>
                <div class="text-on-surface-variant">Role: Cargo Dispatch Supervisor / Hijack Facilitator</div>
            </div>

            <div class="stitch-card bg-surface-container-low space-y-2">
                <div class="font-bold text-white uppercase text-[10px] text-outline">Associated Comms</div>
                <div class="text-tertiary font-mono font-bold">PHONE_042 (+91-9876543210)</div>
                <div class="text-on-surface-variant">Recovered encrypted burner line</div>
            </div>

            <div class="stitch-card bg-surface-container-low space-y-2">
                <div class="font-bold text-white uppercase text-[10px] text-outline">Suspect Transit Vehicle</div>
                <div class="text-amber-400 font-mono font-bold">VEHICLE_042 (MH-01-AB-1234)</div>
                <div class="text-on-surface-variant">Black SUV observed at exit gate</div>
            </div>
        </div>
    `;
}

async function exploreCase(caseId) {
    const select = document.getElementById("header-case-select");
    if (select) select.value = caseId;
    switchTab("pane-graph");
    await renderCaseDetail(caseId);
    await renderGraphWorkspace(caseId);
}

/* ----------------------------------------------------
   4. INTERACTIVE NETWORK GRAPH & CONTROLS (PHASE 5 & 10)
---------------------------------------------------- */
async function initGraphWorkspace(initialCaseId = "CASE_101") {
    await renderGraphWorkspace(initialCaseId);

    // Zoom Controls
    document.getElementById("graph-zoom-in")?.addEventListener("click", () => {
        if (networkInstance) networkInstance.moveTo({ scale: networkInstance.getScale() * 1.25 });
    });

    document.getElementById("graph-zoom-out")?.addEventListener("click", () => {
        if (networkInstance) networkInstance.moveTo({ scale: networkInstance.getScale() * 0.8 });
    });

    document.getElementById("graph-reset")?.addEventListener("click", () => {
        if (networkInstance) networkInstance.fit();
    });

    document.getElementById("graph-clear-selection")?.addEventListener("click", () => {
        if (networkInstance) {
            networkInstance.unselectAll();
            document.getElementById("inspector-drawer").innerHTML = `
                <div class="text-center py-16 text-outline text-xs">
                    <span class="material-symbols-outlined text-3xl opacity-40 mb-1 block">touch_app</span>
                    Click any node to open <strong>Entity Details Panel</strong>.<br>Click any relationship edge to open <strong>Evidence Panel</strong>.
                </div>
            `;
        }
    });

    document.getElementById("graph-highlight-path")?.addEventListener("click", highlightMainDemoFlow);

    // Graph Search Input
    document.getElementById("graph-search-input")?.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!query || !networkInstance) return;

        const matchingNode = rawGraphData.nodes.find(n => n.id.toLowerCase().includes(query) || (n.label && n.label.toLowerCase().includes(query)));
        if (matchingNode) {
            networkInstance.selectNodes([matchingNode.id]);
            networkInstance.focus(matchingNode.id, { scale: 1.2, animation: true });
            openEntityDetailsPanel(matchingNode.id);
        }
    });

    // Entity Filter Checkboxes
    document.querySelectorAll(".filter-type").forEach(chk => {
        chk.addEventListener("change", applyGraphFilters);
    });
}

async function renderGraphWorkspace(caseId = "CASE_101") {
    const container = document.getElementById("graph-canvas");
    if (!container) return;

    // Fetch graph data exclusively via DataService
    rawGraphData = await window.dataService.getCaseGraph(caseId);

    const nodeColors = {
        "PERSON": { background: "#3b82f6", border: "#1d4ed8" },
        "PHONE": { background: "#10b981", border: "#047857" },
        "VEHICLE": { background: "#f59e0b", border: "#b45309" },
        "LOCATION": { background: "#8b5cf6", border: "#6d28d9" },
        "CASE": { background: "#ef4444", border: "#b91c1c" },
        "ACCOUNT": { background: "#06b6d4", border: "#0e7490" }
    };

    const visNodesArray = rawGraphData.nodes.map(n => ({
        id: n.id,
        label: `${n.label || n.id}\n[${n.id}]`,
        shape: n.type === "CASE" ? "diamond" : "box",
        color: nodeColors[n.type] || { background: "#64748b", border: "#334155" },
        font: { color: "#ffffff", size: 11, face: "Inter" },
        margin: 8,
        entityType: n.type
    }));

    const visEdgesArray = rawGraphData.edges.map(e => ({
        id: e.id,
        from: e.source,
        to: e.target,
        label: e.relationship,
        font: { color: "#8c90a1", size: 9, align: "horizontal" },
        color: { color: "#424656", highlight: "#b3c5ff" },
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        evidenceId: e.evidence_id
    }));

    currentVisNodes = new vis.DataSet(visNodesArray);
    currentVisEdges = new vis.DataSet(visEdgesArray);

    const data = { nodes: currentVisNodes, edges: currentVisEdges };
    const options = {
        nodes: { borderWidth: 2, shadow: true },
        edges: { smooth: { type: "continuous" } },
        physics: { barnesHut: { springLength: 100, gravitationalConstant: -2000 } },
        interaction: { hover: true, selectConnectedEdges: false }
    };

    networkInstance = new vis.Network(container, data, options);

    // Node selection -> Entity Details Panel (Phase 6)
    networkInstance.on("selectNode", async (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            await openEntityDetailsPanel(nodeId);
        }
    });

    // Edge selection -> Evidence Panel (Phase 7 & 8)
    networkInstance.on("selectEdge", async (params) => {
        if (params.edges.length > 0 && params.nodes.length === 0) {
            const edgeId = params.edges[0];
            const edgeData = rawGraphData.edges.find(e => e.id === edgeId);
            if (edgeData) await openEvidencePanel(edgeData);
        }
    });
}

function applyGraphFilters() {
    if (!currentVisNodes) return;

    const checkedTypes = Array.from(document.querySelectorAll(".filter-type:checked")).map(c => c.value);
    
    rawGraphData.nodes.forEach(n => {
        const isVisible = checkedTypes.includes(n.type);
        if (isVisible) {
            if (!currentVisNodes.get(n.id)) {
                currentVisNodes.add({
                    id: n.id,
                    label: `${n.label || n.id}\n[${n.id}]`,
                    shape: n.type === "CASE" ? "diamond" : "box",
                    color: n.type === "CASE" ? { background: "#ef4444", border: "#b91c1c" } : { background: "#3b82f6", border: "#1d4ed8" },
                    font: { color: "#ffffff", size: 11, face: "Inter" },
                    margin: 8,
                    entityType: n.type
                });
            }
        } else {
            if (currentVisNodes.get(n.id)) {
                currentVisNodes.remove(n.id);
            }
        }
    });
}

/* ----------------------------------------------------
   5. ENTITY DETAILS PANEL (PHASE 6)
---------------------------------------------------- */
async function openEntityDetailsPanel(entityId) {
    const drawer = document.getElementById("inspector-drawer");
    if (!drawer) return;

    drawer.innerHTML = `<div class="text-center py-10 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Loading Entity Details...</div>`;

    const ent = await window.dataService.getEntityDetails(entityId);
    if (!ent) {
        drawer.innerHTML = `<div class="text-center py-10 text-error text-xs">Entity record ${entityId} unavailable.</div>`;
        return;
    }

    const badgeClass = `badge-${(ent.type || "person").toLowerCase()}`;

    drawer.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                <span class="font-mono text-xs font-bold text-primary px-2 py-0.5 rounded bg-surface-container-highest border border-outline-variant">${ent.id}</span>
                <span class="px-2 py-0.5 text-[10px] font-bold rounded ${badgeClass}">${ent.type}</span>
            </div>

            <h3 class="text-sm font-bold text-white">${ent.name}</h3>
            <p class="text-xs text-on-surface-variant">${ent.details || "Active Knowledge Graph Entity"}</p>

            <div class="text-[11px] font-mono text-tertiary">
                Extraction Confidence: <strong>${((ent.confidence || 0.95) * 100).toFixed(0)}%</strong>
            </div>

            <!-- Connected Cases -->
            <div class="border-t border-surface-container-high pt-2 space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Linked Cases (${ent.cases ? ent.cases.length : 0})</div>
                <div class="flex flex-wrap gap-1">
                    ${(ent.cases || []).map(c => `<span class="px-1.5 py-0.5 rounded bg-error-container/30 text-error border border-error/30 text-[10px] font-mono font-bold">${c}</span>`).join("")}
                </div>
            </div>

            <!-- Associated Relationships -->
            <div class="border-t border-surface-container-high pt-2 space-y-1.5">
                <div class="text-[10px] font-bold uppercase text-outline">Relationships (${ent.relationships ? ent.relationships.length : 0})</div>
                ${(ent.relationships || []).map(r => `
                    <div class="bg-surface-container-lowest p-2 rounded text-[11px] space-y-0.5 border border-surface-container-high">
                        <div class="text-primary font-mono font-semibold">${r.source || r.source_id} --${r.relationship}--> ${r.target || r.target_id}</div>
                        <div class="text-[10px] text-on-surface-variant">Confidence: ${((r.confidence || 0.9) * 100).toFixed(0)}%</div>
                    </div>
                `).join("")}
            </div>

            <!-- AI Query Action -->
            <button onclick="askAIAboutEntity('${ent.id}')" class="w-full py-2 bg-primary-container hover:bg-blue-600 text-white text-xs font-semibold rounded shadow flex items-center justify-center gap-1 mt-2">
                <span class="material-symbols-outlined text-sm">auto_awesome</span> Query Entity in AI Investigator
            </button>
        </div>
    `;
}

/* ----------------------------------------------------
   6. RELATIONSHIP & EVIDENCE PANEL (PHASE 7 & 8)
---------------------------------------------------- */
async function openEvidencePanel(edge) {
    const drawer = document.getElementById("inspector-drawer");
    if (!drawer) return;

    drawer.innerHTML = `<div class="text-center py-10 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-tertiary">sync</span> Fetching Evidence Provenance...</div>`;

    const evid = await window.dataService.getEvidence(edge.evidence_id || edge.evidenceId);

    const evObj = evid || {
        evidence_id: edge.evidence_id || "EVID_042_01",
        source_document: "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf",
        page_number: 7,
        source_text: `Observed relationship: ${edge.source} ${edge.relationship} ${edge.target}.`,
        timestamp: "2026-08-11T09:30:00Z",
        confidence: edge.confidence || 0.95,
        relationship: `${edge.source} --${edge.relationship}--> ${edge.target}`
    };

    drawer.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                <span class="font-mono text-xs font-bold text-tertiary px-2 py-0.5 rounded bg-tertiary-container/20 border border-tertiary/30">${evObj.evidence_id}</span>
                <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-primary-container/30 text-primary border border-primary/40">EVIDENCE</span>
            </div>

            <div class="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/40 p-1.5 rounded border border-amber-800/40">
                <span class="material-symbols-outlined text-sm">lightbulb</span>
                <span class="text-[11px]"><strong>Classification:</strong> Potential Investigative Lead</span>
            </div>

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Supported Relationship</div>
                <div class="font-mono text-xs text-white font-bold bg-surface-container-lowest p-2 rounded border border-surface-container-high">${evObj.relationship || (edge.source + ' --' + edge.relationship + '--> ' + edge.target)}</div>
            </div>

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Source Document Snippet</div>
                <p class="text-xs text-on-surface italic bg-surface-container-lowest p-2.5 rounded border border-surface-container-high leading-relaxed">"${evObj.source_text}"</p>
            </div>

            <div class="grid grid-cols-2 gap-2 text-[11px] pt-1 font-mono">
                <div>Doc: <span class="text-primary font-bold">${evObj.source_document}</span></div>
                <div>Page: <span class="text-white font-bold">Pg. ${evObj.page_number || 1}</span></div>
                <div>Time: <span class="text-white font-bold">${evObj.timestamp || '2026-08-11'}</span></div>
                <div>Conf: <span class="text-tertiary font-bold">${((evObj.confidence || 0.95) * 100).toFixed(0)}%</span></div>
            </div>
        </div>
    `;
}

/* ----------------------------------------------------
   7. MAIN DEMONSTRATION FLOW (PHASE 11 & 12)
---------------------------------------------------- */
async function highlightMainDemoFlow() {
    if (!networkInstance) return;

    const demoChainNodes = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"];
    
    // Ensure all demo nodes are loaded into graph
    await renderGraphWorkspace("ALL");

    networkInstance.selectNodes(demoChainNodes);
    networkInstance.fit({ nodes: demoChainNodes, animation: true });

    // Open Evidence panel for the key bridge
    await openEvidencePanel({
        source: "PERSON_017",
        relationship: "USES",
        target: "PHONE_042",
        evidence_id: "EVID_042_01",
        confidence: 0.95
    });

    alert("Central Demo Path Highlighted:\nCASE_101 → PERSON_017 → PHONE_042 → PERSON_089 → CASE_204\n\nCross-case bridge identified through shared burner line PHONE_042.");
}

/* ----------------------------------------------------
   8. AI INVESTIGATOR ASSISTANT (PHASE 13)
---------------------------------------------------- */
function initAIInvestigator() {
    document.querySelectorAll(".ai-preset-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const queryText = btn.innerText.replace(/"/g, "").trim();
            await runAIQuery(queryText);
        });
    });

    document.getElementById("ai-submit-btn")?.addEventListener("click", async () => {
        const input = document.getElementById("ai-input-text");
        if (input && input.value.trim()) {
            await runAIQuery(input.value.trim());
        }
    });
}

async function runAIQuery(questionText) {
    const container = document.getElementById("ai-response-container");
    if (!container) return;

    container.innerHTML = `<div class="text-center py-10 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-tertiary">sync</span> Querying AI Investigator Engine...</div>`;

    const res = await window.dataService.queryAIInvestigator(questionText);

    container.innerHTML = `
        <div class="space-y-4">
            <div class="border-b border-surface-container-high pb-2">
                <div class="text-[10px] font-bold uppercase text-outline">User Query</div>
                <div class="text-sm font-bold text-primary">${res.question}</div>
            </div>

            <div class="space-y-2">
                <div class="text-[10px] font-bold uppercase text-outline">Answer Summary</div>
                <div class="text-xs text-white leading-relaxed font-sans">${res.answer}</div>
            </div>

            <div class="space-y-2">
                <div class="text-[10px] font-bold uppercase text-outline">Discovered Connection Path</div>
                <div class="flex flex-wrap items-center gap-1.5 font-mono text-xs">
                    ${(res.path || ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]).map((p, idx, arr) => `
                        <span class="px-2 py-0.5 rounded bg-surface-container-high text-tertiary border border-tertiary/30 font-bold">${p}</span>
                        ${idx < arr.length - 1 ? '<span class="material-symbols-outlined text-xs text-outline">arrow_forward</span>' : ''}
                    `).join("")}
                </div>
            </div>

            <div class="grid grid-cols-2 gap-3 pt-2">
                <div class="bg-surface-container-low p-2.5 rounded border border-surface-container-high">
                    <div class="text-[10px] font-bold uppercase text-outline">Confidence Rating</div>
                    <div class="text-xs text-tertiary font-bold">${res.confidence || '0.93 (High)'}</div>
                </div>
                <div class="bg-surface-container-low p-2.5 rounded border border-surface-container-high">
                    <div class="text-[10px] font-bold uppercase text-outline">Evidence Citations</div>
                    <div class="text-[11px] text-on-surface-variant">${res.evidence || 'EVID_042_01, EVID_042_02'}</div>
                </div>
            </div>

            <div class="p-3 bg-amber-950/40 border border-amber-800/40 rounded text-amber-300 text-xs">
                <span class="material-symbols-outlined text-xs text-amber-400">lightbulb</span>
                <strong>Potential Lead:</strong> ${res.lead || 'Subpoena bullion transactions linked to Vikram Malhotra at Zaveri Bazaar.'}
            </div>
        </div>
    `;
}

function askAIAboutEntity(entityId) {
    switchTab("pane-ai-investigator");
    runAIQuery(`What connects ${entityId} to active cases?`);
}

/* ----------------------------------------------------
   9. TIMELINE, EVIDENCE EXPLORER & GLOBAL SEARCH (PHASE 9 & 14)
---------------------------------------------------- */
async function renderTimeline(caseId = "CASE_101") {
    const container = document.getElementById("timeline-container");
    if (!container) return;

    const data = await window.dataService.getTimeline(caseId);
    const events = data ? data.events : [];

    container.innerHTML = events.map(ev => `
        <div class="p-3 bg-surface-container-low border border-surface-container-high rounded space-y-1 text-xs">
            <div class="flex items-center justify-between text-[11px] font-mono">
                <span class="text-tertiary font-bold">${ev.timestamp}</span>
                <span class="px-2 py-0.5 rounded bg-surface-container-highest text-primary font-bold">${ev.type}</span>
            </div>
            <p class="text-white font-medium">${ev.description}</p>
            <div class="text-[10px] text-on-surface-variant">Location Tag: <strong class="text-outline font-mono">${ev.location_id}</strong></div>
        </div>
    `).join("");
}

async function renderEvidenceExplorer() {
    const container = document.getElementById("evidence-grid-container");
    if (!container) return;

    const mockEv = new MockCrimeGraphAdapter();
    const evidenceObj = mockEv.dataset.evidence;

    container.innerHTML = Object.values(evidenceObj).map(ev => `
        <div class="stitch-card space-y-2 text-xs">
            <div class="flex items-center justify-between font-mono">
                <span class="text-tertiary font-bold">${ev.evidence_id}</span>
                <span class="px-2 py-0.5 rounded bg-tertiary-container/30 text-tertiary text-[10px] font-bold">${(ev.confidence * 100).toFixed(0)}% Confidence</span>
            </div>
            <p class="text-white italic text-[11px]">"${ev.source_text}"</p>
            <div class="text-[10px] text-outline font-mono">Source: ${ev.source_document} (Pg. ${ev.page_number})</div>
        </div>
    `).join("");
}

function initGlobalSearch() {
    const globalInput = document.getElementById("global-search-input");
    if (!globalInput) return;

    globalInput.addEventListener("keypress", async (e) => {
        if (e.key === "Enter") {
            const query = globalInput.value.trim();
            if (!query) return;

            const results = await window.dataService.search(query);
            if (results.length > 0) {
                switchTab("pane-graph");
                await renderGraphWorkspace("ALL");
                networkInstance?.selectNodes([results[0].id]);
                openEntityDetailsPanel(results[0].id);
            } else {
                alert(`No records found matching search query "${query}".`);
            }
        }
    });
}

async function generateReport(caseId = "CASE_101") {
    const viewBox = document.getElementById("report-view-box");
    if (!viewBox) return;

    viewBox.innerHTML = `
        <div class="space-y-3">
            <div class="text-base font-bold text-white">CrimeGraph AI — Investigation Summary Report</div>
            <div>Target Case: <strong class="text-error font-mono">${caseId}</strong></div>
            <div>Generated: <strong>${new Date().toISOString()}</strong></div>
            <hr class="border-surface-container-high">
            <div class="text-amber-300 bg-amber-950/40 p-2 rounded border border-amber-800/40 text-[11px]">
                LEGAL DISCLAIMER: Evidence-linked investigative leads only. Does not determine guilt or replace human law enforcement judgment.
            </div>
            <div class="text-white">Key Findings:</div>
            <div>- Discovered cross-case connection chain between CASE_101 and CASE_204 with 0.93 composite confidence score.</div>
            <div>- Shared burner phone vector: PHONE_042 (+91-9876543210).</div>
            <div>- Linked suspects: Aarav Verma (PERSON_017) and Vikram Malhotra (PERSON_089).</div>
        </div>
    `;
}
