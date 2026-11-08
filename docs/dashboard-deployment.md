# SafeHome 운영 배포 및 복구

## 실제 확인한 운영 환경 (2026-11-08)

- Ubuntu EC2, 운영 프로젝트: `/home/ubuntu/safehome`
- 웹 서비스: `safehome.service`, 사용자 `ubuntu`
- 실행: `/home/ubuntu/safehome/venv/bin/gunicorn --chdir /home/ubuntu/safehome/backend --workers 3 --bind 127.0.0.1:8000 app:app`
- Nginx가 외부 HTTPS 요청을 처리합니다. 기존 프록시 및 소셜 로그인 설정을 유지합니다.
- **운영 DB는 PostgreSQL 18.3입니다.** 저장소의 SQLite 기본값과 다르며, 기존 `DATABASE_URL`을 그대로 사용합니다.
- `pg_dump`/`pg_restore` 18.6을 확인했습니다. 웹 서버 코드 배포로 DB 파일을 덮어쓰는 방식이 아닙니다.
- 위 경로와 실행 명령은 2026-11-08 당시 기록입니다. 아래 절차는 GitHub 커밋을 기준으로 새 릴리스 경로를 준비합니다.

## GitHub 커밋으로 릴리스 준비

저장소에는 운영에서 사용한 프록시 연동, 네이버·카카오 로그인, 개인정보처리방침, 관리자 신고 API와 권한 검사, 매물 위치보기 링크가 포함됩니다. 운영 서버의 API 키는 환경 파일에서 주입합니다.

1. Ubuntu에 운영과 같은 Python 3.14, venv, Git과 운영 DB 버전에 맞는 PostgreSQL 클라이언트 도구를 준비합니다. 기존 HTTPS 도메인과 OAuth 콜백 등록은 유지합니다.
2. 운영 경로와 별도인 GitHub 체크아웃에서 배포할 전체 커밋 SHA를 가져온 뒤 `bash deploy/prepare-release.sh <전체 SHA>`를 실행합니다. 이 명령은 그 SHA의 파일과 고정된 Python 의존성을 `/home/ubuntu/safehome-releases/<SHA>`에 설치합니다.
3. 권한 600으로 웹용 `~/.config/safehome-web.env`와 수집용 `~/.config/safehome-dashboard.env`를 구성합니다. 양쪽에 기존 `SECRET_KEY`, PostgreSQL `DATABASE_URL`, 필요한 국토부 키를 설정합니다. 웹에는 추가로 기존 네이버·카카오 설정을 옮깁니다. 수집용 `DASHBOARD_LOCK_PATH`는 릴리스 사이에 유지되는 `/home/ubuntu/.local/state/safehome/dashboard.lock`을 사용합니다. 해당 디렉터리와 백업 디렉터리를 미리 만들어 `ubuntu`가 쓸 수 있도록 합니다.
4. 준비한 릴리스에서 아래 백업 및 마이그레이션 절차를 실행합니다. 이어 웹 서비스와 타이머의 기존 유닛 파일을 백업합니다. 전환할 때 타이머를 정지하고 실행 중인 수집 서비스가 끝난 것을 확인합니다.
5. `/home/ubuntu/safehome-current`가 준비한 릴리스를 가리키도록 심볼릭 링크를 전환합니다. 새 링크를 임시 이름으로 만든 뒤 같은 디렉터리에서 `mv -Tf`로 교체하면 경로가 비는 순간을 피할 수 있습니다. 새 릴리스의 `deploy/safehome*.service`와 `deploy/safehome*.timer`를 `/etc/systemd/system/`에 설치합니다. `systemctl daemon-reload` 후 웹을 재시작하고 수집·백업·복원·감시 타이머를 활성화합니다.
6. Nginx는 Gunicorn의 `127.0.0.1:8000`에만 프록시하고 `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-For`를 직접 설정합니다. 유닛의 `TRUST_NGINX_PROXY=1`은 이 단일 프록시 배치에서만 사용합니다. 메인·로그인·개인정보처리방침·대시보드 API를 확인하고, 웹 서비스의 `MainPID`에 해당하는 `/proc/<PID>/cwd`가 배포한 릴리스의 `backend`를 가리키는지 확인합니다.

웹 검증에 실패하면 이전 릴리스로 링크를 되돌리고 서비스를 재시작합니다. 이 구조로 처음 전환한 경우 백업한 기존 유닛 파일을 복구하고 `daemon-reload` 후 서비스를 재시작합니다.

## 환경 변수 및 키

기존 웹 서비스에 설정된 승인 키로 실제 전세 API 응답을 확인했습니다. 새 웹 유닛은
`/home/ubuntu/.config/safehome-web.env`를 읽고, 자동 수집은
`/home/ubuntu/.config/safehome-dashboard.env`를 읽습니다. 파일은 `ubuntu` 소유, 권한 600이며
실제 값은 문서·Git·브라우저·명령행 인자에 넣지 않습니다. 키 변경 시 웹 서비스와 수집 환경 파일을 함께 갱신하세요.

