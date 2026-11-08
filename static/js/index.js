/* A single summary response includes both chart series from the same DB query. */
function validDashboard(data) {
    const count = n => n === null || (Number.isSafeInteger(n) && n >= 0);
    if (!['complete','partial','stale','unavailable'].includes(data.status) ||
        !data.summary || !data.coverage || !data.period ||
        !count(data.summary.transaction_count) || !count(data.summary.region_count) ||
        !Number.isInteger(data.coverage.completed) || data.coverage.completed < 0 || data.coverage.completed > 300 ||
        data.coverage.expected !== 300 || !Array.isArray(data.regions) || data.regions.length !== 25 ||
        !Array.isArray(data.trends) || data.trends.length !== 12 ||
        !Array.isArray(data.coverage.stale) || !Array.isArray(data.coverage.failures)) return false;
    if (data.status !== 'unavailable' && (!data.last_updated || !Number.isFinite(Date.parse(data.last_updated)) ||
        !data.oldest_updated || !Number.isFinite(Date.parse(data.oldest_updated)))) return false;
    if (!data.regions.every(r => typeof r.name === 'string' && count(r.transaction_count) &&
        Number.isInteger(r.completed_months) && r.completed_months >= 0 && r.completed_months <= 12) ||
        !data.trends.every(r => /^\d{6}$/.test(r.month) && count(r.transaction_count) &&
        Number.isInteger(r.completed_regions) && r.completed_regions >= 0 && r.completed_regions <= 25)) return false;
    if (data.summary.transaction_count !== null) {
        const sum = rows => rows.reduce((n,r) => n + (r.transaction_count ?? 0), 0);
        if (sum(data.regions) !== data.summary.transaction_count || sum(data.trends) !== data.summary.transaction_count) return false;
    }
    return true;
}

function drawBars(id, rows, label, coverage, expected) {
    const chart = document.getElementById(id);
    chart.replaceChildren();
    const max = Math.max(1, ...rows.map(r => r.transaction_count ?? 0));
    for (const row of rows) {
        const li = document.createElement('li');
        const name = document.createElement('span');
        name.className = 'bar-label'; name.textContent = label(row);
        const track = document.createElement('span'); track.className = 'bar-track';
        track.setAttribute('aria-hidden','true');
        const fill = document.createElement('span'); fill.className = 'bar-fill';
        fill.style.width = ((row.transaction_count ?? 0) / max * 100) + '%';
        track.append(fill);
        const value = document.createElement('span'); value.className = 'bar-value';
        value.textContent = row.transaction_count === null ? '미수집' : row.transaction_count.toLocaleString('ko-KR') + '건';
        if (row[coverage] < expected && row.transaction_count !== null) {
            value.textContent += ` (일부 ${row[coverage]}/${expected})`;
            li.className = 'partial-bar';
        }
        li.append(name, track, value); chart.append(li);
    }
}

async function loadDashboardStats() {
    const root = document.querySelector('[data-dashboard-url]');
    if (!root) return;
    const get = id => document.getElementById(id);
    get('retry-stats').hidden = true;
    get('data-status').textContent = '공공데이터 현황을 불러오는 중입니다.';
    ['region-count','transaction-count','last-updated'].forEach(id => { get(id).textContent = '—'; });
    get('data-period').textContent = '';
    ['region-chart','trend-chart'].forEach(id => get(id).replaceChildren());
    ['region-chart-note','trend-chart-note'].forEach(id => { get(id).textContent = '불러오는 중입니다.'; });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
        const response = await fetch(root.dataset.dashboardUrl, {signal:controller.signal, cache:'no-store'});
        if (!response.ok) throw new Error('API failed');
        const data = await response.json();
        if (!validDashboard(data)) throw new Error('Invalid summary');
        root.dataset.state = data.status;
        const formatDate = date => new Intl.DateTimeFormat('ko-KR', {timeZone:'Asia/Seoul',
            year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(date));
        const labels = {complete:'전체 수집 완료', partial:'일부 수집 · 아래 수치는 수집분 합계입니다',
            stale:'갱신 지연 · 이전 정상 수집 자료를 표시합니다', unavailable:'수집 완료된 자료가 없습니다'};
        const recentDelayed = data.coverage.stale.filter(scope => scope.cadence === 'daily').length;
        const delayed = data.coverage.stale.length
            ? ` · 갱신 지연 ${data.coverage.stale.length}개 지역·월${recentDelayed ? ` (최근 3개월 ${recentDelayed}개)` : ''}` : '';
        const failed = data.coverage.failures.length ? ` · 재수집 실패 또는 진행 중 ${data.coverage.failures.length}개` : '';
        get('data-status').textContent = `${labels[data.status]} (${data.coverage.completed}/300개 지역·월)${delayed}${failed}`;
        get('data-period').textContent = `계약일 범위: ${data.period.from} ~ ${data.period.to} · 현재 월 포함`;
        if (data.status === 'unavailable') {
            get('last-updated').textContent = '수집 전';
            ['region-chart-note','trend-chart-note'].forEach(id => { get(id).textContent = '아직 정상 수집된 자료가 없어 차트를 표시하지 않습니다.'; });
            return;
        }
        get('region-count').textContent = data.summary.region_count.toLocaleString('ko-KR') + '개';
        get('transaction-count').textContent = data.summary.transaction_count.toLocaleString('ko-KR') + '건';
        get('last-updated').textContent = formatDate(data.last_updated);
        get('data-period').textContent += ` · 가장 오래된 갱신: ${formatDate(data.oldest_updated)}`;
        const note = data.summary.transaction_count === 0 ? '수집된 범위의 유효 전세 거래는 0건입니다.' : '일부 수집 범위는 따로 표시합니다.';
        ['region-chart-note','trend-chart-note'].forEach(id => { get(id).textContent = note; });
        drawBars('region-chart', data.regions, r=>r.name, 'completed_months',12);
        drawBars('trend-chart', data.trends, r=>r.month.slice(0,4)+'.'+r.month.slice(4), 'completed_regions',25);
    } catch (error) {
        root.dataset.state = 'error';
        get('data-status').textContent = '통계를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
        ['region-count','transaction-count','last-updated'].forEach(id => { get(id).textContent = '—'; });
        ['region-chart-note','trend-chart-note'].forEach(id => { get(id).textContent = '통계 조회에 실패했습니다.'; });
        get('retry-stats').hidden = false;
    } finally { clearTimeout(timeout); }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('retry-stats')?.addEventListener('click', loadDashboardStats);
    loadDashboardStats();
});
