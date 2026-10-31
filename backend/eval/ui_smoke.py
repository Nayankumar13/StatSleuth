"""End-to-end UI smoke test with Playwright (needs the server on :8000 serving frontend/dist).
Run: python -m eval.ui_smoke   -> prints PASS/FAIL per step and saves screenshots to docs/screens/
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parents[2] / "docs" / "screens"
OUT.mkdir(parents=True, exist_ok=True)
fails = []


def step(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1360, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    pg.goto(BASE)
    step("home loads", pg.locator("h1").inner_text().startswith("Find the numbers"))
    step("analyse disabled when empty", pg.get_by_role("button", name="Check statistics").is_disabled())
    pg.screenshot(path=str(OUT / "1_analyse.png"))

    pg.get_by_role("button", name="B", exact=True).click()
    pg.wait_for_function("document.querySelector('textarea').value.length > 100")
    step("demo B loaded", "t(58) = 1.40" in pg.locator("textarea").input_value())
    pg.get_by_role("button", name="Check statistics").click()
    pg.wait_for_url("**/report/*")
    pg.wait_for_selector(".verdict")
    step("report shows serious verdict", "serious" in pg.locator(".verdict").inner_text())
    step("6 serious stat tile", pg.locator(".stat.gross b").inner_text() == "6")
    step("highlights rendered", pg.locator("mark.hl.gross").count() >= 5)
    pg.screenshot(path=str(OUT / "2_report.png"), full_page=True)

    pg.locator(".finding-head").first.click()
    step("finding expands", pg.locator(".finding-body").count() == 1)
    pg.locator("mark.hl.gross").first.click()
    pg.get_by_role("tab", name="All").click()
    step("all filter shows more", pg.locator(".finding").count() >= 11)
    pg.locator(".finding.gross", has_text="t(58) = 1.40").first.locator(".finding-head").click()
    step("range bar drawn", pg.locator(".rangebar").count() == 1)
    pg.screenshot(path=str(OUT / "3_finding_detail.png"), full_page=True)

    # export link works
    href = pg.get_by_role("link", name="CSV").get_attribute("href")
    step("csv export", pg.request.get(BASE + href).text().startswith("id,check,status"))

    pg.get_by_role("link", name="Quick checks").click()
    pg.get_by_role("button", name="Test").click()
    pg.wait_for_selector(".result")
    step("grim tool: 5.19 n=28 impossible", "NOT possible" in pg.locator(".result").first.inner_text())
    pg.screenshot(path=str(OUT / "4_tools.png"))

    pg.get_by_role("link", name="History").click()
    pg.wait_for_selector("table")
    step("history lists report", pg.locator("tbody tr").count() >= 1)
    pg.screenshot(path=str(OUT / "5_history.png"))
    pg.once("dialog", lambda d: d.accept())
    n_before = pg.locator("tbody tr").count()
    pg.get_by_role("button", name="Delete").first.click()
    pg.wait_for_timeout(600)
    step("delete works", pg.locator("tbody tr").count() == n_before - 1 or pg.locator("text=No saved reports").count() == 1)

    # unsaved flow + error handling
    pg.goto(BASE)
    pg.locator("textarea").fill("t(28) = 2.20, p = .200")
    pg.get_by_label("Save report to history", exact=False).uncheck()
    pg.get_by_role("button", name="Check statistics").click()
    pg.wait_for_url("**/report/local")
    pg.wait_for_selector(".verdict")
    step("unsaved report works and has no export", pg.get_by_role("link", name="CSV").count() == 0)
    step("no console/page errors during normal use", not errors)
    errors.clear()
    pg.goto(BASE + "/report/doesnotexist")          # intentionally provokes one API 404
    pg.wait_for_selector(".errorbox")
    errors[:] = [e for e in errors if "404" not in e]
    step("404 report shows error", "not found" in pg.locator(".errorbox").inner_text().lower())

    pg.goto(BASE)
    pg.set_viewport_size({"width": 390, "height": 800})
    pg.screenshot(path=str(OUT / "6_mobile.png"), full_page=True)
    step("mobile has no horizontal scroll", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))

    step("no unexpected errors after error-page test", not errors)
    if errors:
        print(errors[:5])
    b.close()

print("\nFAILED:" if fails else "\nALL UI STEPS PASSED", fails or "")
sys.exit(1 if fails else 0)
