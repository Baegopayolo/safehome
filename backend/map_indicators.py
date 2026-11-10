"""Published Seoul apartment price comparisons, refreshed outside web requests."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median

import click
from sqlalchemy.exc import SQLAlchemyError

from dashboard import KST, iso
from dashboard_ops import collection_lock
from rental_collector import months_for, utcnow
from utils import (
    TransactionSourceError, _comparison_fields, _estimate_jeonse,
    _index_jeonse_candidates, get_heatmap_data, load_transaction_snapshot,
)


MIN_SALE_SAMPLES = 5
MAX_AGE = timedelta(hours=36)


def comparison_period(today):
    # Use three completed contract months and refresh for late reports/cancellations.
    end = today.replace(day=1) - timedelta(days=1)
    months = months_for(end, 3)
    return months, date.fromisoformat(f'{months[0][:4]}-{months[0][4:]}-01'), end


def collect_district(code, months, dongs):
    transactions = {'sale': [], 'rent': []}
    for kind, rows in transactions.items():
        for month in months:
            for tx in load_transaction_snapshot(kind, code, month):
                day = tx.get('거래일자', '').replace('-', '')
                if not day.startswith(month) or tx.get('지역코드') not in ('', None, code):
                    raise TransactionSourceError('WRONG_TRANSACTION_SCOPE')
                if tx.get('법정동') in dongs:
                    rows.append(tx)

    candidates = _index_jeonse_candidates(transactions['rent'])
    rates = defaultdict(list)
    sale_counts = Counter()
    seen = set()
    for sale in transactions['sale']:
        apt, dong = sale['아파트'], sale['법정동']
        price = sale['거래금액']
        fields = _comparison_fields(sale)
        if fields is None or not price or price <= 0:
            continue
        fingerprint = (apt, dong, fields, sale.get('층'), price)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        sale_counts[dong] += 1
        deposit, _ = _estimate_jeonse(sale, candidates.get((apt, dong), []))
        if deposit is not None:
            rates[dong].append(deposit / price * 100)

    return {
        dong: {
            'sale_transaction_count': sale_counts[dong],
            'sale_sample_count': len(rates[dong]),
            'score': round(median(rates[dong]), 2) if len(rates[dong]) >= MIN_SALE_SAMPLES else None,
        }
        for dong in sorted(dongs)
    }


def read_map_indicators(app, db, today=None, now=None):
    Snapshot = app.extensions['map_snapshot']
    today = today or datetime.now(KST).date()
    now = now or utcnow()
    _, start, end = comparison_period(today)
    locations = get_heatmap_data()
    try:
        snapshots = {row.region_code: row for row in Snapshot.query.all()}
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception('Map snapshots unavailable')
        snapshots = {}

    for location in locations:
        location['minimum_sale_sample_count'] = MIN_SALE_SAMPLES
        location['reason'] = 'uncollected' if location['dong'] else 'unmapped'
        snapshot = snapshots.get(location['region_code'])
        if not location['dong'] or snapshot is None:
            continue
        location['last_updated'] = iso(snapshot.collected_at)
        if ((snapshot.period_start, snapshot.period_end) != (start, end)
                or not timedelta(0) <= now - snapshot.collected_at <= MAX_AGE):
            location['reason'] = 'stale'
            continue
        result = snapshot.indicators.get(location['dong'])
        if result is None:
            continue
        location.update(result, period={'from': start.isoformat(), 'to': end.isoformat()})
        if result['score'] is None:
            location['reason'] = 'insufficient'
        else:
            location.update(status='available', reason=None)
    return locations


def register_map_indicators(app, db):
    class MapSnapshot(db.Model):
        __tablename__ = 'map_snapshots'
        region_code = db.Column(db.String(5), primary_key=True)
        period_start = db.Column(db.Date, nullable=False)
        period_end = db.Column(db.Date, nullable=False)
        collected_at = db.Column(db.DateTime, nullable=False)  # UTC naive
        indicators = db.Column(db.JSON, nullable=False)

    app.extensions['map_snapshot'] = MapSnapshot

    @app.cli.command('sync-map-indicators')
    @click.option('--region', 'selected', multiple=True, help='자치구 5자리 코드. 기본: 지도에 표시되는 자치구')
    def sync_map_indicators(selected):
        dongs_by_code = defaultdict(set)
        for location in get_heatmap_data():
            if location['dong']:
                dongs_by_code[location['region_code']].add(location['dong'])
        codes = sorted(set(selected or dongs_by_code))
        if set(codes) - dongs_by_code.keys():
            raise click.ClickException('지도에 표시되는 자치구 코드를 입력하세요.')

        months, start, end = comparison_period(datetime.now(KST).date())
        base_lock = Path(app.config.get('DASHBOARD_LOCK_PATH') or Path(app.instance_path)/'dashboard.lock')
        with collection_lock(base_lock.with_name('map-indicators.lock')):
            failures = 0
            for code in codes:
                try:
                    indicators = collect_district(code, months, dongs_by_code[code])
                    snapshot = db.session.get(MapSnapshot, code)
                    if snapshot is None:
                        snapshot = MapSnapshot(region_code=code)
                        db.session.add(snapshot)
                    snapshot.period_start, snapshot.period_end = start, end
                    snapshot.collected_at, snapshot.indicators = utcnow(), indicators
                    db.session.commit()
                except (TransactionSourceError, SQLAlchemyError) as error:
                    db.session.rollback()
                    failures += 1
                    reason = str(error) if isinstance(error, TransactionSourceError) else 'STORAGE_ERROR'
                    click.echo(f'{code}: 지도 집계 실패 ({reason})')
                else:
                    available = sum(row['score'] is not None for row in indicators.values())
                    click.echo(f'{code}: {available}/{len(indicators)}개 법정동 집계 완료')
            if failures:
                raise click.ClickException(f'{failures}/{len(codes)}개 자치구 갱신 실패. 이전 정상 집계를 보존했습니다.')
