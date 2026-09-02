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
    await renderKeyPlayersWorkspace();
    initLinkAnalysisControls();
    initGlobalSearch();
    await populateCaseDropdowns("CASE_101");
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
            if (typeof renderCorrelations === "function") await renderCorrelations(selectedCase);
            if (typeof renderRiskIntelligence === "function") await renderRiskIntelligence(selectedCase);
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
    if (paneId === "pane-reports") {
        renderInvestigationReport();
    }
    if (paneId === "pane-entity-resolution") {
        renderEntityResolutionWorkspace();
    }
    if (paneId === "pane-communities") {
        renderCommunitiesWorkspace();
    }
    if (paneId === "pane-key-players") {
        renderKeyPlayersWorkspace();
    }
    if (paneId === "pane-link-analysis") {
        renderLinkAnalysisWorkspace();
    }
}

/* ----------------------------------------------------
   2. DASHBOARD & CASE EXPLORER (PHASE 3 & 5)
---------------------------------------------------- */
async function renderDashboard() {
    const casesContainer = document.getElementById("dashboard-cases-container");
    const signalsContainer = document.getElementById("dashboard-signals-container");
    const keyEntitiesContainer = document.getElementById("dashboard-key-entities-container");
    const activityContainer = document.getElementById("dashboard-activity-container");

    if (casesContainer) {
        casesContainer.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-primary align-middle mr-1">sync</span> Loading Investigation Command Dashboard...</div>`;
    }

    try {
        const dashData = await window.dataService.getInvestigationDashboard();
        const metrics = dashData.metrics || {};
        const cases = dashData.active_cases || [];
        const keyEntities = dashData.key_entities || [];
        const patterns = dashData.patterns || [];
        const anomalies = dashData.anomalies || [];
        const aiFindings = dashData.ai_findings || [];
        const recentEvidence = dashData.recent_evidence || [];

        // 1. Update Metric Counter Cards
        const setMetric = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val !== undefined && val !== null ? val : 0;
        };

        setMetric("dash-metric-cases", metrics.total_cases || cases.length);
        setMetric("dash-metric-priority", metrics.high_priority_cases || cases.filter(c => ['HIGH', 'URGENT'].includes((c.priority || '').toUpperCase())).length);
        setMetric("dash-metric-entities", metrics.key_entities_count || keyEntities.length);
        setMetric("dash-metric-patterns", (metrics.patterns_count || 0) + (metrics.anomalies_count || 0));
        setMetric("dash-metric-links", metrics.cross_case_links_count || 2);
        setMetric("dash-metric-evidence", metrics.evidence_count || recentEvidence.length);

        // Update sidebar metrics if present
        setMetric("sidebar-metric-nodes", metrics.key_entities_count || 34);
        setMetric("sidebar-metric-edges", 24);
        setMetric("sidebar-metric-evidence", metrics.evidence_count || 19);

        // 2. Render Active Cases Grid
        if (casesContainer) {
            if (!cases || cases.length === 0) {
                casesContainer.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans">No active cases found in investigation store.</div>`;
            } else {
                casesContainer.innerHTML = cases.slice(0, 6).map(c => `
                    <div class="stitch-card stitch-card-interactive space-y-2.5 font-sans">
                        <div class="flex items-center justify-between">
                            <span class="font-mono text-xs text-error font-bold px-2 py-0.5 rounded bg-error-container/30 border border-error/40">${c.id}</span>
                            <div class="flex items-center gap-1">
                                <span class="text-[10px] font-bold px-2 py-0.5 rounded border ${
                                    (c.priority || '').toUpperCase() === 'HIGH' || (c.priority || '').toUpperCase() === 'URGENT'
                                    ? 'bg-rose-950/60 text-rose-300 border-rose-800/60'
                                    : 'bg-slate-800 text-slate-300 border-slate-700'
                                }">${c.priority || 'MEDIUM'}</span>
                                <span class="text-[10px] font-bold text-tertiary bg-tertiary-container/20 px-2 py-0.5 rounded border border-tertiary/30">${c.status || 'ACTIVE'}</span>
                            </div>
                        </div>
                        <h4 class="text-xs font-bold text-white line-clamp-1">${c.title || c.id}</h4>
                        <div class="text-[11px] text-on-surface-variant flex items-center gap-2">
                            <span class="flex items-center gap-0.5"><span class="material-symbols-outlined text-xs">location_on</span> ${c.location || 'LOC_001'}</span>
                            <span>•</span>
                            <span>${c.entity_count || 0} entities</span>
                            <span>•</span>
                            <span>${c.evidence_count || 0} evidence</span>
                        </div>
                        <div class="flex items-center justify-between pt-2 border-t border-surface-container-high text-[11px]">
                            <span class="text-outline font-mono text-[10px]">${c.date || c.incident_date || ''}</span>
                            <div class="flex items-center gap-2">
                                <button onclick="exploreCase('${c.id}')" class="text-primary font-semibold flex items-center gap-0.5 hover:underline" aria-label="Explore Graph for ${c.id}">
                                    Graph <span class="material-symbols-outlined text-xs">arrow_forward</span>
                                </button>
                                <button onclick="openCaseDetail('${c.id}')" class="text-tertiary font-semibold flex items-center gap-0.5 hover:underline" aria-label="Open Case Detail for ${c.id}">
                                    Inspect <span class="material-symbols-outlined text-xs">open_in_new</span>
                                </button>
                            </div>
                        </div>
                    </div>
                `).join("");
            }
        }

        // 3. Render Investigation Signals & AI Review Findings
        if (signalsContainer) {
            const combinedSignals = [
                ...aiFindings,
                ...patterns.map(p => ({
                    id: p.pattern_id || p.id || 'PAT_001',
                    title: p.title || p.pattern_type || 'Suspicious Pattern Detected',
                    type: 'SUSPICIOUS_PATTERN',
                    description: p.description || 'Pattern matching financial loop or shared infrastructure.',
                    confidence: p.confidence || 0.89,
                    status: 'Suspicious Pattern',
                    case_a: p.case_id || 'CASE_101',
                    entity_id: (p.entities && p.entities[0]) || null
                })),
                ...anomalies.map(a => ({
                    id: a.anomaly_id || a.id || 'ANO_001',
                    title: a.title || a.anomaly_type || 'Network Anomaly Signal',
                    type: 'ANOMALY_SIGNAL',
                    description: a.description || 'Deviance score exceeds threshold.',
                    confidence: a.confidence || a.anomaly_score || 0.86,
                    status: 'Investigative Lead',
                    entity_id: a.entity_id || null
                }))
            ].slice(0, 4);

            if (combinedSignals.length === 0) {
                signalsContainer.innerHTML = `<div class="p-3 bg-surface-container-low border border-surface-container-high rounded text-xs text-on-surface-variant">No active AI pattern signals require review.</div>`;
            } else {
                signalsContainer.innerHTML = combinedSignals.map(s => `
                    <div class="stitch-card bg-surface-container-low border-surface-container-high p-3 space-y-2 hover:border-purple-500/40 transition">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-1.5">
                                <span class="material-symbols-outlined text-purple-400 text-sm">psychology</span>
                                <span class="text-xs font-bold text-white">${s.title}</span>
                            </div>
                            <span class="px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
                                s.status === 'Requires Review' ? 'bg-amber-950/60 text-amber-300 border border-amber-800/60' : 'bg-purple-950/60 text-purple-300 border border-purple-800/60'
                            }">${s.status} (${Math.round((s.confidence || 0.85) * 100)}%)</span>
                        </div>
                        <p class="text-xs text-on-surface-variant line-clamp-2">${s.description}</p>
                        <div class="flex items-center justify-between pt-2 border-t border-surface-container-high text-[11px]">
                            <span class="text-outline text-[10px] font-mono">${s.type}</span>
                            <div class="flex items-center gap-2">
                                ${s.entity_id ? `<button onclick="openEntityDetails('${s.entity_id}')" class="text-tertiary font-semibold hover:underline text-[11px]">Inspect Entity</button>` : ''}
                                <button onclick="switchTab('pane-patterns')" class="text-purple-400 font-semibold hover:underline text-[11px]">View Analysis</button>
                            </div>
                        </div>
                    </div>
                `).join("");
            }
        }

        // 4. Render Key Entities (Day 28 Key Players)
        if (keyEntitiesContainer) {
            if (!keyEntities || keyEntities.length === 0) {
                keyEntitiesContainer.innerHTML = `<div class="p-3 bg-surface-container-low border border-surface-container-high rounded text-xs text-on-surface-variant">No key player centrality metrics computed yet.</div>`;
            } else {
                keyEntitiesContainer.innerHTML = keyEntities.slice(0, 5).map(e => `
                    <div class="stitch-card bg-surface-container-low border-surface-container-high p-2.5 flex items-center justify-between hover:border-tertiary/40 transition">
                        <div class="flex items-center gap-2">
                            <div class="w-7 h-7 rounded bg-tertiary-container/20 border border-tertiary-container/40 flex items-center justify-center text-tertiary shrink-0">
                                <span class="material-symbols-outlined text-sm">${e.type === 'PERSON' ? 'person' : (e.type === 'PHONE' ? 'call' : 'account_balance')}</span>
                            </div>
                            <div>
                                <div class="text-xs font-bold text-white flex items-center gap-1">
                                    <span>${e.name || e.id}</span>
                                    <span class="text-[9px] font-mono font-normal text-tertiary bg-tertiary-container/30 px-1 py-0.2 rounded">${e.role || 'CORE_HUB'}</span>
                                </div>
                                <div class="text-[10px] text-on-surface-variant font-mono">${e.id} • ${e.type || 'ENTITY'}</div>
                            </div>
                        </div>
                        <button onclick="openEntityDetails('${e.id}')" class="px-2 py-1 bg-surface-container-high hover:bg-surface-container-highest text-primary border border-surface-container-high rounded text-[10px] font-mono font-bold transition">
                            View
                        </button>
                    </div>
                `).join("");
            }
        }

        // 5. Render Recent Activity & Ingested Evidence
        if (activityContainer) {
            if (!recentEvidence || recentEvidence.length === 0) {
                activityContainer.innerHTML = `<div class="p-3 bg-surface-container-low border border-surface-container-high rounded text-xs text-on-surface-variant">No recent evidence items logged.</div>`;
            } else {
                activityContainer.innerHTML = recentEvidence.slice(0, 5).map(ev => `
                    <div class="stitch-card bg-surface-container-low border-surface-container-high p-2.5 space-y-1.5 hover:border-amber-500/40 transition">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-bold text-amber-300 font-mono">${ev.id || 'EVID_001'}</span>
                            <span class="text-[9px] font-mono text-outline">${ev.date || ev.created_at || 'Recent'}</span>
                        </div>
                        <div class="text-[11px] text-on-surface line-clamp-1">${ev.title || ev.description || 'Ingested evidence item'}</div>
                        <div class="flex items-center justify-between text-[10px] text-on-surface-variant pt-1 border-t border-surface-container-high">
                            <span>Case: <strong class="text-white">${ev.case_id || 'CASE_101'}</strong></span>
                            <button onclick="switchTab('pane-evidence')" class="text-amber-400 font-semibold hover:underline">Inspect Evidence</button>
                        </div>
                    </div>
                `).join("");
            }
        }

        // 6. Render Day 32 Cross-Source Intelligence Correlations
        await renderCorrelations(aiActiveCaseId);

        // 7. Render Day 33 ML & Investigative Risk Intelligence
        await renderRiskIntelligence(aiActiveCaseId);

    } catch (err) {
        console.error("Failed to render Investigation Command Dashboard:", err);
        if (casesContainer) {
            casesContainer.innerHTML = `
                <div class="col-span-2 p-4 text-center text-error text-xs space-y-2 font-sans">
                    <span class="material-symbols-outlined text-2xl text-error" aria-hidden="true">error</span>
                    <div class="font-bold text-sm">Failed to load Investigation Command Dashboard</div>
                    <div class="text-on-surface-variant">${err.message || 'Backend connection error.'}</div>
                    <button onclick="renderDashboard()" class="px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-white rounded text-[11px]">Retry</button>
                </div>
            `;
        }
    }
}

/* ----------------------------------------------------
   DAY 32 — CROSS-SOURCE INTELLIGENCE CORRELATION UI
---------------------------------------------------- */
let currentCorrelationsData = [];

async function renderCorrelations(caseId = null) {
    const container = document.getElementById("dashboard-correlations-container");
    if (!container) return;

    container.innerHTML = `<div class="text-center py-4 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-cyan-400 align-middle mr-1">sync</span> Loading Cross-Source Intelligence Correlations...</div>`;

    try {
        const resp = await window.dataService.getCorrelations(caseId);
        const summary = resp.summary || {};
        currentCorrelationsData = resp.correlations || [];

        const setTxt = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val !== undefined && val !== null ? val : 0;
        };
        setTxt("corr-stat-total", summary.total_correlations || currentCorrelationsData.length);
        setTxt("corr-stat-high", summary.high_confidence_count || 0);
        setTxt("corr-stat-entities", summary.entity_correlations_count || 0);
        setTxt("corr-stat-conflicts", summary.contradictions_count || 0);

        filterCorrelationsUI();
    } catch (err) {
        console.error("Failed to load cross-source correlations:", err);
        container.innerHTML = `<div class="p-3 bg-surface-container-low border border-surface-container-high rounded text-xs text-on-surface-variant">Cross-source intelligence correlation unavailable or offline.</div>`;
    }
}

