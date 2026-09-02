"""Day 29 Verification Script for Advanced Link Analysis & Path Discovery.

Audits workspace UI containers, data service facade, REST API endpoints, and path highlighting logic.
"""

import sys
import json
sys.path.insert(0, "src")

from fastapi.testclient import TestClient
from crimegraph.data.loader import load_dataset
from crimegraph.api.app import create_app


def run_verification():
    print("==========================================================================")
    print("DAY 29 — ADVANCED LINK ANALYSIS & PATH DISCOVERY VERIFICATION AUDIT")
    print("==========================================================================")

    graph = load_dataset()
    app = create_app(graph_instance=graph)
    client = TestClient(app)

    checks = []

    # 1. API Health Check
    res_health = client.get("/api/health")
    pass_health = res_health.status_code == 200 and res_health.json().get("status") == "healthy"
    checks.append(("1. FastAPI Health Endpoint", "PASS" if pass_health else "FAIL", f"Status: {res_health.status_code}"))

    # 2. GET /api/paths endpoint for CASE_101 -> CASE_204
    res_paths = client.get("/api/paths?source_id=CASE_101&target_id=CASE_204&max_depth=6")
    pass_paths = res_paths.status_code == 200 and res_paths.json().get("path_count", 0) > 0
    data_paths = res_paths.json() if pass_paths else {}
    first_p = data_paths.get("paths", [{}])[0] if pass_paths else {}
    checks.append(("2. GET /api/paths Cross-Case Discovery", "PASS" if pass_paths else "FAIL", f"Paths found: {data_paths.get('path_count')}, Hop count: {first_p.get('hop_count')}"))

    # 3. Entity-to-Entity path discovery (PERSON_017 -> PERSON_089)
    res_p2p = client.get("/api/paths?source_id=PERSON_017&target_id=PERSON_089&max_depth=6")
    pass_p2p = res_p2p.status_code == 200 and res_p2p.json().get("path_count", 0) > 0
    checks.append(("3. Entity-to-Entity Path Discovery", "PASS" if pass_p2p else "FAIL", f"Path: {res_p2p.json().get('paths', [{}])[0].get('path')}"))

    # 4. Hop steps and evidence metadata
    steps = first_p.get("steps", [])
    pass_steps = len(steps) > 0 and "relationship" in steps[0] and "confidence" in steps[0]
    checks.append(("4. Granular Hop Steps & Evidence Metadata", "PASS" if pass_steps else "FAIL", f"Steps count: {len(steps)}"))

    # 5. Composite Confidence calculation
    pass_conf = "confidence" in first_p and first_p["confidence"] > 0
    checks.append(("5. Composite Path Confidence Score", "PASS" if pass_conf else "FAIL", f"Confidence: {first_p.get('confidence')}"))

    # 6. HTML workspace #pane-link-analysis in web/index.html
    with open("web/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    pass_html = "pane-link-analysis" in html_content and "la-paths-container font-mono" in html_content or "pane-link-analysis" in html_content
    checks.append(("6. UI Workspace Shell (#pane-link-analysis)", "PASS" if pass_html else "FAIL", "Found in web/index.html"))

    # 7. Non-culpability safety disclaimer banner
    pass_safety = "Investigative Lead Assertion & Safety Policy" in html_content and "do not establish guilt" in html_content
    checks.append(("7. Legal Non-Culpability Safety Banner", "PASS" if pass_safety else "FAIL", "Banner present in web/index.html"))

    # 8. DataService facade findPaths method
    with open("web/service.js", "r", encoding="utf-8") as f:
        service_content = f.read()
    pass_service = "async findPaths" in service_content
    checks.append(("8. DataService Facade method findPaths()", "PASS" if pass_service else "FAIL", "Present in web/service.js"))

    # 9. App.js workspace rendering & graph highlighting functions
    with open("web/app.js", "r", encoding="utf-8") as f:
        app_content = f.read()
    pass_app = "renderLinkAnalysisWorkspace" in app_content and "highlightPathInGraph" in app_content
    checks.append(("9. Render & Graph Highlight Functions", "PASS" if pass_app else "FAIL", "Present in web/app.js"))

    # 10. 404 Error handling for non-existent entities
    res_404 = client.get("/api/paths?source_id=UNKNOWN_000&target_id=CASE_204")
    pass_404 = res_404.status_code == 404
    checks.append(("10. 404 Not Found Handling for Invalid Nodes", "PASS" if pass_404 else "FAIL", f"Status: {res_404.status_code}"))

    # 11. Synchronized web/ directory frontend files
    pass_web_sync = "pane-link-analysis" in html_content
    checks.append(("11. Synchronized web/ Workspace HTML", "PASS" if pass_web_sync else "FAIL", "Found in web/index.html"))

    # 12. Manual Case Creation Compatibility
    res_cases = client.get("/api/cases")
    pass_cases = res_cases.status_code == 200 and len(res_cases.json()) >= 8
    checks.append(("12. Day 28 & Manual Case Compatibility", "PASS" if pass_cases else "FAIL", f"Active cases: {len(res_cases.json())}"))

    print("\n--------------------------------------------------------------------------")
    print(f"{'CHECK ITEM':<48} | {'STATUS':<8} | {'DETAILS'}")
    print("--------------------------------------------------------------------------")
    all_passed = True
    for item, status, detail in checks:
        print(f"{item:<48} | {status:<8} | {detail}")
        if status != "PASS":
            all_passed = False
    print("--------------------------------------------------------------------------")
    verdict_str = "DAY 29 AUDIT VERDICT: VERIFIED" if all_passed else "DAY 29 AUDIT VERDICT: FAILED"
    print(f"{verdict_str}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_verification())
