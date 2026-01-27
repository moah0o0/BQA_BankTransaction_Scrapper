# Postbank Scrapper

우체국 계좌 내역을 주기적으로 스크래핑하여 PocketBase에 저장하는 자동화 스크래퍼입니다.

## 주요 기능

- PocketBase의 `BankSetting` 컬렉션에서 계좌 정보 자동 동기화
- 설정된 주기(초 단위)로 자동 스크래핑
- 스크래핑 활성화/비활성화 실시간 반영
- Heartbeat 및 로그 기록
- 리소스 사용량 모니터링

## 시스템 요구사항

- Docker & Docker Compose
- 최소 메모리: 64MB
- 권장 메모리: 128MB
- CPU: 0.1 core 이상

## 배포 방법

### 1. 서버에 파일 복사

```bash
# 로컬에서 서버로 파일 복사 (예시)
scp -r postbank-scrapper/ user@your-server-ip:/opt/
```

### 2. 환경변수 설정 (선택사항)

기본값을 사용하지 않으려면 `.env` 파일을 생성하세요:

```bash
cd /opt/postbank-scrapper
cp .env.example .env
nano .env  # 필요한 값 수정
```

`.env` 파일 예시:
```env
PB_URL=https://api-money.busanqueeract.kr
PB_USER=scrapper@busanqueeract.kr
PB_PASS=your_password_here
THREAD_POOL_SIZE=8
DEFAULT_INTERVAL=60
```

### 3. Docker 네트워크 확인

기존 서비스들과 같은 네트워크를 사용합니다:

```bash
# app-network가 없으면 생성 (deploy.sh가 자동으로 생성함)
docker network create app-network
```

### 4. 배포 스크립트 실행

```bash
cd /opt/postbank-scrapper
chmod +x deploy.sh
./deploy.sh start
```

## 관리 명령어

```bash
# 컨테이너 시작
./deploy.sh start

# 컨테이너 중지
./deploy.sh stop

# 컨테이너 재시작
./deploy.sh restart

# 실시간 로그 확인
./deploy.sh logs

# 상태 및 리소스 사용량 확인
./deploy.sh status

# 컨테이너 쉘 접속
./deploy.sh shell

# 컨테이너 및 이미지 삭제
./deploy.sh clean
```

## Docker Compose 직접 사용

```bash
# 시작
docker-compose up -d --build

# 중지
docker-compose down

# 로그 확인
docker-compose logs -f postbank-scrapper

# 재시작
docker-compose restart postbank-scrapper
```

## 설정 관리

### PocketBase에서 계좌 설정

`BankSetting` 컬렉션에서 계좌를 관리할 수 있습니다:

- `scraping_enabled`: true로 설정하면 자동 스크래핑 시작
- `interval_seconds`: 스크래핑 주기 (초 단위)
- `update_period`: "month", "week", "day" 중 선택
- `remove_list`: 제외할 거래 번호 (쉼표로 구분)

변경사항은 1분 이내에 자동으로 반영됩니다.

## 모니터링

### Heartbeat 확인

PocketBase의 `ScrapperHeartbeat` 컬렉션에서 스크래퍼 상태를 확인할 수 있습니다:

- `status`: "running" 또는 "stopped"
- `last_ping`: 마지막 heartbeat 시간
- `memory_mb`: 메모리 사용량 (MB)
- `cpu_percent`: CPU 사용률 (%)
- `active_jobs`: 활성화된 스크래핑 작업 수

### 로그 확인

PocketBase의 `ScrapperLog` 컬렉션에서 스크래핑 로그를 확인할 수 있습니다.

## 트러블슈팅

### 컨테이너가 시작되지 않는 경우

```bash
# 로그 확인
./deploy.sh logs

# 또는
docker logs postbank-scrapper
```

### PocketBase 연결 실패

- `config.py`의 PocketBase URL 확인
- PocketBase 서버가 실행 중인지 확인
- 네트워크 연결 확인: `docker network inspect app-network`

### 메모리 부족

현재 설정은 최대 256MB까지 사용하도록 제한되어 있습니다. 실제 사용량은 60-100MB 수준입니다.

더 낮은 제한이 필요한 경우 `docker-compose.yml`에서 수정:

```yaml
deploy:
  resources:
    limits:
      memory: 128M  # 더 낮게 설정 가능
```

### 스크래핑이 실행되지 않는 경우

1. PocketBase의 `BankSetting`에서 `scraping_enabled=true` 확인
2. 계좌 정보(계좌번호, 비밀번호, 생년월일) 확인
3. `ScrapperLog` 컬렉션에서 에러 로그 확인

## 서버 리소스 최적화

현재 Vultr 서버 사양:
- vCPU: 2개
- RAM: 4GB
- 이 스크래퍼는 약 60-100MB만 사용하므로 리소스 부담이 매우 적습니다.

다른 서비스와 함께 실행해도 충분한 여유가 있습니다.

## 업데이트

코드를 수정한 후:

```bash
cd /opt/postbank-scrapper
git pull  # 또는 파일 직접 복사
./deploy.sh restart
```

## 라이선스

Private