- `DATABASE_URL`: 기존 PostgreSQL 접속 설정 유지
- `SECRET_KEY`: 기존 값 유지
- `MOLIT_RENT_API_KEY`: 국토교통부 아파트 전월세 API 승인 키
- `MOLIT_API_KEY`: 전월세 활용 권한이 있을 때만 대체 키로 사용
- `DASHBOARD_RECENT_STALE_HOURS=36`: 이번 달을 포함한 최근 3개월의 갱신 지연 기준
- `DASHBOARD_STALE_HOURS=192`: 이전 9개월의 갱신 지연 기준
- `DASHBOARD_LOCK_PATH=/home/ubuntu/.local/state/safehome/dashboard.lock`

환경 파일은 systemd가 읽도록 작성했습니다. 비밀번호의 특수문자를 셸에서 확장하지 않도록
임의로 `source`하거나 내용을 화면에 출력하지 마세요. `.env.example`은 설정 이름 안내이며
현재 운영 DB를 새 빈 SQLite DB로 바꾸라는 뜻이 아닙니다.

## 백업과 마이그레이션

이번 배포 전 소스·서비스 설정·DB 백업 디렉터리:
`/home/ubuntu/safehome-backups/dashboard-20261108`

- `source-before.tar.gz`: 배포 전 소스와 로컬 설정. 비밀 설정이 포함될 수 있으므로 외부에 공유하지 않습니다.
- `safehome.service.before`: 기존 웹 서비스 설정 백업
- `safehome-*.dump`: PostgreSQL custom-format 백업

`backup-db`는 PostgreSQL에서 `pg_dump`를 실행하고 `pg_restore`로 전체 아카이브를 읽어 검증합니다.
이 검증은 DB에 복원 쿼리를 실행하지 않습니다. 실제 장애 복구 훈련과는 구별됩니다.
접속 비밀번호는 자식 프로세스 환경으로만 전달하고 오류에는 원문 URL을 출력하지 않습니다.
검증 전 파일은 `.partial`, 검증 완료 파일만 `.dump`로 확정합니다.

DB 마이그레이션은 기존 회원·리뷰·매매 테이블을 건드리지 않고 신규 전세 테이블을 추가합니다.
실제 PostgreSQL에서 `db upgrade`와 `db check`를 확인했습니다. legacy baseline downgrade는
기존 사용자 데이터를 보호하기 위해 비활성화되어 있습니다.

환경 파일을 사용하여 운영 명령을 실행하려면 예를 들어 다음처럼 systemd의 임시 작업을 사용합니다.
작업 디렉터리는 준비한 릴리스 루트이며 해당 가상환경과 기존 DB 설정을 사용해야 합니다. 아래 예시는 활성 릴리스 기준이므로 전환 전에 실행할 때는 `safehome-current` 두 곳을 준비한 릴리스 경로로 바꾸세요.

```bash
sudo systemd-run --wait --pipe --collect \
  -p User=ubuntu \
  -p WorkingDirectory=/home/ubuntu/safehome-current \
  -p EnvironmentFile=/home/ubuntu/.config/safehome-dashboard.env \
  /home/ubuntu/safehome-current/venv/bin/python -m flask --app backend/app check-data-storage
```

마지막 명령 부분을 `db check`, `backup-db --directory /home/ubuntu/safehome-backups/manual`,
`sync-dashboard --region 11110 --month 202610` 등으로 바꿀 수 있습니다. `db upgrade`는 항상
백업과 변경 검토 후 수행하세요. 표본 월은 예시이며 실제 필요한 월로 지정합니다.

## 주기적 수집

설정 파일은 `deploy/safehome-collect.service`, `deploy/safehome-collect.timer`입니다.
운영 경로와 사용자에 맞춰 작성되어 있으며 웹 프로세스 안에서 스케줄러를 실행하지 않습니다.

- 한국 시간 매일 03:10 이후 0~5분 지연 실행
- 월~토: 최근 3개월 + 미수집·최신 실패 범위
- 일요일: 최근 12개월 전체
- 수집 전 DB 연결 검사. 백업은 별도 서비스에서 실행하므로 백업 실패가 당일 수집을 막지 않습니다.
- 파일 잠금으로 동시 수집 차단, 실패 시 이전 정상 자료 보존

```bash
systemctl status safehome-collect.timer
systemctl list-timers safehome-collect.timer
journalctl -u safehome-collect.service
sudo systemctl start safehome-collect.service
```

`ProtectHome=read-only`를 사용하므로 `/home/ubuntu`의 코드·환경은 읽을 수 있고 지정된
`.local/state/safehome`만 쓸 수 있습니다. 비밀 설정이나 파일 경로를 변경하면
환경 파일과 `ReadWritePaths`도 함께 확인하세요.

## 예약 작업 감시와 복구 훈련

처음 전환할 때는 백업과 복원 서비스의 성공을 확인하세요. 각 정상 완료 기한에 해당 일정의 성공 기록이 없으면 감시가 알려줍니다. 수집·백업 디렉터리의 권한과 기존 PostgreSQL 설정을 유지합니다.

