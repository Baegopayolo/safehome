"""Daily backup, isolated PostgreSQL restore drill, and scheduler monitoring."""
import argparse
import base64
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))
ARCHIVE = re.compile(r'safehome-\d{8}T\d{12}Z\.dump')
JOBS = {
    'collect': ('03:10', '08:00', None),
    'backup': ('02:30', '04:30', None),
    'restore': ('09:30', '12:00', 6),
}


def command(args, *, env=None, timeout=900):
    try:
        return subprocess.run(args, env=env, timeout=timeout, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise RuntimeError(f'{Path(args[0]).name} 단계 실패') from None


def archives(directory):
    return sorted((path for path in directory.iterdir()
                   if ARCHIVE.fullmatch(path.name) and not path.is_symlink() and path.is_file()),
                  reverse=True)


def prune(directory, now, days, minimum):
    removed = 0
    for path in archives(directory)[minimum:]:
        if path.stat().st_mtime < now.timestamp() - days * 86400:
            path.unlink()
            removed += 1
    return removed


def checksum(path):
    with path.open('rb') as stream:
        return base64.b64encode(hashlib.file_digest(stream, 'sha256').digest()).decode('ascii')


def s3_location(name):
    bucket = os.getenv('SAFEHOME_BACKUP_S3_BUCKET')
    prefix = os.getenv('SAFEHOME_BACKUP_S3_PREFIX', 'safehome/postgres').strip('/')
    return (bucket, f'{prefix}/{name}' if prefix else name) if bucket else None


def s3_bucket_args(bucket):
    owner = os.getenv('SAFEHOME_BACKUP_S3_ACCOUNT_ID', '')
    if not re.fullmatch(r'[0-9]{12}', owner):
        raise RuntimeError('S3 백업 버킷의 AWS 계정 ID가 필요합니다.')
    return ['--bucket', bucket, '--expected-bucket-owner', owner]


def remote_checksum(bucket, key):
    return command(['aws', 's3api', 'head-object', *s3_bucket_args(bucket), '--key', key,
                    '--checksum-mode', 'ENABLED', '--query', 'ChecksumSHA256', '--output', 'text'])


def upload(archive, location):
    bucket, key = location
    digest = checksum(archive)
    args = [*s3_bucket_args(bucket), '--key', key]
    command(['aws', 's3api', 'put-object', *args, '--body', str(archive), '--server-side-encryption',
             'AES256', '--checksum-sha256', digest])
    if remote_checksum(bucket, key) != digest:
        raise RuntimeError('원격 백업 체크섬 불일치')


def latest_remote_archive(bucket, prefix):
    listing = json.loads(command(['aws', 's3api', 'list-objects-v2', *s3_bucket_args(bucket),
                                  '--prefix', prefix, '--output', 'json']))
    names = [item['Key'][len(prefix):] for item in listing.get('Contents', [])
             if item['Key'].startswith(prefix) and ARCHIVE.fullmatch(item['Key'][len(prefix):])]
    if not names:
        raise RuntimeError('복원 훈련에 사용할 S3 백업이 없습니다.')
    return max(names)


def daily_backup(directory):
    output = command([sys.executable, '-B', '-m', 'flask', '--app', str(ROOT/'backend/app'),
                      'backup-db', '--directory', str(directory)])
    archive = Path(output.splitlines()[-1])
    if archive.parent != directory or not ARCHIVE.fullmatch(archive.name):
        raise RuntimeError('PostgreSQL 백업 경로가 올바르지 않습니다.')
    location = s3_location(archive.name)
    if location:
        upload(archive, location)
    days = int(os.getenv('SAFEHOME_BACKUP_RETENTION_DAYS', '30'))
    minimum = int(os.getenv('SAFEHOME_BACKUP_MINIMUM', '7'))
    if days < 1 or minimum < 1:
        raise RuntimeError('백업 보존 설정은 1 이상이어야 합니다.')
    removed = prune(directory, datetime.now(timezone.utc), days, minimum)
    print(f'백업 검증 완료: {archive.name}, 원격 복사 {"완료" if location else "미설정"}, 만료본 {removed}개 정리')


def verify_restore(archive, bindir):
    """Restore into a newly initialized cluster reachable only via a private Unix socket."""
    if os.name != 'posix' or os.geteuid() == 0:
        raise RuntimeError('복원 훈련은 Linux의 비관리자 계정에서 실행하세요.')
    env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
    with tempfile.TemporaryDirectory(prefix='safehome-restore-') as temporary:
        root = Path(temporary)
        data, socket = root/'data', root/'socket'
        socket.mkdir(mode=0o700)
        options = ['-h', str(socket), '-p', '55432', '-U', 'restore_admin']
        command([str(bindir/'initdb'), '-D', str(data), '-U', 'restore_admin', '--auth=trust',
                 '--locale=C', '--encoding=UTF8'], env=env)
        started = False
        try:
            # No TCP listeners, no connection strings, no inherited PG environment.
            command([str(bindir/'pg_ctl'), '-D', str(data), '-l', str(root/'postgres.log'),
                     '-o', f"-c listen_addresses='' -k {socket} -p 55432 -c shared_buffers=32MB -c max_connections=10",
                     '-w', 'start'], env=env)
            started = True
            command([str(bindir/'createdb'), *options, 'safehome_restore'], env=env)
            command([str(bindir/'pg_restore'), *options, '--dbname', 'safehome_restore', '--no-owner',
                     '--no-acl', '--single-transaction', '--exit-on-error', str(archive)], env=env)
            result = command([str(bindir/'psql'), *options, '-d', 'safehome_restore', '-At',
                              '-v', 'ON_ERROR_STOP=1', '-c', """
                SELECT count(*) = 1 AND EXISTS (SELECT 1 FROM regions HAVING count(*) = 25)
                AND EXISTS (SELECT 1 FROM "user" HAVING count(*) >= 0)
                AND NOT EXISTS (
                    SELECT 1 FROM dashboard_stats s LEFT JOIN real_transactions t
                      ON (t.region_code, t.deal_month) = (s.region_code, s.deal_month)
                      AND NOT t.cancelled AND t.transaction_type = 'jeonse' AND t.monthly_rent = 0
                    GROUP BY s.region_code, s.deal_month, s.transaction_count
                    HAVING count(t.id) <> s.transaction_count
                ) FROM alembic_version;
            """], env=env)
            if result != 't':
                raise RuntimeError('복원된 데이터 무결성 검사 실패')
        finally:
            if started or (data/'postmaster.pid').exists():
                command([str(bindir/'pg_ctl'), '-D', str(data), '-m', 'immediate', '-w', 'stop'],
                        env=env, timeout=30)


def restore_drill(directory, bindir):
    location = s3_location('')
    if location:
        bucket, prefix = location
        name = latest_remote_archive(bucket, prefix)
        key = prefix + name
        expected = remote_checksum(bucket, key)
        with tempfile.TemporaryDirectory(prefix='safehome-offsite-') as temporary:
            downloaded = Path(temporary)/name
            command(['aws', 's3api', 'get-object', *s3_bucket_args(bucket), '--key', key,
                     '--checksum-mode', 'ENABLED', str(downloaded)])
            if checksum(downloaded) != expected:
                raise RuntimeError('다운로드한 백업 체크섬 불일치')
            verify_restore(downloaded, bindir)
    else:
        available = archives(directory)
        if not available:
            raise RuntimeError('복원 훈련에 사용할 백업이 없습니다.')
        archive = available[0]
        verify_restore(archive, bindir)
        name = archive.name
    print(f'격리 PostgreSQL 복원 검증 완료: {name}')


def scheduled_due(now, start, deadline, weekday):
    day = now.date()
    if weekday is not None:
        day -= timedelta(days=(day.weekday() - weekday) % 7)
    if now < datetime.combine(day, time.fromisoformat(deadline), KST):
        day -= timedelta(days=1 if weekday is None else 7)
    return datetime.combine(day, time.fromisoformat(start), KST)


def job_issue(now, schedule, stamp, state, result):
    if state == 'failed' or (state == 'inactive' and result != 'success'):
        return '실패'
    if stamp is None or stamp < scheduled_due(now, *schedule):
        return '완료 기한 초과'
    return None


def read_job(job, state_dir, now):
    service = f'safehome-{job}.service'
    output = command(['systemctl', 'show', service, '-p', 'LoadState', '-p', 'ActiveState', '-p', 'Result'])
    props = dict(line.split('=', 1) for line in output.splitlines())
    if props.get('LoadState') != 'loaded':
        return '서비스 미설치'
    marker = state_dir/f'{job}.ok'
    stamp = datetime.fromtimestamp(marker.stat().st_mtime, KST) if marker.is_file() else None
    return job_issue(now, JOBS[job], stamp, props.get('ActiveState'), props.get('Result'))


def notify(message):
    print(message, flush=True)
    topic = os.getenv('SAFEHOME_ALERT_SNS_TOPIC_ARN')
    url = os.getenv('SAFEHOME_ALERT_WEBHOOK')
    if topic and url:
        raise RuntimeError('이메일과 웹훅 중 한 가지 알림 경로만 설정하세요.')
    if topic:
        match = re.fullmatch(r'arn:aws:sns:([a-z0-9-]+):[0-9]{12}:[A-Za-z0-9_-]{1,256}', topic)
        if not match:
            raise RuntimeError('SNS 표준 주제 ARN이 올바르지 않습니다.')
        command(['aws', 'sns', 'publish', '--region', match.group(1), '--topic-arn', topic,
                 '--subject', 'SafeHome 운영 알림', '--message', message, '--no-cli-pager'],
                timeout=25)
    elif url:
        if urlsplit(url).scheme != 'https' or not urlsplit(url).hostname:
            raise RuntimeError('알림 웹훅에 HTTPS 주소가 필요합니다.')
        request = urllib.request.Request(url, json.dumps({'text': message}).encode(),
                                         headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError('웹훅 전송 실패')
        except (urllib.error.URLError, OSError, ValueError):
            raise RuntimeError('웹훅 전송 실패') from None


def monitor(state_dir):
    now = datetime.now(KST)
    issues = {job: issue for job in JOBS if (issue := read_job(job, state_dir, now))}
    previous = state_dir/'monitor.json'
    old = json.loads(previous.read_text(encoding='utf-8')) if previous.exists() else {}
    if issues == old:
        return
    notify('SafeHome: ' + (', '.join(f'{job} {issue}' for job, issue in issues.items()) or '수집·백업·복원 정상 복구'))
    pending = previous.with_suffix('.tmp')
    pending.write_text(json.dumps(issues), encoding='utf-8')
    pending.replace(previous)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('backup', 'restore', 'monitor'))
    parser.add_argument('--directory', type=Path, default=Path('/home/ubuntu/safehome-backups/scheduled'))
    parser.add_argument('--state-dir', type=Path, default=Path('/home/ubuntu/.local/state/safehome'))
    parser.add_argument('--pg-bindir', type=Path, default=Path(os.getenv('SAFEHOME_PG_BINDIR', '/usr/lib/postgresql/18/bin')))
    options = parser.parse_args()
    try:
        if options.action == 'backup':
            daily_backup(options.directory.resolve())
        elif options.action == 'restore':
            restore_drill(options.directory.resolve(), options.pg_bindir)
        else:
            monitor(options.state_dir)
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else '운영 유지보수 설정 또는 파일 오류', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
