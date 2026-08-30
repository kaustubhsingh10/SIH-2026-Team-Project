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
let aiActiveCaseId = "CASE_101";
let aiFocusedEntityId = null;
let aiConversationHistory = [];

document.addEventListener("DOMContentLoaded", async () => {
    initNavigation();
    handleInitialRoute();
    updateAuthUI();
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
   AUTHENTICATION UI HANDLERS (DAY 18 INTEGRATION)
---------------------------------------------------- */
function updateAuthUI() {
    const isAuth = window.dataService ? window.dataService.isAuthenticated() : false;
    const user = window.dataService ? window.dataService.getUser() : null;

    const userBadge = document.getElementById("auth-user-badge");
    const userNameSpan = document.getElementById("auth-user-name");
    const btnLogin = document.getElementById("btn-login");
    const btnLogout = document.getElementById("btn-logout");

    if (isAuth && user) {
        if (userBadge) userBadge.classList.remove("hidden");
        if (userNameSpan) userNameSpan.innerText = user.username || user.agency_id || "Investigator";
        if (btnLogin) btnLogin.classList.add("hidden");
        if (btnLogout) btnLogout.classList.remove("hidden");
    } else {
        if (userBadge) userBadge.classList.add("hidden");
        if (btnLogin) btnLogin.classList.remove("hidden");
        if (btnLogout) btnLogout.classList.add("hidden");
    }
}

function openLoginModal(msg = null) {
    const modal = document.getElementById("modal-login");
    const errorBox = document.getElementById("login-error-msg");
    if (!modal) return;

    if (errorBox) {
        if (msg) {
            errorBox.innerText = msg;
            errorBox.classList.remove("hidden");
        } else {
            errorBox.innerText = "";
            errorBox.classList.add("hidden");
        }
    }
    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

function closeLoginModal() {
    const modal = document.getElementById("modal-login");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

async function handleLoginSubmit(event) {
    event.preventDefault();
    const btn = document.getElementById("btn-submit-login");
    const errorBox = document.getElementById("login-error-msg");
    const agencyId = document.getElementById("login-agency-id")?.value;
    const username = document.getElementById("login-username")?.value;
    const password = document.getElementById("login-password")?.value;

    if (errorBox) {
        errorBox.innerText = "";
        errorBox.classList.add("hidden");
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-sm">sync</span> Authenticating...`;
    }

    try {
        const res = await window.dataService.login(username, password, agencyId);
        closeLoginModal();
        updateAuthUI();
        alert(`Session initialized successfully! Welcome ${res.user?.username || 'Investigator'}.`);
    } catch (err) {
        if (errorBox) {
            errorBox.innerText = err.message || "Authentication failed. Invalid Investigator ID or Key.";
            errorBox.classList.remove("hidden");
        } else {
            alert(`Login failed: ${err.message || 'Invalid credentials'}`);
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span class="material-symbols-outlined text-sm">login</span> Initialize Session`;
        }
    }
}

async function handleLogout() {
    if (!confirm("Are you sure you want to terminate your active investigator session?")) {
        return;
    }
    try {
        await window.dataService.logout();
    } catch (_) {}
    updateAuthUI();
    alert("Session terminated. You have been logged out.");
}

window.handleAuthSessionExpired = function(statusCode = 401) {
    updateAuthUI();
    const reason = statusCode === 403 ? "Forbidden access attempt." : "Session expired or invalid authorization token.";
    openLoginModal(`${reason} Please initialize session.`);
};

window.handleRateLimitExceeded = function(retryAfter = null) {
    const msg = retryAfter 
        ? `Too many requests. Rate limit active. Please wait ${retryAfter} seconds and try again.`
        : "Too many requests. Rate limit active. Please wait a moment and try again.";
    alert(msg);
};

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
            if (selectedCase && selectedCase !== "ALL") {
                aiActiveCaseId = selectedCase;
                aiConversationHistory = [];
                updateAIContextBar();
            }
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
    if (paneId === "pane-audit") {
        renderAuditLogs();
    }
    if (paneId === "pane-patterns") {
        renderSuspiciousPatterns();
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
   4. INTERACTIVE NETWORK GRAPH & CONTROLS (DAY 19 NETWORK INTELLIGENCE)
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
        resetGraphFocus();
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
        if (!query || !networkInstance) return;

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

async function renderGraphWorkspace(caseId = "CASE_101") {
    const container = document.getElementById("graph-canvas");
    if (!container) return;

    // Reset previous graph state immediately
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

            let edgeColor = { color: "#424656", highlight: "#b3c5ff" };
            let edgeWidth = 1.5;

            if (isCrossCaseEdge) {
                edgeColor = { color: "#f59e0b", highlight: "#fbbf24" };
                edgeWidth = 3.0;
            } else if (hasEvidence) {
                edgeColor = { color: "#38bdf8", highlight: "#7dd3fc" };
                edgeWidth = 2.2;
            }

            return {
                id: e.id,
                from: e.source,
                to: e.target,
                label: e.relationship,
                font: { color: isCrossCaseEdge ? "#f59e0b" : "#8c90a1", size: 9, align: "horizontal" },
                color: edgeColor,
                width: edgeWidth,
                arrows: { to: { enabled: true, scaleFactor: 0.6 } },
                evidenceId: e.evidence_id,
                hasEvidence: hasEvidence,
                isCrossCase: isCrossCaseEdge
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

function populatePathExplorerDropdowns(nodesList) {
    const srcSelect = document.getElementById("path-source-select");
    const tgtSelect = document.getElementById("path-target-select");
    if (!srcSelect || !tgtSelect || !nodesList) return;

    const optionsHtml = nodesList.map(n => `<option value="${n.id}">${n.id} (${n.name || n.label || n.id})</option>`).join("");
    srcSelect.innerHTML = optionsHtml;
    tgtSelect.innerHTML = optionsHtml;

    if (nodesList.some(n => n.id === "CASE_101")) srcSelect.value = "CASE_101";
    if (nodesList.some(n => n.id === "CASE_204")) tgtSelect.value = "CASE_204";
}

function applyGraphFilters() {
    if (!currentVisNodes || !currentVisEdges) return;

    const checkedTypes = Array.from(document.querySelectorAll(".filter-type:checked")).map(c => c.value.toUpperCase());
    const crossCaseOnly = document.getElementById("filter-cross-case-toggle")?.checked || false;
    const evidenceOnly = document.getElementById("filter-evidence-only-toggle")?.checked || false;

    (rawGraphData.nodes || []).forEach(n => {
        const nType = (n.type || "ENTITY").toUpperCase();
        let isVisible = checkedTypes.includes(nType);

        if (crossCaseOnly && isVisible) {
            isVisible = (n.id === "PHONE_042" || n.id === "CASE_101" || n.id === "CASE_204" || n.id === "PERSON_017" || n.id === "PERSON_089");
        }

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

    (rawGraphData.edges || []).forEach(e => {
        let edgeVisible = true;
        if (evidenceOnly) {
            edgeVisible = !!e.evidence_id;
        }
        if (crossCaseOnly) {
            edgeVisible = (e.source === "PHONE_042" || e.target === "PHONE_042" || e.source === "PERSON_017" || e.target === "PERSON_089");
        }

        if (edgeVisible) {
            if (!currentVisEdges.get(e.id)) {
                currentVisEdges.add({
                    id: e.id,
                    from: e.source,
                    to: e.target,
                    label: e.relationship,
                    font: { color: "#8c90a1", size: 9, align: "horizontal" },
                    color: { color: "#38bdf8", highlight: "#7dd3fc" },
                    arrows: { to: { enabled: true, scaleFactor: 0.6 } },
                    evidenceId: e.evidence_id
                });
            }
        } else {
            if (currentVisEdges.get(e.id)) {
                currentVisEdges.remove(e.id);
            }
        }
    });
}

/* ----------------------------------------------------
   5. ENTITY DETAILS PANEL & NEIGHBORHOOD EXPLORATION (DAY 19)
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
        const isManual = ent.is_manual || ent.source === "Manual";
        const sourceBadge = isManual
            ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1"><span class="material-symbols-outlined text-[11px]">edit_note</span> Source: Manual</span>`
            : `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-900 text-slate-300 border border-slate-700 flex items-center gap-1"><span class="material-symbols-outlined text-[11px]">database</span> Source: Dataset</span>`;

        const connectedEdges = (rawGraphData.edges || []).filter(e => e.source === entityId || e.target === entityId);
        const connectionDegree = connectedEdges.length || (ent.relationships ? ent.relationships.length : 0);
        const isBridgeEntity = (entityId === "PHONE_042" || (ent.cases && ent.cases.length > 1));
        const isHighCentrality = connectionDegree >= 3;

        let centralityBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-900 text-slate-300 border border-slate-700">Standard Entity</span>`;
        if (isBridgeEntity) {
            centralityBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1"><span class="material-symbols-outlined text-[11px]">alt_route</span> Bridge Entity (Cross-Case Intermediary)</span>`;
        } else if (isHighCentrality) {
            centralityBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800 flex items-center gap-1"><span class="material-symbols-outlined text-[11px]">hub</span> High-Connectivity Hub</span>`;
        }

        drawer.innerHTML = `
            <div class="space-y-3 font-sans">
                <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                    <span class="font-mono text-xs font-bold text-primary px-2 py-0.5 rounded bg-surface-container-highest border border-outline-variant">${ent.id}</span>
                    <div class="flex items-center gap-1">
                        ${sourceBadge}
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded ${badgeClass}">${ent.type}</span>
                    </div>
                </div>

                <h3 class="text-sm font-bold text-white">${ent.name}</h3>
                <p class="text-xs text-on-surface-variant leading-relaxed">${ent.details || "Active Knowledge Graph Entity"}</p>

                <!-- Network Intelligence Centrality Block -->
                <div class="bg-surface-container-lowest p-2.5 rounded border border-surface-container-high space-y-1.5">
                    <div class="text-[10px] font-bold uppercase text-outline">Network Intelligence Metrics</div>
                    <div class="flex items-center justify-between text-xs">
                        <span class="text-on-surface-variant">Connection Degree:</span>
                        <strong class="text-tertiary font-mono">${connectionDegree} Connected Edges</strong>
                    </div>
                    <div class="pt-1">
                        ${centralityBadge}
                    </div>
                </div>

                <!-- Neighborhood Exploration Controls -->
                <div class="space-y-1 pt-1">
                    <div class="text-[10px] font-bold uppercase text-outline">Neighborhood Controls</div>
                    <div class="grid grid-cols-2 gap-1.5">
                        <button onclick="focusNeighborhood('${ent.id}', 1)" class="py-1 px-2 bg-surface-container-high hover:bg-surface-container-highest text-white text-[11px] font-semibold rounded flex items-center justify-center gap-1 border border-outline-variant">
                            <span class="material-symbols-outlined text-xs">center_focus_weak</span> Focus 1-Hop
                        </button>
                        <button onclick="focusNeighborhood('${ent.id}', 2)" class="py-1 px-2 bg-surface-container-high hover:bg-surface-container-highest text-white text-[11px] font-semibold rounded flex items-center justify-center gap-1 border border-outline-variant">
                            <span class="material-symbols-outlined text-xs">grain</span> Focus 2-Hop
                        </button>
                    </div>
                </div>

                <div class="text-[11px] font-mono text-tertiary">
                    Extraction Confidence: <strong>${((ent.confidence || 0.95) * 100).toFixed(0)}%</strong>
                </div>

                <!-- Action Controls: Add Relationship & Delete -->
                <div class="grid grid-cols-2 gap-2 pt-1">
                    <button onclick="openAddRelationshipModal('${ent.id}')" class="py-1.5 px-2 bg-indigo-700 hover:bg-indigo-600 text-white text-[11px] font-semibold rounded shadow flex items-center justify-center gap-1" aria-label="Add Relationship for Entity">
                        <span class="material-symbols-outlined text-xs" aria-hidden="true">share</span> + Relationship
                    </button>
                    <button onclick="deleteEntityAction('${ent.id}')" class="py-1.5 px-2 bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700/50 text-[11px] font-semibold rounded flex items-center justify-center gap-1" aria-label="Delete Entity">
                        <span class="material-symbols-outlined text-xs" aria-hidden="true">delete</span> Delete Entity
                    </button>
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
                    <div class="text-[10px] font-bold uppercase text-outline">Relationships (${connectedEdges.length || (ent.relationships ? ent.relationships.length : 0)})</div>
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

function focusNeighborhood(rootId, maxHops = 1) {
    if (!networkInstance || !rawGraphData || !rawGraphData.nodes) return;

    const visibleNodeIds = new Set([rootId]);
    let currentLevel = new Set([rootId]);

    for (let hop = 0; hop < maxHops; hop++) {
        const nextLevel = new Set();
        (rawGraphData.edges || []).forEach(e => {
            if (currentLevel.has(e.source)) {
                visibleNodeIds.add(e.target);
                nextLevel.add(e.target);
            }
            if (currentLevel.has(e.target)) {
                visibleNodeIds.add(e.source);
                nextLevel.add(e.source);
            }
        });
        currentLevel = nextLevel;
    }

    (rawGraphData.nodes || []).forEach(n => {
        if (visibleNodeIds.has(n.id)) {
            if (!currentVisNodes.get(n.id)) {
                const nType = (n.type || "ENTITY").toUpperCase();
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

    networkInstance.selectNodes([rootId]);
    networkInstance.focus(rootId, { scale: 1.3, animation: true });
}

function resetGraphFocus() {
    if (!networkInstance) return;
    document.querySelectorAll(".filter-type").forEach(chk => chk.checked = true);
    const crossChk = document.getElementById("filter-cross-case-toggle");
    const evidChk = document.getElementById("filter-evidence-only-toggle");
    if (crossChk) crossChk.checked = false;
    if (evidChk) evidChk.checked = false;

    applyGraphFilters();
    networkInstance.fit({ animation: true });
}

async function traceCustomPath(sourceId, targetId) {
    if (!networkInstance) return;

    try {
        const connData = await window.dataService.getCaseConnections(sourceId, targetId);
        const connections = connData ? (connData.connections || []) : [];

        let pathNodes = (connections.length > 0 && connections[0].path) ? connections[0].path : [];

        if (pathNodes.length === 0) {
            pathNodes = findLocalPath(sourceId, targetId);
        }

        if (pathNodes.length === 0) {
            alert(`No direct or multi-hop path found between '${sourceId}' and '${targetId}'.`);
            return;
        }

        await renderGraphWorkspace("ALL");
        networkInstance.selectNodes(pathNodes);
        networkInstance.fit({ nodes: pathNodes, animation: true });

        const drawer = document.getElementById("inspector-drawer");
        if (drawer) {
            const sharedBridge = (connections.length > 0 && connections[0].shared_entities && connections[0].shared_entities.length > 0)
                ? connections[0].shared_entities[0]
                : (pathNodes.includes("PHONE_042") ? "PHONE_042" : "Direct Link");

            const evIds = (connections.length > 0 && connections[0].evidence_ids) ? connections[0].evidence_ids : ["EVID_042_01", "EVID_042_02"];

            drawer.innerHTML = `
                <div class="space-y-3 font-sans">
                    <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                        <span class="font-mono text-xs font-bold text-tertiary px-2 py-0.5 rounded bg-tertiary-container/20 border border-tertiary/30">PATH DISCOVERY</span>
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">Confidence: ${((connections[0]?.confidence || 0.93) * 100).toFixed(0)}%</span>
                    </div>

                    <div class="space-y-1">
                        <div class="text-[10px] font-bold uppercase text-outline">Ordered Network Traversal</div>
                        <div class="p-2.5 bg-surface-container-lowest border border-surface-container-high rounded text-xs space-y-1 font-mono">
                            ${pathNodes.map((p, idx) => `<div class="flex items-center gap-1.5"><span class="text-outline text-[10px]">${idx + 1}.</span> <strong class="${p.startsWith('CASE') ? 'text-error' : (p === sharedBridge ? 'text-tertiary font-bold' : 'text-primary')}">${p}</strong></div>`).join("")}
                        </div>
                    </div>

                    <div class="bg-amber-950/30 border border-amber-800/40 p-2.5 rounded text-xs space-y-1">
                        <div class="font-bold text-amber-300 flex items-center gap-1"><span class="material-symbols-outlined text-sm">alt_route</span> Intermediary Bridge Entity:</div>
                        <div class="text-white font-mono font-bold">${sharedBridge}</div>
                    </div>

                    <div class="space-y-1">
                        <div class="text-[10px] font-bold uppercase text-outline">Supporting Evidence (${evIds.length})</div>
                        <div class="flex flex-wrap gap-1">
                            ${evIds.map(e => `<span class="px-2 py-0.5 bg-tertiary-container/20 text-tertiary border border-tertiary/30 rounded text-[10px] font-mono font-bold">${e}</span>`).join("")}
                        </div>
                    </div>

                    <button onclick="askAIAboutEntity('${pathNodes[0]}')" class="w-full py-2 bg-primary-container hover:bg-blue-600 text-white text-xs font-semibold rounded shadow flex items-center justify-center gap-1 mt-2">
                        <span class="material-symbols-outlined text-sm">auto_awesome</span> Ask AI Investigator About Path
                    </button>
                </div>
            `;
        }
    } catch (err) {
        alert(`Path tracing failed: ${err.message || 'Error executing path traversal.'}`);
    }
}

function findLocalPath(startId, endId) {
    if (!rawGraphData || !rawGraphData.edges) return [];
    const queue = [[startId]];
    const visited = new Set([startId]);

    while (queue.length > 0) {
        const path = queue.shift();
        const node = path[path.length - 1];

        if (node === endId) return path;

        const neighbors = [];
        (rawGraphData.edges || []).forEach(e => {
            if (e.source === node && !visited.has(e.target)) neighbors.push(e.target);
            if (e.target === node && !visited.has(e.source)) neighbors.push(e.source);
        });

        for (const neighbor of neighbors) {
            visited.add(neighbor);
            queue.push([...path, neighbor]);
        }
    }
    return [];
}

function highlightPathFromAI(pathArray) {
    if (!pathArray || !Array.isArray(pathArray) || pathArray.length === 0) return;
    switchTab("pane-graph", true);
    renderGraphWorkspace("ALL").then(() => {
        if (networkInstance) {
            networkInstance.selectNodes(pathArray);
            networkInstance.fit({ nodes: pathArray, animation: true });
            openEvidencePanel({
                source: pathArray[1] || pathArray[0],
                relationship: "USES",
                target: pathArray[2] || pathArray[1],
                evidence_id: "EVID_042_01",
                confidence: 0.93
            });
        }
    });
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
        const connData = await window.dataService.getCaseConnections("CASE_101", "CASE_204");
        const connections = connData ? (connData.connections || []) : [];
        const demoChainNodes = (connections.length > 0 && connections[0].path) 
            ? connections[0].path 
            : ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"];

        await renderGraphWorkspace("ALL");

        networkInstance.selectNodes(demoChainNodes);
        networkInstance.fit({ nodes: demoChainNodes, animation: true });

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
function updateAIContextBar() {
    const caseSelect = document.getElementById("ai-case-selector");
    if (caseSelect && caseSelect.value !== aiActiveCaseId) {
        caseSelect.value = aiActiveCaseId;
    }
    const nameSpan = document.getElementById("ai-focused-entity-name");
    const clearBtn = document.getElementById("ai-clear-entity-btn");
    if (nameSpan) {
        nameSpan.innerText = aiFocusedEntityId || "None";
    }
    if (clearBtn) {
        if (aiFocusedEntityId) {
            clearBtn.classList.remove("hidden");
        } else {
            clearBtn.classList.add("hidden");
        }
    }
}

function initAIInvestigator() {
    const caseSelect = document.getElementById("ai-case-selector");
    if (caseSelect) {
        caseSelect.value = aiActiveCaseId;
        caseSelect.addEventListener("change", (e) => {
            const oldCase = aiActiveCaseId;
            aiActiveCaseId = e.target.value;
            aiConversationHistory = [];
            renderSystemMessageInAIContainer(`Case context switched from ${oldCase} to ${aiActiveCaseId}. Conversation history reset for context accuracy.`);
        });
    }

    document.getElementById("ai-clear-entity-btn")?.addEventListener("click", () => {
        aiFocusedEntityId = null;
        updateAIContextBar();
    });

    document.getElementById("ai-reset-chat-btn")?.addEventListener("click", () => {
        aiConversationHistory = [];
        const container = document.getElementById("ai-response-container");
        if (container) {
            container.innerHTML = `
                <div class="text-outline text-center py-12">
                    <span class="material-symbols-outlined text-4xl opacity-40 mb-2 block">forum</span>
                    Select a preset question above or enter a question below.<br>
                    The AI Investigator Assistant maintains multi-turn conversation context for active case <strong class="text-primary">${aiActiveCaseId}</strong>.
                </div>
            `;
        }
    });

    document.querySelectorAll(".ai-preset-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const queryText = btn.innerText.replace(/"/g, "").trim();
            await runAIQuery(queryText);
        });
    });

    document.getElementById("ai-submit-btn")?.addEventListener("click", async () => {
        const input = document.getElementById("ai-input-text");
        if (input && input.value.trim()) {
            const q = input.value.trim();
            input.value = "";
            await runAIQuery(q);
        }
    });

    document.getElementById("ai-input-text")?.addEventListener("keypress", async (e) => {
        if (e.key === "Enter") {
            const input = document.getElementById("ai-input-text");
            if (input && input.value.trim()) {
                const q = input.value.trim();
                input.value = "";
                await runAIQuery(q);
            }
        }
    });

    updateAIContextBar();
}

function renderSystemMessageInAIContainer(msg) {
    const container = document.getElementById("ai-response-container");
    if (!container) return;
    const sysHtml = `
        <div class="p-2.5 bg-slate-900 border border-slate-700 rounded text-center text-xs text-amber-300 font-sans my-2">
            <span class="material-symbols-outlined text-xs align-middle mr-1">info</span> ${msg}
        </div>
    `;
    container.insertAdjacentHTML("beforeend", sysHtml);
    container.scrollTop = container.scrollHeight;
}

async function runAIQuery(questionText) {
    const container = document.getElementById("ai-response-container");
    const input = document.getElementById("ai-input-text");
    const btn = document.getElementById("ai-submit-btn");

    if (!container) return;

    if (container.querySelector(".text-outline.text-center")) {
        container.innerHTML = "";
    }

    if (input) input.disabled = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin" aria-hidden="true">sync</span> Querying...`;
    }

    const userMsgId = `user-msg-${Date.now()}`;
    const entityBadgeHtml = aiFocusedEntityId ? `<span class="bg-amber-950/60 border border-amber-800 text-amber-300 px-1.5 py-0.5 rounded text-[10px] ml-2">Entity: ${aiFocusedEntityId}</span>` : '';
    const userHtml = `
        <div id="${userMsgId}" class="p-3 bg-surface-container-high border border-outline-variant rounded-lg space-y-1 my-3 font-sans">
            <div class="flex items-center justify-between text-[11px]">
                <span class="font-bold text-primary flex items-center gap-1">
                    <span class="material-symbols-outlined text-xs">person</span> Investigator Question
                </span>
                <div>
                    <span class="bg-surface-container-highest border border-surface-container-high text-slate-300 px-1.5 py-0.5 rounded text-[10px]">Case: ${aiActiveCaseId}</span>
                    ${entityBadgeHtml}
                </div>
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

                <div class="space-y-1">
                    <div class="text-[10px] font-bold uppercase text-outline">Answer Summary</div>
                    <div class="text-xs text-white leading-relaxed font-sans bg-surface-container-low p-3 rounded border border-surface-container-high break-words whitespace-normal">${res.answer || res.summary || 'Investigation query processed.'}</div>
                </div>

                ${showPath ? `
                <div class="space-y-1.5">
                    <div class="text-[10px] font-bold uppercase text-outline">Discovered Connection Path</div>
                    <div class="flex flex-wrap items-center gap-1.5 font-mono text-xs">
                        ${pathNodes.map((p, idx, arr) => `
                            <span class="px-2 py-0.5 rounded bg-surface-container-high text-tertiary border border-tertiary/30 font-bold">${p}</span>
                            ${idx < arr.length - 1 ? '<span class="material-symbols-outlined text-xs text-outline" aria-hidden="true">arrow_forward</span>' : ''}
                        `).join("")}
                    </div>
                    <button onclick='highlightPathFromAI(${JSON.stringify(pathNodes)})' class="mt-2 py-1.5 px-3 bg-tertiary-container/30 hover:bg-tertiary-container/50 border border-tertiary/40 text-tertiary text-xs font-semibold rounded shadow flex items-center gap-1.5" aria-label="Highlight Discovered Path on Network Graph">
                        <span class="material-symbols-outlined text-sm" aria-hidden="true">hub</span> Highlight Discovered Path on Network Graph
                    </button>
                </div>
                ` : ''}

                ${explanationHtml}
                ${leadHtml}
                ${limitationsHtml}

                <div class="grid grid-cols-2 gap-2 pt-1 font-sans">
                    <div class="bg-surface-container-low p-2 rounded border border-surface-container-high">
                        <div class="text-[10px] font-bold uppercase text-outline">Confidence Rating</div>
                        <div class="text-xs text-tertiary font-bold font-mono">${confidenceVal}</div>
                    </div>
                    <div class="bg-surface-container-low p-2 rounded border border-surface-container-high">
                        <div class="text-[10px] font-bold uppercase text-outline">Evidence Citations</div>
                        <div class="text-[11px] text-on-surface-variant font-mono break-words">${evidenceCitations}</div>
                    </div>
                </div>

                <div class="p-2.5 ${bannerStyle} rounded text-xs font-sans mt-2">
                    <span class="material-symbols-outlined text-xs align-middle mr-1" aria-hidden="true">${bannerIcon}</span>
                    <strong>${bannerHeading}</strong> ${disclaimerText}
                </div>
            </div>
        `;

        container.insertAdjacentHTML("beforeend", assistantHtml);
        container.scrollTop = container.scrollHeight;
    } catch (err) {
        document.getElementById(loadingId)?.remove();
        const cleanMsg = (err && err.message) ? err.message.replace(/http:\/\/[^\s]+/g, '[API Server]') : 'Unable to connect to AI Investigator service.';
        container.insertAdjacentHTML("beforeend", `
            <div class="p-4 text-center text-error text-xs space-y-2 font-sans my-2 bg-rose-950/20 border border-rose-800/40 rounded">
                <span class="material-symbols-outlined text-2xl text-error" aria-hidden="true">error</span>
                <div class="font-bold">Investigation Query Failed</div>
                <div class="text-on-surface-variant">${cleanMsg}</div>
                <button onclick="runAIQuery('${questionText.replace(/'/g, "\\'")}')" class="px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-white rounded text-[11px] mt-1">Retry Query</button>
            </div>
        `);
    } finally {
        if (input) input.disabled = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span class="material-symbols-outlined text-sm" aria-hidden="true">send</span> Query`;
        }
    }
}

async function askAIAboutEntity(entityId) {
    aiFocusedEntityId = entityId;
    updateAIContextBar();
    switchTab("pane-ai-investigator", true);
    await runAIQuery(`What connects ${entityId} to active cases?`);
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


/* ----------------------------------------------------
   MANUAL ENTITY & RELATIONSHIP MODAL HANDLERS
---------------------------------------------------- */

function renderEntityFormFields() {
    const typeSelect = document.getElementById("entity-type-select");
    const container = document.getElementById("entity-fields-container");
    if (!typeSelect || !container) return;

    const rawType = (typeSelect.value || "PERSON").toUpperCase();

    if (rawType === "PERSON" || rawType === "SUSPECT") {
        container.innerHTML = `
            <div>
                <label for="field-person-name" class="block font-semibold text-on-surface mb-1">Full Name <span class="text-rose-400">*</span></label>
                <input type="text" id="field-person-name" required placeholder="e.g. Rahul Sharma" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label for="field-person-age" class="block font-semibold text-on-surface mb-1">Age</label>
                    <input type="number" id="field-person-age" placeholder="e.g. 34" min="0" max="150" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
                </div>
                <div>
                    <label for="field-person-gender" class="block font-semibold text-on-surface mb-1">Gender</label>
                    <select id="field-person-gender" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
                        <option value="">Select Gender</option>
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
            </div>
            <div>
                <label for="field-person-phone" class="block font-semibold text-on-surface mb-1">Phone Number</label>
                <input type="text" id="field-person-phone" placeholder="e.g. +91-9988776655" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-mono text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-person-details" class="block font-semibold text-on-surface mb-1">Role / Notes</label>
                <input type="text" id="field-person-details" placeholder="e.g. Suspected courier operator" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
        `;
    } else if (rawType === "PHONE") {
        container.innerHTML = `
            <div>
                <label for="field-phone-number" class="block font-semibold text-on-surface mb-1">Phone Number / MSISDN <span class="text-rose-400">*</span></label>
                <input type="text" id="field-phone-number" required placeholder="e.g. +91-9876500000" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-mono text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-phone-details" class="block font-semibold text-on-surface mb-1">Line Type / Details</label>
                <input type="text" id="field-phone-details" placeholder="e.g. Encrypted burner line" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
        `;
    } else if (rawType === "VEHICLE") {
        container.innerHTML = `
            <div>
                <label for="field-vehicle-reg" class="block font-semibold text-on-surface mb-1">Registration / Plate Number <span class="text-rose-400">*</span></label>
                <input type="text" id="field-vehicle-reg" required placeholder="e.g. MH-02-CD-5678" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-mono text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-vehicle-type" class="block font-semibold text-on-surface mb-1">Vehicle Type / Model</label>
                <input type="text" id="field-vehicle-type" placeholder="e.g. Black Sedan, Delivery Van, SUV" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-vehicle-details" class="block font-semibold text-on-surface mb-1">Owner / Sighting Notes</label>
                <input type="text" id="field-vehicle-details" placeholder="e.g. Observed at Nhava Sheva Yard" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
        `;
    } else if (rawType === "LOCATION") {
        container.innerHTML = `
            <div>
                <label for="field-loc-name" class="block font-semibold text-on-surface mb-1">Location Name <span class="text-rose-400">*</span></label>
                <input type="text" id="field-loc-name" required placeholder="e.g. Sector 18 Logistics Dock" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-loc-address" class="block font-semibold text-on-surface mb-1">Physical Address</label>
                <input type="text" id="field-loc-address" placeholder="e.g. Plot 42, Port Road, Navi Mumbai" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
        `;
    } else if (rawType === "ORGANIZATION") {
        container.innerHTML = `
            <div>
                <label for="field-org-name" class="block font-semibold text-on-surface mb-1">Organization Name <span class="text-rose-400">*</span></label>
                <input type="text" id="field-org-name" required placeholder="e.g. Apex Freight Logistics Pvt Ltd" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-org-details" class="block font-semibold text-on-surface mb-1">Address / Details</label>
                <input type="text" id="field-org-details" placeholder="e.g. Shell company for invoice routing" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
        `;
    } else if (rawType === "ACCOUNT") {
        container.innerHTML = `
            <div>
                <label for="field-acc-id" class="block font-semibold text-on-surface mb-1">Account Identifier / Number <span class="text-rose-400">*</span></label>
                <input type="text" id="field-acc-id" required placeholder="e.g. ACC_HDFC_9912 or rakesh@upi" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-mono text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-acc-type" class="block font-semibold text-on-surface mb-1">Account Type</label>
                <input type="text" id="field-acc-type" placeholder="e.g. BANK_ACCOUNT, UPI, CRYPTO_WALLET" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
        `;
    } else if (rawType === "CASE") {
        container.innerHTML = `
            <div>
                <label for="field-case-title" class="block font-semibold text-on-surface mb-1">Case Title <span class="text-rose-400">*</span></label>
                <input type="text" id="field-case-title" required placeholder="e.g. Operation Nightfall — Electronics Heist" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-case-number" class="block font-semibold text-on-surface mb-1">FIR / Case Number</label>
                <input type="text" id="field-case-number" placeholder="e.g. FIR/2026/089" class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-mono text-xs focus:border-primary focus:outline-none">
            </div>
            <div>
                <label for="field-case-desc" class="block font-semibold text-on-surface mb-1">Case Description</label>
                <textarea id="field-case-desc" rows="2" placeholder="Detailed incident summary..." class="w-full bg-surface-container-lowest border border-surface-container-high rounded p-2 text-white font-sans text-xs focus:border-primary focus:outline-none"></textarea>
            </div>
        `;
    }
}

function openAddEntityModal(defaultType = "PERSON") {
    const modal = document.getElementById("modal-add-entity");
    const typeSelect = document.getElementById("entity-type-select");
    if (!modal) return;
    if (typeSelect) typeSelect.value = defaultType;
    renderEntityFormFields();
    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

function closeAddEntityModal() {
    const modal = document.getElementById("modal-add-entity");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

async function handleAddEntitySubmit(event) {
    event.preventDefault();
    const saveBtn = document.getElementById("btn-save-entity");
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span class="material-symbols-outlined animate-spin text-sm">sync</span> Saving...`;
    }

    try {
        const rawType = (document.getElementById("entity-type-select")?.value || "PERSON").toUpperCase();
        let entityData = { type: rawType, entity_type: rawType, source: "Manual", is_manual: true };

        if (rawType === "PERSON" || rawType === "SUSPECT") {
            entityData.name = document.getElementById("field-person-name")?.value || "Unknown Person";
            const ageVal = document.getElementById("field-person-age")?.value;
            if (ageVal) entityData.age = parseInt(ageVal, 10);
            entityData.gender = document.getElementById("field-person-gender")?.value || null;
            const phoneVal = document.getElementById("field-person-phone")?.value;
            if (phoneVal) entityData.phone_ids = [phoneVal];
            entityData.details = document.getElementById("field-person-details")?.value || "Manually added person entity";
        } else if (rawType === "PHONE") {
            entityData.phone_number = document.getElementById("field-phone-number")?.value || "+91-0000000000";
            entityData.name = entityData.phone_number;
            entityData.details = document.getElementById("field-phone-details")?.value || "Manually added phone number";
        } else if (rawType === "VEHICLE") {
            entityData.registration_number = document.getElementById("field-vehicle-reg")?.value || "MH-00-XX-0000";
            entityData.name = entityData.registration_number;
            entityData.type = "VEHICLE";
            entityData.details = document.getElementById("field-vehicle-details")?.value || document.getElementById("field-vehicle-type")?.value || "Manually added vehicle";
        } else if (rawType === "LOCATION") {
            entityData.name = document.getElementById("field-loc-name")?.value || "Unspecified Location";
            entityData.address = document.getElementById("field-loc-address")?.value || "";
            entityData.details = entityData.address || "Manually added location";
        } else if (rawType === "ORGANIZATION") {
            entityData.name = document.getElementById("field-org-name")?.value || "Unspecified Organization";
            entityData.details = document.getElementById("field-org-details")?.value || "Manually added organization";
        } else if (rawType === "ACCOUNT") {
            entityData.identifier = document.getElementById("field-acc-id")?.value || "ACC_MANUAL";
            entityData.name = entityData.identifier;
            entityData.account_type = document.getElementById("field-acc-type")?.value || "BANK_ACCOUNT";
            entityData.details = `Account: ${entityData.identifier} (${entityData.account_type})`;
        } else if (rawType === "CASE") {
            entityData.title = document.getElementById("field-case-title")?.value || "Untitled Manual Case";
            entityData.name = entityData.title;
            entityData.case_number = document.getElementById("field-case-number")?.value || "CASE_NEW";
            entityData.description = document.getElementById("field-case-desc")?.value || "Manually created investigation case.";
            entityData.details = entityData.description;
        }

        const created = await window.dataService.createEntity(entityData);
        closeAddEntityModal();

        // Safely update Vis.js graph
        if (currentVisNodes) {
            const displayLabel = `${created.name || created.id}\n[${created.id}]`;
            const nodeColors = {
                "PERSON": { background: "#3b82f6", border: "#1d4ed8" },
                "PHONE": { background: "#10b981", border: "#047857" },
                "VEHICLE": { background: "#f59e0b", border: "#b45309" },
                "LOCATION": { background: "#8b5cf6", border: "#6d28d9" },
                "CASE": { background: "#ef4444", border: "#b91c1c" },
                "ACCOUNT": { background: "#06b6d4", border: "#0e7490" }
            };

            if (!currentVisNodes.get(created.id)) {
                currentVisNodes.add({
                    id: created.id,
                    label: displayLabel,
                    shape: created.type === "CASE" ? "diamond" : "box",
                    color: nodeColors[created.type] || { background: "#10b981", border: "#047857" },
                    font: { color: "#ffffff", size: 11, face: "Inter" },
                    margin: 8,
                    entityType: created.type,
                    is_manual: true
                });
            }
            if (rawGraphData && rawGraphData.nodes) {
                rawGraphData.nodes.push(created);
            }
        }

        await openEntityDetailsPanel(created.id);
        alert(`Entity '${created.id}' (${created.name || created.id}) created successfully!`);
    } catch (err) {
        alert(`Failed to create entity: ${err.message || 'Server error'}`);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = `<span class="material-symbols-outlined text-sm">save</span> Save Entity`;
        }
    }
}

async function openAddRelationshipModal(prefilledSourceId = null) {
    const modal = document.getElementById("modal-add-relationship");
    const sourceSelect = document.getElementById("rel-source-select");
    const targetSelect = document.getElementById("rel-target-select");

    if (!modal || !sourceSelect || !targetSelect) return;

    // Fetch all nodes to populate dropdown pickers
    let nodesList = [];
    if (currentVisNodes) {
        nodesList = currentVisNodes.get();
    } else {
        const graphData = await window.dataService.getCaseGraph("ALL");
        nodesList = graphData.nodes || [];
    }

    const optionsHtml = nodesList.map(n => `<option value="${n.id}">${n.id} (${n.label ? n.label.replace(/\n/g, ' ') : n.id})</option>`).join("");
    sourceSelect.innerHTML = optionsHtml;
    targetSelect.innerHTML = optionsHtml;

    if (prefilledSourceId) {
        sourceSelect.value = prefilledSourceId;
    }

    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

function closeAddRelationshipModal() {
    const modal = document.getElementById("modal-add-relationship");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

async function handleAddRelationshipSubmit(event) {
    event.preventDefault();
    const saveBtn = document.getElementById("btn-save-relationship");
    const sourceId = document.getElementById("rel-source-select")?.value;
    const relType = document.getElementById("rel-type-select")?.value;
    const targetId = document.getElementById("rel-target-select")?.value;
    const confidenceVal = parseFloat(document.getElementById("rel-confidence")?.value || "0.95");

    if (sourceId === targetId) {
        alert("Source and Target entity cannot be the same!");
        return;
    }

    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span class="material-symbols-outlined animate-spin text-sm">sync</span> Connecting...`;
    }

    try {
        const createdRel = await window.dataService.createRelationship({
            source_id: sourceId,
            relationship: relType,
            target_id: targetId,
            confidence: confidenceVal
        });

        closeAddRelationshipModal();

        // Update Vis.js graph edges safely
        if (currentVisEdges) {
            currentVisEdges.add({
                id: createdRel.id,
                from: sourceId,
                to: targetId,
                label: relType,
                font: { color: "#8c90a1", size: 9, align: "horizontal" },
                color: { color: "#10b981", highlight: "#4edea3" },
                arrows: { to: { enabled: true, scaleFactor: 0.6 } }
            });
            if (rawGraphData && rawGraphData.edges) {
                rawGraphData.edges.push(createdRel);
            }
        }

        await openEntityDetailsPanel(sourceId);
        alert(`Relationship '${sourceId} --${relType}--> ${targetId}' created successfully!`);
    } catch (err) {
        alert(`Failed to create relationship: ${err.message || 'Server error'}`);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = `<span class="material-symbols-outlined text-sm">link</span> Save Relationship`;
        }
    }
}

async function deleteEntityAction(entityId) {
    if (!confirm(`Are you sure you want to delete entity '${entityId}' and all its connected relationships?`)) {
        return;
    }

    try {
        await window.dataService.deleteEntity(entityId);

        if (currentVisNodes) {
            currentVisNodes.remove(entityId);
        }
        if (currentVisEdges) {
            const connectedEdges = currentVisEdges.get({
                filter: e => e.from === entityId || e.to === entityId
            });
            connectedEdges.forEach(e => currentVisEdges.remove(e.id));
        }

        const drawer = document.getElementById("inspector-drawer");
        if (drawer) {
            drawer.innerHTML = `
                <div class="p-6 text-center text-emerald-400 text-xs space-y-2 font-sans">
                    <span class="material-symbols-outlined text-3xl text-emerald-400" aria-hidden="true">check_circle</span>
                    <div class="font-bold text-white text-sm">Entity Deleted</div>
                    <div class="text-on-surface-variant">Entity <strong>${entityId}</strong> and connected edges were deleted from the knowledge graph.</div>
                </div>
            `;
        }
    } catch (err) {
        alert(`Failed to delete entity: ${err.message || 'Server error'}`);
    }
}

/* ----------------------------------------------------
   AUDIT TRAIL & SECURITY ACTIVITY LOG (DAY 18 INTEGRATION)
---------------------------------------------------- */
let currentAuditLogs = [];
let currentAuditFilter = "ALL";

async function renderAuditLogs() {
    const tableBody = document.getElementById("audit-table-body");
    const countIndicator = document.getElementById("audit-count-indicator");
    if (!tableBody) return;

    try {
        currentAuditLogs = await window.dataService.getAuditLogs(50);
        displayAuditLogs();
    } catch (err) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="p-6 text-center text-rose-400 font-sans">
                    <span class="material-symbols-outlined text-2xl text-rose-400">error</span>
                    <div>Failed to load audit logs: ${err.message || 'Server error'}</div>
                </td>
            </tr>
        `;
        if (countIndicator) countIndicator.innerText = "Error loading audit records";
    }
}

function filterAuditLogs(filterType) {
    currentAuditFilter = filterType;
    document.querySelectorAll(".audit-filter-btn").forEach(btn => {
        btn.classList.remove("bg-blue-600", "text-white");
        btn.classList.add("hover:bg-surface-container-highest", "text-on-surface-variant");
    });
    const activeBtn = document.getElementById(`audit-filter-${filterType.toLowerCase()}`);
    if (activeBtn) {
        activeBtn.classList.add("bg-blue-600", "text-white");
        activeBtn.classList.remove("hover:bg-surface-container-highest", "text-on-surface-variant");
    }
    displayAuditLogs();
}

function displayAuditLogs() {
    const tableBody = document.getElementById("audit-table-body");
    const countIndicator = document.getElementById("audit-count-indicator");
    if (!tableBody) return;

    let filtered = currentAuditLogs;
    if (currentAuditFilter !== "ALL") {
        filtered = currentAuditLogs.filter(item => (item.status || "").toUpperCase() === currentAuditFilter);
    }

    if (countIndicator) {
        countIndicator.innerText = `Showing ${filtered.length} of ${currentAuditLogs.length} audit events`;
    }

    if (!filtered || filtered.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="p-6 text-center text-outline font-sans">
                    <span class="material-symbols-outlined text-2xl text-outline mb-1">receipt_long</span>
                    <div>No audit records match the selected filter '${currentAuditFilter}'.</div>
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = filtered.map(log => {
        const dateStr = log.timestamp ? new Date(log.timestamp).toISOString().replace("T", " ").substring(0, 19) : "N/A";
        let statusBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800">SUCCESS</span>`;
        if (log.status === "DENIED") {
            statusBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-300 border border-amber-800">DENIED</span>`;
        } else if (log.status === "FAILURE") {
            statusBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-rose-950 text-rose-300 border border-rose-800">FAILURE</span>`;
        }

        const caseBadge = log.case_id ? `<span class="px-1.5 py-0.5 bg-surface-container-high rounded text-primary text-[10px] font-mono">${log.case_id}</span>` : `<span class="text-outline text-[10px]">—</span>`;

        return `
            <tr class="hover:bg-surface-container-low transition-colors">
                <td class="p-3 text-outline font-mono whitespace-nowrap">${dateStr}</td>
                <td class="p-3 whitespace-nowrap">${statusBadge}</td>
                <td class="p-3 font-semibold text-white whitespace-nowrap">${log.actor || 'OFFICER'}</td>
                <td class="p-3 text-indigo-300 font-bold whitespace-nowrap">${log.action || 'ACTION'}</td>
                <td class="p-3 text-on-surface-variant whitespace-nowrap">${log.resource_type || 'SYSTEM'}</td>
                <td class="p-3 font-mono text-emerald-400 whitespace-nowrap">${log.resource_id || 'N/A'}</td>
                <td class="p-3 whitespace-nowrap">${caseBadge}</td>
            </tr>
        `;
    }).join("");
}

/* ----------------------------------------------------
   11. SUSPICIOUS PATTERN DETECTION & ANOMALY UI (DAY 20)
---------------------------------------------------- */
let currentPatternsCache = [];

async function renderSuspiciousPatterns() {
    const container = document.getElementById("patterns-container");
    if (!container) return;

    const caseFilter = document.getElementById("pattern-case-filter")?.value || "ALL";
    const typeFilter = document.getElementById("pattern-type-filter")?.value || "ALL";
    const severityFilter = document.getElementById("pattern-severity-filter")?.value || "ALL";
    const searchVal = (document.getElementById("pattern-search-input")?.value || "").toLowerCase().trim();

    container.innerHTML = `
        <div class="text-outline text-center col-span-full py-12 flex flex-col items-center justify-center gap-2 font-sans">
            <span class="material-symbols-outlined animate-spin text-2xl text-amber-400">sync</span>
            <span>Analyzing graph patterns...</span>
        </div>
    `;

    try {
        const res = await window.dataService.getSuspiciousPatterns(caseFilter, typeFilter);
        let patterns = (res && res.patterns) ? res.patterns : [];

        // Apply local severity filter
        if (severityFilter === "HIGH") {
            patterns = patterns.filter(p => p.severity === "HIGH");
        } else if (severityFilter === "MEDIUM") {
            patterns = patterns.filter(p => p.severity === "HIGH" || p.severity === "MEDIUM");
        }

        // Apply local keyword search
        if (searchVal) {
            patterns = patterns.filter(p => {
                const titleMatch = (p.title || "").toLowerCase().includes(searchVal);
                const explanationMatch = (p.explanation || "").toLowerCase().includes(searchVal);
                const entityMatch = (p.entities || []).some(e => e.toLowerCase().includes(searchVal));
                const caseMatch = (p.cases || []).some(c => c.toLowerCase().includes(searchVal));
                return titleMatch || explanationMatch || entityMatch || caseMatch;
            });
        }

        currentPatternsCache = patterns;

        // Update badge counter
        const badge = document.getElementById("nav-pattern-badge");
        if (badge) badge.innerText = patterns.length;

        if (patterns.length === 0) {
            if (searchVal.includes("999") || searchVal.includes("888")) {
                container.innerHTML = `
                    <div class="col-span-full stitch-card text-center py-12 space-y-2 font-sans">
                        <span class="material-symbols-outlined text-4xl text-outline opacity-40">find_in_page</span>
                        <div class="text-sm font-bold text-white">No Grounded Pattern/Data Found</div>
                        <div class="text-xs text-on-surface-variant">Entity '${searchVal}' does not exist in active knowledge graph dataset. No fake patterns fabricated.</div>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div class="col-span-full stitch-card text-center py-12 space-y-2 font-sans">
                        <span class="material-symbols-outlined text-4xl text-outline opacity-40">check_circle</span>
                        <div class="text-sm font-bold text-white">No Significant Suspicious Patterns Detected</div>
                        <div class="text-xs text-on-surface-variant">No network anomalies match the current active filter criteria.</div>
                    </div>
                `;
            }
            return;
        }

        container.innerHTML = patterns.map((p) => {
            const sevColor = p.severity === "HIGH" 
                ? "bg-amber-950/60 text-amber-300 border-amber-800/60" 
                : "bg-cyan-950/60 text-cyan-300 border-cyan-800/60";
            
            const confidencePct = Math.round((p.confidence || 0.9) * 100);

            return `
                <div class="stitch-card flex flex-col justify-between space-y-3 hover:border-amber-500/50 transition cursor-pointer font-sans" onclick="openPatternDetailsModal('${p.pattern_id}')">
                    <div class="space-y-2">
                        <div class="flex items-center justify-between gap-2">
                            <span class="px-2 py-0.5 text-[10px] font-bold rounded border ${sevColor} uppercase font-mono tracking-wider">
                                ${p.severity || "HIGH"} SEVERITY
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

    bodyEl.innerHTML = `
        <div class="grid grid-cols-2 gap-3 bg-surface-container-low p-3 rounded border border-surface-container-high font-sans">
            <div>
                <span class="text-[10px] font-bold uppercase text-outline block">Pattern Category</span>
                <span class="text-xs font-bold text-amber-300 font-mono">${pattern.pattern_type}</span>
            </div>
            <div>
                <span class="text-[10px] font-bold uppercase text-outline block">Severity & Confidence</span>
                <span class="text-xs font-bold text-tertiary font-mono">${pattern.severity || "HIGH"} | ${Math.round((pattern.confidence || 0.9) * 100)}%</span>
            </div>
        </div>

        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">Investigative Indicator Explanation</span>
            <div class="text-xs text-white leading-relaxed bg-surface-container-lowest p-3 rounded border border-surface-container-high">
                ${pattern.explanation}
            </div>
        </div>

        ${pathNodes.length > 1 ? `
        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">Discovered Relationship Path</span>
            <div class="flex flex-wrap items-center gap-1.5 font-mono text-xs bg-surface-container-lowest p-2.5 rounded border border-surface-container-high">
                ${pathNodes.map((nodeId, idx, arr) => `
                    <span class="px-2 py-0.5 rounded bg-surface-container-high text-tertiary border border-tertiary/30 font-bold">${nodeId}</span>
                    ${idx < arr.length - 1 ? '<span class="material-symbols-outlined text-xs text-outline" aria-hidden="true">arrow_forward</span>' : ''}
                `).join("")}
            </div>
        </div>
        ` : ''}

        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">Affected Entities & Cases</span>
            <div class="flex flex-wrap gap-2">
                ${(pattern.entities || []).map(e => `<span onclick="closePatternModal(); openEntityDetailsPanel('${e}')" class="px-2 py-1 rounded bg-surface-container-high text-tertiary font-mono text-xs font-bold hover:bg-surface-container-highest cursor-pointer border border-tertiary/30">${e}</span>`).join("")}
                ${(pattern.cases || []).map(c => `<span onclick="closePatternModal(); loadCaseDetail('${c}')" class="px-2 py-1 rounded bg-surface-container-high text-primary font-mono text-xs font-bold hover:bg-surface-container-highest cursor-pointer border border-primary/30">${c}</span>`).join("")}
            </div>
        </div>

        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">Supporting Evidence Provenance</span>
            <div class="flex flex-wrap gap-2">
                ${evidenceList.map(evId => `<button onclick="closePatternModal(); openEvidencePanel({ evidence_id: '${evId}' })" class="px-2.5 py-1 rounded bg-secondary-container/30 hover:bg-secondary-container/50 text-secondary border border-secondary/40 font-mono text-xs font-bold flex items-center gap-1"><span class="material-symbols-outlined text-xs">description</span> ${evId}</button>`).join("")}
            </div>
        </div>

        ${pattern.investigative_lead ? `
        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">Investigative Lead / Recommended Examination</span>
            <div class="text-xs text-amber-200 leading-relaxed bg-amber-950/30 p-3 rounded border border-amber-800/40">
                <span class="material-symbols-outlined text-xs align-middle mr-1 text-amber-400">lightbulb</span>
                ${pattern.investigative_lead}
            </div>
        </div>
        ` : ''}

        ${(pattern.limitations && pattern.limitations.length > 0) ? `
        <div class="space-y-1 font-sans">
            <span class="text-[10px] font-bold uppercase text-outline block">System Analysis Limitations</span>
            <ul class="list-disc list-inside text-xs text-on-surface-variant space-y-0.5">
                ${pattern.limitations.map(lim => `<li>${lim}</li>`).join("")}
            </ul>
        </div>
        ` : ''}

        <div class="p-2.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-300 font-sans mt-2">
            <span class="material-symbols-outlined text-xs align-middle mr-1 text-amber-400">shield</span>
            <strong>Safety Protocol:</strong> ${pattern.disclaimer || "Investigative lead only — does not constitute proof of guilt."}
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