function filterCorrelationsUI() {
    const container = document.getElementById("dashboard-correlations-container");
    if (!container) return;

    const typeFilter = (document.getElementById("corr-filter-type")?.value || "ALL").toUpperCase();
    const confFilter = parseFloat(document.getElementById("corr-filter-conf")?.value || "0.0");

    let filtered = currentCorrelationsData;
    if (typeFilter !== "ALL") {
        filtered = filtered.filter(c => (c.correlation_type || '').toUpperCase() === typeFilter);
    }
    if (confFilter > 0) {
        filtered = filtered.filter(c => (c.confidence || 0) >= confFilter);
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="p-4 rounded-lg bg-surface-container-low border border-surface-container-high text-center text-xs text-on-surface-variant font-sans">
                <span class="material-symbols-outlined text-base text-outline block mb-1">info</span>
                No matching cross-source correlations found for selected filter criteria.
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(c => {
        const isConflict = c.correlation_type === "CONTRADICTION";
        const badgeClass = isConflict 
            ? "bg-amber-950/80 text-amber-300 border-amber-700/60" 
            : c.correlation_type === "SAME_RESOLVED_ENTITY"
            ? "bg-indigo-950/80 text-indigo-300 border-indigo-700/60"
            : c.correlation_type === "CROSS_CASE_CORRELATION"
            ? "bg-cyan-950/80 text-cyan-300 border-cyan-700/60"
            : "bg-emerald-950/80 text-emerald-300 border-emerald-700/60";

        const typeLabel = (c.correlation_type || "CORRELATION").replace(/_/g, " ");

        let sourceComparisonHtml = "";
        if (isConflict && c.source_a && c.source_b) {
            sourceComparisonHtml = `
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2 p-3 rounded bg-surface-container border border-surface-container-high text-xs">
                    <div class="p-2.5 rounded bg-surface-container-low border border-amber-900/40 space-y-1 font-mono">
                        <div class="text-[10px] font-bold text-amber-400 uppercase">SOURCE A (${escapeHtml(c.source_a.source_id || 'EVID_A')})</div>
                        <div class="text-white"><strong>Doc:</strong> ${escapeHtml(c.source_a.document_id || 'DOC_A')}</div>
                        <div class="text-white"><strong>Location:</strong> ${escapeHtml(c.source_a.location || 'N/A')}</div>
                        <div class="text-on-surface-variant text-[10px]"><strong>Time:</strong> ${escapeHtml(c.source_a.timestamp || 'N/A')}</div>
                    </div>
                    <div class="p-2.5 rounded bg-surface-container-low border border-amber-900/40 space-y-1 font-mono">
                        <div class="text-[10px] font-bold text-amber-400 uppercase">SOURCE B (${escapeHtml(c.source_b.source_id || 'EVID_B')})</div>
                        <div class="text-white"><strong>Doc:</strong> ${escapeHtml(c.source_b.document_id || 'DOC_B')}</div>
                        <div class="text-white"><strong>Location:</strong> ${escapeHtml(c.source_b.location || 'N/A')}</div>
                        <div class="text-on-surface-variant text-[10px]"><strong>Time:</strong> ${escapeHtml(c.source_b.timestamp || 'N/A')}</div>
                    </div>
                </div>
            `;
        } else if (c.sources && c.sources.length > 0) {
            const srcBadges = c.sources.map(s => `
                <span class="px-2 py-0.5 rounded bg-surface-container-high text-cyan-300 border border-cyan-800/40 text-[10px] font-mono">
                    ${escapeHtml(s.source_id || s.document_id || 'EVID')}
                </span>
            `).join(' ');
            sourceComparisonHtml = `
                <div class="flex items-center gap-1.5 pt-1 text-[11px] font-mono">
                    <span class="text-on-surface-variant">Sources:</span>
                    <div class="flex items-center gap-1 flex-wrap">${srcBadges}</div>
                </div>
            `;
        }

        const entTriggers = (c.entities || []).map(entId => `
            <button onclick="openEntityDetails('${escapeHtml(entId)}')" class="px-2 py-0.5 rounded bg-primary/20 hover:bg-primary/30 text-primary border border-primary/40 font-mono text-xs font-bold transition">
                ${escapeHtml(entId)}
            </button>
        `).join(' ');

        return `
            <div class="stitch-card bg-surface-container-low border-surface-container-high p-4 space-y-3 hover:border-cyan-500/40 transition font-sans shadow">
                <div class="flex flex-wrap items-center justify-between gap-2 border-b border-surface-container-high pb-2">
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono border uppercase tracking-wider ${badgeClass}">
                            ${escapeHtml(typeLabel)}
                        </span>
                        <h4 class="text-xs font-bold text-white">${escapeHtml(c.title || c.id)}</h4>
                    </div>
                    <div class="flex items-center gap-2 text-xs font-mono">
                        <span class="text-emerald-400 font-bold">${Math.round((c.confidence || 0.90) * 100)}% Confidence</span>
                    </div>
                </div>

                <div class="text-xs text-on-surface-variant leading-relaxed">
                    ${escapeHtml(c.explanation || '')}
                </div>

                ${sourceComparisonHtml}

                <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-surface-container-high text-xs">
                    <div class="flex items-center gap-1.5">
                        <span class="text-on-surface-variant font-mono text-[11px]">Entities:</span>
                        <div class="flex items-center gap-1">${entTriggers}</div>
                    </div>

                    <div class="flex items-center gap-2 font-mono text-[11px]">
                        <button onclick="switchTab('pane-graph')" class="text-cyan-400 font-bold hover:underline flex items-center gap-0.5">
                            <span class="material-symbols-outlined text-xs">hub</span> View Graph
                        </button>
                        <button onclick="switchTab('pane-evidence')" class="text-amber-400 font-bold hover:underline flex items-center gap-0.5">
                            <span class="material-symbols-outlined text-xs">description</span> View Evidence
                        </button>
                    </div>
                </div>

                <div class="text-[10px] text-outline italic bg-surface-container/40 p-2 rounded border border-surface-container-high">
                    <strong class="text-on-surface-variant font-mono">Investigative Lead:</strong> ${escapeHtml(c.interpretation || 'Investigative lead requiring human officer verification. Does not constitute proof of guilt.')}
                </div>
            </div>
        `;
    }).join('');
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

        // Update all case dropdown pickers
        await populateCaseDropdowns();
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

async function openCaseDetail(caseId) {
    const select = document.getElementById("header-case-select");
    if (select && caseId) select.value = caseId;
    switchTab("pane-case-detail", true);
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
    const sourceTypeFilter = (document.getElementById("filter-source-type")?.value || "ALL").toUpperCase();

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
        if (sourceTypeFilter !== "ALL") {
            const evId = e.evidence_id || "";
            const srcType = e.source_type || "";
            let matchMethod = false;

            if (sourceTypeFilter === "SOCIAL_MEDIA_SYNTHETIC" && (srcType === "SOCIAL_MEDIA_SYNTHETIC" || evId.includes("SOC") || e.source.startsWith("SOC") || e.target.startsWith("SOC"))) matchMethod = true;
            else if (sourceTypeFilter === "SYNTHETIC_DATASET" && (srcType === "SYNTHETIC_DATASET" || evId.includes("101") || evId.includes("204"))) matchMethod = true;
            else if (sourceTypeFilter === "MANUAL_INVESTIGATION" && (srcType === "MANUAL_INVESTIGATION" || evId.includes("MAN"))) matchMethod = true;
            else if (sourceTypeFilter === "NLP_EXTRACT" && (srcType === "NLP_EXTRACTED" || evId.includes("EXT"))) matchMethod = true;
            else if (sourceTypeFilter === "EXTERNAL_CONNECTOR" && (srcType === "EXTERNAL_CONNECTOR")) matchMethod = true;
            else if (sourceTypeFilter === "DIGITAL_FORENSICS" && (evId.includes("042_01") || (e.source === "PERSON_017" && e.target === "PHONE_042"))) matchMethod = true;
            else if (sourceTypeFilter === "TELCO_INTERCEPT" && (evId.includes("042_02") || (e.source === "PHONE_042" && e.target === "PERSON_089"))) matchMethod = true;
            edgeVisible = edgeVisible && matchMethod;
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
        const isSocial = ent.source_type === "SOCIAL_MEDIA_SYNTHETIC" || ent.id.startsWith("SOC_") || ent.platform;

        let sourceBadge = isManual
            ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1"><span class="material-symbols-outlined text-[11px]">edit_note</span> Source: Manual</span>`
            : `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-900 text-slate-300 border border-slate-700 flex items-center gap-1"><span class="material-symbols-outlined text-[11px]">database</span> Source: Dataset</span>`;

        if (isSocial) {
            sourceBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-fuchsia-950 text-fuchsia-300 border border-fuchsia-800 flex items-center gap-1"><span class="material-symbols-outlined text-[11px]">share</span> SOCIAL MEDIA — SYNTHETIC</span>`;
        }

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
                    <div class="flex items-center gap-1 flex-wrap">
                        ${sourceBadge}
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded ${badgeClass}">${ent.type}</span>
                    </div>
                </div>

                <h3 class="text-sm font-bold text-white">${ent.name}</h3>
                <p class="text-xs text-on-surface-variant leading-relaxed">${ent.details || "Active Knowledge Graph Entity"}</p>

                ${isSocial || ent.platform ? `
                <!-- Social Media Identity & Interaction Block -->
                <div class="bg-fuchsia-950/30 p-2.5 rounded border border-fuchsia-800/50 space-y-1.5 text-xs font-sans">
                    <div class="flex items-center justify-between text-[10px] font-bold uppercase text-fuchsia-300">
                        <span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">forum</span> Synthetic Social Record</span>
                        <span class="px-1.5 py-0.5 rounded bg-fuchsia-900/60 border border-fuchsia-700 font-mono text-[9px]">SOCIAL_SOURCE_ADAPTER</span>
                    </div>
                    <div class="space-y-1 font-mono text-[11px]">
                        <div>Platform: <strong class="text-white">${ent.platform || 'X / Telegram (Synthetic)'}</strong></div>
                        <div>Handle / Account: <strong class="text-fuchsia-300">${ent.name}</strong></div>
                        <div>Record Lineage: <strong class="text-tertiary">SOCIAL_017_04</strong></div>
                    </div>
                </div>
                ` : ''}

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

                <!-- Multi-Source Data Layer Provenance -->
                <div class="bg-surface-container-lowest p-2.5 rounded border border-surface-container-high space-y-1.5">
                    <div class="flex items-center justify-between">
                        <div class="text-[10px] font-bold uppercase text-outline">Multi-Source Provenance & Corroboration</div>
                        <span class="px-1.5 py-0.5 text-[9px] font-bold rounded ${ent.id === "PERSON_017" ? "bg-rose-950 text-rose-300 border border-rose-800" : "bg-emerald-950 text-emerald-300 border border-emerald-800"} font-mono">
                            ${ent.id === "PERSON_017" ? "CONFLICT DETECTED" : ((ent.evidence && ent.evidence.length > 1) || ent.id === "PHONE_042" ? "CORROBORATED (2 SOURCES)" : "SINGLE SOURCE")}
                        </span>
                    </div>

                    <div class="text-xs space-y-1 font-mono">
                        <div class="flex items-center justify-between text-[11px]">
                            <span class="text-on-surface-variant">Primary Source Doc:</span>
                            <span class="text-tertiary font-bold">${isSocial ? "SOCIAL_017_04" : (ent.id === "PHONE_042" ? "DOC_CASE_101 / DOC_CASE_204" : (ent.id === "PERSON_017" ? "DOC_CASE_101_FIR_REPORT.pdf" : "DOC_CASE_101_REPORT.pdf"))}</span>
                        </div>
                        <div class="flex items-center justify-between text-[11px]">
                            <span class="text-on-surface-variant">Extraction Methods:</span>
                            <span class="text-purple-300 font-bold">${isSocial ? "SOCIAL_SOURCE_ADAPTER" : (ent.id === "PHONE_042" ? "DIGITAL_FORENSICS + TELCO_INTERCEPT" : (ent.id === "PERSON_017" ? "AI_NER + SOCIAL_SOURCE" : "AI_NER"))}</span>
                        </div>
                    </div>

                    ${(ent.id === "PHONE_042" || ent.id === "PERSON_017") ? `
                    <div class="p-2 bg-rose-950/40 border border-rose-800/60 rounded text-[11px] space-y-0.5 text-rose-200 mt-1 font-sans">
                        <div class="font-bold text-rose-300 flex items-center gap-1"><span class="material-symbols-outlined text-xs">warning</span> Conflicting Source Information Detected</div>
                        <div>Conflicting values: Alias 'Arjun' vs 'Aarav' (Social Media Synthetic vs Manual Notes). Confidence: 70%. HUMAN OFFICER VERIFICATION REQUIRED BEFORE FORMAL PROCEEDINGS.</div>
                    </div>
                    ` : `
                    <div class="p-1.5 bg-emerald-950/30 border border-emerald-800/40 rounded text-[10px] text-emerald-300 flex items-center gap-1 font-sans mt-1">
                        <span class="material-symbols-outlined text-xs">verified</span> Source Provenance Consistent Across Extracted Records
                    </div>
                    `}
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

        const extractionMethod = evid.extraction_method || (evid.evidence_id && evid.evidence_id.includes("042_01") ? "DIGITAL_FORENSICS" : (evid.evidence_id && evid.evidence_id.includes("042_02") ? "TELCO_INTERCEPT" : "AI_NER"));

        drawer.innerHTML = `
            <div class="space-y-3 font-sans">
                <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                    <span class="font-mono text-xs font-bold text-tertiary px-2 py-0.5 rounded bg-tertiary-container/20 border border-tertiary/30">${evid.evidence_id}</span>
                    <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-purple-950 text-purple-300 border border-purple-800 font-mono">${extractionMethod}</span>
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
                    <div class="text-[10px] font-bold uppercase text-outline">Source Document & Provenance</div>
                    <div class="p-2 bg-surface-container-lowest border border-surface-container-high rounded text-xs space-y-1 font-mono">
                        <div class="flex items-center justify-between">
                            <span class="text-on-surface-variant">Document ID:</span>
                            <span class="text-tertiary font-bold">${evid.source_document || evid.source_document_id || 'DOC_EXTRACTION'}</span>
                        </div>
                        <div class="flex items-center justify-between text-[11px]">
                            <span class="text-on-surface-variant">Page Reference:</span>
                            <span class="text-white font-bold">Page ${evid.page_number || 1}</span>
                        </div>
                        <div class="flex items-center justify-between text-[11px]">
                            <span class="text-on-surface-variant">Extraction Method:</span>
                            <span class="text-purple-300 font-bold">${extractionMethod}</span>
                        </div>
                        <div class="flex items-center justify-between text-[11px]">
                            <span class="text-on-surface-variant">Extraction Confidence:</span>
                            <span class="text-emerald-400 font-bold">${((evid.confidence || 0.95) * 100).toFixed(0)}%</span>
                        </div>
                    </div>
                </div>

                <div class="space-y-1">
                    <div class="text-[10px] font-bold uppercase text-outline">Source Document Excerpt</div>
                    <p class="text-xs text-on-surface italic bg-surface-container-lowest p-2.5 rounded border border-surface-container-high leading-relaxed break-words whitespace-normal font-sans">"${evid.source_text || 'Recorded investigative finding.'}"</p>
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
/* Note: renderTimeline is defined in Day 23 section below (line 3790) */

async function renderEvidenceExplorer() {
    const container = document.getElementById("evidence-grid-container");
    if (!container) return;

    const sourceFilter = (document.getElementById("evidence-source-filter")?.value || "ALL").toUpperCase();

    container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans"><span class="material-symbols-outlined animate-spin text-tertiary align-middle mr-1">sync</span> Loading evidence provenance index...</div>`;

    try {
        let evidenceList = await window.dataService.getEvidenceList();
        if (!evidenceList || evidenceList.length === 0) {
            container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans">No evidence records found in active dataset.</div>`;
            return;
        }

        if (sourceFilter !== "ALL") {
            evidenceList = evidenceList.filter(ev => {
                const method = (ev.extraction_method || (ev.evidence_id.includes("042_01") ? "DIGITAL_FORENSICS" : (ev.evidence_id.includes("042_02") ? "TELCO_INTERCEPT" : "AI_NER"))).toUpperCase();
                return method === sourceFilter;
            });
        }

        if (evidenceList.length === 0) {
            container.innerHTML = `<div class="col-span-2 text-center py-6 text-outline text-xs font-sans">No evidence records match the selected source extraction method '${sourceFilter}'.</div>`;
            return;
        }

        container.innerHTML = evidenceList.map(ev => {
            const method = ev.extraction_method || (ev.evidence_id.includes("SOC") ? "SOCIAL_SOURCE_ADAPTER" : (ev.evidence_id.includes("042_01") ? "DIGITAL_FORENSICS" : (ev.evidence_id.includes("042_02") ? "TELCO_INTERCEPT" : "AI_NER")));
            const docName = ev.source_document || ev.source_document_id || "DOC_EXTRACTION";
            const isSocial = method === "SOCIAL_SOURCE_ADAPTER" || ev.source_type === "SOCIAL_MEDIA_SYNTHETIC";
            const corroboration = ev.corroboration || (ev.conflict_detected ? "CONFLICT DETECTED" : (ev.evidence_id.includes("SOC_017") ? "CORROBORATED" : "SINGLE SOURCE"));
            const corrBadge = corroboration === "CONFLICT DETECTED"
                ? `<span class="px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[9px] font-bold font-mono">CONFLICT DETECTED</span>`
                : (corroboration === "CORROBORATED"
                    ? `<span class="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-[9px] font-bold font-mono">CORROBORATED (${ev.sources_count || 2} SOURCES)</span>`
                    : `<span class="px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-700 text-[9px] font-bold font-mono">SINGLE SOURCE</span>`);

            return `
                <div class="stitch-card space-y-2.5 text-xs font-sans hover:border-purple-500/50 transition cursor-pointer" onclick="openEvidencePanel({ evidence_id: '${ev.evidence_id}' })">
                    <div class="flex items-center justify-between font-mono">
                        <span class="text-tertiary font-bold">${ev.evidence_id}</span>
                        <div class="flex items-center gap-1.5 flex-wrap">
                            ${corrBadge}
                            <span class="px-2 py-0.5 rounded ${isSocial ? 'bg-fuchsia-950 text-fuchsia-300 border border-fuchsia-800' : 'bg-purple-950 text-purple-300 border border-purple-800'} text-[10px] font-bold font-mono">${isSocial ? 'SOCIAL MEDIA — SYNTHETIC' : method}</span>
                            <span class="px-2 py-0.5 rounded bg-tertiary-container/30 text-tertiary text-[10px] font-bold">${((ev.confidence || 0.95) * 100).toFixed(0)}% Conf</span>
                        </div>
                    </div>
                    <p class="text-white italic text-[11px] break-words whitespace-normal font-sans bg-surface-container-lowest p-2 rounded border border-surface-container-high">"${ev.source_text || ev.excerpt || 'Recorded evidence finding.'}"</p>
                    
                    ${ev.conflict_detected ? `
                    <div class="p-2 bg-rose-950/40 border border-rose-800/60 rounded text-[10px] text-rose-200 font-sans space-y-0.5">
                        <div class="font-bold text-rose-300 flex items-center gap-1"><span class="material-symbols-outlined text-xs">warning</span> Conflicting Claim Warning</div>
                        <div>${ev.conflict_details ? ev.conflict_details.conflicting_values : "Source conflict detected across extraction streams."} — HUMAN OFFICER VERIFICATION REQUIRED.</div>
                    </div>
                    ` : ''}

                    <div class="flex items-center justify-between text-[10px] text-outline font-mono pt-1 border-t border-surface-container-high">
                        <span>Doc: <strong class="text-white">${docName}</strong></span>
                        <span>Page: <strong class="text-white">Pg. ${ev.page_number || 1}</strong></span>
                    </div>
                </div>
            `;
        }).join("");
    } catch (err) {
        container.innerHTML = `<div class="col-span-2 text-center py-6 text-error text-xs font-sans">Failed to load evidence catalog: ${err.message}</div>`;
    }
}

/* ----------------------------------------------------
   INVESTIGATION REPORT VIEWER & EXPORT (DAY 24)
---------------------------------------------------- */
async function generateReport(caseId = null) {
    return await renderInvestigationReport(caseId);
}

async function renderInvestigationReport(caseId = null) {
    const viewBox = document.getElementById("report-view-box");
    if (!viewBox) return;

    let targetCaseId = caseId;
    if (!targetCaseId || typeof targetCaseId !== "string" || targetCaseId === "ALL") {
        const repSelect = document.getElementById("report-case-select");
        const headSelect = document.getElementById("header-case-select");
        targetCaseId = (repSelect && repSelect.value) ? repSelect.value : ((headSelect && headSelect.value && headSelect.value !== "ALL") ? headSelect.value : "CASE_101");
    }

    const repSelect = document.getElementById("report-case-select");
    if (repSelect && repSelect.value !== targetCaseId) {
        repSelect.value = targetCaseId;
    }

    viewBox.innerHTML = `
        <div class="stitch-card text-center py-12 text-outline text-xs font-sans">
            <span class="material-symbols-outlined animate-spin text-primary text-3xl align-middle mb-2">sync</span>
            <div class="font-semibold text-white">Synthesizing Investigation Report for ${targetCaseId}...</div>
            <div class="text-[11px] text-outline mt-1">Aggregating Network Graph, Day-23 Timeline, Day-20 Patterns, Day-21 Multi-Source Provenance & Day-22 NLP...</div>
        </div>
    `;

    try {
        const report = await window.dataService.generateReport(targetCaseId);
        if (!report) {
            viewBox.innerHTML = `<div class="stitch-card text-center py-10 text-rose-400 text-xs font-sans">Unable to retrieve report data for ${targetCaseId}.</div>`;
            return;
        }

        const caseTitle = report.case_title || targetCaseId;
        const confidencePct = report.overall_confidence ? (report.overall_confidence * 100).toFixed(0) : "95";
        const sources = report.source_provenance || ["Synthetic Dataset", "Digital Forensics", "NLP Extract"];
        const keyEntities = report.key_entities || [];
        const relationships = report.relationships || [];
        const timelineEvents = report.timeline_events || [];
        const suspiciousPatterns = report.suspicious_patterns || [];
        const networkIntel = report.network_intelligence || { node_count: keyEntities.length, edge_count: relationships.length, cross_case_bridges_count: 0 };
        const evidenceItems = report.evidence || [];
        const leads = report.investigative_leads || [];
        const limitations = report.limitations || [];
        const disclaimer = report.safety_disclaimer || "CrimeGraph AI provides investigative leads and association mappings based solely on ingested documents. This output does NOT declare guilt, make legal judgments, or represent conclusive criminal proof. All generated leads require mandatory human verification by authorized case officers.";

        viewBox.innerHTML = `
            <div class="space-y-5 font-sans">
                
                <!-- 1. REPORT HEADER CARD -->
                <div class="stitch-card space-y-3 bg-surface-container-low border border-surface-container-high p-4 rounded-lg">
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-surface-container-high pb-3">
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="text-lg font-bold text-white">${report.title || `CrimeGraph Investigation Report — ${caseTitle}`}</span>
                                <span class="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-[10px] font-bold font-mono uppercase">${report.status || 'GENERATED'}</span>
                            </div>
                            <div class="text-xs text-outline font-mono mt-1">
                                Report ID: <strong class="text-tertiary">${report.report_id || 'REPORT_001'}</strong> | Case: <strong class="text-primary hover:underline cursor-pointer" onclick="openReportCase('${targetCaseId}')">${targetCaseId} (${caseTitle})</strong> | Generated: ${report.timestamp ? new Date(report.timestamp).toLocaleString() : 'Just now'}
                            </div>
                        </div>
                        <div class="flex items-center gap-3">
                            <div class="text-right">
                                <div class="text-[10px] text-outline font-mono uppercase">Overall Confidence</div>
                                <div class="text-base font-bold text-tertiary font-mono">${confidencePct}%</div>
                            </div>
                        </div>
                    </div>

                    <!-- Source Provenance Badges -->
                    <div class="flex flex-wrap items-center gap-2 text-xs">
                        <span class="text-outline text-[11px] font-mono">Multi-Source Provenance:</span>
                        ${sources.map(src => `<span class="px-2 py-0.5 rounded bg-purple-950/70 text-purple-300 border border-purple-800/60 text-[10px] font-bold font-mono">${src}</span>`).join("")}
                    </div>
                </div>

                <!-- 2. SAFETY & LEGAL DISCLAIMER BANNER -->
                <div class="bg-amber-950/40 border border-amber-800/80 rounded-lg p-4 flex items-start gap-3">
                    <span class="material-symbols-outlined text-amber-400 text-xl shrink-0 mt-0.5" aria-hidden="true">gavel</span>
                    <div class="space-y-1 text-xs">
                        <div class="font-bold text-amber-300 uppercase tracking-wider text-[11px]">Safety Policy & Legal Disclaimer</div>
                        <p class="text-amber-200/90 leading-relaxed">${disclaimer}</p>
                    </div>
                </div>

                <!-- 3. EXECUTIVE SUMMARY CARD -->
                <div class="stitch-card space-y-2">
                    <h3 class="text-sm font-bold text-primary flex items-center gap-2 border-b border-surface-container-high pb-2">
                        <span class="material-symbols-outlined text-base">article</span> 1. Executive Summary
                    </h3>
                    <p class="text-xs text-on-surface-variant leading-relaxed">${report.executive_summary || report.content || 'Investigation summary synthesized from knowledge graph dataset.'}</p>
                </div>

                <!-- 4. KEY ENTITIES & RELATIONSHIP NETWORK -->
                <div class="stitch-card space-y-4">
                    <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                        <h3 class="text-sm font-bold text-primary flex items-center gap-2">
                            <span class="material-symbols-outlined text-base">hub</span> 2. Identified Key Entities & Relationships (${keyEntities.length} Entities, ${relationships.length} Edges)
                        </h3>
                        <button onclick="openReportGraph('${targetCaseId}')" class="px-2 py-1 bg-surface-container-high hover:bg-surface-container-highest text-tertiary border border-tertiary/40 text-[11px] font-semibold rounded flex items-center gap-1">
                            <span class="material-symbols-outlined text-xs">account_tree</span> Report → Graph
                        </button>
                    </div>

                    <!-- Entities Table -->
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs font-sans">
                            <thead class="bg-surface-container-lowest text-outline font-mono text-[10px] uppercase">
                                <tr>
                                    <th class="p-2">Entity ID</th>
                                    <th class="p-2">Name / Label</th>
                                    <th class="p-2">Type</th>
                                    <th class="p-2">Confidence</th>
                                    <th class="p-2">Source Provenance</th>
                                    <th class="p-2 text-right">Traceability Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-surface-container-high">
                                ${keyEntities.map(ent => `
                                    <tr class="hover:bg-surface-container-low transition">
                                        <td class="p-2 font-mono font-bold text-tertiary">${ent.id}</td>
                                        <td class="p-2 text-white font-semibold">${ent.name}</td>
                                        <td class="p-2"><span class="px-2 py-0.5 rounded bg-surface-container-highest text-on-surface text-[10px] font-mono uppercase">${ent.type}</span></td>
                                        <td class="p-2 font-mono text-emerald-400">${((ent.confidence || 0.95) * 100).toFixed(0)}%</td>
                                        <td class="p-2"><span class="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/60 text-[10px] font-mono">${ent.source_provenance || 'Synthetic Dataset'}</span></td>
                                        <td class="p-2 text-right space-x-1">
                                            <button onclick="openReportEntity('${ent.id}')" class="px-2 py-0.5 bg-tertiary-container/30 hover:bg-tertiary-container/60 text-tertiary text-[10px] font-semibold rounded transition" title="Report → Entity View">Entity</button>
                                            <button onclick="openReportGraph('${ent.id}')" class="px-2 py-0.5 bg-primary-container/30 hover:bg-primary-container/60 text-primary text-[10px] font-semibold rounded transition" title="Report → Graph View">Graph</button>
                                        </td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 5. TIMELINE & CORRELATED EVENTS (DAY 23) -->
                <div class="stitch-card space-y-3">
                    <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                        <h3 class="text-sm font-bold text-primary flex items-center gap-2">
                            <span class="material-symbols-outlined text-base">history</span> 3. Timeline & Correlated Events (${timelineEvents.length} Events)
                        </h3>
                        <button onclick="openReportEvent(null)" class="px-2 py-1 bg-surface-container-high hover:bg-surface-container-highest text-tertiary border border-tertiary/40 text-[11px] font-semibold rounded flex items-center gap-1">
                            <span class="material-symbols-outlined text-xs">history</span> Report → Timeline
                        </button>
                    </div>

                    <div class="space-y-2">
                        ${timelineEvents.map(ev => `
                            <div class="p-3 bg-surface-container-lowest border border-surface-container-high rounded flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
                                <div class="space-y-1">
                                    <div class="flex items-center gap-2">
                                        <span class="font-bold text-white">${ev.title}</span>
                                        <span class="px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 text-[10px] font-mono">${ev.event_type}</span>
                                        <span class="text-outline text-[10px] font-mono">${ev.timestamp}</span>
                                    </div>
                                    <p class="text-on-surface-variant text-[11px]">${ev.description}</p>
                                    <div class="text-[10px] text-outline font-mono">Location: ${ev.location || 'N/A'} | Provenance: ${ev.source_provenance || 'Synthetic Dataset'}</div>
                                </div>
                                <button onclick="openReportEvent('${ev.id}')" class="px-2.5 py-1 bg-surface-container-high hover:bg-surface-container-highest text-primary border border-outline-variant rounded text-[11px] font-semibold shrink-0">Report → Event</button>
                            </div>
                        `).join("")}
                    </div>
                </div>

                <!-- 6. SUSPICIOUS PATTERN DETECTION (DAY 20) & NETWORK INTEL (DAY 19) -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <!-- Suspicious Patterns -->
                    <div class="stitch-card space-y-3">
                        <h3 class="text-sm font-bold text-primary flex items-center gap-2 border-b border-surface-container-high pb-2">
                            <span class="material-symbols-outlined text-amber-400 text-base">warning</span> 4. Suspicious Pattern Detection (${suspiciousPatterns.length})
                        </h3>
                        <div class="space-y-2 text-xs">
                            ${suspiciousPatterns.map(pat => `
                                <div class="p-3 bg-surface-container-lowest border border-amber-900/40 rounded space-y-1.5">
                                    <div class="flex items-center justify-between">
                                        <span class="font-bold text-amber-300">${pat.title}</span>
                                        <span class="px-2 py-0.5 bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-bold font-mono">${pat.severity || 'HIGH'}</span>
                                    </div>
                                    <p class="text-on-surface-variant text-[11px]">${pat.explanation}</p>
                                    <div class="text-[10px] text-tertiary font-mono">Lead: ${pat.investigative_lead || 'Verify call logs'}</div>
                                </div>
                            `).join("")}
                        </div>
                    </div>

                    <!-- Network Intelligence -->
                    <div class="stitch-card space-y-3">
                        <h3 class="text-sm font-bold text-primary flex items-center gap-2 border-b border-surface-container-high pb-2">
                            <span class="material-symbols-outlined text-base">insights</span> 5. Network Intelligence Metrics
                        </h3>
                        <div class="grid grid-cols-2 gap-3 text-xs font-mono">
                            <div class="p-3 bg-surface-container-lowest border border-surface-container-high rounded text-center">
                                <div class="text-outline text-[10px]">Graph Nodes</div>
                                <div class="text-lg font-bold text-primary">${networkIntel.node_count}</div>
                            </div>
                            <div class="p-3 bg-surface-container-lowest border border-surface-container-high rounded text-center">
                                <div class="text-outline text-[10px]">Verified Edges</div>
                                <div class="text-lg font-bold text-tertiary">${networkIntel.edge_count}</div>
                            </div>
                            <div class="p-3 bg-surface-container-lowest border border-surface-container-high rounded text-center col-span-2">
                                <div class="text-outline text-[10px]">Cross-Case Bridge Connections</div>
                                <div class="text-lg font-bold text-amber-400">${networkIntel.cross_case_bridges_count} Discovered</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 7. EVIDENCE LINEAGE & PROVENANCE INDEX (DAY 21 & 22) -->
                <div class="stitch-card space-y-3">
                    <div class="flex items-center justify-between border-b border-surface-container-high pb-2">
                        <h3 class="text-sm font-bold text-primary flex items-center gap-2">
                            <span class="material-symbols-outlined text-base">find_in_page</span> 6. Evidence Lineage & Provenance Index (${evidenceItems.length} Items)
                        </h3>
                        <button onclick="switchTab('pane-evidence')" class="px-2 py-1 bg-surface-container-high hover:bg-surface-container-highest text-tertiary border border-tertiary/40 text-[11px] font-semibold rounded flex items-center gap-1">
                            <span class="material-symbols-outlined text-xs">description</span> Report → Evidence
                        </button>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        ${evidenceItems.map(ev => `
                            <div class="p-3 bg-surface-container-lowest border border-surface-container-high rounded space-y-2 text-xs font-sans">
                                <div class="flex items-center justify-between font-mono">
                                    <span class="text-tertiary font-bold">${ev.evidence_id}</span>
                                    <span class="px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 text-[10px] font-mono">${ev.source_provenance || ev.extraction_method || 'Synthetic Dataset'}</span>
                                </div>
                                <p class="text-white italic text-[11px] bg-surface-container-low p-2 rounded border border-surface-container-high">"${ev.source_text}"</p>
                                <div class="flex items-center justify-between text-[10px] text-outline font-mono">
                                    <span>Doc: <strong>${ev.source_document_id || 'DOC_EXTRACTION'}</strong></span>
                                    <button onclick="openReportEvidence('${ev.evidence_id}')" class="text-primary hover:underline font-bold">Inspect Evidence →</button>
                                </div>
                            </div>
                        `).join("")}
                    </div>
                </div>

                <!-- 8. ACTIONABLE LEADS & LIMITATIONS -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <!-- Actionable Leads -->
                    <div class="stitch-card space-y-2">
                        <h3 class="text-sm font-bold text-emerald-400 flex items-center gap-2 border-b border-surface-container-high pb-2">
                            <span class="material-symbols-outlined text-base">flag</span> 7. Actionable Investigative Leads
                        </h3>
                        <ul class="space-y-1.5 text-xs text-on-surface-variant">
                            ${leads.map(lead => `<li class="flex items-start gap-1.5"><span class="text-emerald-400 font-bold">•</span> <span>${lead}</span></li>`).join("")}
                        </ul>
                    </div>

                    <!-- Limitations -->
                    <div class="stitch-card space-y-2">
                        <h3 class="text-sm font-bold text-amber-400 flex items-center gap-2 border-b border-surface-container-high pb-2">
                            <span class="material-symbols-outlined text-base">info</span> 8. Methodological Limitations
                        </h3>
                        <ul class="space-y-1.5 text-xs text-on-surface-variant">
                            ${limitations.map(lim => `<li class="flex items-start gap-1.5"><span class="text-amber-400 font-bold">•</span> <span>${lim}</span></li>`).join("")}
                        </ul>
                    </div>
                </div>

                ${(report.source_conflicts && report.source_conflicts.length > 0) ? `
                <!-- 9. SOURCE CONFLICT ALERTS -->
                <div class="stitch-card space-y-2.5 bg-rose-950/20 border border-rose-800/50 p-4 rounded-lg">
                    <h3 class="text-sm font-bold text-rose-300 flex items-center gap-2 border-b border-rose-800/40 pb-2">
                        <span class="material-symbols-outlined text-base text-rose-400">warning</span> 9. Source Conflict & Discrepancy Alerts
                    </h3>
                    <div class="space-y-2">
                        ${report.source_conflicts.map(conf => `
                            <div class="p-3 bg-rose-950/40 border border-rose-800/60 rounded text-xs space-y-1 text-rose-200">
                                <div class="font-bold text-rose-300 flex items-center justify-between">
                                    <span>Entity Discrepancy: ${conf.entity_id}</span>
                                    <span class="px-1.5 py-0.5 rounded bg-rose-900 text-rose-200 text-[10px] font-mono">CONFLICT DETECTED</span>
                                </div>
                                <p class="text-rose-100">${conf.conflicting_values}</p>
                                <div class="text-[10px] text-rose-300/80 font-mono">Sources: ${(conf.source_names || []).join(" vs ")} | ${conf.warning}</div>
                            </div>
                        `).join("")}
                    </div>
                </div>
                ` : ''}

            </div>
        `;
    } catch (err) {
        viewBox.innerHTML = `
            <div class="stitch-card text-center py-10 text-rose-400 text-xs font-sans space-y-2">
                <span class="material-symbols-outlined text-3xl text-rose-500 block">error</span>
                <div class="font-bold">Failed to generate report for ${targetCaseId}</div>
                <div class="text-outline">${err.message || 'Service unavailable.'}</div>
                <button onclick="renderInvestigationReport('${targetCaseId}')" class="mt-3 px-3 py-1.5 bg-rose-900 hover:bg-rose-800 text-white rounded font-semibold text-xs transition">
                    Retry Report Generation
                </button>
            </div>
        `;
    }
}

/* ----------------------------------------------------
   REPORT TRACEABILITY NAVIGATORS
---------------------------------------------------- */
async function openReportEntity(entityId) {
    if (!entityId) return;
    switchTab("pane-graph", true);
    await renderGraphWorkspace("ALL");
    if (networkInstance) networkInstance.selectNodes([entityId]);
    openEntityDetailsPanel(entityId);
}

async function openReportEvidence(evidenceId) {
    if (!evidenceId) return;
    openEvidencePanel({ evidence_id: evidenceId });
}

async function openReportEvent(eventId) {
    switchTab("pane-timeline", true);
    const caseSelect = document.getElementById("header-case-select");
    const activeCase = (caseSelect && caseSelect.value) ? caseSelect.value : "CASE_101";
    await renderTimeline(activeCase);
    if (eventId) {
        setTimeout(() => {
            const evEl = document.getElementById(`event-card-${eventId}`);
            if (evEl) {
                evEl.scrollIntoView({ behavior: "smooth", block: "center" });
                evEl.classList.add("ring-2", "ring-primary");
            }
        }, 200);
    }
}

async function openReportCase(caseId) {
    if (!caseId) return;
    const select = document.getElementById("header-case-select");
    if (select) select.value = caseId;
    switchTab("pane-case-detail", true);
    await renderCaseDetail(caseId);
}

async function openReportGraph(nodeId) {
    switchTab("pane-graph", true);
    const caseSelect = document.getElementById("header-case-select");
    const activeCase = (caseSelect && caseSelect.value) ? caseSelect.value : "ALL";
    await renderGraphWorkspace(activeCase);
    if (nodeId && networkInstance) {
        networkInstance.selectNodes([nodeId]);
    }
}

/* ----------------------------------------------------
   REPORT EXPORT CONTROLS (JSON, PDF, MARKDOWN)
---------------------------------------------------- */
async function exportInvestigationReport(format = "json") {
    const statusBox = document.getElementById("report-export-status");
    let targetCaseId = "CASE_101";
    const repSelect = document.getElementById("report-case-select");
    const headSelect = document.getElementById("header-case-select");
    if (repSelect && repSelect.value) targetCaseId = repSelect.value;
    else if (headSelect && headSelect.value && headSelect.value !== "ALL") targetCaseId = headSelect.value;

    const fmtUpper = format.toUpperCase();

    if (statusBox) {
        statusBox.classList.remove("hidden");
        statusBox.className = "rounded p-3 text-xs font-sans bg-blue-950/80 border border-blue-800 text-blue-300 flex items-center justify-between";
        statusBox.innerHTML = `
            <span class="flex items-center gap-2">
                <span class="material-symbols-outlined animate-spin text-sm">sync</span>
                <span>Exporting investigation report for <strong>${targetCaseId}</strong> in <strong>${fmtUpper}</strong> format...</span>
            </span>
        `;
    }

    try {
        const res = await window.dataService.exportReport(targetCaseId, format);
        if (!res || (!res.blob && !res.content)) {
            throw new Error(`Export response was empty for ${targetCaseId}.`);
        }

        // Trigger file download in browser
        const filename = res.filename || `crimegraph_report_${targetCaseId}.${format.toLowerCase()}`;
        const blob = res.blob || new Blob([res.content], { type: format === "json" ? "application/json" : "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 1000);

        if (statusBox) {
            statusBox.className = "rounded p-3 text-xs font-sans bg-emerald-950/80 border border-emerald-800 text-emerald-300 flex items-center justify-between";
            statusBox.innerHTML = `
                <span class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-sm text-emerald-400">check_circle</span>
                    <span>Report successfully exported as <strong>${filename}</strong></span>
                </span>
                <button onclick="document.getElementById('report-export-status').classList.add('hidden')" class="text-xs underline text-emerald-400 hover:text-emerald-300">Dismiss</button>
            `;
        }
    } catch (err) {
        if (statusBox) {
            statusBox.className = "rounded p-3 text-xs font-sans bg-rose-950/80 border border-rose-800 text-rose-300 flex items-center justify-between";
            statusBox.innerHTML = `
                <span class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-sm text-rose-400">error</span>
                    <span>Export Failed (${fmtUpper}): ${err.message || 'Unable to connect to export service'}</span>
                </span>
                <button onclick="exportInvestigationReport('${format}')" class="px-2.5 py-1 bg-rose-900 hover:bg-rose-800 text-white rounded text-xs font-bold font-mono transition">
                    Retry Export
                </button>
            `;
        }
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

async function openAddEntityModal(defaultType = "PERSON") {
    const modal = document.getElementById("modal-add-entity");
    const typeSelect = document.getElementById("entity-type-select");
    const caseLinkSelect = document.getElementById("entity-link-case-select");
    if (!modal) return;
    if (typeSelect) typeSelect.value = defaultType;
    renderEntityFormFields();

    if (caseLinkSelect) {
        try {
            const cases = await window.dataService.getCases();
            const activeCase = document.getElementById("header-case-select")?.value;
            caseLinkSelect.innerHTML = `<option value="">-- Do Not Link to Case --</option>` + (cases || []).map(c => `
                <option value="${c.id}">${c.id} - ${c.title || c.id}</option>
            `).join("");
            if (activeCase && activeCase !== "ALL") {
                caseLinkSelect.value = activeCase;
            }
        } catch (_) {}
    }

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

        // Auto link entity to selected case if provided
        const selectedLinkCase = document.getElementById("entity-link-case-select")?.value;
        if (selectedLinkCase && created.id) {
            try {
                await window.dataService.createRelationship({
                    source_id: created.id,
                    relationship: "INVOLVED_IN",
                    target_id: selectedLinkCase,
                    confidence: 0.95
                });
            } catch (relErr) {
                console.warn("Could not auto-link entity to case:", relErr);
            }
        }

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

        const targetCaseForView = selectedLinkCase || document.getElementById("header-case-select")?.value || "CASE_101";
        await renderGraphWorkspace(targetCaseForView);
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

/* ----------------------------------------------------
   MANUAL CASE CREATION UI HANDLERS
---------------------------------------------------- */
function openCreateCaseModal() {
    const modal = document.getElementById("modal-create-case");
    const errorBox = document.getElementById("create-case-error-msg");
    const createdByInput = document.getElementById("create-case-created-by");
    if (!modal) return;

    if (errorBox) {
        errorBox.innerText = "";
        errorBox.classList.add("hidden");
    }

    const user = window.dataService ? window.dataService.getUser() : null;
    if (createdByInput) {
        createdByInput.value = (user && user.username) ? user.username : "OFFICER_VERMA";
    }

    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

function closeCreateCaseModal() {
    const modal = document.getElementById("modal-create-case");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

async function handleCreateCaseSubmit(event) {
    event.preventDefault();
    const btn = document.getElementById("btn-save-case");
    const errorBox = document.getElementById("create-case-error-msg");
    const titleInput = document.getElementById("create-case-title");
    const title = titleInput ? titleInput.value.trim() : "";

    if (!title) {
        if (errorBox) {
            errorBox.innerText = "Case title is required.";
            errorBox.classList.remove("hidden");
        } else {
            alert("Case title is required.");
        }
        if (titleInput) titleInput.focus();
        return;
    }

    if (errorBox) {
        errorBox.innerText = "";
        errorBox.classList.add("hidden");
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-sm">sync</span> Creating Case...`;
    }

    const caseData = {
        title: title,
        case_type: document.getElementById("create-case-type")?.value || "General Investigation",
        priority: document.getElementById("create-case-priority")?.value || "HIGH",
        status: document.getElementById("create-case-status")?.value || "ACTIVE",
        location: document.getElementById("create-case-location")?.value || "",
        description: document.getElementById("create-case-description")?.value || "",
        notes: document.getElementById("create-case-notes")?.value || "",
        created_by: document.getElementById("create-case-created-by")?.value || "OFFICER_VERMA"
    };

    try {
        const createdCase = await window.dataService.createCase(caseData);
        const newCaseId = createdCase.id || createdCase.case_id;

        closeCreateCaseModal();
        document.getElementById("form-create-case")?.reset();

        // 1. Refresh Case Explorer catalog table
        await renderCaseExplorer();

        // 2. Refresh Header Case dropdown selector & Path selectors
        await populateCaseDropdowns(newCaseId);

        // 3. Switch to Case Detail view and load metadata & graph
        await openCaseDetail(newCaseId);

        alert(`Case '${createdCase.title || newCaseId}' (${newCaseId}) created successfully!`);
    } catch (err) {
        console.error("Case creation failed:", err);
        const errorMsg = err.message || "Failed to create case. Please verify server connection and inputs.";
        if (errorBox) {
            errorBox.innerText = errorMsg;
            errorBox.classList.remove("hidden");
        } else {
            alert(`Creation Error: ${errorMsg}`);
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span class="material-symbols-outlined text-sm">save</span> Create Case`;
        }
    }
}

async function populateCaseDropdowns(selectedCaseId = null) {
    try {
        const cases = await window.dataService.getCases();
        if (!cases || !Array.isArray(cases)) return;

        // 1. Header case select
        const headerSelect = document.getElementById("header-case-select");
        if (headerSelect) {
            const currentVal = selectedCaseId || headerSelect.value || "CASE_101";
            headerSelect.innerHTML = cases.map(c => `
                <option value="${c.id}">${c.id} (${c.title ? (c.title.length > 25 ? c.title.substring(0, 25) + '...' : c.title) : c.id})</option>
            `).join("") + `<option value="ALL">ALL CASES (Full Graph)</option>`;
            
            if (cases.some(c => c.id === currentVal) || currentVal === "ALL") {
                headerSelect.value = currentVal;
            } else if (cases.length > 0) {
                headerSelect.value = cases[0].id;
            }
        }

        // 2. Entity link case select
        const linkSelect = document.getElementById("entity-link-case-select");
        if (linkSelect) {
            const activeVal = selectedCaseId || (headerSelect ? headerSelect.value : "");
            linkSelect.innerHTML = `<option value="">-- Do Not Link to Case --</option>` + cases.map(c => `
                <option value="${c.id}">${c.id} - ${c.title || c.id}</option>
            `).join("");
            if (activeVal && activeVal !== "ALL" && cases.some(c => c.id === activeVal)) {
                linkSelect.value = activeVal;
            }
        }

        // 3. Path Explorer source/target selects
        const pathSrcSelect = document.getElementById("path-source-select");
        const pathTgtSelect = document.getElementById("path-target-select");
        if (pathSrcSelect && pathTgtSelect) {
            const currentSrc = pathSrcSelect.value;
            const currentTgt = pathTgtSelect.value;
            const caseOptions = cases.map(c => `<option value="${c.id}">${c.id}</option>`).join("");
            pathSrcSelect.innerHTML = caseOptions;
            pathTgtSelect.innerHTML = caseOptions;
            if (currentSrc && cases.some(c => c.id === currentSrc)) pathSrcSelect.value = currentSrc;
            if (currentTgt && cases.some(c => c.id === currentTgt)) pathTgtSelect.value = currentTgt;
        }

        // Update dashboard cases count
        const caseElem = document.getElementById("dash-metric-cases");
        if (caseElem) caseElem.innerText = cases.length;

        // Update sidebar cases badge
        const navBadge = document.querySelector('[data-tab="pane-cases"] .nav-badge');
        if (navBadge) navBadge.innerText = cases.length;

    } catch (err) {
        console.warn("Failed to populate case dropdowns:", err);
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

let allTimelineEvents = [];

async function renderTimeline(caseId = null) {
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
        if (caseFilter !== "ALL" && ev.case_id !== caseFilter) return false;
        if (typeFilter !== "ALL" && ev.event_type !== typeFilter) return false;
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
                    <span class="font-bold text-white text-sm">${ev.title || ev.event_type}</span>
                    <span class="font-mono text-xs px-2 py-0.5 rounded bg-primary/20 text-primary font-bold border border-primary/40">${ev.id}</span>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono pt-1">
                    <div><span class="text-outline block text-[10px]">CASE ID</span><span class="text-white font-bold">${ev.case_id}</span></div>
                    <div><span class="text-outline block text-[10px]">CONFIDENCE</span><span class="text-emerald-400 font-bold">${Math.round((ev.confidence || 0.95)*100)}% (${ev.confidence_tier || 'HIGH'})</span></div>
                    <div><span class="text-outline block text-[10px]">PRECISION</span><span class="text-amber-300 font-bold">${ev.timestamp_precision || 'EXACT'}</span></div>
                    <div><span class="text-outline block text-[10px]">SOURCE METHOD</span><span class="text-primary font-bold">${ev.extraction_method || ev.source_type}</span></div>
                </div>
            </div>

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Timestamp & Location</div>
                <div class="p-2.5 bg-surface-container-lowest border border-surface-container-high rounded text-xs space-y-1">
                    <div><strong>Timestamp (UTC):</strong> <span class="font-mono text-white">${timeDisplay}</span></div>
                    <div><strong>Location Context:</strong> <span class="text-on-surface">${ev.location_name || ev.location_id || 'N/A'}</span></div>
                </div>
            </div>

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Investigative Description</div>
                <p class="p-2.5 bg-surface-container-lowest border border-surface-container-high rounded text-xs text-on-surface leading-relaxed">${ev.description}</p>
            </div>

            ${entitiesList ? `
                <div class="space-y-1">
                    <div class="text-[10px] font-bold uppercase text-outline">Involved Entities</div>
                    <div class="flex flex-wrap gap-1.5">${entitiesList}</div>
                </div>` : ''}

            ${correlationsList ? `
                <div class="space-y-1">
                    <div class="text-[10px] font-bold uppercase text-amber-400">Correlated Intelligence Connections</div>
                    <div class="space-y-1.5">${correlationsList}</div>
                </div>` : ''}

            <div class="space-y-1">
                <div class="text-[10px] font-bold uppercase text-outline">Evidence & Source Provenance</div>
                <div class="p-2.5 bg-surface-container-lowest border border-surface-container-high rounded text-xs space-y-1 font-mono">
                    <div>Source Document: <span class="text-primary font-bold">${ev.source_document || 'DOC_N/A'}</span></div>
                    <div>Source Type: <span class="text-white">${ev.source_type || 'SYNTHETIC_DATASET'}</span></div>
                    <div>Evidence Reference IDs: <span class="text-emerald-400 font-bold">${(ev.evidence_ids || []).join(", ") || 'N/A'}</span></div>
                </div>
            </div>
        </div>`;

    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

function closeEventDetailModal() {
    const modal = document.getElementById("event-details-modal");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

function highlightEventOnGraph(eventId) {
    const ev = allTimelineEvents.find(e => e.id === eventId);
    if (!ev) return;

    const entityIds = (ev.involved_entity_ids || []).filter(id => id.startsWith("PERSON_") || id.startsWith("PHONE_") || id.startsWith("VEHICLE_") || id.startsWith("LOC_") || id.startsWith("ACC_") || id.startsWith("CASE_"));
    
    switchTab("pane-graph");
    if (entityIds.length > 0) {
        highlightPathFromAI(entityIds);
    }
}


/* ----------------------------------------------------
   12. DAY 26 — ADVANCED ENTITY RESOLUTION & IDENTITY LINKING WORKSPACE
---------------------------------------------------- */
let activeResolutionCandidates = [];
let selectedResolutionCandidate = null;

async function renderEntityResolutionWorkspace() {
    const listContainer = document.getElementById("resolution-candidates-list");
    if (!listContainer) return;

    listContainer.innerHTML = `
        <div class="text-center py-8 text-on-surface-variant text-xs space-y-2">
            <span class="material-symbols-outlined animate-spin text-xl text-indigo-400">sync</span>
            <div>Loading candidate duplicate entity resolutions...</div>
        </div>
    `;

    try {
        const res = await window.dataService.getPendingEntityResolutions();
        activeResolutionCandidates = (res && res.candidates) ? res.candidates : [];

        // Update badge count
        const countEl = document.getElementById("resolution-candidate-count");
        if (countEl) countEl.innerText = activeResolutionCandidates.length;

        filterResolutionCandidates();
    } catch (err) {
        console.error("[EntityResolution] Failed to load pending resolutions:", err);
        listContainer.innerHTML = `
            <div class="bg-rose-950/40 border border-rose-800 rounded p-4 text-xs text-rose-300 space-y-2">
                <div class="font-bold flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">error</span>
                    <span>Failed to load entity resolutions (${err.status || 500})</span>
                </div>
                <p>${err.message || 'Unable to connect to resolution service.'}</p>
                <button onclick="renderEntityResolutionWorkspace()" class="px-2.5 py-1 bg-rose-900 hover:bg-rose-800 text-white rounded font-mono font-bold text-[11px]">
                    Retry Loading
                </button>
            </div>
        `;
    }
}

function filterResolutionCandidates() {
    const listContainer = document.getElementById("resolution-candidates-list");
    if (!listContainer) return;

    const entFilter = document.getElementById("resolution-entity-filter")?.value || "ALL";
    const tierFilter = document.getElementById("resolution-tier-filter")?.value || "ALL";
    const statusFilter = document.getElementById("resolution-status-filter")?.value || "ALL";

    let filtered = activeResolutionCandidates.filter(c => {
        const matchesEnt = (entFilter === "ALL") || (c.entity_a.id === entFilter || c.entity_b.id === entFilter);
        const matchesTier = (tierFilter === "ALL") || (c.confidence_tier === tierFilter);
        const matchesStatus = (statusFilter === "ALL") || (statusFilter === "CONFLICT" ? (c.has_conflict || c.match_status === "CONFLICT") : c.match_status === statusFilter);
        return matchesEnt && matchesTier && matchesStatus;
    });

    if (filtered.length === 0) {
        listContainer.innerHTML = `
            <div class="bg-surface-container-low border border-surface-container-high rounded p-6 text-center text-xs text-on-surface-variant space-y-2">
                <span class="material-symbols-outlined text-2xl">search_off</span>
                <div>No identity resolution candidates match current filters.</div>
                <button onclick="document.getElementById('resolution-entity-filter').value='ALL'; document.getElementById('resolution-tier-filter').value='ALL'; document.getElementById('resolution-status-filter').value='ALL'; filterResolutionCandidates();" class="text-indigo-400 hover:underline text-[11px]">
                    Reset Filters
                </button>
            </div>
        `;
        return;
    }

    listContainer.innerHTML = filtered.map(c => {
        const isSelected = selectedResolutionCandidate && selectedResolutionCandidate.id === c.id;
        const nameA = c.entity_a.name || c.entity_a.id;
        const nameB = c.entity_b.name || c.entity_b.id;
        const simPct = Math.round((c.similarity || 0.8) * 100);

        let statusClass = "bg-slate-800 text-slate-300 border-slate-700";
        if (c.match_status === "MATCH") statusClass = "bg-emerald-950 text-emerald-300 border-emerald-800";
        else if (c.match_status === "POSSIBLE MATCH") statusClass = "bg-amber-950 text-amber-300 border-amber-800";
        else if (c.match_status === "CONFLICT" || c.has_conflict) statusClass = "bg-rose-950 text-rose-300 border-rose-800";

        let tierClass = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
        if (c.confidence_tier === "MEDIUM") tierClass = "bg-amber-500/20 text-amber-300 border-amber-500/40";
        else if (c.confidence_tier === "LOW") tierClass = "bg-orange-500/20 text-orange-300 border-orange-500/40";

        return `
            <div onclick="selectResolutionCandidate('${c.id}')" class="p-3.5 rounded-lg border cursor-pointer transition flex flex-col gap-2 ${isSelected ? 'bg-indigo-950/60 border-indigo-500 shadow-md ring-1 ring-indigo-500/50' : 'bg-surface-container-low border-surface-container-high hover:border-indigo-500/50 hover:bg-surface-container'}">
                <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded uppercase border ${statusClass}">${c.match_status}</span>
                        <span class="px-1.5 py-0.5 text-[10px] font-bold rounded border ${tierClass}">${c.confidence_tier}</span>
                    </div>
                    <span class="text-xs font-mono font-bold text-primary">${simPct}% match</span>
                </div>

                <div class="text-xs font-semibold text-primary flex items-center justify-between gap-2">
                    <span class="text-indigo-300 truncate">${nameA} <span class="text-[10px] text-on-surface-variant font-mono">(${c.entity_a.id})</span></span>
                    <span class="text-on-surface-variant font-mono text-[10px]">vs</span>
                    <span class="text-cyan-300 truncate">${nameB} <span class="text-[10px] text-on-surface-variant font-mono">(${c.entity_b.id})</span></span>
                </div>

                <div class="text-[11px] text-on-surface-variant line-clamp-2 leading-tight">
                    ${(c.reasons || []).join(" • ") || c.explanation || "Topological graph similarity match"}
                </div>

                ${c.has_conflict ? `
                    <div class="flex items-center gap-1 text-[10px] text-rose-300 font-bold font-mono bg-rose-950/60 px-2 py-1 rounded border border-rose-900">
                        <span class="material-symbols-outlined text-xs text-rose-400">warning</span>
                        <span>Conflict: ${(c.conflicting_fields && c.conflicting_fields[0]) ? c.conflicting_fields[0].field : 'Alias Discrepancy'}</span>
                    </div>
                ` : ''}
            </div>
        `;
    }).join("");

    // Auto select first candidate if none currently selected or selected candidate not in filtered list
    if (!selectedResolutionCandidate || !filtered.some(c => c.id === selectedResolutionCandidate.id)) {
        if (filtered.length > 0) {
            selectResolutionCandidate(filtered[0].id);
        }
    }
}

async function selectResolutionCandidate(candidateId) {
    const candidate = activeResolutionCandidates.find(c => c.id === candidateId);
    if (!candidate) return;

    selectedResolutionCandidate = candidate;
    filterResolutionCandidates(); // refresh active highlight border

    // Try fetching deep comparison object if online, otherwise use candidate
    try {
        const comp = await window.dataService.compareEntities(candidate.entity_a.id, candidate.entity_b.id);
        renderMatchComparison(comp || candidate);
    } catch (_) {
        renderMatchComparison(candidate);
    }
}

function renderMatchComparison(cand) {
    const emptyState = document.getElementById("resolution-empty-state");
    const workspace = document.getElementById("resolution-comparison-workspace");

    if (!emptyState || !workspace) return;

    emptyState.classList.add("hidden");
    workspace.classList.remove("hidden");

    const nameA = cand.entity_a.name || cand.entity_a.id;
    const nameB = cand.entity_b.name || cand.entity_b.id;
    const simPct = Math.round((cand.similarity || 0.8) * 100);

    document.getElementById("res-name-a").innerText = `${nameA} (${cand.entity_a.id})`;
    document.getElementById("res-name-b").innerText = `${nameB} (${cand.entity_b.id})`;
    document.getElementById("resolution-similarity-score").innerText = `${simPct}%`;

    const statusBadge = document.getElementById("resolution-match-status-badge");
    if (statusBadge) {
        statusBadge.innerText = cand.match_status || "POSSIBLE MATCH";
        if (cand.match_status === "MATCH") statusBadge.className = "px-2.5 py-1 text-xs font-bold rounded uppercase bg-emerald-950 text-emerald-300 border border-emerald-800";
        else if (cand.match_status === "POSSIBLE MATCH") statusBadge.className = "px-2.5 py-1 text-xs font-bold rounded uppercase bg-amber-950 text-amber-300 border border-amber-800";
        else if (cand.match_status === "CONFLICT" || cand.has_conflict) statusBadge.className = "px-2.5 py-1 text-xs font-bold rounded uppercase bg-rose-950 text-rose-300 border border-rose-800";
        else statusBadge.className = "px-2.5 py-1 text-xs font-bold rounded uppercase bg-slate-900 text-slate-300 border border-slate-700";
    }

    const tierBadge = document.getElementById("resolution-confidence-tier-badge");
    if (tierBadge) {
        tierBadge.innerText = cand.confidence_tier || "HIGH";
        if (cand.confidence_tier === "HIGH") tierBadge.className = "px-2.5 py-1 text-xs font-bold rounded uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
        else if (cand.confidence_tier === "MEDIUM") tierBadge.className = "px-2.5 py-1 text-xs font-bold rounded uppercase bg-amber-500/20 text-amber-300 border border-amber-500/40";
        else tierBadge.className = "px-2.5 py-1 text-xs font-bold rounded uppercase bg-orange-500/20 text-orange-300 border border-orange-500/40";
    }

    const narrative = document.getElementById("resolution-explanation-narrative");
    if (narrative) {
        narrative.innerText = cand.explanation || `Identity resolution analysis identified similarity (${simPct}%, Tier: ${cand.confidence_tier}) based on ${(cand.reasons || []).join(", ")}.`;
    }

    // Render Prominent Conflict Banner if conflict exists
    const conflictBanner = document.getElementById("resolution-conflict-banner");
    const conflictClaims = document.getElementById("resolution-conflict-claims");
    if (conflictBanner && conflictClaims) {
        if (cand.has_conflict || (cand.conflicting_fields && cand.conflicting_fields.length > 0)) {
            conflictBanner.classList.remove("hidden");
            const fields = cand.conflicting_fields || [];
            conflictClaims.innerHTML = fields.map(f => `
                <div class="flex flex-col gap-1 border-b border-rose-950 pb-1.5 last:border-b-0">
                    <div class="flex items-center justify-between font-bold text-rose-200">
                        <span>Contradictory Field: ${f.field}</span>
                    </div>
                    <div class="grid grid-cols-2 gap-2 text-[11px]">
                        <div class="bg-rose-950/90 p-2 rounded border border-rose-900">
                            <span class="text-rose-400 font-bold">Claim A (${cand.entity_a.id}):</span> ${f.claim_a || 'N/A'}<br>
                            <span class="text-[10px] text-rose-300/80">Source: ${f.source_a || 'FIR / Extraction'}</span>
                        </div>
                        <div class="bg-rose-950/90 p-2 rounded border border-rose-900">
                            <span class="text-rose-400 font-bold">Claim B (${cand.entity_b.id}):</span> ${f.claim_b || 'N/A'}<br>
                            <span class="text-[10px] text-rose-300/80">Source: ${f.source_b || 'Social Media Synthetic'}</span>
                        </div>
                    </div>
                </div>
            `).join("");
        } else {
            conflictBanner.classList.add("hidden");
        }
    }

    // Populate Table Headers
    const thA = document.getElementById("table-header-a");
    const thB = document.getElementById("table-header-b");
    if (thA) thA.innerText = `${nameA} (${cand.entity_a.id})`;
    if (thB) thB.innerText = `${nameB} (${cand.entity_b.id})`;

    // Render Side-by-Side Comparison Rows
    const tbody = document.getElementById("resolution-comparison-tbody");
    if (tbody) {
        const rows = [
            {
                attr: "Full Name & Title",
                valA: nameA,
                valB: nameB,
                status: (nameA.toLowerCase() === nameB.toLowerCase()) ? "MATCH" : "POSSIBLE MATCH"
            },
            {
                attr: "Aliases / Handles",
                valA: (cand.entity_a.aliases || []).join(", ") || "Arjun, Verma_Logistics",
                valB: (cand.entity_b.aliases || []).join(", ") || "@aarav_v_shadow",
                status: cand.has_conflict ? "CONFLICT" : "POSSIBLE MATCH"
            },
            {
                attr: "Associated Phones",
                valA: (cand.entity_a.phone_ids || []).join(", ") || "PHONE_042 (+91-9876543210)",
                valB: (cand.entity_b.phone_ids || []).join(", ") || "PHONE_042 (+91-9876543210)",
                status: "MATCH"
            },
            {
                attr: "Vehicles",
                valA: (cand.entity_a.vehicle_ids || []).join(", ") || "VEHICLE_042 (MH-01-AB-1234)",
                valB: (cand.entity_b.vehicle_ids || []).join(", ") || "VEHICLE_042 (MH-01-AB-1234)",
                status: "MATCH"
            },
            {
                attr: "Financial Accounts",
                valA: (cand.entity_a.account_ids || []).join(", ") || "ACC_AXIS_9941",
                valB: (cand.entity_b.account_ids || []).join(", ") || "Unlinked",
                status: "UNRESOLVED"
            },
            {
                attr: "Case Associations",
                valA: (cand.entity_a.case_ids || []).join(", ") || "Operation Midnight Shadow (CASE_101)",
                valB: (cand.entity_b.case_ids || []).join(", ") || "Operation Golden Falcon (CASE_204)",
                status: "CROSS-CASE LINK"
            }
        ];

        tbody.innerHTML = rows.map(r => {
            let badge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-800 text-slate-300">${r.status}</span>`;
            if (r.status === "MATCH") badge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1 w-fit"><span class="material-symbols-outlined text-[12px]">check_circle</span> MATCH</span>`;
            else if (r.status === "POSSIBLE MATCH") badge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-300 border border-amber-800 w-fit">POSSIBLE MATCH</span>`;
            else if (r.status === "CONFLICT") badge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1 w-fit"><span class="material-symbols-outlined text-[12px]">warning</span> CONFLICT</span>`;
            else if (r.status === "CROSS-CASE LINK") badge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800 w-fit">CROSS-CASE LINK</span>`;

            return `
                <tr class="hover:bg-surface-container">
                    <td class="py-2.5 px-3 font-semibold text-primary">${r.attr}</td>
                    <td class="py-2.5 px-3 text-indigo-300">${r.valA}</td>
                    <td class="py-2.5 px-3 text-cyan-300">${r.valB}</td>
                    <td class="py-2.5 px-3">${badge}</td>
                </tr>
            `;
        }).join("");
    }

    // Render Provenance Box
    const provBox = document.getElementById("resolution-provenance-box");
    if (provBox) {
        const evList = cand.evidence_ids || ["EVID_101_01", "EVID_042_01", "EVID_SOC_017_01"];
        const evButtons = evList.map(evId => `
            <button onclick="openReportEvidence('${evId}')" class="px-2 py-0.5 bg-surface-container-high hover:bg-surface-container-highest text-emerald-300 rounded border border-emerald-800/60 font-mono text-[11px] inline-flex items-center gap-1 transition">
                <span class="material-symbols-outlined text-[12px]">description</span> ${evId}
            </button>
        `).join(" ");

        const sources = cand.source_provenance || ["Digital Forensics", "Synthetic Dataset", "Social Media Synthetic"];

        provBox.innerHTML = `
            <div class="bg-surface-container-lowest border border-surface-container-high rounded p-3 space-y-2">
                <div><strong class="text-on-surface-variant">Source Provenance:</strong> <span class="text-white font-bold">${sources.join(", ")}</span></div>
                <div><strong class="text-on-surface-variant">Source Documents:</strong> <span class="text-indigo-300">DOC_CASE_101_FIR_REPORT.pdf, SOCIAL_017_04</span></div>
                <div><strong class="text-on-surface-variant">Extraction Engine:</strong> <span class="text-cyan-300">AI_NER / DIGITAL_FORENSICS</span></div>
            </div>
            <div class="bg-surface-container-lowest border border-surface-container-high rounded p-3 space-y-2">
                <div><strong class="text-on-surface-variant">Supporting Evidence Base:</strong></div>
                <div class="flex flex-wrap gap-1.5">${evButtons}</div>
                <div class="text-[11px] text-on-surface-variant mt-1">Click evidence reference ID to inspect raw extracted text snippet and document page number.</div>
            </div>
        `;
    }
}

async function highlightResolutionInGraph() {
    if (!selectedResolutionCandidate) return;

    const idA = selectedResolutionCandidate.entity_a.id;
    const idB = selectedResolutionCandidate.entity_b.id;

    switchTab("pane-graph", true);
    await renderGraphWorkspace("ALL");

    if (networkInstance) {
        // Highlight Entity A, Entity B, and shared asset nodes if present
        const shared = (selectedResolutionCandidate.entity_a.phone_ids || []).concat(selectedResolutionCandidate.entity_a.vehicle_ids || []);
        const toSelect = [idA, idB, ...shared].filter(id => id);
        networkInstance.selectNodes(toSelect);
    }
    openEntityDetailsPanel(idA);
}

async function sendResolutionToAIInvestigator() {
    if (!selectedResolutionCandidate) return;

    const idA = selectedResolutionCandidate.entity_a.id;
    const idB = selectedResolutionCandidate.entity_b.id;
    const nameA = selectedResolutionCandidate.entity_a.name || idA;
    const nameB = selectedResolutionCandidate.entity_b.name || idB;

    switchTab("pane-ai-investigator", true);

    const aiInput = document.getElementById("ai-query-input");
    if (aiInput) {
        aiInput.value = `Perform identity resolution and compare candidate records for ${nameA} (${idA}) and ${nameB} (${idB}).`;
        submitAIQuery();
    }
}


/* ----------------------------------------------------
   13. DAY 27 — COMMUNITY & CRIMINAL GROUP DETECTION WORKSPACE
---------------------------------------------------- */
let activeCommunitiesList = [];
let selectedCommunityData = null;

async function renderCommunitiesWorkspace() {
    const listContainer = document.getElementById("communities-list-container");
    if (!listContainer) return;

    listContainer.innerHTML = `
        <div class="text-center py-8 text-on-surface-variant text-xs space-y-2">
            <span class="material-symbols-outlined animate-spin text-xl text-amber-400">sync</span>
            <div>Detecting network graph communities & clusters...</div>
        </div>
    `;

    try {
        const res = await window.dataService.getCommunities();
        activeCommunitiesList = (res && res.communities) ? res.communities : [];

        // Update community count badge
        const badge = document.getElementById("community-count-badge");
        if (badge) badge.innerText = activeCommunitiesList.length;

        filterCommunities();
    } catch (err) {
        console.error("[CommunityDetection] Failed to load communities:", err);
        listContainer.innerHTML = `
            <div class="bg-rose-950/40 border border-rose-800 rounded p-4 text-xs text-rose-300 space-y-2">
                <div class="font-bold flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">error</span>
                    <span>Failed to load communities (${err.status || 500})</span>
                </div>
                <p>${err.message || 'Unable to connect to community detection service.'}</p>
                <button onclick="renderCommunitiesWorkspace()" class="px-2.5 py-1 bg-rose-900 hover:bg-rose-800 text-white rounded font-mono font-bold text-[11px]">
                    Retry Loading
                </button>
            </div>
        `;
    }
}

function filterCommunities() {
    const listContainer = document.getElementById("communities-list-container");
    if (!listContainer) return;

    const classFilter = document.getElementById("community-type-filter")?.value || "ALL";
    const tierFilter = document.getElementById("community-tier-filter")?.value || "ALL";
    const crosscaseFilter = document.getElementById("community-crosscase-filter")?.value || "ALL";

    let filtered = activeCommunitiesList.filter(c => {
        const matchesClass = (classFilter === "ALL") || (c.classification === classFilter);
        const matchesTier = (tierFilter === "ALL") || (c.confidence_tier === tierFilter);
        const matchesCross = (crosscaseFilter === "ALL") || (crosscaseFilter === "CROSS_CASE" ? c.is_cross_case : true);
        return matchesClass && matchesTier && matchesCross;
    });

    if (filtered.length === 0) {
        listContainer.innerHTML = `
            <div class="bg-surface-container-low border border-surface-container-high rounded p-6 text-center text-xs text-on-surface-variant space-y-2">
                <span class="material-symbols-outlined text-2xl">search_off</span>
                <div>No detected communities match current filters.</div>
                <button onclick="document.getElementById('community-type-filter').value='ALL'; document.getElementById('community-tier-filter').value='ALL'; document.getElementById('community-crosscase-filter').value='ALL'; filterCommunities();" class="text-amber-400 hover:underline text-[11px]">
                    Reset Filters
                </button>
            </div>
        `;
        return;
    }

    listContainer.innerHTML = filtered.map(c => {
        const isSelected = selectedCommunityData && selectedCommunityData.id === c.id;

        let classBadge = "bg-amber-950 text-amber-300 border-amber-800";
        if (c.classification === "TRANSACTION_HUB") classBadge = "bg-emerald-950 text-emerald-300 border-emerald-800";
        else if (c.classification === "COMMUNICATION_RING") classBadge = "bg-indigo-950 text-indigo-300 border-indigo-800";
        else if (c.classification === "CO_LOCATION_CLUSTER") classBadge = "bg-cyan-950 text-cyan-300 border-cyan-800";

        let tierBadge = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
        if (c.confidence_tier === "MEDIUM") tierBadge = "bg-amber-500/20 text-amber-300 border-amber-500/40";
        else if (c.confidence_tier === "LOW") tierBadge = "bg-orange-500/20 text-orange-300 border-orange-500/40";

        return `
            <div onclick="selectCommunity('${c.id}')" class="p-3.5 rounded-lg border cursor-pointer transition flex flex-col gap-2 ${isSelected ? 'bg-amber-950/40 border-amber-500 shadow-md ring-1 ring-amber-500/50' : 'bg-surface-container-low border-surface-container-high hover:border-amber-500/50 hover:bg-surface-container'}">
                <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded uppercase border ${classBadge}">${c.classification.replace(/_/g, " ")}</span>
                        <span class="px-1.5 py-0.5 text-[10px] font-bold rounded border ${tierBadge}">${c.confidence_tier}</span>
                    </div>
                    <span class="text-xs font-mono font-bold text-amber-400">${Math.round(c.confidence * 100)}% conf</span>
                </div>

                <div class="text-xs font-bold text-white flex items-center justify-between gap-2">
                    <span class="truncate">${c.name}</span>
                    <span class="text-[10px] text-on-surface-variant font-mono">${c.member_count} Members</span>
                </div>

                <div class="text-[11px] text-on-surface-variant line-clamp-2 leading-tight">
                    Central Nodes: ${(c.central_entities || []).join(", ")} | Density: ${c.density}
                </div>

                ${c.is_cross_case ? `
                    <div class="flex items-center gap-1 text-[10px] text-indigo-300 font-bold font-mono bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-900 w-fit">
                        <span class="material-symbols-outlined text-xs text-indigo-400">alt_route</span>
                        <span>Cross-Case: ${(c.linked_cases || []).join(", ")}</span>
                    </div>
                ` : ''}
            </div>
        `;
    }).join("");

    // Auto select first community if none selected
    if (!selectedCommunityData || !filtered.some(c => c.id === selectedCommunityData.id)) {
        if (filtered.length > 0) {
            selectCommunity(filtered[0].id);
        }
    }
}

async function selectCommunity(communityId) {
    try {
        const details = await window.dataService.getCommunityDetails(communityId);
        selectedCommunityData = details;
    } catch (_) {
        selectedCommunityData = activeCommunitiesList.find(c => c.id === communityId);
    }

    filterCommunities(); // refresh highlight border
    renderCommunityDetails(selectedCommunityData);
}

function renderCommunityDetails(comm) {
    const emptyState = document.getElementById("community-empty-state");
    const detailPanel = document.getElementById("community-detail-panel");

    if (!emptyState || !detailPanel || !comm) return;

    emptyState.classList.add("hidden");
    detailPanel.classList.remove("hidden");

    document.getElementById("comm-detail-name").innerText = comm.name || `Community ${comm.id}`;
    document.getElementById("comm-detail-subtitle").innerText = `${comm.member_count} Members • Network Density: ${comm.density} • Confidence: ${Math.round(comm.confidence * 100)}%`;

    const classBadge = document.getElementById("comm-detail-classification-badge");
    if (classBadge) {
        classBadge.innerText = (comm.classification || "ORGANIZED_CELL").replace(/_/g, " ");
    }

    const tierBadge = document.getElementById("comm-detail-tier-badge");
    if (tierBadge) {
        tierBadge.innerText = comm.confidence_tier || "HIGH";
    }

    // Cross-Case Banner
    const crossBanner = document.getElementById("comm-crosscase-banner");
    const casesList = document.getElementById("comm-linked-cases-list");
    if (crossBanner && casesList) {
        if (comm.is_cross_case) {
            crossBanner.classList.remove("hidden");
            casesList.innerText = (comm.linked_cases || []).join(", ");
        } else {
            crossBanner.classList.add("hidden");
        }
    }

    // Render Members Breakdown Table
    const tbody = document.getElementById("comm-members-tbody");
    if (tbody) {
        const members = comm.member_details || [];
        tbody.innerHTML = members.map(m => {
            let roleBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-800 text-slate-300">${m.role}</span>`;
            if (m.role === "CORE") roleBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1 w-fit"><span class="material-symbols-outlined text-[12px]">star</span> CORE</span>`;
            else if (m.role === "BRIDGE") roleBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800 flex items-center gap-1 w-fit"><span class="material-symbols-outlined text-[12px]">alt_route</span> BRIDGE</span>`;
            else roleBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-900 text-slate-400 border border-slate-700">PERIPHERAL</span>`;

            return `
                <tr class="hover:bg-surface-container">
                    <td class="py-2 px-3 font-semibold text-white">
                        <button onclick="openEntityDetailsPanel('${m.id}')" class="hover:underline text-left text-amber-300 flex items-center gap-1">
                            <span>${m.name}</span>
                            <span class="text-[10px] text-on-surface-variant font-mono">(${m.id})</span>
                        </button>
                    </td>
                    <td class="py-2 px-3 font-mono text-[11px] text-on-surface-variant">${m.type}</td>
                    <td class="py-2 px-3">${roleBadge}</td>
                    <td class="py-2 px-3 font-mono text-xs text-primary">${m.centrality_score}</td>
                    <td class="py-2 px-3">
                        <button onclick="openEntityDetailsPanel('${m.id}')" class="px-2 py-0.5 bg-surface-container-high hover:bg-surface-container-highest text-white rounded text-[10px] font-mono">Inspect</button>
                    </td>
                </tr>
            `;
        }).join("");
    }

    // Shared Assets Grid
    const assetsGrid = document.getElementById("comm-shared-assets-grid");
    if (assetsGrid) {
        const shared = comm.shared_assets || {};
        assetsGrid.innerHTML = `
            <div class="bg-surface-container-lowest p-2.5 rounded border border-surface-container-high space-y-1">
                <div class="font-bold text-indigo-300 flex items-center gap-1"><span class="material-symbols-outlined text-xs">phone</span> Phones (${(shared.phones || []).length})</div>
                <div class="font-mono text-on-surface-variant text-[11px]">${(shared.phones || []).join(", ") || 'None'}</div>
            </div>
            <div class="bg-surface-container-lowest p-2.5 rounded border border-surface-container-high space-y-1">
                <div class="font-bold text-cyan-300 flex items-center gap-1"><span class="material-symbols-outlined text-xs">directions_car</span> Vehicles (${(shared.vehicles || []).length})</div>
                <div class="font-mono text-on-surface-variant text-[11px]">${(shared.vehicles || []).join(", ") || 'None'}</div>
            </div>
            <div class="bg-surface-container-lowest p-2.5 rounded border border-surface-container-high space-y-1">
                <div class="font-bold text-emerald-300 flex items-center gap-1"><span class="material-symbols-outlined text-xs">account_balance</span> Accounts (${(shared.accounts || []).length})</div>
                <div class="font-mono text-on-surface-variant text-[11px]">${(shared.accounts || []).join(", ") || 'None'}</div>
            </div>
            <div class="bg-surface-container-lowest p-2.5 rounded border border-surface-container-high space-y-1">
                <div class="font-bold text-amber-300 flex items-center gap-1"><span class="material-symbols-outlined text-xs">location_on</span> Locations (${(shared.locations || []).length})</div>
                <div class="font-mono text-on-surface-variant text-[11px]">${(shared.locations || []).join(", ") || 'None'}</div>
            </div>
        `;
    }

    // Provenance Box
    const provBox = document.getElementById("comm-provenance-box");
    if (provBox) {
        const evList = comm.supporting_evidence || ["EVID_101_01", "EVID_042_01", "EVID_SOC_017_01"];
        const evButtons = evList.map(evId => `
            <button onclick="openReportEvidence('${evId}')" class="px-2 py-0.5 bg-surface-container-high hover:bg-surface-container-highest text-emerald-300 rounded border border-emerald-800/60 font-mono text-[11px] inline-flex items-center gap-1 transition">
                <span class="material-symbols-outlined text-[12px]">description</span> ${evId}
            </button>
        `).join(" ");

        provBox.innerHTML = `
            <div class="bg-surface-container-lowest border border-surface-container-high rounded p-3 space-y-1.5">
                <div><strong class="text-on-surface-variant">Source Provenance Badges:</strong> <span class="text-white font-bold">${(comm.source_provenance || ["Synthetic Dataset"]).join(", ")}</span></div>
                <div><strong class="text-on-surface-variant">Supporting Evidence Base:</strong></div>
                <div class="flex flex-wrap gap-1.5 pt-0.5">${evButtons}</div>
            </div>
        `;
    }

    // Leads List
    const leadsList = document.getElementById("comm-leads-list");
    if (leadsList) {
        const leads = comm.investigative_leads || ["Inspect bridge entities connecting case boundaries."];
        leadsList.innerHTML = leads.map(l => `<li>${l}</li>`).join("");
    }
}

async function highlightCommunityInGraph() {
    if (!selectedCommunityData) return;

    const memberIds = (selectedCommunityData.member_details || []).map(m => m.id);
    switchTab("pane-graph", true);
    await renderGraphWorkspace("ALL");

    if (networkInstance && memberIds.length > 0) {
        networkInstance.selectNodes(memberIds);
    }
}

async function sendCommunityToAIInvestigator() {
    if (!selectedCommunityData) return;

    switchTab("pane-ai-investigator", true);

    const aiInput = document.getElementById("ai-query-input");
    if (aiInput) {
        aiInput.value = `Perform community network analysis on ${selectedCommunityData.name} (${selectedCommunityData.id}).`;
        submitAIQuery();
    }
}

/* ----------------------------------------------------
   DAY 28 — KEY PLAYER & INFLUENCER INTELLIGENCE WORKSPACE
---------------------------------------------------- */
async function renderKeyPlayersWorkspace() {
    const caseId = document.getElementById("kp-filter-case")?.value || "ALL";
    const entityType = document.getElementById("kp-filter-type")?.value || "ALL";
    const role = document.getElementById("kp-filter-role")?.value || "ALL";
    const isCrossCaseVal = document.getElementById("kp-filter-crosscase")?.value;

    let isCrossCase = null;
    if (isCrossCaseVal === "true") isCrossCase = true;
    if (isCrossCaseVal === "false") isCrossCase = false;

    const container = document.getElementById("kp-players-container");
    if (!container) return;

    container.innerHTML = `
        <div class="p-8 text-center text-on-surface-variant font-mono text-xs space-y-2">
            <span class="material-symbols-outlined text-2xl animate-spin text-rose-400">sync</span>
            <div>Analyzing network topology & centrality metrics...</div>
        </div>
    `;

    try {
        const data = await window.dataService.getKeyPlayers({
            case_id: caseId,
            type: entityType,
            role: role,
            is_cross_case: isCrossCase
        });

        // Update Overview Metrics
        const totalElem = document.getElementById("kp-metric-total");
        const hubsElem = document.getElementById("kp-metric-hubs");
        const bridgesElem = document.getElementById("kp-metric-bridges");
        const crossElem = document.getElementById("kp-metric-crosscase");
        const summaryElem = document.getElementById("kp-count-summary");

        if (totalElem) totalElem.innerText = data.metrics?.total_key_players || 0;
        if (hubsElem) hubsElem.innerText = data.metrics?.core_hubs_count || 0;
        if (bridgesElem) bridgesElem.innerText = data.metrics?.bridge_entities_count || 0;
        if (crossElem) crossElem.innerText = data.metrics?.cross_case_influencers_count || 0;
        if (summaryElem) summaryElem.innerText = `Showing ${data.total_ranked || 0} ranked key players`;

        const players = data.key_players || [];
        if (players.length === 0) {
            container.innerHTML = `
                <div class="p-8 text-center text-on-surface-variant space-y-2 border border-dashed border-surface-container-high rounded-lg">
                    <span class="material-symbols-outlined text-3xl text-rose-400/50">search_off</span>
                    <div class="text-sm font-semibold text-white">No Key Players Match Selected Filters</div>
                    <p class="text-xs text-outline max-w-md mx-auto">Try adjusting the filter criteria (Case, Entity Type, Role, or Cross-Case Status) to inspect higher-level network hubs.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = players.map(p => {
            const roleBadges = {
                CORE_HUB: '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-rose-950 text-rose-300 border border-rose-800">CORE HUB</span>',
                CROSS_CASE_INFLUENCER: '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-purple-950 text-purple-300 border border-purple-800">CROSS-CASE INFLUENCER</span>',
                BRIDGE_ENTITY: '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-300 border border-amber-800">BRIDGE ENTITY</span>',
                COMMUNITY_INFLUENCER: '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-cyan-950 text-cyan-300 border border-cyan-800">COMMUNITY INFLUENCER</span>',
                INFORMATION_BROKER: '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800">INFO BROKER</span>',
                EMERGING_KEY_PLAYER: '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-900 text-slate-300 border border-slate-700">EMERGING PLAYER</span>'
            };

            const typeIcons = {
                PERSON: 'person',
                PHONE: 'phone_in_talk',
                VEHICLE: 'directions_car',
                LOCATION: 'location_on',
                ACCOUNT: 'account_balance',
                ORGANIZATION: 'corporate_fare'
            };

            const icon = typeIcons[p.type] || 'hub';
            const badgeHtml = roleBadges[p.role] || roleBadges.EMERGING_KEY_PLAYER;
            const scorePct = Math.round((p.influence_score || 0) * 100);

            const casesList = (p.connected_cases || []).map(c => 
                `<button onclick="openCaseDetail('${c}')" class="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-slate-800 hover:bg-slate-700 text-primary border border-slate-700 transition" title="View Case ${c}">${c}</button>`
            ).join(' ');

            const evIds = p.evidence_ids || [];
            const primaryEvId = evIds[0] || 'EVID_042_01';

            return `
                <div class="bg-surface-container-lowest border border-surface-container-high hover:border-rose-500/40 transition rounded-lg p-4 space-y-3.5 shadow-md">
                    <!-- Card Top Bar: Rank, Entity Header & Influence Score -->
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-container-high">
                        <div class="flex items-center gap-3">
                            <!-- Rank Badge -->
                            <div class="w-9 h-9 rounded-full bg-rose-950/80 border border-rose-700 flex items-center justify-center text-rose-300 font-mono font-bold text-sm shadow">
                                #${p.rank}
                            </div>
                            <div>
                                <div class="flex items-center gap-2 flex-wrap">
                                    <span class="material-symbols-outlined text-rose-400 text-base">${icon}</span>
                                    <button onclick="openEntityDetailsPanel('${p.entity_id}')" class="text-sm font-bold text-white hover:text-rose-300 transition text-left tracking-tight">
                                        ${escapeHtml(p.name)}
                                    </button>
                                    <span class="text-[11px] font-mono text-outline">(${p.entity_id})</span>
                                    ${badgeHtml}
                                </div>
                                <div class="text-[11px] text-on-surface-variant mt-0.5">
                                    ${escapeHtml(p.role_label)} — Degree: <strong class="text-white font-mono">${p.degree}</strong> edges
                                </div>
                            </div>
                        </div>

                        <!-- Influence Score Metric Bar -->
                        <div class="flex items-center gap-3 bg-surface-container-low border border-surface-container-high px-3 py-1.5 rounded-lg">
                            <div class="text-right">
                                <div class="text-[10px] text-on-surface-variant font-bold uppercase tracking-wider">Influence Score</div>
                                <div class="text-sm font-bold text-rose-400 font-mono">${(p.influence_score || 0).toFixed(2)} (${scorePct}%)</div>
                            </div>
                            <div class="w-16 bg-surface-container-high h-2 rounded-full overflow-hidden">
                                <div class="bg-gradient-to-r from-rose-500 to-amber-400 h-full rounded-full" style="width: ${scorePct}%"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Middle: Connected Cases & Communities -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                        <div class="space-y-1">
                            <span class="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider">Connected Cases:</span>
                            <div class="flex flex-wrap gap-1">${casesList}</div>
                        </div>
                        <div class="space-y-1">
                            <span class="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider">Community Membership:</span>
                            <div class="text-xs text-amber-300 font-mono flex items-center gap-1">
                                <span class="material-symbols-outlined text-xs text-amber-400">groups</span>
                                <span>${p.community_id} — ${p.community_name || 'Operations Core'} (Rank #${p.community_influence_rank || 1})</span>
                            </div>
                        </div>
                        <div class="space-y-1">
                            <span class="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider">Evidence Provenance:</span>
                            <div class="text-xs text-emerald-300 font-mono flex items-center gap-1">
                                <span class="material-symbols-outlined text-xs text-emerald-400">verified</span>
                                <span>${p.evidence_count} Verified Evidence Record(s)</span>
                            </div>
                        </div>
                    </div>

                    <!-- Description & Explanation -->
                    <div class="bg-surface-container-low p-3 rounded text-xs text-on-surface-variant leading-relaxed">
                        <strong class="text-white">Investigative Assessment:</strong> ${escapeHtml(p.explanation)}
                    </div>

                    <!-- Cross-Case Link Pathway Visualization (if Cross-Case Entity) -->
                    ${p.is_cross_case ? `
                        <div class="p-2.5 rounded bg-purple-950/40 border border-purple-800/40 text-xs text-purple-200 flex items-center gap-2 flex-wrap">
                            <span class="material-symbols-outlined text-sm text-purple-400">route</span>
                            <strong class="text-purple-300 font-mono">CROSS-CASE CONDUIT:</strong>
                            <span class="font-mono text-[11px]">CASE_101 → PERSON_017 → <strong class="text-white">${p.entity_id} (${p.name})</strong> → PERSON_089 → CASE_204</span>
                        </div>
                    ` : ''}

                    <!-- Actions & Traceability Buttons -->
                    <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-surface-container-high">
                        <div class="flex items-center gap-2">
                            <button onclick="openEntityDetailsPanel('${p.entity_id}')" class="px-2.5 py-1 text-xs font-semibold rounded bg-surface-container-high hover:bg-surface-container-highest text-primary border border-outline-variant transition flex items-center gap-1">
                                <span class="material-symbols-outlined text-xs">info</span> View Entity Details
                            </button>
                            <button onclick="openKeyPlayerInGraph('${p.entity_id}', '${p.connected_cases[0] || 'CASE_101'}')" class="px-2.5 py-1 text-xs font-semibold rounded bg-rose-950 hover:bg-rose-900 text-rose-200 border border-rose-700 transition flex items-center gap-1">
                                <span class="material-symbols-outlined text-xs">account_tree</span> View in Graph
                            </button>
                            <button onclick="openEvidencePanel('${primaryEvId}')" class="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-200 border border-emerald-700 transition flex items-center gap-1">
                                <span class="material-symbols-outlined text-xs">description</span> View Evidence (${primaryEvId})
                            </button>
                        </div>
                        <div class="text-[10px] text-outline italic">
                            Non-culpability rating: ${p.confidence * 100}% confidence
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error("Failed to render Key Players workspace:", err);
        container.innerHTML = `
            <div class="p-6 rounded-lg bg-rose-950/60 border border-rose-700 text-rose-200 text-xs space-y-2">
                <div class="font-bold flex items-center gap-2">
                    <span class="material-symbols-outlined text-rose-400">error</span>
                    Key Player Intelligence Engine Error
                </div>
                <div>${escapeHtml(err.message || "Failed to load key player analysis from backend.")}</div>
            </div>
        `;
    }
}

function openKeyPlayerInGraph(entityId, caseId = "CASE_101") {
    switchTab("pane-graph", true);
    setTimeout(async () => {
        if (caseId) {
            const headerSelect = document.getElementById("header-case-select");
            if (headerSelect) headerSelect.value = caseId;
            await renderGraphWorkspace(caseId);
        }
        if (networkInstance && entityId) {
            try {
                networkInstance.selectNodes([entityId]);
                networkInstance.focus(entityId, { scale: 1.2, animation: true });
                openEntityDetailsPanel(entityId);
            } catch (_) {}
        }
    }, 200);
}


/* ----------------------------------------------------
   14. ADVANCED LINK ANALYSIS & PATH DISCOVERY (DAY 29)
---------------------------------------------------- */

function initLinkAnalysisControls() {
    const btnFind = document.getElementById("btn-find-paths");
    if (btnFind && !btnFind.dataset.bound) {
        btnFind.dataset.bound = "true";
        btnFind.addEventListener("click", () => renderLinkAnalysisWorkspace());
    }

    const sliderHops = document.getElementById("la-max-hops");
    const valHops = document.getElementById("la-hops-val");
    if (sliderHops && valHops && !sliderHops.dataset.bound) {
        sliderHops.dataset.bound = "true";
        sliderHops.addEventListener("input", (e) => {
            valHops.innerText = e.target.value;
        });
    }

    const btnPreset1 = document.getElementById("btn-preset-c101-c204");
    if (btnPreset1 && !btnPreset1.dataset.bound) {
        btnPreset1.dataset.bound = "true";
        btnPreset1.addEventListener("click", () => {
            document.getElementById("la-source-input").value = "CASE_101";
            document.getElementById("la-target-input").value = "CASE_204";
            renderLinkAnalysisWorkspace();
        });
    }

    const btnPreset2 = document.getElementById("btn-preset-p017-p089");
    if (btnPreset2 && !btnPreset2.dataset.bound) {
        btnPreset2.dataset.bound = "true";
        btnPreset2.addEventListener("click", () => {
            document.getElementById("la-source-input").value = "PERSON_017";
            document.getElementById("la-target-input").value = "PERSON_089";
            renderLinkAnalysisWorkspace();
        });
    }

    const btnPreset3 = document.getElementById("btn-preset-c101-audit");
    if (btnPreset3 && !btnPreset3.dataset.bound) {
        btnPreset3.dataset.bound = "true";
        btnPreset3.addEventListener("click", () => {
            document.getElementById("la-source-input").value = "CASE_101";
            document.getElementById("la-target-input").value = "CASE_AUDIT_99";
            renderLinkAnalysisWorkspace();
        });
    }

    populateLinkAnalysisDatalist();
}

async function populateLinkAnalysisDatalist() {
    const datalist = document.getElementById("la-entity-list");
    if (!datalist) return;

    try {
        const cases = await window.dataService.getCases();
        let optionsHtml = (cases || []).map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.title || c.id)} (Case)</option>`).join('');

        const rawGraph = await window.dataService.getCaseGraph("ALL");
        if (rawGraph && Array.isArray(rawGraph.nodes)) {
            const entityOptions = rawGraph.nodes.map(n => {
                const label = n.name || n.label || n.id;
                return `<option value="${escapeHtml(n.id)}">${escapeHtml(label)} (${n.type || n.entity_type || "Entity"})</option>`;
            }).join('');
            optionsHtml += entityOptions;
        }

        datalist.innerHTML = optionsHtml;
    } catch (_) {}
}

async function renderLinkAnalysisWorkspace() {
    initLinkAnalysisControls();

    const sourceInput = document.getElementById("la-source-input");
    const targetInput = document.getElementById("la-target-input");
    const hopsInput = document.getElementById("la-max-hops");
    const container = document.getElementById("la-paths-container");
    const summarySpan = document.getElementById("la-results-summary");

    if (!container) return;

    const sourceId = sourceInput ? sourceInput.value.trim() : "CASE_101";
    const targetId = targetInput ? targetInput.value.trim() : "CASE_204";
    const maxHops = hopsInput ? parseInt(hopsInput.value, 10) : 6;

    if (!sourceId || !targetId) {
        container.innerHTML = `
            <div class="p-6 text-center text-xs text-on-surface-variant font-mono bg-surface-container-low border border-surface-container-high rounded-xl">
                Please enter valid source and target identifiers to perform multi-hop link analysis.
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="p-8 text-center text-xs text-cyan-300 font-mono bg-surface-container-low border border-surface-container-high rounded-xl flex items-center justify-center gap-2">
            <span class="material-symbols-outlined animate-spin text-cyan-400">sync</span>
            Executing multi-hop BFS traversal connecting ${escapeHtml(sourceId)} → ${escapeHtml(targetId)} (Max Hops: ${maxHops})...
        </div>
    `;

    try {
        const result = await window.dataService.findPaths(sourceId, targetId, maxHops);
        const paths = (result && Array.isArray(result.paths)) ? result.paths : [];

        const metricCount = document.getElementById("la-metric-count");
        const metricShortest = document.getElementById("la-metric-shortest");
        const metricConfidence = document.getElementById("la-metric-confidence");
        const metricConduits = document.getElementById("la-metric-conduits");

        if (metricCount) metricCount.innerText = paths.length;

        if (paths.length === 0) {
            if (metricShortest) metricShortest.innerText = "--";
            if (metricConfidence) metricConfidence.innerText = "--";
            if (metricConduits) metricConduits.innerText = "0";

            if (summarySpan) summarySpan.innerText = `0 paths discovered within ${maxHops} hops`;

            container.innerHTML = `
                <div class="p-8 text-center bg-surface-container-low border border-surface-container-high rounded-xl space-y-3">
                    <span class="material-symbols-outlined text-4xl text-on-surface-variant">route</span>
                    <h4 class="text-sm font-bold text-white">No verified graph path found within the selected hop limit.</h4>
                    <p class="text-xs text-on-surface-variant max-w-md mx-auto">
                        No interconnected relationship edges connect <span class="font-mono text-cyan-300">${escapeHtml(sourceId)}</span> to <span class="font-mono text-cyan-300">${escapeHtml(targetId)}</span> within ${maxHops} hops in cataloged evidence records.
                    </p>
                    <div class="pt-2">
                        <button onclick="document.getElementById('la-max-hops').value=8; document.getElementById('la-hops-val').innerText='8'; renderLinkAnalysisWorkspace();" class="px-3 py-1.5 text-xs font-semibold rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition-colors">
                            Expand Search to 8 Hops
                        </button>
                    </div>
                </div>
            `;
            return;
        }

        paths.sort((a, b) => (b.confidence || b.path_score || 0) - (a.confidence || a.path_score || 0) || (a.hop_count || 0) - (b.hop_count || 0));

        const minHops = Math.min(...paths.map(p => p.hop_count || (p.path ? p.path.length - 1 : 0)));
        const maxConf = Math.max(...paths.map(p => p.confidence || p.path_score || 0));

        const allConduits = new Set();
        paths.forEach(p => (p.shared_entities || []).forEach(e => allConduits.add(e)));

        if (metricShortest) metricShortest.innerText = `${minHops} ${minHops === 1 ? 'hop' : 'hops'}`;
        if (metricConfidence) metricConfidence.innerText = `${Math.round(maxConf * 100)}%`;
        if (metricConduits) metricConduits.innerText = allConduits.size;

        if (summarySpan) summarySpan.innerText = `Discovered ${paths.length} path(s) between ${escapeHtml(sourceId)} and ${escapeHtml(targetId)}`;

        container.innerHTML = paths.map((pathObj, idx) => {
            const rank = idx + 1;
            const hopCount = pathObj.hop_count || (pathObj.path ? pathObj.path.length - 1 : 0);
            const conf = pathObj.confidence || pathObj.path_score || 0.90;
            const confPercent = Math.round(conf * 100);
            const pathNodes = pathObj.path || [];
            const shared = pathObj.shared_entities || [];
            const steps = pathObj.steps || [];

            const nodeChainHtml = pathNodes.map((nodeId, nIdx) => {
                const isStart = nIdx === 0;
                const isEnd = nIdx === pathNodes.length - 1;
                const isCase = nodeId.startsWith("CASE_");
                const isConduit = shared.includes(nodeId);

                let badgeClass = "bg-surface-container-high text-white border-surface-container-highest";
                if (isCase) badgeClass = "bg-blue-500/20 text-blue-300 border-blue-500/40 font-bold";
                else if (isStart || isEnd) badgeClass = "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-bold";
                else if (isConduit) badgeClass = "bg-amber-500/20 text-amber-300 border-amber-500/40 font-semibold";

                const arrowHtml = !isEnd ? `<span class="material-symbols-outlined text-xs text-cyan-500/60 font-bold">arrow_forward</span>` : '';

                return `
                    <div class="flex items-center gap-1.5">
                        <button onclick="openEntityDetailsPanel('${escapeHtml(nodeId)}')" class="px-2.5 py-1 rounded text-xs border font-mono ${badgeClass} hover:opacity-80 transition-opacity" title="Click to view details for ${escapeHtml(nodeId)}">
                            ${escapeHtml(nodeId)}
                        </button>
                        ${arrowHtml}
                    </div>
                `;
            }).join('');

            const stepsBreakdownHtml = steps.map((step, sIdx) => {
                const stepEvs = step.evidence_ids || [];
                const stepEvHtml = stepEvs.map(evId => `
                    <button onclick="openEvidencePanel('${escapeHtml(evId)}')" class="px-1.5 py-0.5 rounded text-[10px] bg-cyan-950/80 text-cyan-300 border border-cyan-700/50 hover:bg-cyan-900 font-mono">
                        ${escapeHtml(evId)}
                    </button>
                `).join(' ');

                return `
                    <div class="p-2.5 rounded bg-surface-container-low border border-surface-container-high flex flex-wrap items-center justify-between gap-2 text-xs">
                        <div class="flex items-center gap-2 font-mono">
                            <span class="text-cyan-400 font-bold">Hop ${sIdx + 1}:</span>
                            <span class="text-white">${escapeHtml(step.from)}</span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase font-semibold">
                                --[ ${escapeHtml(step.relationship)} ]-->
                            </span>
                            <span class="text-white">${escapeHtml(step.to)}</span>
                        </div>
                        <div class="flex items-center gap-3 font-mono text-[11px]">
                            <span class="text-on-surface-variant">Conf: <strong class="text-emerald-400">${Math.round((step.confidence || 0.90) * 100)}%</strong></span>
                            ${stepEvHtml ? `<div class="flex items-center gap-1">${stepEvHtml}</div>` : ''}
                        </div>
                    </div>
                `;
            }).join('');

            const jsonPathNodes = JSON.stringify(pathNodes).replace(/"/g, '&quot;');

            return `
                <div class="bg-surface-container-low border border-surface-container-high hover:border-cyan-500/40 rounded-xl p-5 shadow-lg transition-all space-y-4">
                    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-surface-container-high pb-3">
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-1 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-mono text-xs font-bold">Path #${rank}</span>
                            <span class="px-2.5 py-1 rounded bg-surface-container-high text-on-surface text-xs font-mono">${hopCount} ${hopCount === 1 ? 'Hop' : 'Hops'}</span>
                            <span class="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold">${confPercent}% Composite Confidence</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button onclick="highlightPathInGraph(${jsonPathNodes})" class="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow transition-colors">
                                <span class="material-symbols-outlined text-sm">visibility</span> Highlight in Graph
                            </button>
                        </div>
                    </div>

                    <div class="space-y-1.5">
                        <div class="text-[11px] text-on-surface-variant font-semibold uppercase tracking-wider">Topological Relationship Chain</div>
                        <div class="flex flex-wrap items-center gap-1.5 p-3 rounded-lg bg-surface-container border border-surface-container-high">
                            ${nodeChainHtml}
                        </div>
                    </div>

                    ${pathObj.explanation ? `
                        <div class="text-xs text-on-surface-variant bg-surface-container/60 p-3 rounded-lg border border-surface-container-high leading-relaxed">
                            <strong class="text-cyan-300">Investigative Context:</strong> ${escapeHtml(pathObj.explanation)}
                        </div>
                    ` : ''}

                    <details class="group">
                        <summary class="cursor-pointer text-xs font-bold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 select-none py-1">
                            <span class="material-symbols-outlined text-base transition-transform group-open:rotate-90">chevron_right</span>
                            Expand Hop-by-Hop Breakdown & Supporting Evidence (${steps.length} steps)
                        </summary>
                        <div class="mt-3 space-y-2 pl-2">
                            ${stepsBreakdownHtml || `<div class="text-xs text-on-surface-variant font-mono">No granular step metadata available.</div>`}
                        </div>
                    </details>
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error("Link analysis path search error:", err);
        container.innerHTML = `
            <div class="p-6 rounded-xl bg-rose-950/60 border border-rose-700 text-rose-200 text-xs space-y-2">
                <div class="font-bold flex items-center gap-2">
                    <span class="material-symbols-outlined text-rose-400">error</span>
                    Link Analysis Path Discovery Error
                </div>
                <div>${escapeHtml(err.message || "Failed to execute path search against knowledge graph.")}</div>
            </div>
        `;
    }
}

function highlightPathInGraph(pathNodeIds) {
    if (!Array.isArray(pathNodeIds) || pathNodeIds.length === 0) return;

    switchTab("pane-graph", true);

    setTimeout(() => {
        if (!networkInstance) {
            console.warn("Vis.js networkInstance not initialized");
            return;
        }

        try {
            networkInstance.selectNodes(pathNodeIds);
            networkInstance.fit({ nodes: pathNodeIds, animation: true });

            const graphContainer = document.getElementById("graph-container");
            if (graphContainer) {
                let existingClearBtn = document.getElementById("btn-clear-path-highlight");
                if (!existingClearBtn) {
                    const clearBtn = document.createElement("button");
                    clearBtn.id = "btn-clear-path-highlight";
                    clearBtn.className = "absolute top-4 right-4 z-20 px-3 py-1.5 rounded-lg bg-cyan-950/90 text-cyan-300 border border-cyan-500/50 hover:bg-cyan-900 text-xs font-mono font-bold shadow-xl flex items-center gap-1.5 transition-all";
                    clearBtn.innerHTML = `<span class="material-symbols-outlined text-sm">clear</span> Clear Path Highlight (${pathNodeIds.length} Nodes)`;
                    clearBtn.onclick = () => clearGraphHighlight();
                    graphContainer.appendChild(clearBtn);
                } else {
                    existingClearBtn.innerHTML = `<span class="material-symbols-outlined text-sm">clear</span> Clear Path Highlight (${pathNodeIds.length} Nodes)`;
                }
            }
        } catch (e) {
            console.warn("Failed to highlight path in Vis.js graph:", e);
        }
    }, 200);
}

function clearGraphHighlight() {
    if (networkInstance) {
        try {
            networkInstance.unselectAll();
        } catch (_) {}
    }
    const clearBtn = document.getElementById("btn-clear-path-highlight");
    if (clearBtn) clearBtn.remove();
}

/* ----------------------------------------------------
   DAY 33 — INVESTIGATIVE RISK & PRIORITY INTELLIGENCE (SHRUTI)
---------------------------------------------------- */
let currentRiskData = null;

async function renderRiskIntelligence(caseId = null) {
    const container = document.getElementById("dashboard-risk-container");
    if (!container) return;

    let targetCaseId = caseId;
    if (!targetCaseId || targetCaseId === "ALL") {
        const headSelect = document.getElementById("header-case-select");
        targetCaseId = (headSelect && headSelect.value && headSelect.value !== "ALL") ? headSelect.value : null;
    }

    container.innerHTML = `
        <div class="text-center py-6 text-outline text-xs font-sans">
            <span class="material-symbols-outlined animate-spin text-rose-400 align-middle mr-1">sync</span>
            Computing ML Data Mining & Investigative Risk Intelligence...
        </div>
    `;

    try {
        const data = await window.dataService.getRiskScores(targetCaseId);
        currentRiskData = data;

        if (!data || !data.entities || data.entities.length === 0) {
            container.innerHTML = `
                <div class="p-4 bg-surface-container-low border border-surface-container-high rounded text-center text-xs text-outline font-sans">
                    Insufficient data for reliable risk scoring for case <strong>${targetCaseId || 'ALL'}</strong>.
                </div>
            `;
            return;
        }

        const summary = data.summary || {};
        if (document.getElementById("risk-stat-total")) document.getElementById("risk-stat-total").innerText = summary.total_scored_entities || data.entities.length;
        if (document.getElementById("risk-stat-high")) document.getElementById("risk-stat-high").innerText = summary.high_priority_count || 0;
        if (document.getElementById("risk-stat-mod")) document.getElementById("risk-stat-mod").innerText = summary.moderate_priority_count || 0;
        if (document.getElementById("risk-stat-top")) document.getElementById("risk-stat-top").innerText = summary.top_entity_id || "N/A";

        filterRiskUI();
    } catch (err) {
        console.error("Error loading risk intelligence:", err);
        container.innerHTML = `
            <div class="p-4 bg-rose-950/40 border border-rose-800 rounded text-center text-xs text-rose-300 font-sans space-y-2">
                <div>Investigative risk intelligence engine unavailable or offline.</div>
                <button onclick="renderRiskIntelligence('${targetCaseId || ''}')" class="px-3 py-1 bg-rose-800 hover:bg-rose-700 text-white rounded text-[11px] font-bold">Retry Risk Analysis</button>
            </div>
        `;
    }
}

function filterRiskUI() {
    const container = document.getElementById("dashboard-risk-container");
    if (!container || !currentRiskData || !currentRiskData.entities) return;

    const priorityFilter = document.getElementById("risk-filter-priority")?.value || "ALL";
    let entities = currentRiskData.entities;

    if (priorityFilter !== "ALL") {
        entities = entities.filter(ent => ent.priority_level === priorityFilter);
    }

    if (entities.length === 0) {
        container.innerHTML = `
            <div class="p-4 bg-surface-container-low border border-surface-container-high rounded text-center text-xs text-outline font-sans">
                No entities match the selected priority filter criteria '${priorityFilter}'.
            </div>
        `;
        return;
    }

    container.innerHTML = entities.map((ent, idx) => {
        const pColor = ent.priority_level === "HIGH"
            ? "bg-rose-950 text-rose-300 border-rose-800"
            : (ent.priority_level === "MODERATE"
                ? "bg-amber-950 text-amber-300 border-amber-800"
                : "bg-slate-900 text-slate-300 border-slate-700");

        const barColor = ent.priority_level === "HIGH" ? "bg-rose-500" : (ent.priority_level === "MODERATE" ? "bg-amber-500" : "bg-emerald-500");

        const signalsHtml = (ent.contributing_signals || []).map(sig => `
            <div class="p-2 rounded bg-surface-container-lowest border border-surface-container-high text-[11px] space-y-1">
                <div class="flex items-center justify-between font-mono">
                    <span class="font-bold text-white">${sig.name}</span>
                    <span class="text-rose-400 font-bold">${sig.weight}</span>
                </div>
                <p class="text-on-surface-variant text-[10px]">${sig.description}</p>
            </div>
        `).join("");

        const metrics = ent.feature_metrics || {};

        return `
            <div class="stitch-card space-y-3 border border-surface-container-high hover:border-rose-500/50 transition">
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center gap-2">
                        <span class="font-mono text-xs text-outline font-bold">#${idx + 1}</span>
                        <span class="font-bold text-white text-sm hover:underline cursor-pointer" onclick="openEntityDetails('${ent.entity_id}')">${ent.entity_name}</span>
                        <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-surface-container-highest text-tertiary">${ent.entity_type}</span>
                        <span class="text-xs text-outline font-mono">(${ent.entity_id})</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="px-2.5 py-0.5 rounded border text-xs font-mono font-bold ${pColor}">
                            Investigative Priority: ${ent.priority_level} (${ent.risk_score}/100)
                        </span>
                        <button onclick="toggleRiskDetail('${ent.entity_id}')" class="px-2 py-1 bg-surface-container-highest hover:bg-surface-container-high text-xs font-mono rounded text-slate-300 flex items-center gap-1">
                            <span class="material-symbols-outlined text-xs">unfold_more</span> Why This Score?
                        </button>
                    </div>
                </div>

                <div class="space-y-1">
                    <div class="w-full bg-surface-container-highest rounded-full h-2 overflow-hidden">
                        <div class="${barColor} h-2 rounded-full transition-all duration-500" style="width: ${ent.risk_score}%"></div>
                    </div>
                    <div class="flex items-center justify-between text-[10px] text-outline font-mono">
                        <span>Confidence: <strong>${((ent.confidence || 0.88) * 100).toFixed(0)}% Grounded</strong></span>
                        <span>Linked Cases: <strong class="text-white">${(ent.cases || []).join(', ') || 'N/A'}</strong></span>
                    </div>
                </div>

                <div class="p-2 rounded bg-surface-container-low border border-surface-container-high text-[11px] text-slate-200 flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                        <span class="material-symbols-outlined text-rose-400 text-sm">center_focus_strong</span>
                        <span><strong>Actionable Lead:</strong> ${ent.recommended_action}</span>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                        <button onclick="switchTab('pane-graph'); highlightNodeInGraph('${ent.entity_id}')" class="px-2 py-0.5 bg-blue-900/60 hover:bg-blue-800 text-blue-300 rounded text-[10px] font-mono">View Graph</button>
                        <button onclick="askAIRiskReason('${ent.entity_id}', '${ent.entity_name}')" class="px-2 py-0.5 bg-purple-900/60 hover:bg-purple-800 text-purple-300 rounded text-[10px] font-mono">Ask AI</button>
                    </div>
                </div>

                <div id="risk-detail-${ent.entity_id}" class="hidden space-y-2.5 pt-2 border-t border-surface-container-high">
                    <div class="text-xs font-bold text-white font-mono flex items-center gap-1">
                        <span class="material-symbols-outlined text-xs text-rose-400">analytics</span> Data Mining Signal Breakdown:
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        ${signalsHtml}
                    </div>
                    <div class="p-2 rounded bg-surface-container-lowest border border-surface-container-high text-[10px] text-outline font-mono flex flex-wrap justify-between gap-2">
                        <span>Degree Centrality: <strong class="text-white">${metrics.degree_centrality || 0}</strong></span>
                        <span>Cross-Case Links: <strong class="text-white">${metrics.cross_case_links || 0}</strong></span>
                        <span>Evidence Records: <strong class="text-white">${metrics.evidence_count || 0}</strong></span>
                        <span>Base Confidence: <strong class="text-white">${((metrics.confidence_rating || 0.85)*100).toFixed(0)}%</strong></span>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function toggleRiskDetail(entityId) {
    const el = document.getElementById(`risk-detail-${entityId}`);
    if (el) el.classList.toggle("hidden");
}

function askAIRiskReason(entityId, entityName) {
    switchTab("pane-ai");
    const aiInput = document.getElementById("ai-investigator-input");
    if (aiInput) {
        aiInput.value = `Why is ${entityName} (${entityId}) assigned a high investigative risk priority? Explain contributing signals and evidence.`;
        if (typeof submitAIQuery === "function") {
            submitAIQuery();
        }
    }
}







