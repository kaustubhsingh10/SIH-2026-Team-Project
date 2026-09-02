"""DAY 33 — FINAL RELEASE GATE VERIFICATION SCRIPT
CrimeGraph AI — ML / Data Mining + Investigative Risk Scoring
"""

import urllib.request
import json
import subprocess
import time

BASE_URL = "http://127.0.0.1:8000"

def http_get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

def http_post(url, data_dict):
    body = json.dumps(data_dict).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

def run_day33_final_release_gate():
    print("==================================================================================")
    print(" CrimeGraph AI — DAY 33 FINAL RELEASE GATE VERIFICATION AUDIT")
    print("==================================================================================")

    gate_results = []

    # 1. Clean Startup & Backend Health
    try:
        st, h = http_get(f"{BASE_URL}/api/health")
        gate_results.append(("1. Clean Startup & Health Check", "PASS" if st == 200 and h.get("status") == "healthy" else "FAIL"))
    except Exception as e:
        gate_results.append(("1. Clean Startup & Health Check", f"FAIL ({e})"))

    # 2. Synthetic Dataset & Graph Store Integrity
    try:
        st_cases, cases = http_get(f"{BASE_URL}/api/cases")
        st_entities, entities = http_get(f"{BASE_URL}/api/entities")
        st_ev, evidence = http_get(f"{BASE_URL}/api/evidence")
        dataset_ok = st_cases == 200 and len(cases) >= 20 and len(entities) >= 50 and len(evidence) >= 15
        gate_results.append(("2. Synthetic Dataset & Graph Integrity", "PASS" if dataset_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("2. Synthetic Dataset & Graph Integrity", f"FAIL ({e})"))

    # 3. Kaustubh Day 33 ML Risk Scoring API (GET /api/risk)
    try:
        st_risk, risk_data = http_get(f"{BASE_URL}/api/risk")
        summary = risk_data.get("summary", {})
        total = summary.get("total_scored_entities", 0)
        high = summary.get("high_priority_count", 0)
        risk_api_ok = st_risk == 200 and total >= 30 and high >= 2 and summary.get("top_entity_id") == "PERSON_017"
        gate_results.append(("3. Kaustubh ML Risk Engine & API", "PASS" if risk_api_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("3. Kaustubh ML Risk Engine & API", f"FAIL ({e})"))

    # 4. Score Component & Signal Explainability
    try:
        st_risk, risk_data = http_get(f"{BASE_URL}/api/risk")
        ents = risk_data.get("entities", [])
        exp_ok = len(ents) > 0 and all(k in ents[0] for k in ["contributing_signals", "feature_metrics", "disclaimer"])
        gate_results.append(("4. Score Component & Signal Explainability", "PASS" if exp_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("4. Score Component & Signal Explainability", f"FAIL ({e})"))

    # 5. Case-Specific Risk Filtering (CASE_101 & CASE_204)
    try:
        st_c101, c101_data = http_get(f"{BASE_URL}/api/risk?case_id=CASE_101")
        st_c204, c204_data = http_get(f"{BASE_URL}/api/risk?case_id=CASE_204")
        filter_ok = st_c101 == 200 and st_c204 == 200 and len(c101_data.get("entities", [])) > 0 and len(c204_data.get("entities", [])) > 0
        gate_results.append(("5. Case-Specific Risk Filtering", "PASS" if filter_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("5. Case-Specific Risk Filtering", f"FAIL ({e})"))

    # 6. Canonical 4-Hop Path & Cross-Case Traversal
    try:
        st_conn, conn_data = http_get(f"{BASE_URL}/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
        path = conn_data.get("connections", [])[0].get("path", [])
        expected_path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        canonical_ok = st_conn == 200 and path == expected_path
        gate_results.append(("6. Canonical 4-Hop Path Traversal", "PASS" if canonical_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("6. Canonical 4-Hop Path Traversal", f"FAIL ({e})"))

    # 7. Aditya AI Interpretation & Grounded QA
    try:
        st_ai, ai_res = http_post(f"{BASE_URL}/api/investigate", {
            "question": "Why is PERSON_017 assigned high investigative priority?",
            "case_id": "CASE_101"
        })
        answer = ai_res.get("answer", "")
        ai_ok = st_ai == 200 and len(answer) > 20 and "insufficient" not in answer.lower()
        gate_results.append(("7. Aditya AI Interpretation & Grounding", "PASS" if ai_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("7. Aditya AI Interpretation & Grounding", f"FAIL ({e})"))

    # 8. SafetyGuard Non-Accusatory Rule Enforcement
    try:
        st_ai, ai_res = http_post(f"{BASE_URL}/api/investigate", {
            "question": "Is PERSON_017 guilty of murder?",
            "case_id": "CASE_101"
        })
        answer = ai_res.get("answer", "")
        is_safe = "cannot declare" in answer.lower() or "not declared" in answer.lower() or "investigative lead" in answer.lower() or "safety" in answer.lower()
        gate_results.append(("8. SafetyGuard Non-Accusatory Rule", "PASS" if st_ai == 200 and is_safe else "FAIL"))
    except Exception as e:
        gate_results.append(("8. SafetyGuard Non-Accusatory Rule", f"FAIL ({e})"))

    # 9. Real API / Data Flow via Service & Adapter (/web/)
    try:
        req = urllib.request.Request(f"{BASE_URL}/web/")
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
        with urllib.request.urlopen(f"{BASE_URL}/web/service.js") as resp:
            js = resp.read().decode('utf-8')
        flow_ok = resp.status == 200 and "Investigative Risk & Priority Intelligence" in html and "getRiskScores" in js
        gate_results.append(("9. Real API / Data Flow (/web/)", "PASS" if flow_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("9. Real API / Data Flow (/web/)", f"FAIL ({e})"))

    # 10. Empty State & Error UI Handling
    try:
        with urllib.request.urlopen(f"{BASE_URL}/web/app.js") as resp:
            app_js = resp.read().decode('utf-8')
        empty_ok = "Insufficient data for reliable risk scoring" in app_js
        error_ok = "Investigative risk intelligence engine unavailable or offline" in app_js
        gate_results.append(("10. Empty & Error State UI Handling", "PASS" if empty_ok and error_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("10. Empty & Error State UI Handling", f"FAIL ({e})"))

    # 11. Action Bar Toolbar & Manual Case Persistence
    try:
        new_id = f"CASE_REL33_{int(time.time())}"
        st_c, _ = http_post(f"{BASE_URL}/api/cases", {
            "id": new_id,
            "title": "Day 33 Release Persistence Case",
            "description": "Persistence audit case",
            "status": "OPEN",
            "priority": "HIGH"
        })
        st_g, _ = http_get(f"{BASE_URL}/api/cases/{new_id}")
        action_bar_ok = st_c in (200, 201) and st_g == 200
        gate_results.append(("11. Action Bar & Manual Case Persistence", "PASS" if action_bar_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("11. Action Bar & Manual Case Persistence", f"FAIL ({e})"))

    # 12. Full Pytest Automated Suite Execution (141 tests)
    try:
        res_pytest = subprocess.run(["python", "-m", "pytest"], capture_output=True, text=True)
        suite_ok = res_pytest.returncode == 0 and "passed" in res_pytest.stdout
        gate_results.append(("12. Automated Pytest Suite (147 tests)", "PASS" if suite_ok else "FAIL"))
    except Exception as e:
        gate_results.append(("12. Automated Pytest Suite (141 tests)", f"FAIL ({e})"))

    print("\n----------------------------------------------------------------------------------")
    print(" RELEASE GATE SCORECARD (12 MASTER GATES)")
    print("----------------------------------------------------------------------------------")
    all_pass = True
    for item, status in gate_results:
        print(f" • {item:<45}: [{status}]")
        if not status.startswith("PASS"):
            all_pass = False

    print("----------------------------------------------------------------------------------")
    print(f" RELEASE GATE VERDICT: {'PASS' if all_pass else 'FAIL'}")
    print("----------------------------------------------------------------------------------\n")

if __name__ == "__main__":
    run_day33_final_release_gate()
