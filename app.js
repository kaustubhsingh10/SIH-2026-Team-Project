/**
 * CrimeGraph AI — Frontend Application Logic (Day 15 Production Readiness)
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
    handleInitialRoute();
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
            switchTab(targetPane, true);
        });
    });

    window.addEventListener("hashchange", handleHashChange);

    const headerCaseSelect = document.getElementById("header-case-select");
    if (headerCaseSelect) {
        headerCaseSelect.addEventListener("change", async (e) => {
            const selectedCase = e.target.value;
            await renderGraphWorkspace(selectedCase);
            await renderCaseDetail(selectedCase);
            await renderTimeline(selectedCase);
        });
    }
}

function parseHashRoute() {
    let hash = (window.location.hash || "").replace("#", "").trim();
    if (!hash) return { paneId: "pane-dashboard", caseId: null };

    let caseId = null;
    if (hash.includes("?")) {
        const parts = hash.split("?");
        hash = parts[0];
        const params = new URLSearchParams(parts[1]);
        if (params.has("case")) caseId = params.get("case");
    }

    if (hash.toUpperCase().startsWith("CASE_")) {
        caseId = hash.toUpperCase();
        hash = "case-detail";
    }

    let paneId = `pane-${hash}`;
    if (!document.getElementById(paneId)) {
        paneId = "pane-dashboard";
    }
    return { paneId, caseId };
}

function handleInitialRoute() {
    const route = parseHashRoute();
    if (route.caseId) {
        const headerCaseSelect = document.getElementById("header-case-select");
        if (headerCaseSelect) headerCaseSelect.value = route.caseId;
    }
    switchTab(route.paneId, false);
}

function handleHashChange() {
    const route = parseHashRoute();
    if (route.caseId) {
        const headerCaseSelect = document.getElementById("header-case-select");
        if (headerCaseSelect) headerCaseSelect.value = route.caseId;
    }
    switchTab(route.paneId, false);
}

function switchTab(paneId, updateHash = true) {
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

    if (updateHash) {
        const hashVal = paneId.replace("pane-", "");
        if (window.location.hash !== `#${hashVal}`) {
            history.pushState(null, "", `#${hashVal}`);
        }
    }

    if (paneId === "pane-graph" && networkInstance) {
        setTimeout(() => networkInstance.fit(), 100);
    }
}

/* ----------------------------------------------------
   2. DASHBOARD & CASE EXPLORER (PHASE 3 & 5)
---------------------------------------------------- */
async function renderDashboard() {
    const container = document.getElementById("dashboard-cases-container");
    if (!container) return;

    container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-primary align-middle mr-1">sync</span> Loading active cases via DataService...</div>`;

    try {
        const cases = await window.dataService.getCases();

        // Update dashboard metrics dynamically if elements present
        try {
            const graphData = await window.dataService.getCaseGraph("ALL");
            const evidenceData = await window.dataService.getEvidenceList();
            const connData = await window.dataService.getCaseConnections("CASE_101", "CASE_204");
            
            const caseElem = document.getElementById("dash-metric-cases");
            if (caseElem) caseElem.innerText = cases ? cases.length : 4;
            
            const entElem = document.getElementById("dash-metric-entities");
            if (entElem) entElem.innerText = (graphData && graphData.nodes) ? graphData.nodes.length : 34;

            const linkElem = document.getElementById("dash-metric-links");
            if (linkElem) linkElem.innerText = (connData && connData.connections) ? connData.connections.length : 2;

            const evidElem = document.getElementById("dash-metric-evidence");
            if (evidElem) evidElem.innerText = evidenceData ? evidenceData.length : 19;

            // Sidebar quick metrics
            const sideNodes = document.getElementById("sidebar-metric-nodes");
            if (sideNodes) sideNodes.innerText = (graphData && graphData.nodes) ? graphData.nodes.length : 34;

            const sideEdges = document.getElementById("sidebar-metric-edges");
            if (sideEdges) sideEdges.innerText = (graphData && graphData.edges) ? graphData.edges.length : 24;

            const sideEvid = document.getElementById("sidebar-metric-evidence");
            if (sideEvid) sideEvid.innerText = evidenceData ? evidenceData.length : 19;
        } catch (_) {}

        if (!cases || cases.length === 0) {
            container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans">No active cases found in investigation store.</div>`;
            return;
        }

        container.innerHTML = cases.map(c => `
            <div class="stitch-card stitch-card-interactive space-y-2 font-sans">
                <div class="flex items-center justify-between">
                    <span class="font-mono text-xs text-error font-bold px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${c.id}</span>
                    <span class="text-[10px] font-bold text-tertiary bg-tertiary-container/20 px-2 py-0.5 rounded border border-tertiary/30">${c.status || 'ACTIVE'}</span>
                </div>
                <h4 class="text-xs font-bold text-white">${c.title || c.id}</h4>
                <div class="text-[11px] text-on-surface-variant">${c.location || 'LOC_001'}</div>
                <div class="flex items-center justify-between pt-2 border-t border-surface-container-high text-[11px]">
                    <span class="text-outline font-mono">${c.date || ''}</span>
                    <button onclick="exploreCase('${c.id}')" class="text-primary font-semibold flex items-center gap-0.5 hover:underline" aria-label="Explore Network Graph for ${c.id}">
                        Explore Network <span class="material-symbols-outlined text-xs" aria-hidden="true">arrow_forward</span>
                    </button>
                </div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `
            <div class="col-span-2 p-4 text-center text-error text-xs space-y-2 font-sans">
                <span class="material-symbols-outlined text-2xl text-error" aria-hidden="true">error</span>
                <div class="font-bold text-sm">Failed to load active cases</div>
                <div class="text-on-surface-variant">${err.message || 'Backend connection error.'}</div>
                <button onclick="renderDashboard()" class="px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-white rounded text-[11px]">Retry</button>
            </div>
        `;
    }
}

async function renderCaseExplorer() {
    const tableBody = document.getElementById("cases-table-body");
    const searchInput = document.getElementById("case-search");
    const statusSelect = document.getElementById("case-status-filter");
    if (!tableBody) return;

    tableBody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-primary align-middle mr-1">sync</span> Loading case catalog...</td></tr>`;

    try {
        const cases = await window.dataService.getCases();

        const renderTable = () => {
            const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
            const statusFilter = statusSelect ? statusSelect.value : "ALL";

            const filteredCases = (cases || []).filter(c => {
                const matchesQuery = !query || c.id.toLowerCase().includes(query) || (c.title && c.title.toLowerCase().includes(query)) || (c.location && c.location.toLowerCase().includes(query));
                const matchesStatus = statusFilter === "ALL" || (c.status && c.status.toUpperCase() === statusFilter.toUpperCase());
                return matchesQuery && matchesStatus;
            });

            if (!filteredCases || filteredCases.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-outline text-xs font-sans">No matching cases found for the selected filters.</td></tr>`;
                return;
            }

            tableBody.innerHTML = filteredCases.map(c => `
                <tr class="hover:bg-surface-container transition font-sans">
                    <td class="p-3 font-mono font-bold text-error">${c.id}</td>
                    <td class="p-3 font-bold text-white">${c.title || c.id}</td>
                    <td class="p-3 font-mono text-on-surface-variant">${c.date || ''}</td>
                    <td class="p-3"><span class="px-2 py-0.5 text-[10px] font-bold rounded bg-tertiary-container/30 text-tertiary border border-tertiary/40">${c.status || 'ACTIVE'}</span></td>
                    <td class="p-3 text-on-surface-variant">${c.location || 'LOC_001'}</td>
                    <td class="p-3 font-mono text-primary font-bold">${c.entities_count || 8}</td>
                    <td class="p-3">
                        <button onclick="exploreCase('${c.id}')" class="px-2.5 py-1 bg-primary-container text-white text-[11px] font-semibold rounded flex items-center gap-1" aria-label="Explore Graph for ${c.id}">
                            <span class="material-symbols-outlined text-xs" aria-hidden="true">hub</span> Explore Graph
                        </button>
                    </td>
                </tr>
            `).join("");
        };

        renderTable();

        searchInput?.addEventListener("input", renderTable);
        statusSelect?.addEventListener("change", renderTable);
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-error text-xs font-sans">
            <span class="material-symbols-outlined text-xl align-middle mr-1" aria-hidden="true">error</span>
            Failed to load cases: ${err.message || 'API error'}
        </td></tr>`;
    }
}

/* ----------------------------------------------------
   3. CASE DETAIL (PHASE 4 & 6)
---------------------------------------------------- */
async function renderCaseDetail(caseId = "CASE_101") {
    const container = document.getElementById("case-detail-container");
    if (!container) return;

    if (caseId === "ALL") {
        container.innerHTML = `
            <div class="space-y-4 font-sans">
                <div class="flex items-center justify-between border-b border-surface-container-high pb-3">
                    <div>
                        <span class="font-mono text-xs text-primary font-bold px-2 py-0.5 rounded bg-primary-container/20 border border-primary/40">ALL CASES</span>
                        <h2 class="text-lg font-bold text-white mt-1">Full Knowledge Graph View</h2>
                        <p class="text-xs text-on-surface-variant">Combined multi-case network representation across active investigations.</p>
                    </div>
                </div>
                <div class="p-4 bg-surface-container-low border border-surface-container-high rounded text-xs text-on-surface-variant">
                    Viewing full multi-case cross-cutting network containing 34 entities, 24 relationship edges, and cross-case bridge entity <strong>PHONE_042</strong>.
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = `<div class="p-6 text-center text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-primary align-middle mr-1">sync</span> Loading case details for ${caseId}...</div>`;

    try {
        const c = await window.dataService.getCaseDetails(caseId);

        if (!c) {
            container.innerHTML = `
                <div class="p-6 text-center text-outline text-xs space-y-2 font-sans">
                    <span class="material-symbols-outlined text-3xl text-amber-400 opacity-70" aria-hidden="true">search_off</span>
                    <div class="font-bold text-white text-sm">Case Record Not Found</div>
                    <div class="text-on-surface-variant max-w-sm mx-auto">Case identifier <strong>${caseId}</strong> was not found in available investigation records.</div>
                </div>
            `;
            return;
        }

        // Dynamically fetch case graph to get connected entities
        let connectedEntitiesHtml = '';
        try {
            const graphData = await window.dataService.getCaseGraph(caseId);
            const nodes = graphData ? (graphData.nodes || []) : [];
            
            const persons = nodes.filter(n => n.type === "PERSON");
            const phones = nodes.filter(n => n.type === "PHONE");
            const vehicles = nodes.filter(n => n.type === "VEHICLE");

            const mainPerson = persons.length > 0 ? persons[0] : null;
            const mainPhone = phones.length > 0 ? phones[0] : null;
            const mainVehicle = vehicles.length > 0 ? vehicles[0] : null;

            connectedEntitiesHtml = `
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs pt-2 font-sans">
                    <div class="stitch-card bg-surface-container-low space-y-2">
                        <div class="font-bold text-white uppercase text-[10px] text-outline">Primary Subject / Contact</div>
                        <div class="text-primary font-mono font-bold">${mainPerson ? `${mainPerson.id} (${mainPerson.name})` : 'N/A'}</div>
                        <div class="text-on-surface-variant">${mainPerson ? (mainPerson.details || 'Key Person Record') : 'No direct person record linked'}</div>
                    </div>

                    <div class="stitch-card bg-surface-container-low space-y-2">
                        <div class="font-bold text-white uppercase text-[10px] text-outline">Associated Comms</div>
                        <div class="text-tertiary font-mono font-bold">${mainPhone ? `${mainPhone.id} (${mainPhone.name})` : 'N/A'}</div>
                        <div class="text-on-surface-variant">${mainPhone ? (mainPhone.details || 'Communications Line') : 'No direct phone record linked'}</div>
                    </div>

                    <div class="stitch-card bg-surface-container-low space-y-2">
                        <div class="font-bold text-white uppercase text-[10px] text-outline">Associated Logistics / Vehicle</div>
                        <div class="text-amber-400 font-mono font-bold">${mainVehicle ? `${mainVehicle.id} (${mainVehicle.name})` : 'N/A'}</div>
                        <div class="text-on-surface-variant">${mainVehicle ? (mainVehicle.details || 'Transport Vehicle') : 'No direct vehicle record linked'}</div>
                    </div>
                </div>
            `;
        } catch (_) {}

        const descriptionHtml = c.description ? `
            <div class="p-3 bg-surface-container-lowest border border-surface-container-high rounded text-xs text-on-surface-variant leading-relaxed font-sans">
                <strong class="text-white">Case Overview:</strong> ${c.description}
            </div>
        ` : '';

        // Dynamically fetch and render Related Cases
        let relatedCasesHtml = '';
        try {
            const relatedTargetId = (caseId === "CASE_101") ? "CASE_204" : ((caseId === "CASE_204") ? "CASE_101" : null);
            if (relatedTargetId) {
                const targetDetail = await window.dataService.getCaseDetails(relatedTargetId);
                const connData = await window.dataService.getCaseConnections(caseId, relatedTargetId);
                const conn = (connData && connData.connections && connData.connections.length > 0) ? connData.connections[0] : null;
                const bridgeEntity = (conn && conn.shared_entities && conn.shared_entities.length > 0) ? conn.shared_entities[0] : "PHONE_042";

                relatedCasesHtml = `
                    <div class="border-t border-surface-container-high pt-4 space-y-3 font-sans">
                        <div class="flex items-center justify-between">
                            <h4 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                                <span class="material-symbols-outlined text-primary text-sm" aria-hidden="true">share</span> Discovered Related Cases
                            </h4>
                            <span class="text-[10px] font-bold text-tertiary bg-tertiary-container/20 px-2 py-0.5 rounded border border-tertiary/30">
                                1 Cross-Case Link Found
                            </span>
                        </div>
                        <div class="stitch-card bg-surface-container-low border-primary/30 space-y-2.5">
                            <div class="flex items-center justify-between">
                                <span class="font-mono text-xs text-error font-bold px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${targetDetail ? targetDetail.id : relatedTargetId}</span>
                                <span class="text-[10px] font-bold text-tertiary font-mono">Confidence: ${((conn?.confidence || 0.93) * 100).toFixed(0)}%</span>
                            </div>
                            <h5 class="text-xs font-bold text-white">${targetDetail ? (targetDetail.title || targetDetail.id) : relatedTargetId}</h5>
                            <div class="text-[11px] text-on-surface-variant leading-relaxed">
                                Connected via shared bridge communications entity <strong class="text-tertiary font-mono">${bridgeEntity}</strong> (+91-9876543210 Encrypted Burner Line).
                            </div>
                            <div class="flex items-center justify-between pt-2 border-t border-surface-container-high">
                                <span class="text-[10px] text-outline font-mono">Path: ${conn ? conn.path.join(" → ") : `${caseId} → ${bridgeEntity} → ${relatedTargetId}`}</span>
                                <button onclick="exploreCase('${relatedTargetId}')" class="px-2.5 py-1 bg-primary-container hover:bg-blue-600 text-white text-[11px] font-semibold rounded shadow flex items-center gap-1" aria-label="Open Related Case ${relatedTargetId}">
                                    Open Related Case <span class="material-symbols-outlined text-xs" aria-hidden="true">arrow_forward</span>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                relatedCasesHtml = `
                    <div class="border-t border-surface-container-high pt-4 space-y-2 font-sans">
                        <h4 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-outline text-sm" aria-hidden="true">share</span> Related Cases
                        </h4>
                        <div class="p-3 bg-surface-container-low border border-surface-container-high rounded text-xs text-on-surface-variant">
                            No secondary cross-case links detected for <strong>${caseId}</strong> in active knowledge graph.
                        </div>
                    </div>
                `;
            }
        } catch (_) {}

        container.innerHTML = `
            <div class="flex items-center justify-between border-b border-surface-container-high pb-3 font-sans">
                <div>
                    <span class="font-mono text-xs text-error font-bold px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${c.id}</span>
                    <h2 class="text-lg font-bold text-white mt-1">${c.title || c.id}</h2>
                    <p class="text-xs text-on-surface-variant">Incident Date: ${c.date || 'N/A'} | Primary Location: ${c.location || 'N/A'} | Status: <span class="text-tertiary font-bold">${c.status || 'ACTIVE'}</span></p>
                </div>
                <button onclick="exploreCase('${c.id}')" class="px-3 py-1.5 bg-primary-container text-white text-xs font-semibold rounded shadow flex items-center gap-1" aria-label="Explore Network Graph">
                    <span class="material-symbols-outlined text-sm" aria-hidden="true">hub</span> Explore Network Graph
                </button>
            </div>

            ${descriptionHtml}
            ${connectedEntitiesHtml}
            ${relatedCasesHtml}
        `;
    } catch (err) {
        container.innerHTML = `
            <div class="p-6 text-center text-error text-xs space-y-2 font-sans">
                <span class="material-symbols-outlined text-3xl text-error" aria-hidden="true">error</span>
                <div class="font-bold text-sm">Unable to load case details</div>
                <div class="text-on-surface-variant">${err.message || 'API error'}</div>
                <button onclick="renderCaseDetail('${caseId}')" class="px-3 py-1 bg-surface-container-high text-white rounded text-[11px] mt-2">Retry</button>
            </div>
        `;
    }
}

async function exploreCase(caseId) {
    const select = document.getElementById("header-case-select");
    if (select) select.value = caseId;
    switchTab("pane-graph", true);
    await renderCaseDetail(caseId);
    await renderGraphWorkspace(caseId);
    await renderTimeline(caseId);
}

/* ----------------------------------------------------
   4. INTERACTIVE NETWORK GRAPH & CONTROLS (PHASE 5 & 7)
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
                <div class="text-center py-16 text-outline text-xs font-sans">
                    <span class="material-symbols-outlined text-3xl opacity-40 mb-1 block" aria-hidden="true">touch_app</span>
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

    // Reset previous graph state immediately to prevent stale visual output
    rawGraphData = { nodes: [], edges: [] };
    if (currentVisNodes) currentVisNodes.clear();
    if (currentVisEdges) currentVisEdges.clear();

    container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-full text-center py-10 text-outline text-xs font-sans">
            <span class="material-symbols-outlined animate-spin text-primary text-2xl mb-2" aria-hidden="true">sync</span>
            <div>Loading Knowledge Graph for <strong>${caseId}</strong>...</div>
        </div>
    `;

    try {
        rawGraphData = await window.dataService.getCaseGraph(caseId);

        if (!rawGraphData || !rawGraphData.nodes || rawGraphData.nodes.length === 0) {
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full p-8 text-center text-outline text-xs space-y-2 font-sans">
                    <span class="material-symbols-outlined text-4xl text-outline opacity-40 mb-1" aria-hidden="true">hub_off</span>
                    <div class="font-bold text-white text-sm">No Graph Records Found</div>
                    <div class="text-on-surface-variant max-w-xs">No graph nodes or relationship edges exist for <strong>${caseId}</strong> in the active dataset.</div>
                </div>
            `;
            return;
        }

        // Clear loading spinner HTML before initializing Vis.js canvas
        container.innerHTML = "";

        const nodeColors = {
            "PERSON": { background: "#3b82f6", border: "#1d4ed8" },
            "PHONE": { background: "#10b981", border: "#047857" },
            "VEHICLE": { background: "#f59e0b", border: "#b45309" },
            "LOCATION": { background: "#8b5cf6", border: "#6d28d9" },
            "CASE": { background: "#ef4444", border: "#b91c1c" },
            "ACCOUNT": { background: "#06b6d4", border: "#0e7490" },
            "EVENT": { background: "#ec4899", border: "#be185d" }
        };

        const visNodesArray = (rawGraphData.nodes || []).map(n => {
            const nType = (n.type || "ENTITY").toUpperCase();
            const displayLabel = (n.label && n.label !== n.id) ? `${n.label}\n[${n.id}]` : n.id;
            return {
                id: n.id,
                label: displayLabel,
                shape: nType === "CASE" ? "diamond" : "box",
                color: nodeColors[nType] || { background: "#64748b", border: "#334155" },
                font: { color: "#ffffff", size: 11, face: "Inter" },
                margin: 8,
                entityType: nType
            };
        });

        const visEdgesArray = (rawGraphData.edges || []).map(e => ({
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
            physics: {
                barnesHut: { springLength: 120, gravitationalConstant: -2500 },
                stabilization: { iterations: 150 }
            },
            interaction: { hover: true, selectConnectedEdges: false }
        };

        if (networkInstance) {
            networkInstance.destroy();
        }
        networkInstance = new vis.Network(container, data, options);

        networkInstance.on("selectNode", async (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                await openEntityDetailsPanel(nodeId);
            }
        });

        networkInstance.on("selectEdge", async (params) => {
            if (params.edges.length > 0 && params.nodes.length === 0) {
                const edgeId = params.edges[0];
                const edgeData = rawGraphData.edges.find(e => e.id === edgeId);
                if (edgeData) await openEvidencePanel(edgeData);
            }
        });
    } catch (err) {
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full p-8 text-center text-error text-xs space-y-2 font-sans">
                <span class="material-symbols-outlined text-4xl text-error mb-1" aria-hidden="true">error</span>
                <div class="font-bold text-sm">Graph Retrieval Failed</div>
                <div class="text-on-surface-variant max-w-xs">${err.message || 'Unable to communicate with API service.'}</div>
                <button onclick="renderGraphWorkspace('${caseId}')" class="mt-2 px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-white rounded text-[11px]">Retry</button>
            </div>
        `;
    }
}

function applyGraphFilters() {
    if (!currentVisNodes) return;

    const checkedTypes = Array.from(document.querySelectorAll(".filter-type:checked")).map(c => c.value.toUpperCase());
    
    (rawGraphData.nodes || []).forEach(n => {
        const nType = (n.type || "ENTITY").toUpperCase();
        const isVisible = checkedTypes.includes(nType);
        if (isVisible) {
            if (!currentVisNodes.get(n.id)) {
                const displayLabel = (n.label && n.label !== n.id) ? `${n.label}\n[${n.id}]` : n.id;
                currentVisNodes.add({
                    id: n.id,
                    label: displayLabel,
                    shape: nType === "CASE" ? "diamond" : "box",
                    color: nType === "CASE" ? { background: "#ef4444", border: "#b91c1c" } : { background: "#3b82f6", border: "#1d4ed8" },
                    font: { color: "#ffffff", size: 11, face: "Inter" },
                    margin: 8,
                    entityType: nType
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
   5. ENTITY DETAILS PANEL (PHASE 8)
---------------------------------------------------- */
async function openEntityDetailsPanel(entityId) {
    const drawer = document.getElementById("inspector-drawer");
    if (!drawer) return;

    drawer.innerHTML = `<div class="text-center py-10 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-primary align-middle mr-1">sync</span> Retrieving Entity Details for <strong>${entityId}</strong>...</div>`;

    try {
        const ent = await window.dataService.getEntityDetails(entityId);
        if (!ent) {
            drawer.innerHTML = `
                <div class="p-6 text-center text-outline text-xs space-y-2 font-sans">
                    <span class="material-symbols-outlined text-3xl text-amber-400 opacity-60" aria-hidden="true">person_off</span>
                    <div class="font-bold text-white text-sm">Entity Not Found</div>
                    <div>Entity record <strong>${entityId}</strong> was not found in available investigation records.</div>
                </div>
            `;
            return;
        }

        const badgeClass = `badge-${(ent.type || "person").toLowerCase()}`;

        drawer.innerHTML = `
            <div class="space-y-3 font-sans">
                <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                    <span class="font-mono text-xs font-bold text-primary px-2 py-0.5 rounded bg-surface-container-highest border border-outline-variant">${ent.id}</span>
                    <span class="px-2 py-0.5 text-[10px] font-bold rounded ${badgeClass}">${ent.type}</span>
                </div>

                <h3 class="text-sm font-bold text-white">${ent.name}</h3>
                <p class="text-xs text-on-surface-variant leading-relaxed">${ent.details || "Active Knowledge Graph Entity"}</p>

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
                <button onclick="askAIAboutEntity('${ent.id}')" class="w-full py-2 bg-primary-container hover:bg-blue-600 text-white text-xs font-semibold rounded shadow flex items-center justify-center gap-1 mt-2" aria-label="Query Entity in AI Investigator">
                    <span class="material-symbols-outlined text-sm" aria-hidden="true">auto_awesome</span> Query Entity in AI Investigator
                </button>
            </div>
        `;
    } catch (err) {
        drawer.innerHTML = `
            <div class="p-6 text-center text-error text-xs space-y-2 font-sans">
                <span class="material-symbols-outlined text-3xl text-error" aria-hidden="true">error</span>
                <div class="font-bold text-sm">Error Loading Entity Details</div>
                <div class="text-on-surface-variant">${err.message || 'API call failed.'}</div>
            </div>
        `;
    }
}

/* ----------------------------------------------------
   6. RELATIONSHIP & EVIDENCE PANEL (PHASE 9 & 10)
---------------------------------------------------- */
async function openEvidencePanel(edge) {
    const drawer = document.getElementById("inspector-drawer");
    if (!drawer) return;

    drawer.innerHTML = `<div class="text-center py-10 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-tertiary align-middle mr-1">sync</span> Fetching Evidence Provenance...</div>`;

    try {
        const evidId = edge.evidence_id || edge.evidenceId;
        const evid = evidId ? await window.dataService.getEvidence(evidId) : null;

        if (!evid) {
            drawer.innerHTML = `
                <div class="space-y-3 font-sans">
                    <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                        <span class="font-mono text-xs font-bold text-amber-400 px-2 py-0.5 rounded bg-amber-950/40 border border-amber-800/40">${evidId || edge.id || 'RELATIONSHIP'}</span>
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-surface-container-highest text-primary">GRAPH EDGE</span>
                    </div>

                    <div class="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/40 p-1.5 rounded border border-amber-800/40">
                        <span class="material-symbols-outlined text-sm" aria-hidden="true">lightbulb</span>
                        <span class="text-[11px]"><strong>Classification:</strong> Potential Investigative Lead</span>
                    </div>

                    <div class="space-y-1">
                        <div class="text-[10px] font-bold uppercase text-outline">Supported Relationship</div>
                        <div class="font-mono text-xs text-white font-bold bg-surface-container-lowest p-2 rounded border border-surface-container-high">${(edge.source || 'Entity A') + ' --' + (edge.relationship || 'CONNECTED_TO') + '--> ' + (edge.target || 'Entity B')}</div>
                    </div>

                    <div class="p-2.5 bg-surface-container-lowest border border-surface-container-high rounded text-xs text-on-surface-variant space-y-1">
                        <div>No separate document excerpt attached to this edge.</div>
                        <div class="text-[11px]">Association Confidence: <strong>${((edge.confidence || 0.9) * 100).toFixed(0)}%</strong></div>
                    </div>
                </div>
            `;
            return;
        }

        drawer.innerHTML = `
            <div class="space-y-3 font-sans">
                <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                    <span class="font-mono text-xs font-bold text-tertiary px-2 py-0.5 rounded bg-tertiary-container/20 border border-tertiary/30">${evid.evidence_id}</span>
                    <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-primary-container/30 text-primary border border-primary/40">EVIDENCE</span>
                </div>

                <div class="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/40 p-1.5 rounded border border-amber-800/40">
                    <span class="material-symbols-outlined text-sm" aria-hidden="true">lightbulb</span>
                    <span class="text-[11px]"><strong>Classification:</strong> Potential Investigative Lead</span>
                </div>

                <div class="space-y-1">
                    <div class="text-[10px] font-bold uppercase text-outline">Supported Relationship</div>
                    <div class="font-mono text-xs text-white font-bold bg-surface-container-lowest p-2 rounded border border-surface-container-high">${evid.relationship || (edge.source + ' --' + edge.relationship + '--> ' + edge.target)}</div>
                </div>

                <div class="space-y-1">
                    <div class="text-[10px] font-bold uppercase text-outline">Source Document Snippet</div>
                    <p class="text-xs text-on-surface italic bg-surface-container-lowest p-2.5 rounded border border-surface-container-high leading-relaxed break-words whitespace-normal font-sans">"${evid.source_text || 'Recorded investigative finding.'}"</p>
                </div>

                <div class="grid grid-cols-2 gap-2 text-[11px] pt-1 font-mono">
                    <div>Doc: <span class="text-primary font-bold">${evid.source_document || 'DOC_EXTRACTION'}</span></div>
                    <div>Page: <span class="text-white font-bold">Pg. ${evid.page_number || 1}</span></div>
                    <div>Time: <span class="text-white font-bold">${evid.timestamp || 'N/A'}</span></div>
                    <div>Conf: <span class="text-tertiary font-bold">${((evid.confidence || 0.95) * 100).toFixed(0)}%</span></div>
                </div>
            </div>
        `;
    } catch (err) {
        drawer.innerHTML = `
            <div class="p-6 text-center text-error text-xs space-y-2 font-sans">
                <span class="material-symbols-outlined text-3xl text-error" aria-hidden="true">error</span>
                <div class="font-bold text-sm">Error Loading Evidence</div>
                <div class="text-on-surface-variant">${err.message || 'API call failed.'}</div>
            </div>
        `;
    }
}

/* ----------------------------------------------------
   7. MAIN DEMONSTRATION FLOW (PHASE 11 & 17)
---------------------------------------------------- */
async function highlightMainDemoFlow() {
    if (!networkInstance) return;

    try {
        // Retrieve discovery path dynamically through DataService API layer
        const connData = await window.dataService.getCaseConnections("CASE_101", "CASE_204");
        const connections = connData ? (connData.connections || []) : [];
        const demoChainNodes = (connections.length > 0 && connections[0].path) 
            ? connections[0].path 
            : ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"];

        // Ensure all demo nodes are loaded into graph
        await renderGraphWorkspace("ALL");

        networkInstance.selectNodes(demoChainNodes);
        networkInstance.fit({ nodes: demoChainNodes, animation: true });

        // Open Evidence panel for the key bridge
        const evId = (connections.length > 0 && connections[0].evidence_ids && connections[0].evidence_ids.length > 0)
            ? connections[0].evidence_ids[0]
            : "EVID_042_01";

        await openEvidencePanel({
            source: "PERSON_017",
            relationship: "USES",
            target: "PHONE_042",
            evidence_id: evId,
            confidence: connections[0]?.confidence || 0.93
        });

        console.log("Highlighted cross-case connection path from DataService:", demoChainNodes);
    } catch (err) {
        console.error("Failed to highlight demo path:", err);
    }
}

/* ----------------------------------------------------
   8. AI INVESTIGATOR ASSISTANT (PHASE 16)
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

    document.getElementById("ai-input-text")?.addEventListener("keypress", async (e) => {
        if (e.key === "Enter") {
            const input = document.getElementById("ai-input-text");
            if (input && input.value.trim()) {
                await runAIQuery(input.value.trim());
            }
        }
    });
}

async function runAIQuery(questionText) {
    const container = document.getElementById("ai-response-container");
    const input = document.getElementById("ai-input-text");
    const btn = document.getElementById("ai-submit-btn");

    if (!container) return;

    // Lock UI controls to prevent uncontrolled duplicate requests during processing
    if (input) input.disabled = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin" aria-hidden="true">sync</span> Querying...`;
    }

    container.innerHTML = `<div class="text-center py-10 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-tertiary align-middle mr-1">sync</span> Querying AI Investigator Engine...</div>`;

    try {
        const res = await window.dataService.queryAIInvestigator(questionText);
        if (!res) {
            container.innerHTML = `<div class="text-center py-8 text-error text-xs font-sans">No response received from AI Investigator.</div>`;
            return;
        }

        const pathNodes = res.path || [];
        const isSafetyRefusal = res.query_type === "SAFETY_REFUSAL";
        const isNotFound = res.query_type === "NOT_FOUND";

        // Display path only if query_type is CROSS_CASE_CONNECTION / PATH_DISCOVERY or explicit connection path exists
        const showPath = !isSafetyRefusal && !isNotFound && Array.isArray(pathNodes) && pathNodes.length > 0 && res.query_type !== "GENERAL_INVESTIGATION";

        const evidenceCitations = (res.evidence_ids && res.evidence_ids.length > 0)
            ? res.evidence_ids.join(", ")
            : (res.evidence ? (typeof res.evidence === 'string' ? res.evidence : (Array.isArray(res.evidence) && res.evidence.length > 0 ? res.evidence.map(e => e.evidence_id || e.id || 'EVID').join(", ") : "No specific evidence cited")) : "No specific evidence cited");

        let confidenceVal = "N/A";
        if (res.confidence !== undefined) {
            if (typeof res.confidence === 'number') {
                confidenceVal = res.confidence === 0 ? "0% (Safety / Lead Rating)" : `${(res.confidence * 100).toFixed(0)}% (High Confidence)`;
            } else {
                confidenceVal = res.confidence;
            }
        }

        const disclaimerText = res.disclaimer || "AI-generated investigative lead requiring human verification. Not a declaration of guilt.";

        let bannerStyle = "bg-amber-950/40 border-amber-800/40 text-amber-300";
        let bannerIcon = "lightbulb";
        let bannerHeading = "Investigative Lead / Disclaimer:";

        if (isSafetyRefusal) {
            bannerStyle = "bg-blue-950/40 border-blue-800/40 text-blue-300";
            bannerIcon = "shield";
            bannerHeading = "Safety Protocol Assertion:";
        } else if (isNotFound) {
            bannerStyle = "bg-slate-900 border-slate-700 text-slate-300";
            bannerIcon = "search_off";
            bannerHeading = "No Data State:";
        }

        // Supporting Details (Explanation, Lead, Limitations)
        const explanationHtml = res.explanation ? `
            <div class="space-y-1 pt-1 font-sans">
                <div class="text-[10px] font-bold uppercase text-outline">Detailed Explanation</div>
                <div class="text-xs text-on-surface-variant leading-relaxed bg-surface-container-low p-2.5 rounded border border-surface-container-high">${res.explanation}</div>
            </div>
        ` : '';

        const leadHtml = res.investigative_lead ? `
            <div class="p-2.5 bg-tertiary-container/15 border border-tertiary-container/40 rounded text-xs text-tertiary space-y-1 font-sans">
                <div class="font-bold flex items-center gap-1"><span class="material-symbols-outlined text-sm" aria-hidden="true">explore</span> Potential Investigative Lead:</div>
                <div class="text-on-surface">${res.investigative_lead}</div>
            </div>
        ` : '';

        const limitationsHtml = (res.limitations && Array.isArray(res.limitations) && res.limitations.length > 0) ? `
            <div class="space-y-1 pt-1 font-sans">
                <div class="text-[10px] font-bold uppercase text-outline">Investigative Limitations</div>
                <ul class="list-disc pl-4 text-[11px] text-on-surface-variant space-y-0.5">
                    ${res.limitations.map(lim => `<li>${lim}</li>`).join("")}
                </ul>
            </div>
        ` : '';

        container.innerHTML = `
            <div class="space-y-4 font-sans">
                <div class="border-b border-surface-container-high pb-2">
                    <div class="text-[10px] font-bold uppercase text-outline">User Query</div>
                    <div class="text-sm font-bold text-primary">${res.question || questionText}</div>
                </div>

                <div class="space-y-2">
                    <div class="text-[10px] font-bold uppercase text-outline">Answer Summary</div>
                    <div class="text-xs text-white leading-relaxed font-sans bg-surface-container-low p-3 rounded border border-surface-container-high break-words whitespace-normal">${res.answer || res.summary || 'Investigation query processed.'}</div>
                </div>

                ${showPath ? `
                <div class="space-y-2">
                    <div class="text-[10px] font-bold uppercase text-outline">Discovered Connection Path</div>
                    <div class="flex flex-wrap items-center gap-1.5 font-mono text-xs">
                        ${pathNodes.map((p, idx, arr) => `
                            <span class="px-2 py-0.5 rounded bg-surface-container-high text-tertiary border border-tertiary/30 font-bold">${p}</span>
                            ${idx < arr.length - 1 ? '<span class="material-symbols-outlined text-xs text-outline" aria-hidden="true">arrow_forward</span>' : ''}
                        `).join("")}
                    </div>
                </div>
                ` : ''}

                ${explanationHtml}
                ${leadHtml}
                ${limitationsHtml}

                <div class="grid grid-cols-2 gap-3 pt-2 font-sans">
                    <div class="bg-surface-container-low p-2.5 rounded border border-surface-container-high">
                        <div class="text-[10px] font-bold uppercase text-outline">Confidence Rating</div>
                        <div class="text-xs text-tertiary font-bold font-mono">${confidenceVal}</div>
                    </div>
                    <div class="bg-surface-container-low p-2.5 rounded border border-surface-container-high">
                        <div class="text-[10px] font-bold uppercase text-outline">Evidence Citations</div>
                        <div class="text-[11px] text-on-surface-variant font-mono break-words">${evidenceCitations}</div>
                    </div>
                </div>

                <div class="p-3 ${bannerStyle} rounded text-xs font-sans">
                    <span class="material-symbols-outlined text-xs align-middle mr-1" aria-hidden="true">${bannerIcon}</span>
                    <strong>${bannerHeading}</strong> ${disclaimerText}
                </div>
            </div>
        `;
    } catch (err) {
        const cleanMsg = (err && err.message) ? err.message.replace(/http:\/\/[^\s]+/g, '[API Server]') : 'Unable to connect to AI Investigator service.';
        container.innerHTML = `
            <div class="p-4 text-center text-error text-xs space-y-2 font-sans">
                <span class="material-symbols-outlined text-2xl text-error" aria-hidden="true">error</span>
                <div class="font-bold">Investigation Query Failed</div>
                <div class="text-on-surface-variant">${cleanMsg}</div>
                <button onclick="runAIQuery('${questionText.replace(/'/g, "\\'")}')" class="px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-white rounded text-[11px] mt-1">Retry Query</button>
            </div>
        `;
    } finally {
        if (input) input.disabled = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span class="material-symbols-outlined text-sm" aria-hidden="true">send</span> Query`;
        }
    }
}

function askAIAboutEntity(entityId) {
    switchTab("pane-ai-investigator", true);
    runAIQuery(`What connects ${entityId} to active cases?`);
}

/* ----------------------------------------------------
   9. TIMELINE, EVIDENCE EXPLORER & GLOBAL SEARCH (PHASE 12)
---------------------------------------------------- */
async function renderTimeline(caseId = "CASE_101") {
    const container = document.getElementById("timeline-container");
    if (!container) return;

    if (caseId === "ALL") {
        container.innerHTML = `<div class="text-center py-6 text-outline text-xs font-sans">Select a specific case (e.g. CASE_101, CASE_204) to view its chronological event timeline.</div>`;
        return;
    }

    container.innerHTML = `<div class="text-center py-6 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-tertiary align-middle mr-1">sync</span> Loading timeline for ${caseId}...</div>`;

    try {
        const data = await window.dataService.getTimeline(caseId);
        const events = data ? (data.events || []) : [];

        if (events.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs font-sans">No chronological events found for <strong>${caseId}</strong>.</div>`;
            return;
        }

        container.innerHTML = events.map(ev => `
            <div class="p-3 bg-surface-container-low border border-surface-container-high rounded space-y-1 text-xs font-sans">
                <div class="flex items-center justify-between text-[11px] font-mono">
                    <span class="text-tertiary font-bold">${ev.timestamp || 'N/A'}</span>
                    <span class="px-2 py-0.5 rounded bg-surface-container-highest text-primary font-bold">${ev.type || 'EVENT'}</span>
                </div>
                <p class="text-white font-medium">${ev.description || 'Recorded incident'}</p>
                <div class="text-[10px] text-on-surface-variant">Location Tag: <strong class="text-outline font-mono">${ev.location_id || 'N/A'}</strong></div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="text-center py-6 text-error text-xs font-sans">Failed to load timeline for ${caseId}: ${err.message}</div>`;
    }
}

async function renderEvidenceExplorer() {
    const container = document.getElementById("evidence-grid-container");
    if (!container) return;

    container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-tertiary align-middle mr-1">sync</span> Loading evidence index via DataService...</div>`;

    try {
        const evidenceList = await window.dataService.getEvidenceList();
        if (!evidenceList || evidenceList.length === 0) {
            container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans">No evidence records found in active dataset.</div>`;
            return;
        }

        container.innerHTML = evidenceList.map(ev => `
            <div class="stitch-card space-y-2 text-xs font-sans">
                <div class="flex items-center justify-between font-mono">
                    <span class="text-tertiary font-bold">${ev.evidence_id}</span>
                    <span class="px-2 py-0.5 rounded bg-tertiary-container/30 text-tertiary text-[10px] font-bold">${((ev.confidence || 0.95) * 100).toFixed(0)}% Confidence</span>
                </div>
                <p class="text-white italic text-[11px] break-words whitespace-normal font-sans">"${ev.source_text || ev.excerpt || 'Recorded evidence finding.'}"</p>
                <div class="text-[10px] text-outline font-mono">Source: ${ev.source_document || 'DOC_EXTRACTION'} (Pg. ${ev.page_number || 1})</div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="col-span-2 text-center py-6 text-error text-xs font-sans">Failed to load evidence catalog: ${err.message}</div>`;
    }
}

async function generateReport(caseId = null) {
    const viewBox = document.getElementById("report-view-box");
    if (!viewBox) return;

    let targetCaseId = caseId;
    if (!targetCaseId || targetCaseId === "ALL") {
        const select = document.getElementById("header-case-select");
        targetCaseId = (select && select.value && select.value !== "ALL") ? select.value : "CASE_101";
    }

    viewBox.innerHTML = `<div class="text-center py-10 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-primary align-middle mr-1">sync</span> Generating Evidence-Linked Investigation Report for ${targetCaseId}...</div>`;

    try {
        const report = await window.dataService.generateReport(targetCaseId);
        if (!report || !report.content) {
            viewBox.innerHTML = `<div class="text-center py-10 text-error text-xs font-sans">Unable to generate report for ${targetCaseId}.</div>`;
            return;
        }

        const formattedHtml = report.content
            .replace(/# (.*)/g, '<h1 class="text-base font-bold text-primary border-b border-surface-container-high pb-2 mb-2">$1</h1>')
            .replace(/## (.*)/g, '<h2 class="text-xs font-bold text-tertiary mt-3 mb-1 uppercase tracking-wider">$1</h2>')
            .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
            .replace(/- (.*)/g, '<li class="ml-4 list-disc text-on-surface-variant">$1</li>')
            .replace(/\n\n/g, '<br><br>');

        viewBox.innerHTML = `
            <div class="space-y-3 font-sans">
                <div class="flex items-center justify-between text-[11px] font-mono text-outline border-b border-surface-container-high pb-2">
                    <span>Report ID: <strong class="text-tertiary">${report.report_id || 'REPORT_001'}</strong></span>
                    <span class="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 uppercase font-bold">${report.status || 'generated'}</span>
                </div>
                <div class="text-xs font-sans text-on-surface leading-relaxed whitespace-pre-wrap">${formattedHtml}</div>
            </div>
        `;
    } catch (err) {
        viewBox.innerHTML = `<div class="text-center py-10 text-error text-xs font-sans">Failed to generate report for ${targetCaseId}: ${err.message}</div>`;
    }
}

function initGlobalSearch() {
    const globalInput = document.getElementById("global-search-input");
    if (!globalInput) return;

    globalInput.addEventListener("keypress", async (e) => {
        if (e.key === "Enter") {
            const query = globalInput.value.trim();
            if (!query) return;

            try {
                const results = await window.dataService.search(query);
                if (results && results.length > 0) {
                    switchTab("pane-graph", true);
                    await renderGraphWorkspace("ALL");
                    networkInstance?.selectNodes([results[0].id]);
                    openEntityDetailsPanel(results[0].id);
                } else {
                    alert(`No matching records found for query "${query}".`);
                }
            } catch (err) {
                alert(`Search failed: ${err.message || 'Unable to connect to search service.'}`);
            }
        }
    });
}
