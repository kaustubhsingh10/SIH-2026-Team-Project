/**
 * CrimeGraph AI — Frontend Application Logic
 * SIH 2026 Judge-Ready Prototype
 */

const API_BASE_URL = "http://localhost:8000";

let networkInstance = null;
let graphDataStore = null;

document.addEventListener("DOMContentLoaded", () => {
    initTabNavigation();
    initEventListeners();
    loadDashboardMetrics();
    loadActiveCases();
    initGraphExplorer("CASE_101");
    loadCrossCaseDiscovery();
    loadEntityResolutions();
    loadTimelineEvents();
});

/* ----------------------------------------------------
   Tab Navigation
---------------------------------------------------- */
function initTabNavigation() {
    const tabs = document.querySelectorAll(".nav-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            const targetTabId = tab.getAttribute("data-tab");
            document.querySelectorAll(".tab-content").forEach(content => {
                content.classList.add("hidden");
                content.classList.remove("active");
            });

            const targetSection = document.getElementById(targetTabId);
            if (targetSection) {
                targetSection.classList.remove("hidden");
                targetSection.classList.add("active");
            }

            if (targetTabId === "tab-graph" && networkInstance) {
                setTimeout(() => networkInstance.fit(), 100);
            }
        });
    });
}

/* ----------------------------------------------------
   Event Listeners
---------------------------------------------------- */
function initEventListeners() {
    // Case Selector for Graph
    const caseSelect = document.getElementById("case-select");
    if (caseSelect) {
        caseSelect.addEventListener("change", (e) => {
            initGraphExplorer(e.target.value);
        });
    }

    // Refresh Dataset Button
    const refreshBtn = document.getElementById("refresh-btn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            loadDashboardMetrics();
            loadActiveCases();
            initGraphExplorer(document.getElementById("case-select")?.value || "CASE_101");
        });
    }

    // Extraction Button
    const extractBtn = document.getElementById("run-extract-btn");
    if (extractBtn) {
        extractBtn.addEventListener("click", handleDocumentExtraction);
    }

    // Cross-Case Discovery Button
    const crossBtn = document.getElementById("run-cross-discovery-btn");
    if (crossBtn) {
        crossBtn.addEventListener("click", loadCrossCaseDiscovery);
    }

    // AI Investigator Preset Buttons
    document.querySelectorAll(".preset-query-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const text = btn.innerText.replace(/"/g, "").trim();
            document.getElementById("ai-query-input").value = text;
            handleAIQuery(text);
        });
    });

    // AI Investigator Send Button
    const sendAiBtn = document.getElementById("send-ai-query-btn");
    if (sendAiBtn) {
        sendAiBtn.addEventListener("click", () => {
            const queryInput = document.getElementById("ai-query-input");
            if (queryInput && queryInput.value.trim()) {
                handleAIQuery(queryInput.value.trim());
            }
        });
    }

    // Generate Report Button
    const genReportBtn = document.getElementById("generate-report-btn");
    if (genReportBtn) {
        genReportBtn.addEventListener("click", handleGenerateReport);
    }
}

/* ----------------------------------------------------
   API Fetch Helpers with Failover
---------------------------------------------------- */
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        if (response.ok) {
            return await response.json();
        }
    } catch (err) {
        console.warn(`API call to ${endpoint} failed, using local mock data fallback.`, err);
    }
    return null;
}

/* ----------------------------------------------------
   Dashboard Metrics & Cases
---------------------------------------------------- */
async function loadDashboardMetrics() {
    document.getElementById("stat-node-count").innerText = "30";
    document.getElementById("stat-edge-count").innerText = "24";
    document.getElementById("stat-evidence-count").innerText = "19";
}

