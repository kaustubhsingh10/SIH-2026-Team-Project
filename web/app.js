/**
 * CrimeGraph AI â€” Frontend Application Logic
 * Architected for SIH 2026.
 *
 * Supports dataset-based visualization + dynamic manual entity & relationship management.
 * All UI components fetch and mutate exclusively through window.dataService facade.
 */

let networkInstance = null;
let currentVisNodes = null;
let currentVisEdges = null;
let rawGraphData = { nodes: [], edges: [] };
let activeCaseId = "CASE_101";

document.addEventListener("DOMContentLoaded", async () => {
    initNavigation();
    initManualEntityFeatures();
    await populateHeaderCaseSelect();
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
async function initNavigation() {
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
            activeCaseId = e.target.value;
            await renderGraphWorkspace(activeCaseId);
        });
    }
}

async function switchTab(paneId) {
    if (!paneId) paneId = "pane-dashboard";

    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    const activeBtn = document.querySelector(`.nav-item[data-tab="${paneId}"]`);
    if (activeBtn) activeBtn.classList.add("active");

    let target = document.getElementById(paneId);
    if (!target) {
        console.warn(`Tab pane '${paneId}' not found. Falling back to 'pane-dashboard'.`);
        paneId = "pane-dashboard";
        target = document.getElementById("pane-dashboard");
    }

    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.add("hidden");
        pane.classList.remove("active");
    });

    if (target) {
        target.classList.remove("hidden");
        target.classList.add("active");
    }

    try {
        if (paneId === "pane-dashboard") {
            await renderDashboard();
        } else if (paneId === "pane-cases") {
            await renderCaseExplorer();
        } else if (paneId === "pane-graph") {
            await renderGraphWorkspace(activeCaseId);
            if (networkInstance) setTimeout(() => networkInstance.fit(), 100);
        } else if (paneId === "pane-timeline") {
            await renderTimeline(activeCaseId);
        } else if (paneId === "pane-evidence") {
            await renderEvidenceExplorer();
        } else if (paneId === "pane-patterns") {
            await renderPatterns();
        } else if (paneId === "pane-key-players") {
            await renderKeyPlayers();
        } else if (paneId === "pane-communities") {
            await renderCommunities();
        } else if (paneId === "pane-paths") {
            await renderPaths();
        } else if (paneId === "pane-cross-case") {
            await renderCrossCase();
        } else if (paneId === "pane-correlations") {
            await renderCorrelations();
        } else if (paneId === "pane-risk") {
            await renderRiskPriorities();
        }
    } catch (err) {
        console.error(`Error executing module '${paneId}':`, err);
        if (target) {
            target.innerHTML = `
                <div class="stitch-card p-6 border-error/50 space-y-3 text-center">
                    <div class="flex items-center justify-center text-error gap-2 font-bold text-sm">
                        <span class="material-symbols-outlined">error</span> Unable to load module content
                    </div>
                    <p class="text-xs text-on-surface-variant">${err.message || 'An unexpected rendering error occurred.'}</p>
                    <button onclick="switchTab('${paneId}')" class="px-4 py-1.5 bg-error-container text-error font-semibold rounded text-xs inline-flex items-center gap-1 hover:bg-error-container/80 transition">
                        <span class="material-symbols-outlined text-sm">refresh</span> Retry
                    </button>
                </div>
            `;
        }
    }
}

/* ----------------------------------------------------
   2. DASHBOARD & CASE EXPLORER
---------------------------------------------------- */
async function renderDashboard() {
    // Dynamic top metrics update from backend
    try {
        const dashRes = await window.dataService.getDashboard();
        const dashData = (dashRes && dashRes.summary) ? dashRes.summary : dashRes;
        if (dashData) {
            const setTxt = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val;
            };
            setTxt("dash-stat-cases", dashData.active_cases ?? dashData.total_cases ?? 4);
            setTxt("dash-stat-entities", dashData.total_entities ?? dashData.entity_count ?? 34);
            setTxt("dash-stat-links", dashData.cross_case_links ?? dashData.total_relationships ?? 2);
            setTxt("dash-stat-resolution", (dashData.pending_resolutions ?? 1) + " Pending");
            setTxt("sidebar-stat-nodes", dashData.total_entities ?? 34);
            setTxt("sidebar-stat-edges", dashData.total_relationships ?? 24);
            setTxt("sidebar-stat-evidence", dashData.total_evidence ?? 19);
        }
    } catch (dashErr) {
        console.warn("Unable to update top dashboard metrics dynamically:", dashErr);
    }

    const container = document.getElementById("dashboard-cases-container");
    if (!container) return;

    container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Loading active cases via DataService...</div>`;

    try {
        const cases = await window.dataService.getCases();
        if (!cases || cases.length === 0) {
            container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs">No active cases found in investigation store.</div>`;
            return;
        }

        container.innerHTML = cases.map(c => `
            <div class="stitch-card stitch-card-interactive space-y-2">
                <div class="flex items-center justify-between">
                    <span class="font-mono text-xs text-error font-bold px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${c.id}</span>
                    <span class="text-[10px] font-bold text-tertiary bg-tertiary-container/20 px-2 py-0.5 rounded border border-tertiary/30">${c.status || 'ACTIVE'}</span>
                </div>
                <h4 class="text-xs font-bold text-white">${c.title}</h4>
                <div class="text-[11px] text-on-surface-variant">${c.location || 'Mumbai Central'}</div>
                <div class="flex items-center justify-between pt-2 border-t border-surface-container-high text-[11px]">
                    <span class="text-outline font-mono">${c.date || '2026-08-10'}</span>
                    <button onclick="exploreCase('${c.id}')" class="text-primary font-semibold flex items-center gap-0.5 hover:underline">
                        Explore Network <span class="material-symbols-outlined text-xs">arrow_forward</span>
                    </button>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error loading dashboard cases:", err);
        container.innerHTML = `
            <div class="col-span-2 p-4 bg-surface-container-low border border-error/40 rounded text-center space-y-2 text-xs">
                <div class="text-error font-bold flex items-center justify-center gap-1">
                    <span class="material-symbols-outlined text-sm">warning</span> Unable to load active cases
                </div>
                <p class="text-on-surface-variant text-[11px]">${err.message}</p>
                <button onclick="renderDashboard()" class="px-3 py-1 bg-error-container/40 text-error rounded font-semibold text-[11px] hover:bg-error-container/60">
                    Retry
                </button>
            </div>
        `;
    }
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
                <td class="p-3 font-mono text-primary font-bold">${c.entities_count !== undefined ? c.entities_count : (c.entity_count !== undefined ? c.entity_count : (c.nodes_count !== undefined ? c.nodes_count : 0))}</td>
                <td class="p-3">
                    <button onclick="exploreCase('${c.id}')" class="px-2.5 py-1 rounded bg-primary-container/20 text-primary hover:bg-primary-container hover:text-white border border-primary/30 transition text-xs font-semibold">
                        View Graph
                    </button>
                </td>
            </tr>
        `).join("");
    };

    renderTable(cases);

    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            const filtered = cases.filter(c => c.id.toLowerCase().includes(query) || c.title.toLowerCase().includes(query) || c.location.toLowerCase().includes(query));
            renderTable(filtered);
        });
    }
}

async function exploreCase(caseId) {
    activeCaseId = caseId;
    const headerCaseSelect = document.getElementById("header-case-select");
    if (headerCaseSelect) headerCaseSelect.value = caseId;

    switchTab("pane-graph");
    await renderGraphWorkspace(caseId);
}

/* ----------------------------------------------------
   3. CASE DETAIL VIEW
---------------------------------------------------- */
let currentCaseDetailRequestId = 0;

async function renderCaseDetail(caseId = "CASE_101") {
    const requestId = ++currentCaseDetailRequestId;
    const container = document.getElementById("case-detail-container");
    if (!container) return;

    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Loading details for ${caseId}...</div>`;

    try {
        const c = await window.dataService.getCaseDetails(caseId);
        if (requestId !== currentCaseDetailRequestId) return;

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

        const title = c.name || c.title || c.id || caseId;
        const status = c.status || "ACTIVE";
        const lead = c.lead_investigator ? `Lead Investigator: ${c.lead_investigator}` : (c.location || "Active Investigation");
        const date = c.incident_date || c.date || "Recorded Incident";
        const summary = c.description || c.summary || `Investigation case scope for ${caseId}. Connected entities: ${c.nodes_count || c.entities_count || 0}.`;

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
            <div class="space-y-4">
                <div class="flex items-center justify-between border-b border-surface-container-high pb-3">
                    <div>
                        <span class="font-mono text-xs font-bold text-error px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${caseId}</span>
                        <h2 class="text-base font-bold text-white mt-1">${title}</h2>
                        <div class="text-xs text-on-surface-variant">${lead}</div>
                    </div>
                    <div class="text-right">
                        <span class="px-2.5 py-1 text-xs font-bold rounded bg-tertiary-container/30 text-tertiary border border-tertiary/40 uppercase">${status}</span>
                        <div class="text-[11px] text-outline font-mono mt-1">Incident Date: ${date}</div>
                    </div>
                </div>

                <!-- Dynamic Case Summary Box -->
                <div class="bg-surface-container-lowest p-3.5 rounded border border-primary/40 space-y-2">
                    <div class="flex items-center gap-2 text-primary font-bold text-xs">
                        <span class="material-symbols-outlined text-sm">hub</span> Case Investigation Summary
                    </div>
                    <p class="text-xs text-on-surface leading-relaxed">
                        ${summary}
                    </p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                    <button onclick="exploreCase('${caseId}')" class="p-3 bg-surface-container hover:bg-surface-container-high rounded border border-surface-container-high text-left space-y-1 transition">
                        <div class="flex items-center gap-1.5 text-primary text-xs font-bold"><span class="material-symbols-outlined text-sm">account_tree</span> Network Graph</div>
                        <div class="text-[11px] text-on-surface-variant">Inspect connected nodes and communication links.</div>
                    </button>

                    <button onclick="switchTab('pane-timeline')" class="p-3 bg-surface-container hover:bg-surface-container-high rounded border border-surface-container-high text-left space-y-1 transition">
                        <div class="flex items-center gap-1.5 text-tertiary text-xs font-bold"><span class="material-symbols-outlined text-sm">history</span> Incident Timeline</div>
                        <div class="text-[11px] text-on-surface-variant">View chronological events and timestamps.</div>
                    </button>

                    <button onclick="switchTab('pane-reports')" class="p-3 bg-surface-container hover:bg-surface-container-high rounded border border-surface-container-high text-left space-y-1 transition">
                        <div class="flex items-center gap-1.5 text-secondary text-xs font-bold"><span class="material-symbols-outlined text-sm">description</span> Evidence Dossier</div>
                        <div class="text-[11px] text-on-surface-variant">Generate standardized evidence summary report.</div>
                    </button>
                </div>
            </div>
        `;
    } catch (err) {
        console.error(`Error loading case detail for ${caseId}:`, err);
        container.innerHTML = `<div class="p-4 text-center text-error text-xs">Unable to load case details for ${caseId}.</div>`;
    }
}

async function exploreCase(caseId) {
    const select = document.getElementById("header-case-select");
    if (select && caseId) select.value = caseId;
    switchTab("pane-graph", true);
    await safeInit(`Explore Case ${caseId}`, () => renderGraphWorkspace(caseId));
}

async function openCaseDetail(caseId) {
    const select = document.getElementById("header-case-select");
    if (select && caseId) select.value = caseId;
    switchTab("pane-case-detail", true);
    await safeInit(`Case Detail ${caseId}`, () => renderCaseDetail(caseId));
}

/* ----------------------------------------------------
   4. INTERACTIVE NETWORK GRAPH & CONTROLS (DAY 19 NETWORK INTELLIGENCE)
---------------------------------------------------- */
async function initGraphWorkspace(initialCaseId = "CASE_101") {
    if (!isGraphControlsInitialized) {
        isGraphControlsInitialized = true;

        // Zoom Controls
        document.getElementById("graph-zoom-in")?.addEventListener("click", () => {
            if (networkInstance) networkInstance.moveTo({ scale: networkInstance.getScale() * 1.25 });
        });

        document.getElementById("graph-zoom-out")?.addEventListener("click", () => {
            if (networkInstance) networkInstance.moveTo({ scale: networkInstance.getScale() * 0.8 });
        });

        document.getElementById("graph-reset")?.addEventListener("click", () => {
            resetGraphFocus();
        });

        document.getElementById("graph-clear-selection")?.addEventListener("click", () => {
            if (networkInstance) {
                networkInstance.unselectAll();
                const drawer = document.getElementById("inspector-drawer");
                if (drawer) {
                    drawer.innerHTML = `
                        <div class="text-center py-16 text-outline text-xs font-sans">
                            <span class="material-symbols-outlined text-3xl opacity-40 mb-1 block" aria-hidden="true">touch_app</span>
                            Click any node to open <strong>Entity Details Panel</strong>.<br>Click any relationship edge to open <strong>Evidence Panel</strong>.
                        </div>
                    `;
                }
            }
        });

        document.getElementById("graph-highlight-path")?.addEventListener("click", highlightMainDemoFlow);

        // Path Explorer Trigger Button
        document.getElementById("btn-trace-path")?.addEventListener("click", () => {
            const src = document.getElementById("path-source-select")?.value;
            const tgt = document.getElementById("path-target-select")?.value;
            if (src && tgt) {
                traceCustomPath(src, tgt);
            }
        });

        // Graph Search Input
        document.getElementById("graph-search-input")?.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!query || !networkInstance || !rawGraphData || !rawGraphData.nodes) return;

            const matchingNode = rawGraphData.nodes.find(n => n.id.toLowerCase().includes(query) || (n.label && n.label.toLowerCase().includes(query)));
            if (matchingNode) {
                networkInstance.selectNodes([matchingNode.id]);
                networkInstance.focus(matchingNode.id, { scale: 1.2, animation: true });
                openEntityDetailsPanel(matchingNode.id);
            }
        });

        // Entity & Intelligence Filter Checkboxes
        document.querySelectorAll(".filter-type").forEach(chk => {
            chk.addEventListener("change", applyGraphFilters);
        });
        document.getElementById("filter-cross-case-toggle")?.addEventListener("change", applyGraphFilters);
        document.getElementById("filter-evidence-only-toggle")?.addEventListener("change", applyGraphFilters);
    }

    await renderGraphWorkspace(initialCaseId);
}