| 예약 작업 (한국 시간) | 정상 완료 기준 |
| --- | --- |
| 일일 수집 03:10~03:15 | 08:00 |
| 일일 PostgreSQL 백업 02:30 | 04:30 |
| 일요일 격리 복원 09:30 | 12:00 |

실패 시 systemd가 즉시 감시를 실행하고, 15분 간격으로 성공 기록을 검사해 작업이 실행되지 않았거나 늦어진 경우도 탐지합니다. 장애 항목이 바뀌거나 모두 복구됐을 때만 저널과 선택한 웹훅에 알립니다. 웹훅 요청에 실패하면 다음 감시에서 재시도합니다.

운영 선택 설정은 권한 600인 `/home/ubuntu/.config/safehome-maintenance.env`에 둡니다.

- `SAFEHOME_ALERT_SNS_TOPIC_ARN`: 이메일 구독이 확인된 SNS 표준 주제 ARN. 운영 EC2 역할에는 해당 주제의 `sns:Publish` 권한만 부여합니다. 구독 이메일 주소는 SNS에서 관리합니다.
- `SAFEHOME_ALERT_WEBHOOK`: `{"text":"..."}` 형식의 POST를 받는 HTTPS 주소. SNS와 웹훅 중 하나를 설정합니다. 둘 다 미설정이면 `journalctl -u safehome-monitor.service`에서 알림을 확인합니다.
- `SAFEHOME_BACKUP_RETENTION_DAYS=30`, `SAFEHOME_BACKUP_MINIMUM=7`: 자동 생성한 로컬 PostgreSQL 백업의 보존 기간과 최소 보존 개수. 원격 저장을 설정했을 때는 새 복사본을 검증한 후에만 만료본을 정리합니다.
- `SAFEHOME_BACKUP_S3_BUCKET`, `SAFEHOME_BACKUP_S3_ACCOUNT_ID`, `SAFEHOME_BACKUP_S3_PREFIX=safehome/postgres`, `AWS_DEFAULT_REGION`: 비공개 버킷, 소유 계정, 접두사와 리전입니다. AWS CLI v2 및 EC2 역할에 해당 접두사의 `ListBucket`과 백업 객체의 `GetObject`·`PutObject` 권한이 필요합니다. 모든 S3 요청에서 버킷 소유 계정을 확인하고 서버 측 암호화와 SHA-256을 사용합니다. 원격 만료 정책은 S3에서 설정합니다.
- `SAFEHOME_PG_BINDIR=/usr/lib/postgresql/18/bin`: 복원 훈련에 사용할 PostgreSQL 서버·클라이언트 도구의 경로. `initdb`와 `pg_ctl`을 포함한 운영과 같은 메이저 버전이 필요합니다.

백업은 `/home/ubuntu/safehome-backups/scheduled`에 보관합니다. 복원 훈련은 최근 백업을 새 임시 PostgreSQL 클러스터에 실제로 넣고, 스키마·25개 지역·사용자 테이블·통계 정합성을 확인합니다. 이 클러스터는 전용 Unix 소켓에서만 접속을 받고 훈련 후 종료·삭제됩니다. S3를 설정하면 해당 접두사의 최신 복사본을 S3에서 찾아 체크섬을 확인하고 복원합니다. 로컬에 백업 파일이 없어도 같은 절차를 쓸 수 있습니다.

PR과 main 푸시 때 GitHub Actions가 PostgreSQL 18 테스트용 클러스터에 마이그레이션·수집·롤백·백업·복원을 검증합니다. 별도 Chromium 작업에서 390px 및 데스크톱 레이아웃, 503 안내와 재시도를 확인합니다.

## 완료 확인 및 장애 대응

`https://safehome-kr.com/api/dashboard/data-status`에서 `status=complete`,
`coverage.completed=300`, 실패·미수집 범위가 없는지 확인합니다. 현재 월은 진행 중이며
원천 자료의 신고 지연은 이 범위 검증만으로 해결되지 않습니다.

웹 배포는 위 절차대로 버전이 명확한 릴리스 경로로 전환합니다.
로그인·개인정보처리방침·매물 분석·지도 및 기존 OAuth/관리자 경로를 확인합니다.
추가된 전세 테이블은 기존 코드에 영향을 주지 않으므로 코드 롤백 때문에 운영 DB 전체를
과거 백업으로 되돌려 새 회원·리뷰를 잃지 않도록 주의하세요.

실제 DB 복구는 웹·수집 작업을 중지하고 현재 DB도 백업한 뒤 별도 검증 환경에서 복원을
확인하고 진행합니다. 운영 DB에 `pg_restore --clean`을 무심코 실행하지 마세요.
관리형 DB의 자동 백업과 S3 수명 주기는 각 서비스 설정에서 별도로 관리합니다.

## 로컬 SQLite 개발

`DATABASE_URL`이 없을 때만 로컬 기본값 `backend/instance/site.db`를 사용합니다.
`backup-db`는 SQLite backup API와 `PRAGMA integrity_check`도 계속 지원합니다.
테스트는 메모리/임시 SQLite DB에서 실행하며 운영 거래를 모의 데이터로 채우지 않습니다.