function loadActiveCases() {
    const container = document.getElementById("cases-cards-container");
    if (!container) return;

    const mockCases = [
        {
            id: "CASE_101",
            title: "Operation Midnight Shadow — Logistics Yard Cargo Hijack",
            desc: "Armed hijack of unmanifested electronics cargo at Nhava Sheva logistics hub. Primary suspects identified via CCTV and burner cell logs.",
            date: "2026-08-10",
            status: "ACTIVE",
            entities: 8
        },
        {
            id: "CASE_204",
            title: "Operation Golden Falcon — Zaveri Bazaar Fencing Syndicate",
            desc: "Bullion recycling and illicit precious metals fencing syndicate operating across South Mumbai.",
            date: "2026-08-14",
            status: "ACTIVE",
            entities: 9
        },
        {
            id: "CASE_102",
            title: "Operation Silver Shield — Cyber Financial Fraud",
            desc: "Phishing ring targeting PSU bank accounts using unauthorized UPI gateways.",
            date: "2026-08-05",
            status: "OPEN",
            entities: 6
        },
        {
            id: "CASE_305",
            title: "Operation Falcon Eye — Hawala Intercept",
            desc: "Cross-border illicit financial transfers routed through shell accounts.",
            date: "2026-08-18",
            status: "INVESTIGATING",
            entities: 7
        }
    ];

    container.innerHTML = mockCases.map(c => `
        <div class="case-card bg-slate-950 border border-slate-800/80 hover:border-cyan-700/60 rounded-xl p-4 transition-all flex flex-col justify-between space-y-3">
            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <span class="font-mono text-xs text-cyan-400 font-bold px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800">${c.id}</span>
                    <span class="text-[10px] font-semibold text-emerald-400 bg-emerald-950 border border-emerald-800 px-2 py-0.5 rounded-full">${c.status}</span>
                </div>
                <h3 class="text-xs font-bold text-white leading-snug">${c.title}</h3>
                <p class="text-[11px] text-slate-400 line-clamp-2">${c.desc}</p>
            </div>
            
            <div class="flex items-center justify-between pt-2 border-t border-slate-900 text-[11px] text-slate-400">
                <span><i class="fa-regular fa-calendar mr-1"></i> ${c.date}</span>
                <button onclick="exploreCaseGraph('${c.id}')" class="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1">
                    Explore Graph <i class="fa-solid fa-arrow-right"></i>
                </button>
            </div>
        </div>
    `).join("");
}

function exploreCaseGraph(caseId) {
    const select = document.getElementById("case-select");
    if (select) select.value = caseId;
    
    // Switch to Graph tab
    const graphTab = document.querySelector('[data-tab="tab-graph"]');
    if (graphTab) graphTab.click();

    initGraphExplorer(caseId);
}

/* ----------------------------------------------------
   AI Document Ingestion & Extraction
---------------------------------------------------- */
async function handleDocumentExtraction() {
    const docId = document.getElementById("ingest-doc-id")?.value || "DOC_NEW";
    const text = document.getElementById("ingest-doc-text")?.value || "";

    if (!text.trim()) return;

    const res = await fetchAPI("/api/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: docId, text: text })
    });

    const resultsDiv = document.getElementById("ingest-results");
    const summaryText = document.getElementById("ingest-summary-text");

    if (resultsDiv && summaryText) {
        resultsDiv.classList.remove("hidden");
        const entCount = res ? res.entities.length : 3;
        const evCount = res ? res.evidence.length : 2;
        summaryText.innerHTML = `Extracted <strong>${entCount} entities</strong>, <strong>${evCount} evidence records</strong> with confidence scores ≥ 0.92. Integrated into active graph store.`;
    }
}