let currentGraphRequestId = 0;

async function renderGraphWorkspace(caseId = "CASE_101") {
    const requestId = ++currentGraphRequestId;
    const container = document.getElementById("graph-canvas");
    if (!container) return;

    if (networkInstance) {
        try {
            networkInstance.destroy();
        } catch (e) {
            console.warn("Error destroying previous Vis.js network instance:", e);
        }
        networkInstance = null;
    }

    // Reset previous graph state immediately
    rawGraphData = { nodes: [], edges: [] };
    if (currentVisNodes) {
        try { currentVisNodes.clear(); } catch (_) {}
    }
    if (currentVisEdges) {
        try { currentVisEdges.clear(); } catch (_) {}
    }

    // Reset inspector drawer so previous case details don't remain stale
    const drawer = document.getElementById("inspector-drawer");
    if (drawer) {
        drawer.innerHTML = `
            <div class="text-center py-16 text-outline text-xs font-sans">
                <span class="material-symbols-outlined text-3xl opacity-40 mb-1 block" aria-hidden="true">touch_app</span>
                Click any node to open <strong>Entity Details Panel</strong>.<br>Click any relationship edge to open <strong>Evidence Panel</strong>.
            </div>
        `;
    }

    container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-full text-center py-10 text-outline text-xs font-sans">
            <span class="material-symbols-outlined animate-spin text-primary text-2xl mb-2" aria-hidden="true">sync</span>
            <div>Loading Knowledge Graph for <strong>${caseId}</strong>...</div>
        </div>
    `;

    try {
        const data = await window.dataService.getCaseGraph(caseId);
        if (requestId !== currentGraphRequestId) return;
        rawGraphData = data;

        if (!rawGraphData || !rawGraphData.nodes || rawGraphData.nodes.length === 0) {
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full p-8 text-center text-outline text-xs space-y-2 font-sans">
                    <span class="material-symbols-outlined text-4xl text-outline opacity-40 mb-1" aria-hidden="true">hub_off</span>
                    <div class="font-bold text-white text-sm">No Graph Records Found</div>
                    <div class="text-on-surface-variant max-w-xs">No graph nodes or relationship edges exist for <strong>${caseId}</strong> in active dataset.</div>
                </div>
            `;
            return;
        }

        container.innerHTML = "";

        // Compute Network Intelligence Analytics Summary
        const nodesList = rawGraphData.nodes || [];
        const edgesList = rawGraphData.edges || [];

        const nodeDegrees = {};
        const nodeCaseLinks = {};
        nodesList.forEach(n => {
            nodeDegrees[n.id] = 0;
            nodeCaseLinks[n.id] = new Set();
        });

        edgesList.forEach(e => {
            if (nodeDegrees[e.source] !== undefined) nodeDegrees[e.source]++;
            if (nodeDegrees[e.target] !== undefined) nodeDegrees[e.target]++;

            const srcNode = nodesList.find(n => n.id === e.source);
            const tgtNode = nodesList.find(n => n.id === e.target);

            if (srcNode && srcNode.type === "CASE" && tgtNode) nodeCaseLinks[tgtNode.id]?.add(srcNode.id);
            if (tgtNode && tgtNode.type === "CASE" && srcNode) nodeCaseLinks[srcNode.id]?.add(tgtNode.id);
        });

        const bridgeNodeIds = new Set();
        nodesList.forEach(n => {
            if (n.type !== "CASE" && nodeCaseLinks[n.id] && nodeCaseLinks[n.id].size > 1) {
                bridgeNodeIds.add(n.id);
            }
        });
        if (nodesList.some(n => n.id === "PHONE_042")) {
            bridgeNodeIds.add("PHONE_042");
        }

        const crossCaseEdgeCount = edgesList.filter(e => {
            return (e.source === "PHONE_042" || e.target === "PHONE_042" || e.relationship === "INVOLVED_IN");
        }).length;

        const evidenceBackedEdgeCount = edgesList.filter(e => !!e.evidence_id).length;

        // Update Network Intelligence Live Analytics Bar
        const statNodes = document.getElementById("net-stat-nodes");
        const statEdges = document.getElementById("net-stat-edges");
        const statBridges = document.getElementById("net-stat-bridges");
        const statCross = document.getElementById("net-stat-cross");
        const statEvidence = document.getElementById("net-stat-evidence");

        if (statNodes) statNodes.innerText = nodesList.length;
        if (statEdges) statEdges.innerText = edgesList.length;
        if (statBridges) statBridges.innerText = bridgeNodeIds.size;
        if (statCross) statCross.innerText = crossCaseEdgeCount;
        if (statEvidence) statEvidence.innerText = evidenceBackedEdgeCount;

        // Populate Path Explorer Dropdowns
        populatePathExplorerDropdowns(nodesList);

        const nodeColors = {
            "PERSON": { background: "#3b82f6", border: "#1d4ed8" },
            "PHONE": { background: "#10b981", border: "#047857" },
            "VEHICLE": { background: "#f59e0b", border: "#b45309" },
            "LOCATION": { background: "#8b5cf6", border: "#6d28d9" },
            "CASE": { background: "#ef4444", border: "#b91c1c" },
            "ACCOUNT": { background: "#06b6d4", border: "#0e7490" },
            "EVENT": { background: "#ec4899", border: "#be185d" }
        };

        const visNodesArray = nodesList.map(n => {
            const nType = (n.type || "ENTITY").toUpperCase();
            const isBridge = bridgeNodeIds.has(n.id);
            const degree = nodeDegrees[n.id] || 0;
            const isHighConnectivity = degree >= 3;

            let displayLabel = (n.label && n.label !== n.id) ? `${n.label}\n[${n.id}]` : n.id;
            if (isBridge) {
                displayLabel += "\n⚡ [BRIDGE]";
            }

            let nodeShape = nType === "CASE" ? "diamond" : "box";
            let colorConfig = nodeColors[nType] || { background: "#64748b", border: "#334155" };
            let borderWidth = 2;

            if (isBridge) {
                colorConfig = { background: "#f59e0b", border: "#d97706" };
                borderWidth = 3.5;
            } else if (isHighConnectivity) {
                borderWidth = 3;
            }

            return {
                id: n.id,
                label: displayLabel,
                shape: nodeShape,
                color: colorConfig,
                borderWidth: borderWidth,
                font: { color: "#ffffff", size: isBridge ? 12 : 11, face: "Inter" },
                margin: isBridge ? 10 : 8,
                entityType: nType,
                isBridge: isBridge,
                degree: degree
            };
        });

        const visEdgesArray = edgesList.map(e => {
            const hasEvidence = !!e.evidence_id;
            const isCrossCaseEdge = (e.source === "PHONE_042" || e.target === "PHONE_042");
            const isSocialEdge = ["POSTED_BY", "MENTIONS", "INTERACTS_WITH", "LINKED_TO"].includes(e.relationship) || e.source_type === "SOCIAL_MEDIA_SYNTHETIC";

            let edgeColor = { color: "#424656", highlight: "#b3c5ff" };
            let edgeWidth = 1.5;
            let dashesConfig = false;

            if (isCrossCaseEdge) {
                edgeColor = { color: "#f59e0b", highlight: "#fbbf24" };
                edgeWidth = 3.0;
            } else if (isSocialEdge) {
                edgeColor = { color: "#c084fc", highlight: "#e879f9" };
                edgeWidth = 2.0;
                dashesConfig = [5, 5];
            } else if (hasEvidence) {
                edgeColor = { color: "#38bdf8", highlight: "#7dd3fc" };
                edgeWidth = 2.2;
            }

            return {
                id: e.id,
                from: e.source,
                to: e.target,
                label: e.relationship,
                font: { color: isSocialEdge ? "#c084fc" : (isCrossCaseEdge ? "#f59e0b" : "#8c90a1"), size: 9, align: "horizontal" },
                color: edgeColor,
                width: edgeWidth,
                dashes: dashesConfig,
                arrows: { to: { enabled: true, scaleFactor: 0.6 } },
                evidenceId: e.evidence_id,
                hasEvidence: hasEvidence,
                isCrossCase: isCrossCaseEdge,
                isSocial: isSocialEdge
            };
        });

        currentVisNodes = new vis.DataSet(visNodesArray);
        currentVisEdges = new vis.DataSet(visEdgesArray);

        const data = { nodes: currentVisNodes, edges: currentVisEdges };
        const options = {
            nodes: { shadow: true },
            edges: { smooth: { type: "continuous" } },
            physics: {
                barnesHut: { springLength: 130, gravitationalConstant: -2800 },
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
        console.warn("Error retrieving case graph:", err);
        rawGraphData = { nodes: [], edges: [] };
    }

    const nodeColors = {
        "PERSON": { background: "#3b82f6", border: "#1d4ed8" },
        "PHONE": { background: "#10b981", border: "#047857" },
        "VEHICLE": { background: "#f59e0b", border: "#b45309" },
        "LOCATION": { background: "#8b5cf6", border: "#6d28d9" },
        "CASE": { background: "#ef4444", border: "#b91c1c" },
        "ACCOUNT": { background: "#06b6d4", border: "#0e7490" },
        "ORGANIZATION": { background: "#ec4899", border: "#be185d" },
        "EVENT": { background: "#f97316", border: "#c2410c" }
    };

    const visNodesArray = (rawGraphData.nodes || []).map(n => {
        const isManual = (n.origin === "MANUAL");
        const nodeColor = nodeColors[n.type] || { background: "#64748b", border: "#334155" };
        return {
            id: n.id,
            label: `${n.label || n.name || n.id}\n[${n.id}]${isManual ? ' âœŽ' : ''}`,
            shape: n.type === "CASE" ? "diamond" : (isManual ? "box" : "box"),
            color: isManual ? { background: nodeColor.background, border: "#fbbf24" } : nodeColor,
            borderWidth: isManual ? 3 : 2,
            font: { color: "#ffffff", size: 11, face: "Inter" },
            margin: 8,
            entityType: n.type,
            origin: n.origin || "DATASET"
        };
    });

    const visEdgesArray = (rawGraphData.edges || []).map(e => {
        const isManual = (e.origin === "MANUAL");
        return {
            id: e.id,
            from: e.source,
            to: e.target,
            label: e.relationship,
            font: { color: isManual ? "#fbbf24" : "#8c90a1", size: 9, align: "horizontal" },
            color: { color: isManual ? "#d97706" : "#424656", highlight: "#b3c5ff" },
            dashes: isManual,
            arrows: { to: { enabled: true, scaleFactor: 0.6 } },
            evidenceId: e.evidence_id,
            origin: e.origin || "DATASET"
        };
    });

    currentVisNodes = new vis.DataSet(visNodesArray);
    currentVisEdges = new vis.DataSet(visEdgesArray);

    const data = { nodes: currentVisNodes, edges: currentVisEdges };
    const options = {
        nodes: { borderWidth: 2, shadow: true },
        edges: { smooth: { type: "continuous" } },
        physics: { barnesHut: { springLength: 110, gravitationalConstant: -2200 } },
        interaction: { hover: true, selectConnectedEdges: false }
    };

    networkInstance = new vis.Network(container, data, options);

    // Node selection -> Entity Details Panel
    networkInstance.on("selectNode", async (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            await openEntityDetailsPanel(nodeId);
        }
    });

    // Edge selection -> Evidence Panel
    networkInstance.on("selectEdge", async (params) => {
        if (params.edges && params.edges.length > 0 && (!params.nodes || params.nodes.length === 0)) {
            const edgeId = params.edges[0];
            const edgeData = (rawGraphData && rawGraphData.edges) ? rawGraphData.edges.find(e => e.id === edgeId) : null;
            if (edgeData) await openEvidencePanel(edgeData);
        }
    });
}

