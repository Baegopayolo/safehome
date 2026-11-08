"""Run with Playwright installed and SAFEHOME_APP_PYTHON pointing at the app venv."""
import os
from pathlib import Path
import subprocess
import sys

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
server = subprocess.Popen(
    [os.getenv('SAFEHOME_APP_PYTHON', sys.executable), '-B', str(ROOT/'tests/browser_fixture.py')],
    cwd=ROOT, stdout=subprocess.PIPE, text=True,
)
try:
    url = server.stdout.readline().strip()
    assert url.startswith('http://127.0.0.1:'), 'Flask fixture did not start'
    with sync_playwright() as playwright:
        channel = os.getenv('SAFEHOME_BROWSER_CHANNEL')
        browser = playwright.chromium.launch(**({'channel': channel} if channel else {}))
        for width in (390, 1280):
            page = browser.new_page(viewport={'width': width, 'height': 850}, locale='ko-KR')
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url, wait_until='domcontentloaded')
            expect(page.locator('#transaction-count')).to_have_text('1건')
            expect(page.locator('#region-chart li')).to_have_count(25)
            expect(page.locator('#trend-chart li')).to_have_count(12)
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors, errors
            page.close()
        page = browser.new_page(viewport={'width': 390, 'height': 850})
        endpoint = '**/api/dashboard/*'
        page.route(endpoint, lambda route: route.fulfill(status=503, json={'status': 'unavailable'}))
        page.goto(url, wait_until='domcontentloaded')
        expect(page.locator('#data-status')).to_contain_text('통계를 불러오지 못했습니다')
        expect(page.locator('#region-chart li')).to_have_count(0)
        expect(page.locator('#transaction-count')).to_have_text('—')
        page.unroute(endpoint)
        page.locator('#retry-stats').click()
        expect(page.locator('#transaction-count')).to_have_text('1건')
        expect(page.locator('#trend-chart li')).to_have_count(12)
        browser.close()
    print('Browser checks passed: 390px and desktop layout, 503 and retry.')
finally:
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