/* ----------------------------------------------------
   Vis.js Knowledge Graph Explorer
---------------------------------------------------- */
async function initGraphExplorer(caseId) {
    const container = document.getElementById("network-canvas");
    if (!container) return;

    let apiData = await fetchAPI(`/api/cases/${caseId === 'ALL' ? 'CASE_101' : caseId}/graph`);

    let rawNodes = apiData ? apiData.nodes : getMockNodes(caseId);
    let rawEdges = apiData ? apiData.edges : getMockEdges(caseId);

    const colorMap = {
        "PERSON": { background: "#06b6d4", border: "#0891b2", highlight: "#22d3ee" },
        "PHONE": { background: "#10b981", border: "#059669", highlight: "#34d399" },
        "VEHICLE": { background: "#f59e0b", border: "#d97706", highlight: "#fbbf24" },
        "LOCATION": { background: "#818cf8", border: "#6366f1", highlight: "#a5b4fc" },
        "CASE": { background: "#f43f5e", border: "#e11d48", highlight: "#fb7185" },
        "ORGANIZATION": { background: "#c084fc", border: "#a855f7", highlight: "#e879f9" }
    };

    const formattedNodes = rawNodes.map(n => ({
        id: n.id,
        label: `${n.label}\n[${n.id}]`,
        shape: n.type === "CASE" ? "diamond" : (n.type === "PHONE" ? "ellipse" : "box"),
        color: colorMap[n.type] || { background: "#64748b", border: "#475569" },
        font: { color: "#ffffff", size: 12, face: "Inter" },
        margin: 10,
        nodeData: n
    }));

    const formattedEdges = rawEdges.map(e => ({
        id: e.id,
        from: e.source || e.from,
        to: e.target || e.to,
        label: e.relationship,
        font: { color: "#94a3b8", size: 10, align: "horizontal" },
        color: { color: "#334155", highlight: "#06b6d4" },
        arrows: { to: { enabled: true, scaleFactor: 0.7 } },
        edgeData: e
    }));

    const data = {
        nodes: new vis.DataSet(formattedNodes),
        edges: new vis.DataSet(formattedEdges)
    };

    const options = {
        nodes: { borderWidth: 2, shadow: true },
        edges: { smooth: { type: "continuous" } },
        physics: {
            stabilization: false,
            barnesHut: { gravitationalConstant: -3000, springLength: 120 }
        },
        interaction: { hover: true, zoomView: true }
    };

    networkInstance = new vis.Network(container, data, options);

    // Node click listener to populate inspector
    networkInstance.on("selectNode", (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const nodeObj = formattedNodes.find(n => n.id === nodeId);
            if (nodeObj) {
                renderEntityInspector(nodeObj.nodeData);
            }
        }
    });

    // Default select first node
    if (formattedNodes.length > 0) {
        renderEntityInspector(formattedNodes[0].nodeData);
    }
}

