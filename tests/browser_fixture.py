"""Disposable Flask fixture for browser tests. Writes only to its in-memory DB."""
from datetime import datetime
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'backend'))
os.environ.update(DATABASE_URL='sqlite://', SECRET_KEY='safehome-browser-fixture-only')
from sqlalchemy.pool import StaticPool
from werkzeug.serving import make_server
from app import app, db
from dashboard import KST
from rental_collector import collect_scope, months_for, normalize, utcnow
from utils import SEOUL_SIGUNGU_CODES


with app.app_context():
    assert isinstance(db.engine.pool, StaticPool)
    db.create_all()
    Region, _, Stat, _ = models = app.extensions['dashboard_models']
    today = datetime.now(KST).date()
    month = today.strftime('%Y%m')
    for name, code in SEOUL_SIGUNGU_CODES.items():
        db.session.add(Region(code=code, name=name))
        for deal_month in months_for(today):
            db.session.add(Stat(region_code=code, deal_month=deal_month,
                                transaction_count=0, source_count=0, calculated_at=utcnow()))
    db.session.commit()
    row = normalize(dict(deposit='50000', monthlyRent='0', excluUseAr='84.9',
        dealYear=str(today.year), dealMonth=str(today.month), dealDay='1',
        aptNm='Fixture', umdNm='사직동', sggCd='11110'), '11110', month, today)
    assert collect_scope(db, models, '11110', month, 'fixture', today, fetch=lambda *_: ([row], 1))

with make_server('127.0.0.1', 0, app) as server:
    print(f'http://127.0.0.1:{server.server_port}', flush=True)
    server.serve_forever()
