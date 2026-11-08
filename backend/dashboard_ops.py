"""Single-host collection lock and SQLite/PostgreSQL backup."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import shutil
import subprocess
import click
from sqlalchemy import text


def postgres_backup(url, destination):
    """Credentials stay in the child environment, never command arguments/logs."""
    if not shutil.which('pg_dump') or not shutil.which('pg_restore'):
        raise click.ClickException('PostgreSQL 백업에는 pg_dump와 pg_restore가 필요합니다.')
    env = os.environ.copy()
    for name, value in {'PGHOST': url.host, 'PGPORT': url.port or 5432,
                        'PGDATABASE': url.database, 'PGUSER': url.username,
                        'PGPASSWORD': url.password, 'PGCONNECT_TIMEOUT': 15}.items():
        if value is not None:
            env[name] = str(value)
    for parameter, variable in {'sslmode': 'PGSSLMODE', 'sslrootcert': 'PGSSLROOTCERT',
                                'sslcert': 'PGSSLCERT', 'sslkey': 'PGSSLKEY'}.items():
        if parameter in url.query:
            env[variable] = url.query[parameter]
    result = subprocess.run(['pg_dump', '--format=custom', '--no-owner', '--file', str(destination)],
                            env=env, capture_output=True)
    if result.returncode:
        raise click.ClickException('PostgreSQL 백업 실패: 연결 권한과 pg_dump 버전을 확인하세요.')
    # Read the whole archive, not just its table of contents, without connecting
    # to any database or emitting restored SQL/data to logs.
    result = subprocess.run(['pg_restore', '--no-owner', '--file', os.devnull, str(destination)], capture_output=True)
    if result.returncode:
        raise click.ClickException('PostgreSQL 백업 아카이브 검증 실패')


@contextmanager
def collection_lock(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            if not handle.read(1):
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise click.ClickException('다른 수집 작업이 실행 중입니다.') from None
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise click.ClickException('다른 수집 작업이 실행 중입니다.') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def register_operations(app, db):
    @app.cli.command('backup-db')
    @click.option('--directory', type=click.Path(file_okay=False), required=True)
    def backup_db(directory):
        dialect = db.engine.dialect.name
        if dialect not in ('sqlite', 'postgresql'):
            raise click.ClickException('SQLite 또는 PostgreSQL 백업만 지원합니다.')
        if dialect == 'sqlite':
            source = Path(db.engine.url.database).resolve()
            if not source.is_file():
                raise click.ClickException('원본 SQLite 파일이 없습니다.')
        target_dir = Path(directory).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        suffix = '.sqlite' if dialect == 'sqlite' else '.dump'
        name = datetime.now(timezone.utc).strftime('safehome-%Y%m%dT%H%M%S%fZ') + suffix
        destination = target_dir/name
        temporary = destination.with_suffix(destination.suffix + '.partial')
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
        if dialect == 'postgresql':
            postgres_backup(db.engine.url, temporary)
        else:
            with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as src, closing(sqlite3.connect(temporary)) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise click.ClickException('백업 무결성 검사 실패')
        temporary.rename(destination)
        if os.name != 'nt':
            destination.chmod(0o600)
        click.echo(str(destination))

    @app.cli.command('check-data-storage')
    def check_storage():
        if db.engine.dialect.name == 'postgresql':
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            click.echo('PostgreSQL connection: ok. 영속성·자동 백업 정책은 DB 운영 설정에서 확인하세요.')
            return
        if db.engine.dialect.name != 'sqlite':
            click.echo('SQLite가 아닙니다. 관리형 DB의 백업 및 영속성 설정을 별도로 확인하세요.')
            return
        path = Path(db.engine.url.database).resolve()
        click.echo(f'SQLite path: {path}')
        if not path.is_file():
            raise click.ClickException('DB 파일 없음: 마이그레이션을 먼저 실행하세요.')
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as connection:
            integrity = connection.execute('PRAGMA integrity_check').fetchone()[0]
        click.echo(f'integrity: {integrity}; parent_writable: {os.access(path.parent, os.W_OK)}')
        if integrity != 'ok':
            raise click.ClickException('DB 무결성 검사 실패')
        click.echo('운영 DB는 배포 디렉터리 밖의 영속 디스크에 두고 재시작 후 경로를 다시 확인하세요.')