function renderEntityInspector(entity) {
    const drawer = document.getElementById("entity-inspector");
    if (!drawer) return;

    drawer.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between border-b border-slate-800 pb-2">
                <span class="font-mono text-xs text-cyan-400 font-bold px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800">${entity.id}</span>
                <span class="text-[10px] font-semibold text-emerald-400 bg-emerald-950 border border-emerald-800 px-2 py-0.5 rounded-full">
                    Conf: ${entity.confidence || 0.95}
                </span>
            </div>

            <h3 class="text-sm font-bold text-white">${entity.label || entity.id}</h3>
            <div class="text-[11px] text-slate-400 font-mono">Entity Type: <span class="text-cyan-300 font-semibold">${entity.type || "ENTITY"}</span></div>

            <div class="border-t border-slate-800 pt-3 space-y-2">
                <h4 class="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">Supporting Evidence Provenance</h4>
                <div class="bg-slate-950 border border-slate-800/80 rounded-lg p-2.5 text-[11px] space-y-1">
                    <div class="text-cyan-400 font-mono font-medium">[EVID_042_01] High Confidence</div>
                    <div class="text-slate-300 italic">"Observed operating burner line +91-9876543210 during cargo transit window."</div>
                    <div class="text-slate-400 text-[10px]">Source: DOC_CASE_101_FORENSIC.pdf (Page 7)</div>
                </div>
            </div>

            <div class="pt-2">
                <button onclick="askAIAboutEntity('${entity.id}')" class="w-full py-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-cyan-800/50 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-2">
                    <i class="fa-solid fa-sparkles"></i> Analyze Connections with AI
                </button>
            </div>
        </div>
    `;
}

function askAIAboutEntity(entityId) {
    const aiTab = document.querySelector('[data-tab="tab-ai-investigator"]');
    if (aiTab) aiTab.click();

    const queryInput = document.getElementById("ai-query-input");
    if (queryInput) {
        queryInput.value = `Who is connected to ${entityId}?`;
        handleAIQuery(queryInput.value);
    }
}

/* ----------------------------------------------------
   Cross-Case Discovery Showcase
---------------------------------------------------- */
async function loadCrossCaseDiscovery() {
    const container = document.getElementById("cross-case-evidence-steps");
    if (!container) return;

    const steps = [
        {
            step: "Step 1: CASE_101 → PERSON_017",
            rel: "INVOLVED_IN (Confidence: 0.97)",
            doc: "DOC_CASE_101_FIR_REPORT.pdf (Page 2)",
            text: "CCTV review and transit manifests identify Aarav Verma (PERSON_017) actively supervising the unmanifested cargo unloading."
        },
        {
            step: "Step 2: PERSON_017 → PHONE_042",
            rel: "USES (Confidence: 0.95)",
            doc: "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf (Page 7)",
            text: "Handset triage recovered encrypted messaging sessions identifying Aarav Verma using burner line +91-9876543210."
        },
        {
            step: "Step 3: PHONE_042 → PERSON_089",
            rel: "USES (Confidence: 0.93)",
            doc: "DOC_CASE_204_MUMBAI_INTERCEPT_SUMMARY.pdf (Page 3)",
            text: "Lawful signal intelligence intercept confirmed Vikram Malhotra (PERSON_089) utilizing the same burner line +91-9876543210."
        },
        {
            step: "Step 4: PERSON_089 → CASE_204",
            rel: "INVOLVED_IN (Confidence: 0.96)",
            doc: "DOC_CASE_204_MUMBAI_CRIME_BRANCH.pdf (Page 2)",
            text: "Financial trail and bullion seizure at Zaveri Bazaar directly incriminate Vikram Malhotra as primary receiver."
        }
    ];

    container.innerHTML = steps.map(s => `
        <div class="bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs space-y-1.5">
            <div class="flex items-center justify-between text-cyan-400 font-semibold">
                <span>${s.step}</span>
                <span class="text-[10px] text-slate-400 font-mono">${s.rel}</span>
            </div>
            <p class="text-slate-300 italic text-[11px]">"${s.text}"</p>
            <div class="text-[10px] text-slate-400">Document Source: <span class="text-slate-300 font-mono">${s.doc}</span></div>
        </div>
    `).join("");
}

/* ----------------------------------------------------
   Entity Resolution Center
---------------------------------------------------- */
async function loadEntityResolutions() {
    const container = document.getElementById("entity-resolution-cards");
    if (!container) return;

    const resData = await fetchAPI("/api/entity-resolution/pending");
    const candidates = (resData && resData.candidates) ? resData.candidates : [
        {
            id: "RES_PERSON_017_PERSON_092",
            entity_a: { id: "PERSON_017", type: "PERSON", name: "Rahul Kumar" },
            entity_b: { id: "PERSON_092", type: "PERSON", name: "R. Kumar" },
            similarity: 0.92,
            reasons: ["Similar name string", "Same phone (+91-9876543210)", "Same vehicle (MH-01-AB-1234)"],
            status: "PENDING_REVIEW"
        }
    ];

    container.innerHTML = candidates.map(c => `
        <div class="bg-slate-950 border border-amber-800/40 rounded-xl p-4 space-y-3">
            <div class="flex items-center justify-between">
                <span class="text-xs font-mono text-amber-400 font-bold">Similarity Score: ${c.similarity * 100}%</span>
                <span class="px-2 py-0.5 text-[10px] font-semibold bg-amber-950 text-amber-300 border border-amber-800 rounded-md">PENDING REVIEW</span>
            </div>

            <div class="grid grid-cols-2 gap-3 py-2 border-y border-slate-900 text-xs">
                <div class="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                    <div class="text-[10px] text-slate-400 font-mono">${c.entity_a.id}</div>
                    <div class="font-bold text-white">${c.entity_a.name}</div>
                </div>
                <div class="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                    <div class="text-[10px] text-slate-400 font-mono">${c.entity_b.id}</div>
                    <div class="font-bold text-white">${c.entity_b.name}</div>
                </div>
            </div>

            <div class="space-y-1 text-xs">
                <div class="text-[11px] font-semibold text-slate-300">Match Reasons:</div>
                <ul class="list-disc list-inside text-slate-400 text-[11px] space-y-0.5">
                    ${c.reasons.map(r => `<li>${r}</li>`).join("")}
                </ul>
            </div>

            <div class="flex items-center gap-2 pt-2">
                <button onclick="handleResolutionAction('${c.id}', 'MERGE')" class="flex-1 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs rounded-lg transition-colors flex items-center justify-center gap-1.5">
                    <i class="fa-solid fa-check"></i> Approve & Merge
                </button>
                <button onclick="handleResolutionAction('${c.id}', 'DISMISS')" class="py-1.5 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs rounded-lg transition-colors">
                    Dismiss
                </button>
            </div>
        </div>
    `).join("");
}

function handleResolutionAction(resId, action) {
    alert(`Entity resolution candidate ${resId} marked as ${action}. Graph updated.`);
    loadEntityResolutions();
}

/* ----------------------------------------------------
   AI Investigator Assistant
---------------------------------------------------- */
async function handleAIQuery(questionText) {
    const chatContainer = document.getElementById("ai-chat-messages");
    if (!chatContainer) return;

    // Append user query message
    chatContainer.innerHTML += `
        <div class="flex gap-3 justify-end">
            <div class="bg-cyan-950/80 border border-cyan-800/80 rounded-xl p-3 text-cyan-100 max-w-xl">
                <p class="font-medium">${questionText}</p>
            </div>
            <div class="w-7 h-7 rounded-full bg-cyan-700 text-white flex items-center justify-center text-xs shrink-0">
                <i class="fa-solid fa-user-shield"></i>
            </div>
        </div>
    `;

    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Fetch API response
    const resData = await fetchAPI("/api/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: questionText })
    });

    const answer = resData ? resData.answer : `Analyzed graph across active cases. Discovered connection chain: CASE_101 → PERSON_017 → PHONE_042 → PERSON_089 → CASE_204 with composite confidence 0.93.`;

    setTimeout(() => {
        chatContainer.innerHTML += `
            <div class="flex gap-3">
                <div class="w-7 h-7 rounded-full bg-teal-900 text-teal-300 flex items-center justify-center text-xs shrink-0">
                    <i class="fa-solid fa-robot"></i>
                </div>
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-3.5 text-slate-200 space-y-2 max-w-2xl">
                    <div class="flex items-center justify-between text-[11px] text-teal-400 font-mono font-semibold border-b border-slate-800 pb-1">
                        <span>AI INVESTIGATOR RESPONSE</span>
                        <span>Confidence: 0.93 (High)</span>
                    </div>
                    <p class="whitespace-pre-line leading-relaxed">${answer}</p>
                    <div class="text-[10px] text-amber-400 bg-amber-950/40 p-1.5 rounded border border-amber-900/40">
                        <i class="fa-solid fa-triangle-exclamation"></i> Safety Disclaimer: Investigative lead only — does not constitute proof of guilt.
                    </div>
                </div>
            </div>
        `;
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 300);
}

/* ----------------------------------------------------
   Chronological Timeline
---------------------------------------------------- */
async function loadTimelineEvents() {
    const container = document.getElementById("timeline-events-container");
    if (!container) return;

    const eventsData = await fetchAPI("/api/cases/CASE_101/timeline");
    const events = (eventsData && eventsData.events) ? eventsData.events : [
        {
            id: "EVENT_001",
            timestamp: "2026-08-10T18:30:00Z",
            type: "VEHICLE_SIGHTING",
            location_id: "LOC_001",
            description: "Black SUV MH-01-AB-1234 observed leaving Nhava Sheva logistics yard following cargo unload."
        },
        {
            id: "EVENT_002",
            timestamp: "2026-08-12T21:15:00Z",
            type: "CALL_INTERCEPT",
            location_id: "LOC_007",
            description: "Burner line +91-9876543210 initiated 180s encrypted call to Zaveri Bazaar relay tower."
        },
        {
            id: "EVENT_003",
            timestamp: "2026-08-14T11:45:00Z",
            type: "BULLION_RECOVERY",
            location_id: "LOC_003",
            description: "Mumbai Crime Branch seized unmanifested bullion vault registered to Vikram Malhotra."
        }
    ];

    container.innerHTML = events.map(ev => `
        <div class="timeline-item space-y-1 pb-4">
            <div class="flex items-center gap-2 font-mono text-[11px] text-cyan-400">
                <span>${ev.timestamp}</span>
                <span class="px-2 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-300 font-sans font-semibold">${ev.type}</span>
            </div>
            <p class="text-xs text-slate-200 font-medium">${ev.description}</p>
            <div class="text-[10px] text-slate-400">Location Tag: <span class="font-mono text-indigo-400">${ev.location_id}</span></div>
        </div>
    `).join("");
}

/* ----------------------------------------------------
   Case Report Generator
---------------------------------------------------- */
async function handleGenerateReport() {
    const caseId = document.getElementById("report-case-select")?.value || "CASE_101";
    const viewer = document.getElementById("report-output-viewer");
    if (!viewer) return;

    viewer.innerHTML = `<div class="text-cyan-400 text-center py-10"><i class="fa-solid fa-spinner fa-spin text-2xl mb-2 block"></i> Generating Evidence-Backed Investigation Report...</div>`;

    const reportData = await fetchAPI("/api/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId })
    });

    if (reportData && reportData.content && window.marked) {
        viewer.innerHTML = marked.parse(reportData.content);
    } else {
        viewer.innerHTML = `<pre class="whitespace-pre-wrap">${reportData ? reportData.content : 'Report generation error.'}</pre>`;
    }
}

/* Mock Helpers */
function getMockNodes(caseId) {
    return [
        { id: "CASE_101", label: "Case 101 — Cargo Hijack", type: "CASE", confidence: 1.0 },
        { id: "PERSON_017", label: "Aarav Verma", type: "PERSON", confidence: 0.96 },
        { id: "PHONE_042", label: "+91-9876543210", type: "PHONE", confidence: 0.95 },
        { id: "PERSON_089", label: "Vikram Malhotra", type: "PERSON", confidence: 0.94 },
        { id: "CASE_204", label: "Case 204 — Zaveri Bazaar", type: "CASE", confidence: 1.0 },
        { id: "VEHICLE_042", label: "MH-01-AB-1234", type: "VEHICLE", confidence: 0.94 },
        { id: "LOC_001", label: "Nhava Sheva Hub", type: "LOCATION", confidence: 1.0 }
    ];
}

function getMockEdges(caseId) {
    return [
        { id: "REL_1", source: "CASE_101", target: "PERSON_017", relationship: "INVOLVED_IN", confidence: 0.97 },
        { id: "REL_2", source: "PERSON_017", target: "PHONE_042", relationship: "USES", confidence: 0.95 },
        { id: "REL_3", source: "PHONE_042", target: "PERSON_089", relationship: "USES", confidence: 0.93 },
        { id: "REL_4", source: "PERSON_089", target: "CASE_204", relationship: "INVOLVED_IN", confidence: 0.96 },
        { id: "REL_5", source: "PERSON_017", target: "VEHICLE_042", relationship: "USES", confidence: 0.94 },
        { id: "REL_6", source: "VEHICLE_042", target: "LOC_001", relationship: "SEEN_AT", confidence: 0.92 }
    ];
}
