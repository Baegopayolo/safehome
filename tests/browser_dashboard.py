"""Run with Playwright installed and SAFEHOME_APP_PYTHON pointing at the app venv."""
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

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
        page.close()

        # Keep the actual Flask response and browser UI, but replace the external
        # Kakao SDK so CI can observe circle color without any API credentials.
        page = browser.new_page(viewport={'width': 390, 'height': 850}, locale='ko-KR')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.add_init_script("""
            localStorage.setItem('regionJeonseRates', JSON.stringify({
                역삼동: {score: 45, category: 'safe', timestamp: Date.now()}
            }));
        """)
        page.route('https://dapi.kakao.com/v2/maps/sdk.js?*', lambda route: route.fulfill(
            content_type='application/javascript', body="""
            window.__mapCircles = [];
            window.kakao = {maps: {
                LatLng: class { constructor(lat, lng) { this.lat = lat; this.lng = lng; } },
                Map: class { setCenter() {} setLevel() {} },
                Circle: class {
                    constructor(options) { this.options = options; window.__mapCircles.push(this); }
                    setMap(map) { this.map = map; }
                    getPosition() { return this.options.center; }
                },
                InfoWindow: class {
                    constructor(options) {
                        this.node = document.createElement('div');
                        this.node.className = 'map-fixture-popup';
                        this.node.innerHTML = options.content;
                    }
                    open() { document.getElementById('map').append(this.node); }
                    close() { this.node.remove(); }
                },
                event: { addListener() {} }
            }};
        """))

        def legacy_map_response(route):
            rows = route.fetch().json()
            legacy = next(row for row in rows if row['region'] == '역삼동')
            legacy['score'] = 45
            legacy.pop('status')
            route.fulfill(json=rows)

        page.route('**/heatmap', legacy_map_response)
        page.goto(url + '/map', wait_until='domcontentloaded')
        expect(page.locator('#unknown-count')).not_to_have_text('0')
        count = int(page.locator('#unknown-count').inner_text())
        expect(page.locator('#safe-count')).to_have_text('0')
        expect(page.locator('#region-list .region-item.unknown')).to_have_count(count)
        expect(page.locator('#region-list .region-item').filter(has_text='역삼동')).to_contain_text('판단 불가')
        assert page.evaluate("window.__mapCircles.every(circle => circle.options.fillColor === '#6b7280')")
        assert page.evaluate('window.__mapCircles.length') == count

        def map_search_response(route):
            assert parse_qs(urlsplit(route.request.url).query)['region'] == ['강남구 삼성동']
            route.fulfill(json={'properties': [{'name': '비교 가능한 아파트', 'jeonse_rate': 72}]})

        page.route('**/analyze?*', map_search_response)
        page.locator('#address-search').fill('강남구 삼성동')
        page.locator('#search-btn').click()
        expect(page.locator('.map-fixture-popup')).to_contain_text('판단 불가')
        expect(page.locator('#real-tx-results')).to_contain_text('72%')
        expect(page.locator('#unknown-count')).to_have_text(str(count))
        assert page.evaluate("window.__mapCircles.at(-1).options.fillColor === '#6b7280'")
        assert not errors, errors
        page.close()
        browser.close()
    print('Browser checks passed: dashboard layout, 503 and retry, and gray markers for legacy map scores.')
finally:
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
