/**
 * CrimeGraph AI — Frontend Application Logic
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
                <td class="p-3 font-mono text-primary font-bold">${c.entities_count || 8}</td>
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
async function renderCaseDetail(caseId = "CASE_101") {
    const container = document.getElementById("case-detail-container");
    if (!container) return;

    container.innerHTML = `
        <div class="space-y-4">
            <div class="flex items-center justify-between border-b border-surface-container-high pb-3">
                <div>
                    <span class="font-mono text-xs font-bold text-error px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${caseId}</span>
                    <h2 class="text-base font-bold text-white mt-1">Operation Midnight Shadow — Nhava Sheva Hub Cargo Hijack</h2>
                    <div class="text-xs text-on-surface-variant">FIR #MH-NAV-2026-8812 • Lead Investigator: ACP S. Sharma</div>
                </div>
                <div class="text-right">
                    <span class="px-2.5 py-1 text-xs font-bold rounded bg-tertiary-container/30 text-tertiary border border-tertiary/40">ACTIVE INVESTIGATION</span>
                    <div class="text-[11px] text-outline font-mono mt-1">Incident Date: 2026-08-10</div>
                </div>
            </div>

            <!-- Key Discovery Box -->
            <div class="bg-surface-container-lowest p-3.5 rounded border border-primary/40 space-y-2">
                <div class="flex items-center gap-2 text-primary font-bold text-xs">
                    <span class="material-symbols-outlined text-sm">hub</span> Automated Multi-Hop Lead Association
                </div>
                <p class="text-xs text-on-surface leading-relaxed">
                    Graph traversal cross-referenced encrypted burner communication <strong>PHONE_042</strong> (+91-9876543210) recovered from <strong>Aarav Verma</strong> (PERSON_017) to bullion receiver <strong>Vikram Malhotra</strong> (PERSON_089) in <strong>CASE_204</strong> (Zaveri Bazaar Syndicate).
                </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                <button onclick="exploreCase('${caseId}')" class="p-3 bg-surface-container hover:bg-surface-container-high rounded border border-surface-container-high text-left space-y-1 transition">
                    <div class="flex items-center gap-1.5 text-primary text-xs font-bold"><span class="material-symbols-outlined text-sm">account_tree</span> Network Graph</div>
                    <div class="text-[11px] text-on-surface-variant">Inspect connected nodes, burner lines & bullion trail.</div>
                </button>

                <button onclick="switchTab('pane-timeline')" class="p-3 bg-surface-container hover:bg-surface-container-high rounded border border-surface-container-high text-left space-y-1 transition">
                    <div class="flex items-center gap-1.5 text-tertiary text-xs font-bold"><span class="material-symbols-outlined text-sm">history</span> Incident Timeline</div>
                    <div class="text-[11px] text-on-surface-variant">View chronological ANPR logs and CCTV timestamps.</div>
                </button>

                <button onclick="switchTab('pane-reports')" class="p-3 bg-surface-container hover:bg-surface-container-high rounded border border-surface-container-high text-left space-y-1 transition">
                    <div class="flex items-center gap-1.5 text-secondary text-xs font-bold"><span class="material-symbols-outlined text-sm">description</span> Evidence Dossier</div>
                    <div class="text-[11px] text-on-surface-variant">Generate standardized evidence summary report.</div>
                </button>
            </div>
        </div>
    `;
}

/* ----------------------------------------------------
   4. NETWORK GRAPH WORKSPACE & VIS.JS ENGINE
---------------------------------------------------- */
async function initGraphWorkspace(caseId = "CASE_101") {
    activeCaseId = caseId;
    await renderGraphWorkspace(caseId);

    // Zoom & Fit Controls
    document.getElementById("graph-zoom-in")?.addEventListener("click", () => {
        if (!networkInstance) return;
        const scale = networkInstance.getScale() * 1.3;
        networkInstance.moveTo({ scale: scale, animation: { duration: 300 } });
    });

    document.getElementById("graph-zoom-out")?.addEventListener("click", () => {
        if (!networkInstance) return;
        const scale = networkInstance.getScale() * 0.7;
        networkInstance.moveTo({ scale: scale, animation: { duration: 300 } });
    });

    document.getElementById("graph-reset")?.addEventListener("click", () => {
        networkInstance?.fit({ animation: { duration: 400 } });
    });

    document.getElementById("graph-clear-selection")?.addEventListener("click", () => {
        networkInstance?.unselectAll();
        renderDefaultDrawerPlaceholder();
    });

    // Highlight Main Demo Path
    document.getElementById("graph-highlight-path")?.addEventListener("click", highlightMainDemoPath);

    // Graph Type Filters
    document.querySelectorAll(".filter-type").forEach(chk => {
        chk.addEventListener("change", applyGraphFilters);
    });

    // Graph Search
    const searchInput = document.getElementById("graph-search-input");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!query || !currentVisNodes) {
                networkInstance?.unselectAll();
                return;
            }
            const match = (rawGraphData && rawGraphData.nodes) ? rawGraphData.nodes.find(n => n.id.toLowerCase().includes(query) || (n.name && n.name.toLowerCase().includes(query))) : null;
            if (match) {
                networkInstance.selectNodes([match.id]);
                networkInstance.focus(match.id, { scale: 1.2, animation: { duration: 300 } });
                openEntityDetailsPanel(match.id);
            }
        });
    }
}

