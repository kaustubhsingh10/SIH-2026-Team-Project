"""CrimeGraph AI — Comprehensive Browser Error Log Capture.
"""

import sys
import time
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    print("\n=======================================================================")
    print(" BROWSER PAGE ERROR & CONSOLE CAPTURE LOG")
    print("=======================================================================\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.on("console", lambda msg: print(f"  [CONSOLE {msg.type.upper()}] {msg.text} (Location: {msg.location})"))
        page.on("pageerror", lambda err: print(f"  [PAGE ERROR DETAILED]\n    Message: {err.message}\n    Stack:   {err.stack}\n"))
        page.on("requestfailed", lambda req: print(f"  [REQUEST FAILED] {req.url}: {req.failure}"))

        print("Navigating to http://127.0.0.1:8000/web/...")
        response = page.goto("http://127.0.0.1:8000/web/", wait_until="networkidle")
        print(f"HTTP Status: {response.status}")
        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    main()