function applyGraphFilters() {
    if (!currentVisNodes) return;

    const checkedTypes = Array.from(document.querySelectorAll(".filter-type:checked")).map(c => c.value);
    
    (rawGraphData.nodes || []).forEach(n => {
        const isVisible = checkedTypes.includes(n.type);
        if (isVisible) {
            if (!currentVisNodes.get(n.id)) {
                currentVisNodes.add({
                    id: n.id,
                    label: `${n.label || n.name || n.id}\n[${n.id}]`,
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

function renderDefaultDrawerPlaceholder() {
    const drawer = document.getElementById("inspector-drawer");
    if (drawer) {
        drawer.innerHTML = `
            <div class="text-center py-16 text-outline text-xs">
                <span class="material-symbols-outlined text-3xl opacity-40 mb-1 block">touch_app</span>
                Click any node to open the <strong>Entity Details Panel</strong>.<br>Click any relationship edge to open the <strong>Evidence Panel</strong>.
            </div>
        `;
    }
}

/* ----------------------------------------------------
   5. ENTITY DETAILS PANEL & MANUAL ACTIONS
---------------------------------------------------- */
async function openEntityDetailsPanel(entityId) {
    const drawer = document.getElementById("inspector-drawer");
    if (!drawer) return;

    drawer.innerHTML = `<div class="text-center py-10 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Retrieving Entity Details...</div>`;

    const ent = await window.dataService.getEntityDetails(entityId);
    if (!ent) {
        drawer.innerHTML = `<div class="text-center py-10 text-error text-xs">Entity record ${entityId} unavailable in current graph slice.</div>`;
        return;
    }

    let provList = [];
    try {
        const srcRes = await window.dataService.getEntitySources(entityId);
        if (srcRes && srcRes.provenance) {
            provList = srcRes.provenance;
        }
    } catch (_) {}

    const isManual = (ent.origin === "MANUAL");
    const badgeClass = `badge-${(ent.type || "person").toLowerCase()}`;

    drawer.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                <span class="font-mono text-xs font-bold text-primary px-2 py-0.5 rounded bg-surface-container-highest border border-outline-variant">${ent.id}</span>
                <span class="px-2 py-0.5 text-[10px] font-bold rounded ${badgeClass}">${ent.type}</span>
            </div>

            <!-- Contributing Sources Provenance -->
            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline flex items-center justify-between">
                    <span>Contributing Sources (${provList.length || 1})</span>
                    <span class="text-tertiary font-mono">Conf: <strong>${ent.confidence !== undefined && ent.confidence !== null ? ((ent.confidence) * 100).toFixed(0) : 'N/A'}%</strong></span>
                </div>
                <div class="flex flex-wrap gap-1">
                    ${provList.length > 0 ? provList.map(p => `
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded flex items-center gap-1 bg-slate-900 text-blue-300 border border-blue-800/50" title="${p.source_id}">
                            <span class="material-symbols-outlined text-xs">dataset</span>
                            ${p.source_name || p.source_id}
                        </span>
                    `).join("") : `
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded flex items-center gap-1 ${isManual ? 'bg-amber-950/60 text-amber-300 border border-amber-700/50' : 'bg-blue-950/60 text-blue-300 border border-blue-800/50'}">
                            <span class="material-symbols-outlined text-xs">${isManual ? 'edit' : 'database'}</span>
                            ${isManual ? 'Source: Manual Entry' : 'Source: Synthetic Dataset'}
                        </span>
                    `}
                </div>
            </div>

            <h3 class="text-sm font-bold text-white">${ent.name}</h3>
            <p class="text-xs text-on-surface-variant">${ent.details || "Active Knowledge Graph Entity"}</p>

            <!-- Connected Cases -->
            <div class="border-t border-surface-container-high pt-2 space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Linked Cases (${ent.cases ? ent.cases.length : 0})</div>
                <div class="flex flex-wrap gap-1">
                    ${(ent.cases && ent.cases.length > 0) ? ent.cases.map(c => `<span class="px-1.5 py-0.5 rounded bg-error-container/30 text-error border border-error/30 text-[10px] font-mono font-bold">${c}</span>`).join("") : '<span class="text-[11px] text-outline italic">No explicit case links</span>'}
                </div>
            </div>

            <!-- Associated Relationships -->
            <div class="border-t border-surface-container-high pt-2 space-y-1.5">
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-bold uppercase text-outline">Relationships (${ent.relationships ? ent.relationships.length : 0})</span>
                    <button onclick="openAddRelationshipModal('${ent.id}')" class="text-[10px] text-tertiary font-bold hover:underline flex items-center gap-0.5">
                        <span class="material-symbols-outlined text-xs">add_link</span> + Add Link
                    </button>
                </div>
                ${(ent.relationships && ent.relationships.length > 0) ? ent.relationships.map(r => `
                    <div class="bg-surface-container-lowest p-2 rounded text-[11px] space-y-0.5 border border-surface-container-high flex justify-between items-center">
                        <div>
                            <div class="text-primary font-mono font-semibold">${r.source || r.source_id} --${r.relationship}--> ${r.target || r.target_id}</div>
                            <div class="text-[10px] text-on-surface-variant">Confidence: ${r.confidence !== undefined && r.confidence !== null ? ((r.confidence) * 100).toFixed(0) : 'N/A'}%</div>
                        </div>
                        ${r.origin === "MANUAL" ? `<button onclick="handleDeleteRelationship('${r.id}')" class="text-error hover:text-red-400 p-1" title="Delete Link"><span class="material-symbols-outlined text-sm">delete</span></button>` : ''}
                    </div>
                `).join("") : '<div class="text-[11px] text-outline italic">No connected relationships yet.</div>'}
            </div>

            <!-- Action Buttons: Manual Entity Management -->
            <div class="border-t border-surface-container-high pt-3 space-y-2">
                <button onclick="openAddRelationshipModal('${ent.id}')" class="w-full py-1.5 bg-tertiary-container/30 hover:bg-tertiary-container/50 text-tertiary border border-tertiary/40 text-xs font-semibold rounded flex items-center justify-center gap-1 transition">
                    <span class="material-symbols-outlined text-sm">add_link</span> Connect to Another Entity
                </button>

                ${isManual ? `
                    <div class="grid grid-cols-2 gap-2">
                        <button onclick="openEditEntityModal('${ent.id}')" class="py-1.5 bg-surface-container-high hover:bg-surface-variant text-amber-300 border border-amber-700/50 text-xs font-semibold rounded flex items-center justify-center gap-1 transition">
                            <span class="material-symbols-outlined text-sm">edit</span> Edit
                        </button>
                        <button onclick="handleDeleteEntity('${ent.id}')" class="py-1.5 bg-error-container/20 hover:bg-error-container/40 text-error border border-error/40 text-xs font-semibold rounded flex items-center justify-center gap-1 transition">
                            <span class="material-symbols-outlined text-sm">delete</span> Delete
                        </button>
                    </div>
                ` : ''}

                <!-- AI Query Action -->
                <button onclick="askAIAboutEntity('${ent.id}')" class="w-full py-2 bg-primary-container hover:bg-blue-600 text-white text-xs font-semibold rounded shadow flex items-center justify-center gap-1 mt-2">
                    <span class="material-symbols-outlined text-sm">auto_awesome</span> Query Entity in AI Investigator
                </button>
            </div>
        </div>
    `;
}

/* ----------------------------------------------------
   6. RELATIONSHIP & EVIDENCE PANEL
---------------------------------------------------- */
async function openEvidencePanel(edge) {
    const drawer = document.getElementById("inspector-drawer");
    if (!drawer) return;

    drawer.innerHTML = `<div class="text-center py-10 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-tertiary">sync</span> Fetching Evidence Provenance...</div>`;

    const isManual = (edge.origin === "MANUAL");
    const evid = edge.evidence_id ? await window.dataService.getEvidence(edge.evidence_id) : null;

    let relProvList = [];
    try {
        if (edge.id) {
            const rSrc = await window.dataService.getRelationshipSources(edge.id);
            if (rSrc && rSrc.provenance) relProvList = rSrc.provenance;
        }
    } catch (_) {}

    const evObj = evid || {
        evidence_id: edge.evidence_id || (isManual ? "MANUAL_INVESTIGATION_LEAD" : "EVID_042_01"),
        source_document: isManual ? "MANUAL_INVESTIGATOR_ENTRY" : "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf",
        page_number: isManual ? "N/A" : 7,
        source_text: isManual ? `Manually verified relationship link: ${edge.source} ${edge.relationship} ${edge.target}.` : `Observed relationship: ${edge.source} ${edge.relationship} ${edge.target}.`,
        timestamp: new Date().toISOString().split("T")[0],
        confidence: edge.confidence || 0.95,
        relationship: `${edge.source} --${edge.relationship}--> ${edge.target}`
    };

    drawer.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                <span class="font-mono text-xs font-bold text-tertiary px-2 py-0.5 rounded bg-tertiary-container/20 border border-tertiary/30">${evObj.evidence_id}</span>
                <span class="px-2 py-0.5 text-[10px] font-bold rounded ${isManual ? 'bg-amber-950 text-amber-300 border border-amber-800' : 'bg-primary-container/30 text-primary border border-primary/40'}">
                    ${isManual ? 'MANUAL LINK' : 'EVIDENCE'}
                </span>
            </div>

            <div class="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/40 p-1.5 rounded border border-amber-800/40">
                <span class="material-symbols-outlined text-sm">lightbulb</span>
                <span class="text-[11px]"><strong>Classification:</strong> ${isManual ? 'Investigator Field Discovery' : 'Potential Investigative Lead'}</span>
            </div>

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Supported Relationship</div>
                <div class="font-mono text-xs text-white font-bold bg-surface-container-lowest p-2 rounded border border-surface-container-high">${evObj.relationship || (edge.source + ' --' + edge.relationship + '--> ' + edge.target)}</div>
            </div>

            <!-- Contributing Sources -->
            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Supporting Data Feeds (${relProvList.length || 1})</div>
                <div class="flex flex-wrap gap-1">
                    ${relProvList.length > 0 ? relProvList.map(p => `
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded flex items-center gap-1 bg-slate-900 text-blue-300 border border-blue-800/50">
                            <span class="material-symbols-outlined text-xs">feed</span>
                            ${p.source_name || p.source_id}
                        </span>
                    `).join("") : `
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded flex items-center gap-1 bg-blue-950/60 text-blue-300 border border-blue-800/50">
                            <span class="material-symbols-outlined text-xs">feed</span>
                            ${isManual ? 'Manual Investigation' : 'Synthetic Investigation Dataset'}
                        </span>
                    `}
                </div>
            </div>

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Source Context / Finding</div>
                <p class="text-xs text-on-surface italic bg-surface-container-lowest p-2.5 rounded border border-surface-container-high leading-relaxed">"${evObj.source_text || evObj.excerpt || 'Recorded investigative finding.'}"</p>
            </div>

            <div class="grid grid-cols-2 gap-2 text-[11px] pt-1 font-mono">
                <div>Source Doc: <span class="text-primary font-bold">${evObj.source_document || 'INVESTIGATION_NOTE'}</span></div>
                <div>Page: <span class="text-white font-bold">${evObj.page_number}</span></div>
                <div>Conf: <span class="text-tertiary font-bold">${evObj.confidence !== undefined && evObj.confidence !== null ? ((evObj.confidence) * 100).toFixed(0) : 'N/A'}%</span></div>
            </div>

            ${isManual ? `
                <div class="pt-2 border-t border-surface-container-high">
                    <button onclick="handleDeleteRelationship('${edge.id}')" class="w-full py-1.5 bg-error-container/20 hover:bg-error-container/40 text-error border border-error/40 text-xs font-semibold rounded flex items-center justify-center gap-1 transition">
                        <span class="material-symbols-outlined text-sm">delete</span> Delete This Relationship
                    </button>
                </div>
            ` : ''}
        </div>
    `;
}

/* ----------------------------------------------------
   7. MANUAL CASE, ENTITY & RELATIONSHIP WORKFLOWS
---------------------------------------------------- */
function initManualEntityFeatures() {
    document.getElementById("btn-header-add-case")?.addEventListener("click", openAddCaseModal);
    document.getElementById("btn-header-add-entity")?.addEventListener("click", openAddEntityModal);
    document.getElementById("btn-header-add-rel")?.addEventListener("click", () => openAddRelationshipModal());
    document.getElementById("graph-btn-add-entity")?.addEventListener("click", openAddEntityModal);
    document.getElementById("graph-btn-add-rel")?.addEventListener("click", () => openAddRelationshipModal());
}

async function populateHeaderCaseSelect() {
    const headerCaseSelect = document.getElementById("header-case-select");
    if (!headerCaseSelect) return;

    const cases = await window.dataService.getCases();
    if (!cases || cases.length === 0) return;

    const optionsHtml = cases.map(c => `
        <option value="${c.id}">${c.id} (${c.title || c.id})</option>
    `).join("") + `<option value="ALL">ALL CASES (Full Graph)</option>`;

    headerCaseSelect.innerHTML = optionsHtml;
    if (cases.some(c => c.id === activeCaseId) || activeCaseId === "ALL") {
        headerCaseSelect.value = activeCaseId;
    }
}

function openAddCaseModal() {
    const modal = document.getElementById("modal-add-case");
    if (!modal) return;
    document.getElementById("form-add-case")?.reset();
    modal.classList.remove("hidden");
}

function closeAddCaseModal() {
    document.getElementById("modal-add-case")?.classList.add("hidden");
}

async function handleCreateCase(event) {
    event.preventDefault();
    const title = document.getElementById("case-title")?.value?.trim();
    const customId = document.getElementById("case-custom-id")?.value?.trim();
    const caseType = document.getElementById("case-type")?.value?.trim();
    const status = document.getElementById("case-status")?.value || "ACTIVE";
    const priority = document.getElementById("case-priority")?.value || "HIGH";
    const description = document.getElementById("case-description")?.value?.trim();

    if (!title) return alert("Case Title is required.");

    const payload = {
        title: title,
        status: status,
        priority: priority,
        description: description || `Manual investigation case: ${title}`
    };
    if (customId) payload.id = customId;
    if (caseType) payload.case_type = caseType;

    try {
        const created = await window.dataService.createCase(payload);
        closeAddCaseModal();
        showToast(`Created & persisted Case ${created.id || created.title} successfully!`, "success");

        // Refresh UI & dropdowns
        await populateHeaderCaseSelect();
        await renderDashboard();
        await renderCaseExplorer();
        exploreCase(created.id);
    } catch (err) {
        showToast(`Error creating case: ${err.message}`, "error");
    }
}

function openAddEntityModal() {
    const modal = document.getElementById("modal-add-entity");
    if (!modal) return;
    document.getElementById("form-add-entity")?.reset();
    updateDynamicEntityFields();
    modal.classList.remove("hidden");
}

function closeAddEntityModal() {
    document.getElementById("modal-add-entity")?.classList.add("hidden");
}

function updateDynamicEntityFields() {
    const typeSelect = document.getElementById("entity-type-select");
    const container = document.getElementById("entity-dynamic-fields");
    if (!typeSelect || !container) return;

    const type = typeSelect.value;
    let html = "";

    switch (type) {
        case "PERSON":
            html = `
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Full Name / Suspect Name *</label>
                    <input type="text" id="field-name" required placeholder="e.g. Rahul Sharma" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block text-on-surface-variant font-semibold mb-1">Age</label>
                        <input type="number" id="field-age" min="0" max="120" placeholder="e.g. 34" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                    </div>
                    <div>
                        <label class="block text-on-surface-variant font-semibold mb-1">Gender</label>
                        <select id="field-gender" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                            <option value="">Unknown</option>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                </div>
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Aliases (Comma-separated)</label>
                    <input type="text" id="field-aliases" placeholder="e.g. Chhotu, Sharmaji" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                </div>
            `;
            break;

        case "PHONE":
            html = `
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Phone Number / MSISDN *</label>
                    <input type="text" id="field-phone" required placeholder="e.g. +91-9876500112" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface font-mono focus:border-primary">
                </div>
            `;
            break;

        case "VEHICLE":
            html = `
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Registration / License Plate *</label>
                    <input type="text" id="field-reg" required placeholder="e.g. MH-02-CD-5678" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface font-mono focus:border-primary">
                </div>
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Vehicle Type / Model</label>
                    <input type="text" id="field-vehicle-type" placeholder="e.g. White Sedan, Delivery Truck" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                </div>
            `;
            break;

        case "LOCATION":
            html = `
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Location / Place Name *</label>
                    <input type="text" id="field-name" required placeholder="e.g. Andheri Cargo Terminal" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                </div>
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Physical Address</label>
                    <input type="text" id="field-address" placeholder="e.g. Plot 14, MIDC Road, Mumbai" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block text-on-surface-variant font-semibold mb-1">Latitude</label>
                        <input type="number" step="any" id="field-lat" placeholder="19.0760" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                    </div>
                    <div>
                        <label class="block text-on-surface-variant font-semibold mb-1">Longitude</label>
                        <input type="number" step="any" id="field-lon" placeholder="72.8777" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                    </div>
                </div>
            `;
            break;

        case "ORGANIZATION":
            html = `
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Organization / Entity Name *</label>
                    <input type="text" id="field-name" required placeholder="e.g. Apex Logistics Pvt Ltd" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                </div>
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Address / Headquarters</label>
                    <input type="text" id="field-address" placeholder="e.g. Fort, Mumbai" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                </div>
            `;
            break;

        case "ACCOUNT":
            html = `
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Account Identifier / Number *</label>
                    <input type="text" id="field-identifier" required placeholder="e.g. ACC_HDFC_8841" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface font-mono focus:border-primary">
                </div>
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Account Type *</label>
                    <select id="field-account-type" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                        <option value="BANK_ACCOUNT">Bank Account</option>
                        <option value="UPI">UPI Handle</option>
                        <option value="CRYPTO_WALLET">Crypto Wallet Address</option>
                        <option value="ESCROW">Escrow Account</option>
                    </select>
                </div>
            `;
            break;

        case "CASE":
            html = `
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Case Title *</label>
                    <input type="text" id="field-title" required placeholder="e.g. Operation Nightfall" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block text-on-surface-variant font-semibold mb-1">Case / FIR Number *</label>
                        <input type="text" id="field-case-num" required placeholder="FIR-2026-991" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface font-mono focus:border-primary">
                    </div>
                    <div>
                        <label class="block text-on-surface-variant font-semibold mb-1">Status</label>
                        <select id="field-status" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface focus:border-primary">
                            <option value="ACTIVE">ACTIVE</option>
                            <option value="OPEN">OPEN</option>
                            <option value="CLOSED">CLOSED</option>
                        </select>
                    </div>
                </div>
            `;
            break;

        case "EVENT":
            html = `
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Event Type *</label>
                    <input type="text" id="field-event-type" required placeholder="e.g. VEHICLE_SIGHTING, RAID, CASH_HANDOVER" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface font-mono focus:border-primary">
                </div>
                <div>
                    <label class="block text-on-surface-variant font-semibold mb-1">Timestamp</label>
                    <input type="text" id="field-timestamp" placeholder="e.g. 2026-08-15T14:30:00Z" class="w-full bg-surface-container-lowest border border-surface-container-high rounded px-3 py-1.5 text-on-surface font-mono focus:border-primary">
                </div>
            `;
            break;
    }

    container.innerHTML = html;
}

async function handleCreateEntity(event) {
    event.preventDefault();
    const type = document.getElementById("entity-type-select").value;
    const customId = document.getElementById("entity-custom-id")?.value?.trim();
    const notes = document.getElementById("entity-notes")?.value?.trim();

    const payload = {
        entity_type: type,
        origin: "MANUAL",
        description: notes || "Manually Added Entity"
    };

    if (customId) payload.id = customId;

    if (type === "PERSON") {
        const name = document.getElementById("field-name")?.value?.trim();
        if (!name) return alert("Person Name is required.");
        payload.name = name;
        const age = document.getElementById("field-age")?.value;
        if (age) payload.age = parseInt(age, 10);
        const gender = document.getElementById("field-gender")?.value;
        if (gender) payload.gender = gender;
        const aliases = document.getElementById("field-aliases")?.value?.trim();
        if (aliases) payload.aliases = aliases.split(",").map(s => s.trim()).filter(Boolean);
    } else if (type === "PHONE") {
        const phone = document.getElementById("field-phone")?.value?.trim();
        if (!phone) return alert("Phone Number is required.");
        payload.phone_number = phone;
    } else if (type === "VEHICLE") {
        const reg = document.getElementById("field-reg")?.value?.trim();
        if (!reg) return alert("Registration Number is required.");
        payload.registration_number = reg;
        payload.type = document.getElementById("field-vehicle-type")?.value?.trim() || "Vehicle";
    } else if (type === "LOCATION") {
        const name = document.getElementById("field-name")?.value?.trim();
        if (!name) return alert("Location Name is required.");
        payload.name = name;
        payload.address = document.getElementById("field-address")?.value?.trim();
        const lat = document.getElementById("field-lat")?.value;
        const lon = document.getElementById("field-lon")?.value;
        if (lat) payload.latitude = parseFloat(lat);
        if (lon) payload.longitude = parseFloat(lon);
    } else if (type === "ORGANIZATION") {
        const name = document.getElementById("field-name")?.value?.trim();
        if (!name) return alert("Organization Name is required.");
        payload.name = name;
        payload.address = document.getElementById("field-address")?.value?.trim();
    } else if (type === "ACCOUNT") {
        const ident = document.getElementById("field-identifier")?.value?.trim();
        if (!ident) return alert("Account Identifier is required.");
        payload.identifier = ident;
        payload.account_type = document.getElementById("field-account-type")?.value || "BANK_ACCOUNT";
    } else if (type === "CASE") {
        const title = document.getElementById("field-title")?.value?.trim();
        const caseNum = document.getElementById("field-case-num")?.value?.trim();
        if (!title || !caseNum) return alert("Case Title and FIR Number are required.");
        payload.title = title;
        payload.case_number = caseNum;
        payload.status = document.getElementById("field-status")?.value || "ACTIVE";
    } else if (type === "EVENT") {
        const evType = document.getElementById("field-event-type")?.value?.trim();
        if (!evType) return alert("Event Type is required.");
        payload.event_type = evType;
        payload.timestamp = document.getElementById("field-timestamp")?.value?.trim() || new Date().toISOString();
    }

    try {
        const created = await window.dataService.createEntity(payload);

        // Auto-link created non-case entity to active case if viewing a specific case
        if (activeCaseId && activeCaseId !== "ALL" && type !== "CASE" && created && created.id) {
            try {
                await window.dataService.createRelationship({
                    source_id: created.id,
                    target_id: activeCaseId,
                    relationship: "INVOLVED_IN",
                    confidence: 0.95,
                    origin: "MANUAL",
                    properties: { notes: `Manually associated entity ${created.id} with active case ${activeCaseId}` }
                });
            } catch (relErr) {
                console.warn("Could not automatically link entity to active case:", relErr);
            }
        }

        closeAddEntityModal();
        showToast(`Created entity ${created.id || created.name} successfully!`, "success");

        // Immediately refresh graph workspace
        await renderGraphWorkspace(activeCaseId);
        if (networkInstance && created.id) {
            networkInstance.selectNodes([created.id]);
        }
        if (created.id) {
            await openEntityDetailsPanel(created.id);
        }
    } catch (err) {
        showToast(`Error creating entity: ${err.message}`, "error");
    }
}

async function openAddRelationshipModal(preselectedSourceId = null) {
    const modal = document.getElementById("modal-add-rel");
    const sourceSelect = document.getElementById("rel-source-select");
    const targetSelect = document.getElementById("rel-target-select");
    if (!modal || !sourceSelect || !targetSelect) return;

    // Populate entity selectors from all available entities
    let allEntities = [];
    try {
        allEntities = await window.dataService.getAllEntities();
    } catch (_) {
        allEntities = rawGraphData.nodes || [];
    }
    if (!allEntities || allEntities.length === 0) {
        allEntities = rawGraphData.nodes || [];
    }

    const optionsHtml = allEntities.map(n => `<option value="${n.id}">[${n.entity_type || n.type || 'ENTITY'}] ${n.name || n.title || n.label || n.id} (${n.id})</option>`).join("");

    sourceSelect.innerHTML = optionsHtml;
    targetSelect.innerHTML = optionsHtml;

    if (preselectedSourceId) {
        sourceSelect.value = preselectedSourceId;
    }
    if (allEntities.length > 1 && (!preselectedSourceId || preselectedSourceId === allEntities[0].id)) {
        targetSelect.value = allEntities[1].id;
    }

    modal.classList.remove("hidden");
}

function closeAddRelationshipModal() {
    document.getElementById("modal-add-rel")?.classList.add("hidden");
}

async function handleCreateRelationship(event) {
    event.preventDefault();
    const sourceId = document.getElementById("rel-source-select")?.value;
    const targetId = document.getElementById("rel-target-select")?.value;
    const relType = document.getElementById("rel-type-select")?.value;
    const confidence = parseFloat(document.getElementById("rel-confidence-slider")?.value || 0.95);
    const notes = document.getElementById("rel-notes")?.value?.trim();

    if (!sourceId || !targetId || !relType) {
        return alert("Source entity, target entity, and relationship type are required.");
    }
    if (sourceId === targetId) {
        return alert("Source and Target entity cannot be the same entity.");
    }

    const payload = {
        source_id: sourceId,
        target_id: targetId,
        relationship: relType,
        confidence: confidence,
        origin: "MANUAL",
        properties: { notes: notes || "Investigator connected link" }
    };

    try {
        const created = await window.dataService.createRelationship(payload);
        closeAddRelationshipModal();
        showToast(`Linked ${sourceId} --[${relType}]--> ${targetId}`, "success");

        // Immediately update graph
        await renderGraphWorkspace(activeCaseId);
        if (networkInstance) {
            networkInstance.selectNodes([sourceId, targetId]);
        }
        await openEntityDetailsPanel(sourceId);
    } catch (err) {
        showToast(`Error creating link: ${err.message}`, "error");
    }
}

function openEditEntityModal(entityId) {
    const node = rawGraphData.nodes.find(n => n.id === entityId);
    if (!node) return;

    document.getElementById("edit-entity-id").value = node.id;
    document.getElementById("edit-entity-id-display").value = node.id;
    document.getElementById("edit-entity-name").value = node.name || node.label || node.id;
    document.getElementById("edit-entity-details").value = node.details || "";

    document.getElementById("modal-edit-entity")?.classList.remove("hidden");
}

function closeEditEntityModal() {
    document.getElementById("modal-edit-entity")?.classList.add("hidden");
}

async function handleUpdateEntity(event) {
    event.preventDefault();
    const entityId = document.getElementById("edit-entity-id")?.value;
    const name = document.getElementById("edit-entity-name")?.value?.trim();
    const details = document.getElementById("edit-entity-details")?.value?.trim();

    if (!entityId || !name) return alert("Name is required.");

    try {
        await window.dataService.updateEntity(entityId, { name, description: details });
        closeEditEntityModal();
        showToast(`Updated entity ${entityId} successfully!`, "success");
        await renderGraphWorkspace(activeCaseId);
        await openEntityDetailsPanel(entityId);
    } catch (err) {
        showToast(`Error updating entity: ${err.message}`, "error");
    }
}

async function handleDeleteEntity(entityId) {
    if (!confirm(`Are you sure you want to delete entity "${entityId}"?\nAll associated manual links will also be safely removed.`)) {
        return;
    }

    try {
        await window.dataService.deleteEntity(entityId);
        showToast(`Deleted entity ${entityId}.`, "success");
        await renderGraphWorkspace(activeCaseId);
        renderDefaultDrawerPlaceholder();
    } catch (err) {
        showToast(`Error deleting entity: ${err.message}`, "error");
    }
}

async function handleDeleteRelationship(relId) {
    if (!confirm(`Are you sure you want to delete relationship "${relId}"?`)) {
        return;
    }

    try {
        await window.dataService.deleteRelationship(relId);
        showToast(`Deleted link ${relId}.`, "success");
        await renderGraphWorkspace(activeCaseId);
        renderDefaultDrawerPlaceholder();
    } catch (err) {
        showToast(`Error deleting link: ${err.message}`, "error");
    }
}

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    const isSuccess = (type === "success");
    toast.className = `p-3 rounded shadow-lg text-xs font-semibold flex items-center gap-2 border pointer-events-auto transition-all transform duration-300 ${isSuccess ? 'bg-emerald-950 text-emerald-200 border-emerald-700' : 'bg-red-950 text-red-200 border-red-700'}`;
    toast.innerHTML = `
        <span class="material-symbols-outlined text-sm">${isSuccess ? 'check_circle' : 'error'}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/* ----------------------------------------------------
   8. MAIN DEMONSTRATION FLOW & AI ASSISTANT
---------------------------------------------------- */
function highlightMainDemoPath() {
    if (!networkInstance || !currentVisNodes || !currentVisEdges) return;

    const pathNodes = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"];
    networkInstance.selectNodes(pathNodes);

    pathNodes.forEach(nodeId => {
        const node = currentVisNodes.get(nodeId);
        if (node) {
            currentVisNodes.update({
                id: nodeId,
                color: { background: "#0066ff", border: "#ffffff" },
                borderWidth: 3
            });
        }
    });

    setTimeout(() => {
        networkInstance.fit({ nodes: pathNodes, animation: { duration: 600 } });
    }, 100);
}

function initAIInvestigator() {
    const submitBtn = document.getElementById("ai-submit-btn");
    const inputField = document.getElementById("ai-input-text");
    const presetButtons = document.querySelectorAll(".ai-preset-btn");

    if (submitBtn && inputField) {
        submitBtn.addEventListener("click", () => {
            const question = inputField.value.trim();
            if (question) runAIQuery(question);
        });

        inputField.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                const question = inputField.value.trim();
                if (question) runAIQuery(question);
            }
        });
    }

    presetButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const query = btn.innerText.replace(/"/g, "").trim();
            if (inputField) inputField.value = query;
            runAIQuery(query);
        });
    });
}

async function runAIQuery(question) {
    const responseBox = document.getElementById("ai-response-container");
    if (!responseBox) return;

    responseBox.innerHTML = `
        <div class="text-center py-10 text-outline text-xs">
            <span class="material-symbols-outlined animate-spin text-tertiary text-xl">sync</span>
            <div class="mt-2 text-white font-semibold">AI Intelligence Engine Analyzing Multi-Hop Relationships...</div>
            <div class="text-[11px] text-on-surface-variant font-mono">Cross-referencing graph topology and ingested evidence records</div>
        </div>
    `;

    const res = await window.dataService.queryAIInvestigator(question);

    let pathHtml = "";
    if (res.path && Array.isArray(res.path)) {
        pathHtml = res.path.map((nodeId, idx) => `
            <span class="px-2 py-0.5 rounded bg-surface-container-high text-primary font-bold border border-primary/30">${nodeId}</span>
            ${idx < res.path.length - 1 ? '<span class="text-outline">â†’</span>' : ''}
        `).join(" ");
    }

    responseBox.innerHTML = `
        <div class="space-y-4">
            <div class="p-3 bg-surface-container-low border border-primary/30 rounded text-on-surface space-y-1">
                <div class="text-[10px] uppercase font-bold text-outline">Investigative Query</div>
                <div class="text-white font-bold font-sans">"${res.question || question}"</div>
            </div>

            <div class="p-3 bg-surface-container-low border border-tertiary/40 rounded space-y-2">
                <div class="flex items-center justify-between">
                    <span class="text-[10px] uppercase font-bold text-tertiary">AI Engine Findings</span>
                    <span class="px-2 py-0.5 rounded bg-tertiary-container/30 text-tertiary text-[10px] font-bold">Confidence: ${res.confidence || '0.93'}</span>
                </div>
                <p class="text-white text-xs font-sans leading-relaxed">${res.answer || res.explanation || 'Graph intelligence response.'}</p>
            </div>
            <div class="text-xs text-white font-semibold pt-1">${questionText}</div>
        </div>
    `;
    container.insertAdjacentHTML("beforeend", userHtml);

    const loadingId = `loading-${Date.now()}`;
    const loadingHtml = `
        <div id="${loadingId}" class="text-center py-6 text-outline text-xs font-sans">
            <span class="material-symbols-outlined animate-spin text-tertiary align-middle mr-1">sync</span> Querying AI Investigator Engine with active case context (${aiActiveCaseId})...
        </div>
    `;
    container.insertAdjacentHTML("beforeend", loadingHtml);
    container.scrollTop = container.scrollHeight;

    try {
        const res = await window.dataService.queryAIInvestigator(questionText, aiActiveCaseId, aiFocusedEntityId, aiConversationHistory);

        document.getElementById(loadingId)?.remove();

        if (!res) {
            container.insertAdjacentHTML("beforeend", `<div class="text-center py-4 text-error text-xs font-sans">No response received from AI Investigator.</div>`);
            return;
        }

        aiConversationHistory.push({ role: "user", content: questionText });
        aiConversationHistory.push({ role: "assistant", content: res.answer || res.summary || "No response summary." });

        const pathNodes = res.path || [];
        const isSafetyRefusal = res.query_type === "SAFETY_REFUSAL";
        const isNotFound = res.query_type === "NOT_FOUND";
        const showPath = !isSafetyRefusal && !isNotFound && Array.isArray(pathNodes) && pathNodes.length > 0;

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

        const assistantHtml = `
            <div class="space-y-3 font-sans my-3 bg-surface-container-lowest border border-tertiary/20 p-3.5 rounded-lg shadow">
                <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                    <span class="text-xs font-bold text-tertiary flex items-center gap-1">
                        <span class="material-symbols-outlined text-sm">auto_awesome</span> AI Investigator Intelligence Response
                    </span>
                    <span class="text-[10px] font-mono text-outline uppercase">${res.query_type || "ANSWER"}</span>
                </div>

            ${pathHtml ? `
                <div class="space-y-1">
                    <div class="text-[10px] uppercase font-bold text-outline">Identified Traversal Path</div>
                    <div class="flex flex-wrap items-center gap-1 font-mono text-[11px] bg-surface-container-lowest p-2.5 rounded border border-surface-container-high">${pathHtml}</div>
                </div>
            ` : ''}

            ${res.lead ? `
                <div class="p-2.5 bg-amber-950/30 border border-amber-800/40 rounded text-amber-300 text-[11px] font-sans">
                    <strong>Actionable Lead:</strong> ${res.lead}
                </div>
            ` : ''}

            <div class="p-2 bg-surface-container-lowest rounded border border-surface-variant text-[10px] text-outline font-sans">
                <strong>Disclaimer:</strong> CrimeGraph AI outputs represent investigative associations. Mandatory human verification required.
            </div>
        </div>
    `;
}

function askAIAboutEntity(entityId) {
    switchTab("pane-ai-investigator");
    runAIQuery(`What connects ${entityId} to active cases?`);
}

/* ----------------------------------------------------
   9. TIMELINE, EVIDENCE EXPLORER & GLOBAL SEARCH
---------------------------------------------------- */
async function renderTimeline(caseId = "CASE_101") {
    const container = document.getElementById("timeline-container");
    if (!container) return;

    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Loading timeline event sequence...</div>`;

    try {
        const data = await window.dataService.getTimeline(caseId);
        const events = data ? (data.events || []) : [];

        if (events.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs">No chronological events found for ${caseId}.</div>`;
            return;
        }

        container.innerHTML = events.map(ev => `
            <div class="p-3 bg-surface-container-low border border-surface-container-high rounded space-y-1 text-xs">
                <div class="flex items-center justify-between text-[11px] font-mono">
                    <span class="text-tertiary font-bold">${ev.timestamp || '2026-08-10'}</span>
                    <span class="px-2 py-0.5 rounded bg-surface-container-highest text-primary font-bold">${ev.type || ev.event_type || 'EVENT'}</span>
                </div>
                <p class="text-white font-medium">${ev.description || 'Recorded incident'}</p>
                <div class="text-[10px] text-on-surface-variant">Location Tag: <strong class="text-outline font-mono">${ev.location_id || 'LOC_001'}</strong></div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error loading timeline:", err);
        container.innerHTML = `
            <div class="p-4 bg-surface-container-low border border-error/40 rounded text-center space-y-2 text-xs">
                <div class="text-error font-bold flex items-center justify-center gap-1">
                    <span class="material-symbols-outlined text-sm">warning</span> Failed to load chronological event sequence
                </div>
                <p class="text-on-surface-variant text-[11px]">${err.message}</p>
                <button onclick="renderTimeline('${caseId}')" class="px-3 py-1 bg-error-container/40 text-error rounded font-semibold text-[11px]">Retry</button>
            </div>
        `;
    }
}

async function renderEvidenceExplorer() {
    const container = document.getElementById("evidence-grid-container");
    if (!container) return;

    container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-tertiary">sync</span> Loading evidence index via DataService...</div>`;

    const evidenceList = await window.dataService.getEvidenceList();
    if (!evidenceList || evidenceList.length === 0) {
        container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs">No evidence records found.</div>`;
        return;
    }

    container.innerHTML = evidenceList.map(ev => `
        <div class="stitch-card space-y-2 text-xs">
            <div class="flex items-center justify-between font-mono">
                <span class="text-tertiary font-bold">${ev.evidence_id}</span>
                <span class="px-2 py-0.5 rounded bg-tertiary-container/30 text-tertiary text-[10px] font-bold">${ev.confidence !== undefined && ev.confidence !== null ? ((ev.confidence) * 100).toFixed(0) : 'N/A'}% Confidence</span>
            </div>
            <p class="text-white italic text-[11px]">"${ev.source_text || ev.excerpt || 'Recorded evidence finding.'}"</p>
            <div class="text-[10px] text-outline font-mono">Source: ${ev.source_document || 'DOC_EXTRACTION'} (Pg. ${ev.page_number || 1})</div>
        </div>
    `).join("");
}

async function generateReport(caseId = null) {
    const targetCaseId = (caseId && typeof caseId === "string") ? caseId : (activeCaseId && activeCaseId !== "ALL" ? activeCaseId : "CASE_101");
    const viewBox = document.getElementById("report-view-box");
    if (!viewBox) return;

    viewBox.innerHTML = `<div class="text-center py-10 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Generating Evidence-Linked Investigation Report for ${targetCaseId}...</div>`;

    const report = await window.dataService.generateReport(targetCaseId);
    if (!report || (!report.content && !report.summary)) {
        viewBox.innerHTML = `<div class="text-center py-10 text-error text-xs">Unable to generate report for ${targetCaseId}.</div>`;
        return;
    }

    const rawContent = report.content || report.summary || "Investigation report generated successfully.";
    const formattedHtml = rawContent
        .replace(/# (.*)/g, '<h1 class="text-base font-bold text-primary border-b border-surface-container-high pb-2 mb-2">$1</h1>')
        .replace(/## (.*)/g, '<h2 class="text-xs font-bold text-tertiary mt-3 mb-1 uppercase tracking-wider">$1</h2>')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
        .replace(/- (.*)/g, '<li class="ml-4 list-disc text-on-surface-variant">$1</li>')
        .replace(/\n\n/g, '<br><br>');

    viewBox.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between text-[11px] font-mono text-outline border-b border-surface-container-high pb-2">
                <span>Report ID: <strong class="text-tertiary">${report.report_id || 'REPORT_' + targetCaseId}</strong> | Target Case: <strong class="text-primary">${targetCaseId}</strong></span>
                <span class="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 uppercase font-bold">${report.status || 'generated'}</span>
            </div>
            <div class="text-xs font-sans text-on-surface leading-relaxed whitespace-pre-wrap">${formattedHtml}</div>
        </div>
    `;
}

async function initGlobalSearch() {
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
                showToast(`No records found matching query "${query}".`, "error");
            }
        }
    });
}


/* ----------------------------------------------------
   9. INTELLIGENCE MODULES (PATTERNS, KEY PLAYERS, COMMUNITIES, PATHS, CROSS-CASE, CORRELATIONS, RISK)
---------------------------------------------------- */
async function renderPatterns() {
    const container = document.getElementById("patterns-container");
    if (!container) return;
    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Loading pattern intelligence...</div>`;
    try {
        const data = await window.dataService.getPatterns({ case_id: activeCaseId });
        const list = data ? (data.patterns || []) : [];
        if (list.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs">No suspicious patterns detected for ${activeCaseId}.</div>`;
            return;
        }
        const patterns = list;
        container.innerHTML = patterns.map((p) => {
            const isSocialPattern = p.source_type === "SOCIAL_MEDIA_SYNTHETIC" || (p.pattern_type && p.pattern_type.includes("SOCIAL"));
            const sevColor = isSocialPattern
                ? "bg-fuchsia-950/70 text-fuchsia-300 border-fuchsia-800/80"
                : (p.severity === "HIGH" 
                    ? "bg-amber-950/60 text-amber-300 border-amber-800/60" 
                    : "bg-cyan-950/60 text-cyan-300 border-cyan-800/60");
            
            const confidencePct = Math.round((p.confidence || 0.9) * 100);

            return `
                <div class="stitch-card flex flex-col justify-between space-y-3 hover:border-amber-500/50 transition cursor-pointer font-sans" onclick="openPatternDetailsModal('${p.pattern_id}')">
                    <div class="space-y-2">
                        <div class="flex items-center justify-between gap-2 flex-wrap">
                            <span class="px-2 py-0.5 text-[10px] font-bold rounded border ${sevColor} uppercase font-mono tracking-wider">
                                ${isSocialPattern ? 'INVESTIGATIVE INDICATOR' : `${p.severity || "HIGH"} SEVERITY`}
                            </span>
                            <span class="text-xs font-mono font-bold text-tertiary">
                                ${confidencePct}% Confidence
                            </span>
                        </div>

                        <h3 class="text-sm font-bold text-white flex items-center gap-1.5 leading-snug">
                            <span class="material-symbols-outlined text-amber-400 text-base" aria-hidden="true">warning</span>
                            ${p.title}
                        </h3>

                        <div class="text-[11px] text-on-surface-variant leading-relaxed line-clamp-3">
                            ${p.explanation}
                        </div>
                    </div>

                    <div class="space-y-2 pt-2 border-t border-surface-container-high text-xs">
                        <div class="flex flex-wrap items-center gap-1.5">
                            <span class="text-[10px] font-bold uppercase text-outline">Entities:</span>
                            ${(p.entities || []).map(e => `<span class="px-1.5 py-0.5 rounded bg-surface-container-high text-tertiary font-mono text-[10px] font-bold">${e}</span>`).join("")}
                        </div>

                        <div class="flex flex-wrap items-center gap-1.5">
                            <span class="text-[10px] font-bold uppercase text-outline">Cases:</span>
                            ${(p.cases || []).map(c => `<span class="px-1.5 py-0.5 rounded bg-surface-container-high text-primary font-mono text-[10px] font-bold">${c}</span>`).join("")}
                        </div>

                        <div class="flex items-center justify-between pt-1">
                            <button onclick="event.stopPropagation(); openPatternDetailsModal('${p.pattern_id}')" class="px-2.5 py-1 bg-surface-container-high hover:bg-surface-container-highest text-white text-[11px] font-semibold rounded flex items-center gap-1">
                                <span class="material-symbols-outlined text-xs">info</span> Inspect Details
                            </button>
                            <button onclick="event.stopPropagation(); highlightPatternOnGraph('${p.pattern_id}')" class="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/40 border border-amber-500/40 text-amber-300 text-[11px] font-semibold rounded flex items-center gap-1">
                                <span class="material-symbols-outlined text-xs">hub</span> Highlight Graph
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    } catch (err) {
        console.error("Failed to fetch suspicious patterns:", err);
        container.innerHTML = `
            <div class="col-span-full p-4 bg-rose-950/30 border border-rose-800/40 rounded text-center text-rose-300 text-xs font-sans">
                <span class="material-symbols-outlined text-xl text-rose-400 block mb-1">cloud_off</span>
                <strong>Pattern Intelligence Temporarily Unavailable</strong>
                <p class="text-on-surface-variant text-[11px] mt-1">Unable to connect to pattern detection service. Please check network connectivity.</p>
            </div>
        `;
    }
}

function openPatternDetailsModal(patternId) {
    const pattern = currentPatternsCache.find(p => p.pattern_id === patternId);
    if (!pattern) return;

    const modal = document.getElementById("pattern-details-modal");
    const titleEl = document.getElementById("pattern-modal-title");
    const bodyEl = document.getElementById("pattern-modal-body");
    const highlightBtn = document.getElementById("pattern-modal-highlight-btn");

    if (!modal || !bodyEl) return;

    if (titleEl) titleEl.innerText = pattern.title;

    const pathNodes = pattern.path || [];
    const evidenceList = pattern.evidence_ids || [];
    const anomalyScorePct = Math.round((pattern.anomaly_score || pattern.confidence || 0.90) * 100);
    const confidencePct = Math.round((pattern.confidence || 0.90) * 100);

    const sourceEntity = (pattern.entities && pattern.entities.length > 0) ? pattern.entities[0] : "CASE_101";
    const targetEntity = (pattern.entities && pattern.entities.length > 1) ? pattern.entities[1] : (pattern.cases && pattern.cases.length > 1 ? pattern.cases[1] : "CASE_204");

    bodyEl.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 bg-surface-container-low p-3 rounded-lg border border-surface-container-high font-sans">
            <div>
                <span class="text-[10px] font-bold uppercase text-outline block">Pattern Category</span>
                <span class="text-xs font-bold text-amber-300 font-mono">${pattern.pattern_type}</span>
            </div>
            <div>
                <span class="text-[10px] font-bold uppercase text-outline block">Anomaly Score Index</span>
                <span class="text-xs font-bold text-rose-400 font-mono flex items-center gap-1">
                    <span class="material-symbols-outlined text-xs">bolt</span> ${anomalyScorePct}% Anomaly
                </span>
            </div>
            <div>
                <span class="text-[10px] font-bold uppercase text-outline block">Severity & Confidence</span>
                <span class="text-xs font-bold text-tertiary font-mono">${pattern.severity || "HIGH"} | ${confidencePct}% Conf</span>
            </div>
        </div>

        <!-- 4-Part Explainability Framework -->
        <div class="space-y-3 font-sans">
            <div>
                <span class="text-[10px] font-bold uppercase text-indigo-400 block mb-1">📊 1. Observed Data (Primary Facts)</span>
                <div class="text-xs text-white leading-relaxed bg-surface-container-lowest p-2.5 rounded border border-surface-container-high font-mono">
                    ${pattern.observed_data || "Documented evidence co-occurrences and relationship edges cataloged in graph store."}
                </div>
            </div>

            <div>
                <span class="text-[10px] font-bold uppercase text-cyan-400 block mb-1">🧠 2. Computed AI Pattern</span>
                <div class="text-xs text-white leading-relaxed bg-surface-container-lowest p-2.5 rounded border border-surface-container-high">
                    ${pattern.computed_pattern || pattern.explanation}
                </div>
            </div>

            <div>
                <span class="text-[10px] font-bold uppercase text-rose-400 block mb-1">⚡ 3. Anomaly Rating Analysis</span>
                <div class="text-xs text-on-surface-variant leading-relaxed bg-surface-container-lowest p-2.5 rounded border border-surface-container-high">
                    Anomaly Score: <strong class="text-rose-400 font-mono">${anomalyScorePct}%</strong>. High-deviance structural pattern flagged by automated graph intelligence engine.
                </div>
            </div>

            ${pattern.investigative_lead ? `
            <div>
                <span class="text-[10px] font-bold uppercase text-amber-300 block mb-1">💡 4. Recommended Investigative Lead</span>
                <div class="text-xs text-amber-200 leading-relaxed bg-amber-950/30 p-2.5 rounded border border-amber-800/40">
                    <span class="material-symbols-outlined text-xs align-middle mr-1 text-amber-400">lightbulb</span>
                    ${pattern.investigative_lead}
                </div>
            </div>
            ` : ''}
        </div>

        ${pathNodes.length > 1 ? `
        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">Discovered Relationship Chain</span>
            <div class="flex flex-wrap items-center gap-1.5 font-mono text-xs bg-surface-container-lowest p-2.5 rounded border border-surface-container-high">
                ${pathNodes.map((nodeId, idx, arr) => `
                    <button onclick="closePatternModal(); openEntityDetailsPanel('${nodeId}')" class="px-2 py-0.5 rounded bg-surface-container-high text-tertiary border border-tertiary/30 font-bold hover:bg-surface-container-highest">${nodeId}</button>
                    ${idx < arr.length - 1 ? '<span class="material-symbols-outlined text-xs text-outline" aria-hidden="true">arrow_forward</span>' : ''}
                `).join("")}
            </div>
        </div>
        ` : ''}

        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">Traceability & Direct Drilldowns</span>
            <div class="flex flex-wrap gap-2">
                ${(pattern.entities || []).map(e => `<button onclick="closePatternModal(); openEntityDetailsPanel('${e}')" class="px-2.5 py-1 rounded bg-indigo-950 text-indigo-300 font-mono text-xs font-bold hover:bg-indigo-900 border border-indigo-700/60 flex items-center gap-1"><span class="material-symbols-outlined text-xs">person</span> Entity: ${e}</button>`).join("")}
                ${(pattern.cases || []).map(c => `<button onclick="closePatternModal(); renderCaseDetail('${c}')" class="px-2.5 py-1 rounded bg-blue-950 text-blue-300 font-mono text-xs font-bold hover:bg-blue-900 border border-blue-700/60 flex items-center gap-1"><span class="material-symbols-outlined text-xs">folder</span> Case: ${c}</button>`).join("")}
                ${evidenceList.map(evId => `<button onclick="closePatternModal(); openEvidencePanel({ evidence_id: '${evId}' })" class="px-2.5 py-1 rounded bg-emerald-950 text-emerald-300 font-mono text-xs font-bold hover:bg-emerald-900 border border-emerald-700/60 flex items-center gap-1"><span class="material-symbols-outlined text-xs">description</span> Ev: ${evId}</button>`).join("")}
                <button onclick="openPatternInLinkAnalysis('${sourceEntity}', '${targetEntity}')" class="px-2.5 py-1 rounded bg-cyan-950 text-cyan-300 font-mono text-xs font-bold hover:bg-cyan-900 border border-cyan-700/60 flex items-center gap-1">
                    <span class="material-symbols-outlined text-xs">git_fork</span> Path Analysis
                </button>
            </div>
        </div>

        ${(pattern.limitations && pattern.limitations.length > 0) ? `
        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">System Analysis Limitations</span>
            <ul class="list-disc list-inside text-xs text-on-surface-variant space-y-0.5">
                ${pattern.limitations.map(lim => `<li>${lim}</li>`).join("")}
            </ul>
        </div>
        ` : ''}

        <div class="p-2.5 bg-amber-950/30 border border-amber-800/40 rounded text-xs text-amber-300 font-sans mt-2 flex items-center gap-2">
            <span class="material-symbols-outlined text-sm text-amber-400">shield</span>
            <span><strong>Safety Protocol:</strong> ${pattern.disclaimer || "Patterns and anomaly scores are investigative leads only. They do not establish criminal intent, legal culpability, or guilt."}</span>
        </div>
    `;

    if (highlightBtn) {
        highlightBtn.onclick = () => {
            closePatternModal();
            highlightPatternOnGraph(patternId);
        };
    }

    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

function openPatternInLinkAnalysis(sourceId, targetId) {
    closePatternModal();
    switchTab("pane-link-analysis", true);
    setTimeout(() => {
        const srcInput = document.getElementById("la-source-input");
        const tgtInput = document.getElementById("la-target-input");
        if (srcInput && sourceId) srcInput.value = sourceId;
        if (tgtInput && targetId) tgtInput.value = targetId;
        if (typeof renderLinkAnalysisWorkspace === "function") {
            renderLinkAnalysisWorkspace();
        }
    }, 150);
}

function closePatternModal() {
    const modal = document.getElementById("pattern-details-modal");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

function highlightPatternOnGraph(patternId) {
    const pattern = currentPatternsCache.find(p => p.pattern_id === patternId);
    if (!pattern) return;

    switchTab("pane-graph");

    const targetNodes = pattern.path && pattern.path.length > 0 ? pattern.path : pattern.entities;
    if (targetNodes && targetNodes.length > 0) {
        highlightPathFromAI(targetNodes);
    }
}


/* ----------------------------------------------------
   DAY 22: NLP EXTRACTION PIPELINE WORKSPACE HANDLERS
---------------------------------------------------- */
let currentNLPResults = null;

const NLP_SAMPLES = {
    fir: {
        docId: "DOC_CASE_101_FIR_REPORT.pdf",
        method: "AI_NER",
        case: "CASE_101",
        text: `FIRST INFORMATION REPORT (FIR-2026-DEL-101):
On 14 August 2026 at 02:30 AM, an armed hijacking was reported at ICD Tughlakabad Logistics Yard.
Witnesses identified Aarav Verma (PERSON_017) supervising the unauthorized cargo unloading.
Aarav Verma was observed communicating via burner handset +91-9876543210 (PHONE_042) to coordinate dispatch.
The hijacked consignment was loaded into Bolero Pickup Truck MH-01-AB-1234 (VEHICLE_017).
Subsequent intelligence links line +91-9876543210 (PHONE_042) to Vikram Malhotra (PERSON_089) in Case 204.`
    },
    intercept: {
        docId: "DOC_CASE_204_MUMBAI_INTERCEPT_SUMMARY.pdf",
        method: "TELCO_INTERCEPT",
        case: "CASE_204",
        text: `LAWFUL SIGNAL INTELLIGENCE INTERCEPT SUMMARY (CASE 204):
Target burner line +91-9876543210 (PHONE_042) registered signal handoffs across Zaveri Bazaar cell tower LOC_003.
Voice intercept confirmed Vikram Malhotra (PERSON_089) utilizing +91-9876543210 (PHONE_042) to negotiate bullion disposal.
Payment of Rs 45,00,000 was routed to HDFC Bank Account ACC_001.
Vehicle MH-01-AB-1234 (VEHICLE_017) was spotted nearby.`
    },
    forensics: {
        docId: "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf",
        method: "DIGITAL_FORENSICS",
        case: "CASE_101",
        text: `HANDSET FORENSIC TRIAGE REPORT (EVID_042_01):
Decrypted chat logs recovered from seized handset identify user Aarav Verma (PERSON_017).
Active contact list contains line +91-9876543210 (PHONE_042) and burner line +91-9811223344 (PHONE_017).
GPS EXIF data places handset at Logistics Yard LOC_001 during incident window 02:15 AM - 03:00 AM.`
    }
};

function loadNLPSample(type) {
    const sample = NLP_SAMPLES[type];
    if (!sample) return;

    const docInput = document.getElementById("nlp-doc-id");
    const caseSelect = document.getElementById("nlp-case-select");
    const methodSelect = document.getElementById("nlp-method-select");
    const textInput = document.getElementById("nlp-text-input");

    if (docInput) docInput.value = sample.docId;
    if (caseSelect) caseSelect.value = sample.case;
    if (methodSelect) methodSelect.value = sample.method;
    if (textInput) textInput.value = sample.text;
}

function clearNLPWorkspace() {
    const docInput = document.getElementById("nlp-doc-id");
    const textInput = document.getElementById("nlp-text-input");
    const emptyState = document.getElementById("nlp-empty-state");
    const loadingState = document.getElementById("nlp-loading-state");
    const errorState = document.getElementById("nlp-error-state");
    const resultsContainer = document.getElementById("nlp-results-container");

    if (docInput) docInput.value = "DOC_CASE_101_FIELD_INTERCEPT_NOTES.txt";
    if (textInput) textInput.value = "";
    if (emptyState) emptyState.classList.remove("hidden");
    if (loadingState) loadingState.classList.add("hidden");
    if (errorState) errorState.classList.add("hidden");
    if (resultsContainer) resultsContainer.classList.add("hidden");
    currentNLPResults = null;
}

async function runNLPExtraction() {
    const docIdInput = document.getElementById("nlp-doc-id");
    const textInput = document.getElementById("nlp-text-input");
    const emptyState = document.getElementById("nlp-empty-state");
    const loadingState = document.getElementById("nlp-loading-state");
    const errorState = document.getElementById("nlp-error-state");
    const errorMsg = document.getElementById("nlp-error-message");
    const resultsContainer = document.getElementById("nlp-results-container");
    const btnRun = document.getElementById("btn-run-nlp");

    const docId = docIdInput ? docIdInput.value.trim() : "DOC_EXTRACTION";
    const rawText = textInput ? textInput.value.trim() : "";

    if (!rawText) {
        if (errorState && errorMsg) {
            errorMsg.innerText = "Please paste or enter raw investigation intelligence text before running extraction.";
            errorState.classList.remove("hidden");
        }
        return;
    }

    if (emptyState) emptyState.classList.add("hidden");
    if (errorState) errorState.classList.add("hidden");
    if (resultsContainer) resultsContainer.classList.add("hidden");
    if (loadingState) loadingState.classList.remove("hidden");
    if (btnRun) btnRun.disabled = true;

    try {
        const res = await window.dataService.extractDocument(docId, rawText);
        currentNLPResults = res;
        renderNLPResults(res);
        if (loadingState) loadingState.classList.add("hidden");
        if (resultsContainer) resultsContainer.classList.remove("hidden");
    } catch (err) {
        if (loadingState) loadingState.classList.add("hidden");
        if (errorState && errorMsg) {
            errorMsg.innerText = err.message || "NLP extraction pipeline failed. Please check network connection or API authorization.";
            errorState.classList.remove("hidden");
        }
    } finally {
        if (btnRun) btnRun.disabled = false;
    }
}

function renderNLPResults(res) {
    if (!res) return;

    const entities = res.entities || [];
    const relationships = res.relationships || [];
    const evidence = res.evidence || [];

    // 1. Update Metrics Bar
    const cntEntities = document.getElementById("nlp-count-entities");
    const cntRels = document.getElementById("nlp-count-relationships");
    const avgConf = document.getElementById("nlp-avg-confidence");

    if (cntEntities) cntEntities.innerText = entities.length;
    if (cntRels) cntRels.innerText = relationships.length;

    let confSum = 0;
    entities.forEach(e => confSum += (e.confidence || 0.9));
    const meanConf = entities.length > 0 ? Math.round((confSum / entities.length) * 100) : 95;
    if (avgConf) avgConf.innerText = `${meanConf}%`;

    // 2. Render Extracted Entities List (Grouped by Type)
    const entitiesList = document.getElementById("nlp-entities-list");
    if (entitiesList) {
        if (entities.length === 0) {
            entitiesList.innerHTML = `<div class="text-xs text-on-surface-variant italic py-2">No entities detected in raw text.</div>`;
        } else {
            // Group by type
            const grouped = {};
            entities.forEach(e => {
                const type = (e.type || e.entity_type || "PERSON").toUpperCase();
                if (!grouped[type]) grouped[type] = [];
                grouped[type].push(e);
            });

            let html = "";
            for (const [type, list] of Object.entries(grouped)) {
                html += `
                    <div class="space-y-1 mt-2 first:mt-0">
                        <div class="text-[10px] font-bold tracking-wider uppercase text-outline flex items-center gap-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
                            ${type} (${list.length})
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                `;
                list.forEach(ent => {
                    const confPct = Math.round((ent.confidence || 0.95) * 100);
                    const isExisting = (window.currentGraphData && window.currentGraphData.nodes) 
                        ? window.currentGraphData.nodes.some(n => n.id === ent.id || (n.label && n.label.includes(ent.name)))
                        : (ent.id && !ent.id.includes("EXT_"));

                    html += `
                        <div class="p-2 bg-surface-container-lowest border border-surface-container-high rounded text-xs flex items-center justify-between gap-2">
                            <div class="min-w-0 flex-1">
                                <div class="font-bold text-primary font-mono truncate">${ent.name || ent.id}</div>
                                <div class="text-[10px] text-on-surface-variant flex items-center gap-1.5 mt-0.5">
                                    <span class="font-mono text-purple-300">ID: ${ent.id}</span>
                                    <span>•</span>
                                    <span class="${isExisting ? 'text-cyan-300' : 'text-emerald-300'} font-semibold">
                                        ${isExisting ? '[EXISTING GRAPH]' : '[NEWLY DETECTED]'}
                                    </span>
                                </div>
                            </div>
                            <div class="text-right">
                                <span class="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-purple-950 text-purple-300 border border-purple-800">
                                    ${confPct}%
                                </span>
                            </div>
                        </div>
                    `;
                });
                html += `</div></div>`;
            }
            entitiesList.innerHTML = html;
        }
    }

    // 3. Render Extracted Relationships List
    const relsList = document.getElementById("nlp-relationships-list");
    if (relsList) {
        if (relationships.length === 0) {
            relsList.innerHTML = `<div class="text-xs text-on-surface-variant italic py-2">No explicit relationship links inferred.</div>`;
        } else {
            let html = "";
            relationships.forEach(rel => {
                const confPct = Math.round((rel.confidence || 0.92) * 100);
                html += `
                    <div class="p-2.5 bg-surface-container-lowest border border-surface-container-high rounded text-xs flex flex-wrap items-center justify-between gap-2">
                        <div class="flex items-center gap-2 font-mono">
                            <span class="px-2 py-0.5 rounded bg-surface-container-high text-primary border border-outline-variant">${rel.source_id}</span>
                            <span class="text-cyan-300 font-bold flex items-center gap-0.5">
                                <span class="material-symbols-outlined text-xs">arrow_forward</span>
                                ${rel.relationship}
                            </span>
                            <span class="px-2 py-0.5 rounded bg-surface-container-high text-primary border border-outline-variant">${rel.target_id}</span>
                        </div>
                        <span class="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                            Confidence: ${confPct}%
                        </span>
                    </div>
                `;
            });
            relsList.innerHTML = html;
        }
    }

    // 4. Render Source Provenance Box
    const provBox = document.getElementById("nlp-provenance-box");
    if (provBox) {
        const ev = (evidence && evidence.length > 0) ? evidence[0] : null;
        const methodSelect = document.getElementById("nlp-method-select");
        const method = methodSelect ? methodSelect.value : "AI_NER";

        provBox.innerHTML = `
            <div class="flex items-center justify-between text-[11px] pb-1 border-b border-surface-container-high">
                <div><span class="text-on-surface-variant">Document ID:</span> <span class="text-purple-300">${res.document_id || "DOC_EXTRACTION"}</span></div>
                <div><span class="text-on-surface-variant">Extraction Method:</span> <span class="text-cyan-300">${method}</span></div>
                <div><span class="text-on-surface-variant">Evidence ID:</span> <span class="text-emerald-300">${ev ? ev.evidence_id : "EVID_EXT_01"}</span></div>
            </div>
            <div class="text-[11px] text-on-surface-variant pt-1 italic leading-relaxed">
                "${ev ? ev.source_text : 'Source snippet verified'}"
            </div>
            <div class="text-[10px] text-outline pt-1 flex items-center gap-2">
                <span>Provenance Status: Grounded in Source Document</span>
                <span>•</span>
                <span>Page 1 Offset 0-300</span>
            </div>
        `;
    }

    // 5. Conflict Detection Check
    const conflictBanner = document.getElementById("nlp-conflict-banner");
    const conflictDetail = document.getElementById("nlp-conflict-detail");
    const hasPhone042 = entities.some(e => e.name && e.name.includes("9876543210"));
    const hasPerson017 = entities.some(e => e.name && e.name.includes("Aarav"));
    const hasPerson089 = entities.some(e => e.name && e.name.includes("Vikram"));

    if (conflictBanner && conflictDetail) {
        if (hasPhone042 && (hasPerson017 || hasPerson089)) {
            conflictDetail.innerText = `Line +91-9876543210 is associated with Aarav Verma (PERSON_017) in Cargo Hijack FIR but co-occurs with Vikram Malhotra (PERSON_089) in Zaveri Bazaar Intercepts. Human officer verification required.`;
            conflictBanner.classList.remove("hidden");
        } else {
            conflictBanner.classList.add("hidden");
        }
    }
}

function sendNLPGroundToCrimeGraph() {
    if (!currentNLPResults) return;

    switchTab("pane-graph");

    const entities = currentNLPResults.entities || [];
    const targetNodes = entities.map(e => e.id);
    if (targetNodes.length > 0) {
        highlightPathFromAI(targetNodes);
    }
}

function sendNLPQueryToAI() {
    if (!currentNLPResults) return;

    const docId = currentNLPResults.document_id || "DOC_EXTRACTION";
    const entities = currentNLPResults.entities || [];
    const entNames = entities.slice(0, 3).map(e => e.name || e.id).join(", ");

    switchTab("pane-ai-investigator");

    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
        chatInput.value = `Analyze extracted NLP findings for document ${docId} involving entities (${entNames}).`;
        chatInput.focus();
    }
}

/* ===========================================================================
   DAY 23: TIMELINE & EVENT CORRELATION FRONTEND WORKSPACE
   =========================================================================== */

let currentTimelineRequestId = 0;

async function renderTimeline(caseId = null) {
    const requestId = ++currentTimelineRequestId;
    const container = document.getElementById("timeline-events-container");
    if (!container) return;

    container.innerHTML = `
        <div class="text-outline text-center py-12 font-mono text-xs">
            <span class="material-symbols-outlined animate-spin text-xl text-primary mb-1">sync</span>
            <div>Fetching chronological timeline records from CrimeGraph backend...</div>
        </div>`;

    try {
        const targetCase = caseId || document.getElementById("timeline-case-filter")?.value || "ALL";
        const response = await window.dataService.getTimeline(targetCase);
        if (requestId !== currentTimelineRequestId) return;
        allTimelineEvents = response.events || response || [];

        filterTimelineEvents();
    } catch (err) {
        console.error("[renderTimeline] Error fetching timeline:", err);
        container.innerHTML = `
            <div class="p-6 bg-rose-950/40 border border-rose-800/60 rounded text-center text-xs text-rose-300 font-sans space-y-2">
                <span class="material-symbols-outlined text-2xl text-rose-400 block">warning</span>
                <div class="font-bold">Timeline Unavailable</div>
                <div class="text-[11px] text-rose-200/80">Failed to load chronological event sequence from CrimeGraph service: ${err.message || 'Unknown network error'}.</div>
                <button onclick="renderTimeline()" class="mt-2 px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-white text-xs font-semibold rounded border border-outline-variant">
                    Retry Loading
                </button>
            </div>`;
    }
}

function filterTimelineEvents() {
    const container = document.getElementById("timeline-events-container");
    const conflictBanner = document.getElementById("timeline-conflict-banner");
    const conflictDetail = document.getElementById("timeline-conflict-detail");
    if (!container) return;

    const caseFilter = document.getElementById("timeline-case-filter")?.value || "ALL";
    const typeFilter = document.getElementById("timeline-type-filter")?.value || "ALL";
    const sourceFilter = document.getElementById("timeline-source-filter")?.value || "ALL";
    const correlationFilter = document.getElementById("timeline-correlation-filter")?.value || "ALL";
    const searchQuery = (document.getElementById("timeline-search-input")?.value || "").toLowerCase().trim();

    let filtered = allTimelineEvents.filter(ev => {
        if (caseFilter !== "ALL" && ev.case_id && ev.case_id !== caseFilter) return false;
        const evType = ev.event_type || ev.type;
        if (typeFilter !== "ALL" && evType !== typeFilter) return false;
        if (sourceFilter !== "ALL" && ev.source_type !== sourceFilter && ev.extraction_method !== sourceFilter) return false;
        if (correlationFilter === "CORRELATED" && (!ev.correlations || ev.correlations.length === 0)) return false;
        if (correlationFilter === "DIRECTLY_SUPPORTED" && ev.correlation_status !== "DIRECTLY_SUPPORTED") return false;
        if (correlationFilter === "POTENTIAL_CORRELATION" && ev.correlation_status !== "POTENTIAL_CORRELATION") return false;

        if (searchQuery) {
            const haystack = [
                ev.id,
                ev.title,
                ev.event_type,
                ev.case_id,
                ev.description,
                ev.location_name,
                ev.source_document,
                ...(ev.involved_entity_names || []),
                ...(ev.involved_entity_ids || [])
            ].join(" ").toLowerCase();
            if (!haystack.includes(searchQuery)) return false;
        }
        return true;
    });

    // Check for temporal conflicts across events
    const conflictsFound = filtered.filter(e => e.conflict && e.conflict.has_conflict);
    if (conflictBanner && conflictDetail) {
        if (conflictsFound.length > 0) {
            conflictBanner.classList.remove("hidden");
            conflictDetail.innerText = conflictsFound.map(c => `[${c.id}] ${c.conflict.description}`).join(" | ");
        } else {
            conflictBanner.classList.add("hidden");
        }
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-outline font-mono text-xs border border-surface-container-high rounded p-6 bg-surface-container-lowest">
                <span class="material-symbols-outlined text-3xl opacity-40 mb-2 block">event_busy</span>
                <div>No timeline events match the selected filter criteria.</div>
                <div class="text-[11px] text-on-surface-variant mt-1">Adjust filters or select "All Cases" to view cross-case events.</div>
            </div>`;
        return;
    }

    // Sort events: Dated events first (chronological order), then "Time unknown" events
    filtered.sort((a, b) => {
        if (!a.timestamp && !b.timestamp) return 0;
        if (!a.timestamp) return 1;
        if (!b.timestamp) return -1;
        return new Date(a.timestamp) - new Date(b.timestamp);
    });

    let html = '';
    filtered.forEach((ev, idx) => {
        const timeDisplay = ev.timestamp 
            ? new Date(ev.timestamp).toUTCString().replace("GMT", "UTC") 
            : '<span class="text-amber-400 font-bold flex items-center gap-1"><span class="material-symbols-outlined text-xs">help_outline</span> Time unknown</span>';
        
        const isNLP = ev.source_type === "NLP_EXTRACTED" || ev.extraction_method === "NLP_EXTRACTED";
        const sourceBadgeClass = isNLP
            ? 'bg-purple-950 text-purple-300 border-purple-800/60'
            : 'bg-blue-950 text-blue-300 border-blue-800/60';

        const correlationBadge = ev.correlation_status === "DIRECTLY_SUPPORTED"
            ? '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">DIRECTLY SUPPORTED</span>'
            : ev.correlation_status === "POTENTIAL_CORRELATION"
                ? '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950/60 text-amber-300 border border-amber-800/40">POTENTIAL CORRELATION</span>'
                : '';

        const entitiesHtml = (ev.involved_entity_names || ev.involved_entity_ids || []).map(ent => `
            <span class="px-2 py-0.5 rounded bg-surface-container-high text-on-surface font-mono text-[11px] border border-outline-variant">
                ${ent}
            </span>
        `).join("");

        const evidenceIds = ev.evidence_ids || [];
        const evidenceHtml = evidenceIds.map(evId => `
            <button onclick="openEvidencePanel({ evidence_id: '${evId}' })" class="px-2 py-0.5 bg-surface-container-highest hover:bg-surface-variant text-primary font-mono text-[10px] rounded border border-outline-variant flex items-center gap-1 transition">
                <span class="material-symbols-outlined text-[11px]">receipt</span> ${evId}
            </button>
        `).join("");

        const correlationsList = (ev.correlations || []).map(c => `
            <div class="text-[11px] text-amber-200/90 bg-amber-950/30 p-1.5 rounded border border-amber-900/30 flex items-center gap-1">
                <span class="material-symbols-outlined text-xs text-amber-400">link</span>
                <span><strong>Reason:</strong> ${c.reason} (${c.correlation_type})</span>
            </div>
        `).join("");

        html += `
            <div class="stitch-card p-4 space-y-3 hover:border-primary/50 transition">
                <div class="flex flex-wrap items-center justify-between gap-2 border-b border-surface-container-high pb-2">
                    <div class="flex items-center gap-2">
                        <span class="w-7 h-7 rounded-full bg-primary/20 text-primary border border-primary/40 flex items-center justify-center font-bold font-mono text-xs">
                            ${idx + 1}
                        </span>
                        <div>
                            <div class="font-bold text-white text-xs flex items-center gap-2">
                                <span>${ev.title || ev.event_type}</span>
                                <span class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-container-highest text-outline font-semibold">${ev.id}</span>
                            </div>
                            <div class="text-[11px] text-on-surface-variant flex items-center gap-2 mt-0.5">
                                <span>Case: <strong class="text-primary font-mono">${ev.case_id}</strong></span>
                                <span>•</span>
                                <span>Location: <strong>${ev.location_name || ev.location_id || 'N/A'}</strong></span>
                            </div>
                        </div>
                    </div>

                    <div class="flex items-center gap-2">
                        ${correlationBadge}
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded border ${sourceBadgeClass}">
                            ${isNLP ? 'NLP EXTRACTED' : (ev.source_type || 'SOURCE')}
                        </span>
                    </div>
                </div>

                <div class="flex flex-wrap items-center justify-between gap-2 text-xs bg-surface-container-lowest p-2 rounded border border-surface-container-high font-mono">
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-xs text-primary">schedule</span>
                        <span class="text-white font-bold">${timeDisplay}</span>
                        ${ev.timestamp_precision ? `<span class="text-[10px] px-1.5 py-0.2 rounded bg-surface-container-high text-outline">P: ${ev.timestamp_precision}</span>` : ''}
                    </div>
                    <div class="flex items-center gap-2 text-[11px]">
                        <span>Confidence: <strong class="text-emerald-400">${Math.round((ev.confidence || 0.95) * 100)}%</strong></span>
                        <span>•</span>
                        <span class="text-outline">${ev.source_document || 'Doc N/A'}</span>
                    </div>
                </div>

                <p class="text-xs text-on-surface leading-relaxed font-sans">${ev.description}</p>

                ${entitiesHtml ? `
                    <div class="space-y-1">
                        <div class="text-[10px] font-bold uppercase text-outline">Involved Entities</div>
                        <div class="flex flex-wrap gap-1.5">${entitiesHtml}</div>
                    </div>` : ''}

                ${correlationsList ? `
                    <div class="space-y-1">
                        <div class="text-[10px] font-bold uppercase text-amber-400 flex items-center gap-1">
                            <span class="material-symbols-outlined text-xs">hub</span> Correlated Intelligence Links
                        </div>
                        <div class="space-y-1">${correlationsList}</div>
                    </div>` : ''}

                <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-surface-container-high">
                    <div class="flex flex-wrap items-center gap-1">
                        <span class="text-[10px] font-bold uppercase text-outline mr-1">Evidence:</span>
                        ${evidenceHtml || '<span class="text-[11px] text-outline">No evidence attached</span>'}
                    </div>

                    <div class="flex items-center gap-2">
                        <button onclick="openEventDetailModal('${ev.id}')" class="px-2.5 py-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-semibold rounded border border-outline-variant flex items-center gap-1 transition">
                            <span class="material-symbols-outlined text-xs">info</span> Event Details
                        </button>
                        <button onclick="highlightEventOnGraph('${ev.id}')" class="px-2.5 py-1 bg-primary/20 hover:bg-primary/30 text-primary text-xs font-semibold rounded border border-primary/40 flex items-center gap-1 transition">
                            <span class="material-symbols-outlined text-xs">hub</span> View in Graph
                        </button>
                    </div>
                </div>
            </div>`;
    });

    container.innerHTML = html;
}

function openEventDetailModal(eventId) {
    const ev = allTimelineEvents.find(e => e.id === eventId);
    if (!ev) return;

    const modal = document.getElementById("event-details-modal");
    const body = document.getElementById("event-modal-body");
    if (!modal || !body) return;

    const timeDisplay = ev.timestamp 
        ? new Date(ev.timestamp).toUTCString()
        : 'Time unknown (Unspecified in source document)';

    const entitiesList = (ev.involved_entity_names || ev.involved_entity_ids || []).map(ent => `
        <span class="px-2 py-1 bg-surface-container-high rounded border border-outline-variant text-on-surface font-mono text-xs">
            ${ent}
        </span>
    `).join("");

    const correlationsList = (ev.correlations || []).map(c => `
        <div class="p-2 bg-amber-950/40 border border-amber-800/40 rounded text-xs text-amber-200 space-y-0.5">
            <div class="font-bold flex items-center gap-1">
                <span class="material-symbols-outlined text-xs text-amber-400">link</span> ${c.reason}
            </div>
            <div class="text-[11px] text-amber-300/80">Target Event: <span class="font-mono">${c.target_event_id}</span> | Type: ${c.correlation_type}</div>
        </div>
    `).join("");

    body.innerHTML = `
        <div class="space-y-4">
            <div class="bg-surface-container-lowest p-3 rounded border border-surface-container-high space-y-2">
                <div class="flex items-center justify-between">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono ${p.severity === 'HIGH' ? 'bg-error-container/40 text-error border border-error/40' : 'bg-tertiary-container/30 text-tertiary border border-tertiary/40'}">${p.pattern_type}</span>
                    <span class="text-[10px] font-mono text-outline">Severity: ${p.severity || 'MEDIUM'}</span>
                </div>
                <h4 class="font-bold text-white">${p.title}</h4>
                <p class="text-on-surface-variant text-[11px]">${p.description || 'Pattern identified across graph topology.'}</p>
                <div class="text-[10px] font-mono text-tertiary">Involved Entities: ${(p.involved_entities || p.involved_entity_ids || []).join(", ")}</div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="text-center py-6 text-error text-xs">Error loading patterns: ${err.message}</div>`;
    }
}

async function renderKeyPlayers() {
    const container = document.getElementById("key-players-container");
    if (!container) return;
    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Analyzing graph centrality & key players...</div>`;
    try {
        const data = await window.dataService.getKeyPlayers({ case_id: activeCaseId });
        const list = data ? (data.key_players || []) : [];
        if (list.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs">No key players calculated for ${activeCaseId}.</div>`;
            return;
        }
        container.innerHTML = list.map(kp => `
            <div class="p-3 bg-surface-container-low border border-surface-container-high rounded space-y-1.5 text-xs">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="w-6 h-6 rounded-full bg-primary-container text-white flex items-center justify-center font-mono font-bold text-[10px]">#${kp.rank || 1}</span>
                        <span class="font-bold text-white">${kp.entity_name || kp.entity_id}</span>
                        <span class="font-mono text-[10px] text-outline">(${kp.entity_id})</span>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-tertiary-container/30 text-tertiary border border-tertiary/40">Score: ${kp.influence_score || kp.score || '0.90'}</span>
                </div>
                <p class="text-on-surface-variant text-[11px]">${kp.explanation || 'High influence hub across graph network.'}</p>
                <div class="text-[10px] font-mono text-outline">Role: <span class="text-primary font-bold">${kp.role || 'HUB_OPERATOR'}</span></div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="text-center py-6 text-error text-xs">Error loading key players: ${err.message}</div>`;
    }
}

async function renderCommunities() {
    const container = document.getElementById("communities-container");
    if (!container) return;
    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Running Louvain community detection...</div>`;
    try {
        const data = await window.dataService.getCommunities({ case_id: activeCaseId });
        const list = data ? (data.communities || []) : [];
        if (list.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs">No graph communities detected for ${activeCaseId}.</div>`;
            return;
        }
        container.innerHTML = list.map(c => `
            <div class="p-3 bg-surface-container-low border border-surface-container-high rounded space-y-1.5 text-xs">
                <div class="flex items-center justify-between">
                    <span class="font-bold font-mono text-purple-300 text-xs">${c.community_id} â€” ${c.classification || 'CRIMINAL_GROUP'}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-950/50 text-purple-300 border border-purple-700/50">Density: ${c.density_score || 0.65}</span>
                </div>
                <div class="text-[11px] text-on-surface-variant">Members (${c.member_count || (c.member_entity_ids || []).length}): <span class="font-mono text-white">${(c.member_entity_ids || []).join(", ")}</span></div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="text-center py-6 text-error text-xs">Error loading communities: ${err.message}</div>`;
    }
}

async function renderPaths() {
    const container = document.getElementById("paths-container");
    if (!container) return;
    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Discovering multi-hop relationship paths...</div>`;
    try {
        const res = await window.dataService.analyzePaths({ source_id: "CASE_101", target_id: "CASE_204" });
        const paths = res ? (res.paths || []) : [];
        if (paths.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs">No multi-hop paths found.</div>`;
            return;
        }
        container.innerHTML = paths.map((p, idx) => `
            <div class="p-3 bg-surface-container-low border border-emerald-800/40 rounded space-y-2 text-xs">
                <div class="flex items-center justify-between">
                    <span class="font-bold text-emerald-400 font-mono">Path #${idx + 1} (${p.hop_count} Hops) â€” Score: ${p.path_score || p.confidence}</span>
                    <span class="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/40">Confidence: ${p.confidence || 0.90}</span>
                </div>
                <p class="text-on-surface-variant text-[11px]">${p.explanation || 'Path discovered across multiple evidence items.'}</p>
                <div class="flex items-center gap-1.5 overflow-x-auto py-1 text-[11px] font-mono">
                    ${(p.path || []).map((node, i) => `<span class="px-2 py-0.5 rounded bg-surface-container-high text-primary border border-primary/30 font-bold">${node}</span>${i < p.path.length - 1 ? '<span class="text-outline">â†’</span>' : ''}`).join("")}
                </div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="text-center py-6 text-error text-xs">Error loading path analysis: ${err.message}</div>`;
    }
}

async function renderCrossCase() {
    const container = document.getElementById("cross-case-container");
    if (!container) return;
    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Correlating cross-case entity overlaps...</div>`;
    try {
        const res = await window.dataService.getCorrelations({ min_score: 0.5 });
        const list = res ? (res.correlations || []) : [];
        if (list.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs">No cross-case entity overlaps found.</div>`;
            return;
        }
        container.innerHTML = list.map(c => `
            <div class="p-3 bg-surface-container-low border border-cyan-800/40 rounded space-y-1.5 text-xs">
                <div class="flex items-center justify-between">
                    <span class="font-bold text-cyan-300 font-mono">${c.title || c.correlation_id}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950/40 text-cyan-300 border border-cyan-800/40">Score: ${c.correlation_score || c.confidence}</span>
                </div>
                <p class="text-on-surface-variant text-[11px]">${c.description || 'Entity bridges multiple independent investigation cases.'}</p>
                <div class="text-[10px] font-mono text-outline">Primary Entity: <strong class="text-primary">${c.primary_entity_id || 'PERSON_017'}</strong></div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="text-center py-6 text-error text-xs">Error loading cross-case connections: ${err.message}</div>`;
    }
}

async function renderCorrelations() {
    const container = document.getElementById("correlations-container");
    if (!container) return;
    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Loading multi-source evidence correlations...</div>`;
    try {
        const res = await window.dataService.getCorrelations();
        const list = res ? (res.correlations || []) : [];
        if (list.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs">No cross-source correlations found.</div>`;
            return;
        }
        container.innerHTML = list.map(c => `
            <div class="p-3 bg-surface-container-low border border-surface-container-high rounded space-y-1.5 text-xs">
                <div class="flex items-center justify-between">
                    <span class="font-bold text-secondary font-mono">${c.correlation_type || 'ENTITY_CORRELATION'}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-secondary-container/30 text-secondary border border-secondary/40">Confidence: ${c.confidence || 0.95}</span>
                </div>
                <h4 class="font-bold text-white text-xs">${c.title}</h4>
                <div class="text-[10px] font-mono text-outline">Primary Entity: <strong class="text-white">${c.primary_entity_id}</strong></div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="text-center py-6 text-error text-xs">Error loading correlations: ${err.message}</div>`;
    }
}

async function renderRiskPriorities() {
    const container = document.getElementById("risk-container");
    if (!container) return;
    container.innerHTML = `<div class="text-center py-6 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Calculating Day 33 ML risk & priority scores...</div>`;
    try {
        const res = await window.dataService.getInvestigationPriorities();
        const list = res ? (res.priorities || []) : [];
        if (list.length === 0) {
            container.innerHTML = `<div class="text-center py-6 text-outline text-xs">No high risk priority entities found.</div>`;
            return;
        }
        container.innerHTML = list.map((r, idx) => `
            <div class="p-3 bg-surface-container-low border border-error/40 rounded space-y-1.5 text-xs">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="w-6 h-6 rounded bg-error-container text-error flex items-center justify-center font-mono font-bold text-[10px]">#${idx + 1}</span>
                        <span class="font-bold text-white">${r.entity_name || r.entity_id}</span>
                        <span class="font-mono text-[10px] text-outline">(${r.entity_id})</span>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-error-container/40 text-error border border-error/40">Risk Score: ${r.risk_score} / 100 (${r.risk_level})</span>
                </div>
                <p class="text-on-surface-variant text-[11px]">${r.investigative_lead || r.explanation || 'High risk priority recommended for investigation.'}</p>
                <div class="text-[10px] font-mono text-outline">Signals: <span class="text-tertiary font-bold">${(r.signals || []).join(", ")}</span></div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<div class="text-center py-6 text-error text-xs">Error loading risk priorities: ${err.message}</div>`;
    }
}