async function renderGraphWorkspace(caseId = "CASE_101") {
    activeCaseId = caseId;
    const container = document.getElementById("graph-canvas");
    if (!container) return;

    try {
        const data = await window.dataService.getCaseGraph(caseId);
        rawGraphData = data || { nodes: [], edges: [] };
        if (!rawGraphData.nodes) rawGraphData.nodes = [];
        if (!rawGraphData.edges) rawGraphData.edges = [];
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
            label: `${n.label || n.name || n.id}\n[${n.id}]${isManual ? ' ✎' : ''}`,
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
                    <span class="text-tertiary font-mono">Conf: <strong>${((ent.confidence || 1.0) * 100).toFixed(0)}%</strong></span>
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
                            <div class="text-[10px] text-on-surface-variant">Confidence: ${((r.confidence || 0.9) * 100).toFixed(0)}%</div>
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
                <div>Conf: <span class="text-tertiary font-bold">${((evObj.confidence || 0.95) * 100).toFixed(0)}%</span></div>
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
        closeAddEntityModal();
        showToast(`Created entity ${created.id || created.name} successfully!`, "success");

        // Immediately refresh graph workspace
        await renderGraphWorkspace(activeCaseId === "CASE_101" ? "ALL" : activeCaseId);
        networkInstance?.selectNodes([created.id]);
        await openEntityDetailsPanel(created.id);
    } catch (err) {
        showToast(`Error creating entity: ${err.message}`, "error");
    }
}

function openAddRelationshipModal(preselectedSourceId = null) {
    const modal = document.getElementById("modal-add-rel");
    const sourceSelect = document.getElementById("rel-source-select");
    const targetSelect = document.getElementById("rel-target-select");
    if (!modal || !sourceSelect || !targetSelect) return;

    // Populate entity selectors
    const nodes = rawGraphData.nodes || [];
    const optionsHtml = nodes.map(n => `<option value="${n.id}">[${n.type}] ${n.label || n.name} (${n.id})</option>`).join("");

    sourceSelect.innerHTML = optionsHtml;
    targetSelect.innerHTML = optionsHtml;

    if (preselectedSourceId) {
        sourceSelect.value = preselectedSourceId;
    }
    if (nodes.length > 1 && (!preselectedSourceId || preselectedSourceId === nodes[0].id)) {
        targetSelect.value = nodes[1].id;
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
            ${idx < res.path.length - 1 ? '<span class="text-outline">→</span>' : ''}
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
                <span class="px-2 py-0.5 rounded bg-tertiary-container/30 text-tertiary text-[10px] font-bold">${((ev.confidence || 0.95) * 100).toFixed(0)}% Confidence</span>
            </div>
            <p class="text-white italic text-[11px]">"${ev.source_text || ev.excerpt || 'Recorded evidence finding.'}"</p>
            <div class="text-[10px] text-outline font-mono">Source: ${ev.source_document || 'DOC_EXTRACTION'} (Pg. ${ev.page_number || 1})</div>
        </div>
    `).join("");
}

async function generateReport(caseId = "CASE_101") {
    const viewBox = document.getElementById("report-view-box");
    if (!viewBox) return;

    viewBox.innerHTML = `<div class="text-center py-10 text-outline text-xs"><span class="material-symbols-outlined animate-spin text-primary">sync</span> Generating Evidence-Linked Investigation Report for ${caseId}...</div>`;

    const report = await window.dataService.generateReport(caseId);
    if (!report || !report.content) {
        viewBox.innerHTML = `<div class="text-center py-10 text-error text-xs">Unable to generate report for ${caseId}.</div>`;
        return;
    }

    const formattedHtml = report.content
        .replace(/# (.*)/g, '<h1 class="text-base font-bold text-primary border-b border-surface-container-high pb-2 mb-2">$1</h1>')
        .replace(/## (.*)/g, '<h2 class="text-xs font-bold text-tertiary mt-3 mb-1 uppercase tracking-wider">$1</h2>')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
        .replace(/- (.*)/g, '<li class="ml-4 list-disc text-on-surface-variant">$1</li>')
        .replace(/\n\n/g, '<br><br>');

    viewBox.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between text-[11px] font-mono text-outline border-b border-surface-container-high pb-2">
                <span>Report ID: <strong class="text-tertiary">${report.report_id || 'REPORT_001'}</strong></span>
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
        container.innerHTML = list.map(p => `
            <div class="p-3 bg-surface-container-low border border-surface-container-high rounded space-y-2 text-xs">
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
                    <span class="font-bold font-mono text-purple-300 text-xs">${c.community_id} — ${c.classification || 'CRIMINAL_GROUP'}</span>
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
                    <span class="font-bold text-emerald-400 font-mono">Path #${idx + 1} (${p.hop_count} Hops) — Score: ${p.path_score || p.confidence}</span>
                    <span class="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/40">Confidence: ${p.confidence || 0.90}</span>
                </div>
                <p class="text-on-surface-variant text-[11px]">${p.explanation || 'Path discovered across multiple evidence items.'}</p>
                <div class="flex items-center gap-1.5 overflow-x-auto py-1 text-[11px] font-mono">
                    ${(p.path || []).map((node, i) => `<span class="px-2 py-0.5 rounded bg-surface-container-high text-primary border border-primary/30 font-bold">${node}</span>${i < p.path.length - 1 ? '<span class="text-outline">→</span>' : ''}`).join("")}
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
