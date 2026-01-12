"""한국 시간 관련 유틸리티 함수"""
from datetime import datetime, timedelta, timezone

KST_OFFSET = timedelta(hours=9)
KST = timezone(KST_OFFSET)

def get_kst_now():
    return datetime.now(KST)

def to_kst(dt):
    if dt is None:
        return None
    if dt.tzinfo is not None:
        if dt.tzinfo.utcoffset(dt) is not None:
            utc_dt = dt.astimezone(timezone.utc)
            return utc_dt.astimezone(KST)
        return dt.astimezone(KST)
    return dt

def format_kst_datetime(dt, format_str='%Y-%m-%d %H:%M'):
    if dt is None:
        return ''
    if dt.tzinfo is not None:
        kst_dt = to_kst(dt)
        return kst_dt.strftime(format_str)
    return dt.strftime(format_str)

def format_kst_date(dt, format_str='%Y-%m-%d'):
    if dt is None:
        return ''
    if dt.tzinfo is not None:
        kst_dt = to_kst(dt)
        return kst_dt.strftime(format_str)
    return dt.strftime(format_str)
