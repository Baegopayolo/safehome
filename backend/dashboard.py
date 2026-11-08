"""Seoul apartment jeonse dashboard: all totals share one verified scope."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import click
from flask import jsonify
from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError
from dashboard_models import define_models
from rental_collector import SOURCE, months_for, utcnow, collect_scope, validate_scope
from utils import SEOUL_SIGUNGU_CODES, _get_api_key

KST = timezone(timedelta(hours=9))


def iso(value):
    return value.replace(tzinfo=timezone.utc).astimezone(KST).isoformat() if value else None


def build_dashboard(db, models, today=None, now=None, stale_hours=192):
    Region, Transaction, Stat, Log = models
    today = today or datetime.now(KST).date()
    now = now or utcnow()
    months = months_for(today)
    codes = list(SEOUL_SIGUNGU_CODES.values())
    # One grouped statement pairs coverage with actual rows, including successful
    # zero-result collections. Stale cached counts are never trusted silently.
    rows = db.session.query(Stat.region_code, Stat.deal_month, Stat.calculated_at,
        Stat.transaction_count, func.count(Transaction.id)).outerjoin(Transaction, and_(
            Transaction.region_code == Stat.region_code, Transaction.deal_month == Stat.deal_month,
            Transaction.cancelled.is_(False), Transaction.transaction_type == 'jeonse',
            Transaction.monthly_rent == 0)).filter(Stat.region_code.in_(codes), Stat.deal_month.in_(months)) \
        .group_by(Stat.region_code, Stat.deal_month, Stat.calculated_at, Stat.transaction_count).all()
    if any(cached != actual for _, _, _, cached, actual in rows):
        raise ValueError('AGGREGATE_INCONSISTENCY')
    covered = {(r, m): (stamp, count) for r, m, stamp, _, count in rows}
    latest_ids = db.session.query(func.max(Log.id)).filter(
        Log.region_code.in_(codes), Log.deal_month.in_(months)).group_by(Log.region_code, Log.deal_month)
    logs = Log.query.filter(Log.id.in_(latest_ids)).all()
    # Also surface refresh failures after an earlier successful snapshot.
    failures = [dict(region_code=l.region_code, month=l.deal_month, status=l.status,
                     error_code=l.error_code, started_at=iso(l.started_at)) for l in logs
                if l.status in ('failed','running') and
                ((l.region_code,l.deal_month) not in covered or
                 l.started_at >= covered[(l.region_code,l.deal_month)][0])]
    missing = [dict(region_code=r, month=m) for r in codes for m in months if (r,m) not in covered]
    stale = [dict(region_code=r, month=m) for (r,m),(stamp,_) in covered.items()
             if now - stamp > timedelta(hours=stale_hours)]
    status = ('unavailable' if not covered else 'partial' if missing or failures else
              'stale' if stale else 'complete')
    region_rows = []
    for name, code in SEOUL_SIGUNGU_CODES.items():
        available = [(m,covered[(code,m)]) for m in months if (code,m) in covered]
        region_rows.append(dict(code=code, name=name,
            transaction_count=sum(value[1] for _,value in available) if available else None,
            completed_months=len(available), expected_months=12))
    trends = []
    for month in months:
        values = [covered[(r,month)][1] for r in codes if (r,month) in covered]
        trends.append(dict(month=month, transaction_count=sum(values) if values else None,
                           completed_regions=len(values), expected_regions=25))
    stamps = [stamp for stamp,_ in covered.values()]
    total = sum(count for _,count in covered.values()) if covered else None
    return dict(status=status, source=SOURCE,
        period={'from':months[0][:4]+'-'+months[0][4:]+'-01','to':today.isoformat(),
                'months':months, 'includes_current_month':True},
        last_updated=iso(max(stamps)) if stamps else None,
        oldest_updated=iso(min(stamps)) if stamps else None,
        computed_at=iso(now),
        coverage={'expected':300, 'completed':len(covered), 'missing':missing,
                  'stale':stale, 'failures':failures, 'stale_hours':stale_hours},
        summary={'region_count':sum(1 for r in region_rows if (r['transaction_count'] or 0)>0) if covered else None,
                 'transaction_count':total, 'fully_collected_regions':sum(r['completed_months']==12 for r in region_rows)},
        regions=region_rows, trends=trends,
        limitations=['월세 0원인 아파트 전세 공개 레코드만 집계합니다. 현재 월은 진행 중입니다.',
            '공개 필드가 동일한 별개 계약은 구별하지 못할 수 있습니다.',
            '원천 API가 취소 정보를 제공하지 않는 경우 재수집 시 삭제·정정된 자료로 반영됩니다. 신고 지연과 원천자료 변경이 있을 수 있습니다.'])


def register_dashboard(app, db):
    models = define_models(db)
    app.extensions['dashboard_models'] = models

    def respond(kind):
        try:
            payload = build_dashboard(db, models, stale_hours=app.config.get('DASHBOARD_STALE_HOURS',192))
            if kind != 'summary':
                for key in ('summary','regions','trends'):
                    if key != kind:
                        payload.pop(key)
            response = jsonify(payload)
            response.headers['Cache-Control'] = 'no-store'
            return response
        except (SQLAlchemyError, ValueError):
            db.session.rollback()
            app.logger.exception('Dashboard unavailable')
            return jsonify(status='unavailable', error='통계 조회 실패. 잠시 후 다시 시도하세요.',
                           source=SOURCE, last_updated=None), 503

    @app.get('/api/dashboard/summary')
    @app.get('/api/dashboard/stats')
    def dashboard_summary():
        # Summary includes matching chart values to prevent cross-request races.
        return respond('summary')

    @app.get('/api/dashboard/regions')
    def dashboard_regions():
        return respond('regions')

    @app.get('/api/dashboard/trends')
    def dashboard_trends():
        return respond('trends')

    @app.get('/api/dashboard/data-status')
    def dashboard_data_status():
        return respond('data-status')

    @app.cli.command('sync-dashboard')
    @click.option('--mode', type=click.Choice(['full','recent','scheduled']), default='full')
    @click.option('--region', 'regions', multiple=True, help='기본: 서울 25개 구')
    @click.option('--month', 'selected_months', multiple=True, help='YYYYMM. 기본: 최근 12개월')
    def sync_dashboard(mode, regions, selected_months):
        from dashboard_ops import collection_lock
        from rental_collector import CollectionError
        today = datetime.now(KST).date()
        codes = sorted(set(regions or SEOUL_SIGUNGU_CODES.values()))
        months = sorted(set(selected_months or months_for(today)))
        for r in codes:
            for m in months:
                try:
                    validate_scope(r,m,today)
                except CollectionError as e:
                    raise click.ClickException(str(e)) from None
        lock_path = app.config.get('DASHBOARD_LOCK_PATH') or str(Path(app.instance_path)/'dashboard.lock')
        with collection_lock(lock_path):
            Region, Transaction, Stat, Log = models
            # Any previous running log under this exclusive lock was interrupted.
            Log.query.filter_by(status='running').update({'status':'failed','error_code':'INTERRUPTED','finished_at':utcnow()})
            db.session.commit()
            recent = mode == 'recent' or (mode == 'scheduled' and today.weekday()!=6)
            scopes = [(r,m) for r in codes for m in months]
            if recent and not selected_months:
                latest_ids = db.session.query(func.max(Log.id)).group_by(Log.region_code, Log.deal_month)
                failed_scopes = {(log.region_code, log.deal_month) for log in
                                 Log.query.filter(Log.id.in_(latest_ids), Log.status == 'failed').all()}
                scopes = [(r,m) for r,m in scopes if m in months_for(today,3) or
                          db.session.get(Stat,(r,m)) is None or (r,m) in failed_scopes]
            key = _get_api_key(rent=True) or _get_api_key()
            if not key:
                r,m = scopes[0]
                db.session.add(Log(region_code=r,deal_month=m,status='failed',error_code='MISSING_API_KEY',started_at=utcnow(),finished_at=utcnow()))
                db.session.commit()
                raise click.ClickException('MOLIT_RENT_API_KEY가 필요합니다. 가짜 데이터를 저장하지 않았습니다.')
            failed = 0
            for r,m in scopes:
                ok = collect_scope(db,models,r,m,key,today)
                failed += not ok
                click.echo(f'{r} {m}: '+('success' if ok else 'failed (collection_logs 확인)'))
            if failed:
                raise click.ClickException(f'{failed}/{len(scopes)}개 범위 수집 실패. 해당 범위의 이전 자료는 보존했습니다.')
            click.echo(f'{len(scopes)}개 지역·월 수집 완료')

    from dashboard_ops import register_operations
    register_operations(app, db)
    return models
