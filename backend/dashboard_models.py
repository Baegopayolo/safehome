"""Dashboard tables; the legacy real_transaction search cache is unchanged."""
def define_models(db):
    class Region(db.Model):
        __tablename__ = 'regions'
        code = db.Column(db.String(5), primary_key=True)
        name = db.Column(db.String(40), nullable=False, unique=True)

    class RentalTransaction(db.Model):
        __tablename__ = 'real_transactions'
        id = db.Column(db.Integer, primary_key=True)
        region_code = db.Column(db.String(5), db.ForeignKey('regions.code'), nullable=False)
        deal_month = db.Column(db.String(6), nullable=False)
        fingerprint = db.Column(db.String(64), nullable=False)
        transaction_type = db.Column(db.String(10), nullable=False, default='jeonse')
        deposit = db.Column(db.BigInteger, nullable=False)  # KRW 10,000
        monthly_rent = db.Column(db.BigInteger, nullable=False)
        contract_date = db.Column(db.Date, nullable=False)
        area = db.Column(db.Numeric(12, 4), nullable=False)
        apartment = db.Column(db.String(200), nullable=False)
        dong = db.Column(db.String(100), nullable=False)
        floor = db.Column(db.String(20), nullable=False)
        cancelled = db.Column(db.Boolean, nullable=False, default=False)
        collected_at = db.Column(db.DateTime, nullable=False)  # UTC naive in DB
        __table_args__ = (
            db.UniqueConstraint('region_code', 'deal_month', 'fingerprint', name='uq_rental_scope_fingerprint'),
            db.Index('ix_rental_region_month', 'region_code', 'deal_month'),
            db.CheckConstraint('deposit > 0 AND monthly_rent = 0 AND area > 0', name='ck_jeonse_values'),
        )

    class DashboardStat(db.Model):
        __tablename__ = 'dashboard_stats'
        region_code = db.Column(db.String(5), db.ForeignKey('regions.code'), primary_key=True)
        deal_month = db.Column(db.String(6), primary_key=True)
        transaction_count = db.Column(db.Integer, nullable=False)
        source_count = db.Column(db.Integer, nullable=False)
        calculated_at = db.Column(db.DateTime, nullable=False)
        __table_args__ = (db.CheckConstraint('transaction_count >= 0 AND source_count >= 0', name='ck_stats_counts'),)

    class CollectionLog(db.Model):
        __tablename__ = 'collection_logs'
        id = db.Column(db.Integer, primary_key=True)
        region_code = db.Column(db.String(5), nullable=False)
        deal_month = db.Column(db.String(6), nullable=False)
        status = db.Column(db.String(16), nullable=False)
        source_count = db.Column(db.Integer)
        transaction_count = db.Column(db.Integer)
        error_code = db.Column(db.String(60))
        started_at = db.Column(db.DateTime, nullable=False)
        finished_at = db.Column(db.DateTime)
        __table_args__ = (db.Index('ix_collection_scope', 'region_code', 'deal_month', 'id'),)

    return Region, RentalTransaction, DashboardStat, CollectionLog
