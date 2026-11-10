"""Run with Playwright installed and SAFEHOME_APP_PYTHON pointing at the app venv."""
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, quote, urlsplit

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
                청담동: {score: 45, category: 'safe', timestamp: Date.now()}
            }));
        """)
        page.route('https://dapi.kakao.com/v2/maps/sdk.js?*', lambda route: route.fulfill(
            content_type='application/javascript', body="""
            window.__mapCircles = [];
            window.kakao = {maps: {
                LatLng: class { constructor(lat, lng) { this.lat = lat; this.lng = lng; } },
                Map: class { setCenter() {} setLevel() {} panBy() {} },
                Circle: class {
                    constructor(options) { this.options = options; window.__mapCircles.push(this); }
                    setMap(map) { this.map = map; }
                    getPosition() { return this.options.center; }
                },
                CustomOverlay: class {
                    constructor(options) {
                        this.node = options.content;
                        this.setMap(options.map);
                    }
                    setMap(map) {
                        if (map) {
                            Object.assign(this.node.style, {
                                position: 'absolute', left: '50%', top: 'calc(50% + 85px)',
                                transform: 'translate(-50%, -100%)'
                            });
                            document.getElementById('map').append(this.node);
                        } else this.node.remove();
                    }
                },
                InfoWindow: class {
                    constructor(options) {
                        this.node = document.createElement('div');
                        this.node.className = 'map-fixture-popup';
                        if (typeof options.content === 'string') this.node.innerHTML = options.content;
                        else this.node.append(options.content);
                    }
                    open() { document.getElementById('map').append(this.node); }
                    close() { this.node.remove(); }
                },
                event: { addListener(target, name, handler) { target[name] = handler; } }
            }};
        """))

        def legacy_map_response(route):
            rows = route.fetch().json()
            legacy = next(row for row in rows if row['region'] == '청담동')
            legacy['score'] = 45
            legacy.pop('status')
            route.fulfill(json=rows)

        page.route('**/heatmap', legacy_map_response)
        page.goto(url + '/map', wait_until='domcontentloaded')
        expect(page.locator('#unknown-count')).not_to_have_text('0')
        count = int(page.locator('#unknown-count').inner_text())
        expect(page.locator('#safe-count')).to_have_text('0')
        expect(page.locator('#region-list .region-item.unknown')).to_have_count(count)
        expect(page.locator('#region-list .region-item').filter(has_text='청담동')).to_contain_text('판단 불가')
        expect(page.locator('#warning-count')).to_have_text('1')
        assert page.evaluate("window.__mapCircles.filter(circle => circle.options.fillColor === '#6b7280').length") == count
        page.get_by_role('button', name='☰').click()
        page.locator('#region-list .region-item').filter(has_text='강남구 삼성동').click()
        popup = page.get_by_role('dialog', name='강남구 삼성동')
        expect(popup.locator('[data-field="ratio"]')).to_have_text('72.5%')
        expect(popup.locator('[data-field="matched"]')).to_have_text('8건 / 최소 5건')
        expect(popup).to_contain_text('계약 기간')
        expect(popup).to_contain_text('마지막 정상 갱신')
        page.evaluate("window.regionData['관악구 삼성동'].circle.click()")
        expect(page.get_by_role('dialog', name='관악구 삼성동')).to_contain_text('판단 불가')
        page.evaluate("window.regionData['역삼동'].circle.click()")
        gray_popup = page.get_by_role('dialog', name='역삼동')
        expect(gray_popup.locator('[data-field="status"]')).to_have_text('판단 불가')
        expect(gray_popup.locator('[data-field="total"]')).to_have_text('43건')
        expect(gray_popup.locator('[data-field="matched"]')).to_have_text('2건 / 최소 5건')
        expect(gray_popup).to_contain_text('순수 전세가 3건 이상')
        expect(gray_popup).to_have_css('padding-bottom', '24px')
        box = gray_popup.bounding_box()
        assert 0 <= box['x'] and box['x'] + box['width'] <= 390 and 120 <= box['y']
        page.keyboard.press('Escape')
        expect(gray_popup).to_have_count(0)

        def map_search_response(route):
            region, = parse_qs(urlsplit(route.request.url).query)['region']
            assert region in {'등촌동', '강남구 삼성동'}
            route.fulfill(json={'properties': [{
                'name': f'{region} 아파트', 'address': f'{region} 123', 'price': '8억',
                'jeonse_price': '5.76억', 'jeonse_rate': 72, 'comparison_sample_count': 4,
            }]})

        page.route('**/analyze?*', map_search_response)
        page.route('**/api/real-transactions?*', lambda route: route.fulfill(json={'transactions': []}))
        page.evaluate("window.regionData['등촌동'].circle.click()")
        deungchon_popup = page.get_by_role('dialog', name='등촌동')
        deungchon_popup.get_by_role('link', name='개별 매물 조회').click()
        expect(page).to_have_url(f'{url}/searchscan?region={quote("등촌동")}#search-result')
        expect(deungchon_popup).to_have_count(0)
        property_card = page.locator('#search-result .property-item')
        expect(property_card).to_contain_text('등촌동 아파트')
        expect(property_card).to_contain_text('72%')
        expect(property_card).to_be_in_viewport()

        page.goto(url + '/map', wait_until='domcontentloaded')
        expect(page.locator('#unknown-count')).to_have_text(str(count))
        page.locator('#address-search').fill('강남구 삼성동')
        page.locator('#search-btn').click()
        expect(page.locator('#right-sidebar')).to_have_class('active')
        expect(page.locator('#real-tx-results')).to_contain_text('72%')
        expect(page.get_by_role('button', name='즐겨찾기 추가')).to_be_visible()
        expect(page.locator('.map-fixture-popup')).to_have_count(0)
        expect(page.locator('#unknown-count')).to_have_text(str(count))
        assert page.evaluate('window.__mapCircles.length') == count + 1
        assert not errors, errors
        page.close()
        browser.close()
    print('Browser checks passed: dashboard layout, 503 and retry, map evidence and gray markers.')
finally:
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
