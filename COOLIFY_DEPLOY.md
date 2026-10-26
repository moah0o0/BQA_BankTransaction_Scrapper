# Coolify 배포 가이드

Coolify를 사용하여 Postbank Scrapper를 배포하는 방법입니다.

## 사전 요구사항

- Coolify가 설치된 서버
- GitHub 저장소 접근 권한
- 기존 `app-network` 네트워크 (PocketBase와 연결용)

## 배포 방법

### 1. Coolify 대시보드에서 새 프로젝트 생성

1. Coolify 대시보드 접속
2. **+ New Resource** 클릭
3. **Docker Compose** 선택

### 2. Git 저장소 연결

- **Repository**: `https://github.com/moah0o0/money-scrapper-busanqueeract-kr.git`
- **Branch**: `main`
- **Docker Compose Location**: `/` (루트 디렉토리)

### 3. 환경변수 설정

Coolify의 Environment Variables 섹션에서 다음 환경변수를 설정합니다:

```env
# 필수 환경변수
PB_URL=https://api-money.busanqueeract.kr
PB_USER=scrapper@busanqueeract.kr
PB_PASS=your_password_here

# 선택사항 (기본값 사용 가능)
THREAD_POOL_SIZE=8
DEFAULT_INTERVAL=60
TZ=Asia/Seoul
PYTHONUNBUFFERED=1
```

### 4. 네트워크 설정

#### 방법 A: 기존 app-network 사용 (권장)

기존 PocketBase와 같은 네트워크를 사용하려면:

1. Coolify 서버에 SSH 접속
2. `app-network` 네트워크가 있는지 확인:
   ```bash
   docker network ls | grep app-network
   ```
3. 없다면 생성:
   ```bash
   docker network create app-network
   ```

docker-compose.yml의 networks 설정이 자동으로 이를 사용합니다.

#### 방법 B: Coolify 자동 네트워크 사용

Coolify가 자동으로 관리하는 네트워크를 사용하려면 docker-compose.yml 수정:

```yaml
networks:
  app-network:
    external: true
    name: ${COOLIFY_NETWORK:-app-network}
```

그리고 Coolify 환경변수에 추가:
```env
COOLIFY_NETWORK=coolify
```

### 5. 배포 시작

1. **Deploy** 버튼 클릭
2. 빌드 로그 확인
3. 배포 완료 대기

### 6. 상태 확인

#### Coolify 대시보드에서 확인
- 컨테이너 상태
- 리소스 사용량 (CPU, 메모리)
- 실시간 로그

#### PocketBase에서 확인
- `ScrapperHeartbeat` 컬렉션에서 heartbeat 확인
- `ScrapperLog` 컬렉션에서 스크래핑 로그 확인
- `Transaction` 컬렉션에서 거래 내역 확인

### 7. 업데이트

코드를 업데이트한 후:

1. GitHub에 푸시:
   ```bash
   git push origin main
   ```

2. Coolify 대시보드에서:
   - **Redeploy** 버튼 클릭
   - 또는 **Auto Deploy**를 활성화하면 자동 배포

## 리소스 설정

현재 설정된 리소스 제한:

```yaml
deploy:
  resources:
    limits:
      cpus: '0.2'
      memory: 128M
    reservations:
      cpus: '0.05'
      memory: 32M
```

- **예상 메모리 사용량**: 60-100MB
- **예상 CPU 사용량**: 거의 idle (주기적으로 스파이크)

필요시 docker-compose.yml에서 조정 가능합니다.

## 트러블슈팅

### 컨테이너가 시작되지 않는 경우

Coolify 로그에서 확인:
- 빌드 에러
- 환경변수 설정 확인
- 네트워크 연결 확인

### PocketBase 연결 실패

1. 환경변수 `PB_URL` 확인
2. 네트워크 설정 확인:
   ```bash
   docker network inspect app-network
   ```
3. PocketBase 컨테이너가 같은 네트워크에 있는지 확인

### 메모리 부족

현재 128MB 제한이지만 실제로는 60-100MB만 사용합니다.
메모리 부족 문제가 발생하면:

1. docker-compose.yml에서 제한 조정:
   ```yaml
   limits:
     memory: 256M
   ```
2. Git에 커밋 후 Coolify에서 재배포

### 스크래핑이 실행되지 않는 경우

1. PocketBase `BankSetting` 컬렉션 확인:
   - `scraping_enabled=true` 설정 확인
   - 계좌 정보 확인

2. Coolify 로그에서 에러 확인

3. PocketBase `ScrapperLog` 컬렉션에서 에러 로그 확인

## Coolify 장점

- **자동 배포**: Git push 시 자동으로 재배포 가능
- **실시간 모니터링**: CPU, 메모리 사용량 실시간 확인
- **로그 관리**: 통합 로그 뷰어
- **롤백**: 이전 버전으로 쉽게 롤백 가능
- **환경변수 관리**: UI에서 쉽게 관리

## 참고사항

- Coolify는 자동으로 SSL 인증서를 관리하지만, 이 스크래퍼는 포트를 열지 않으므로 SSL이 필요하지 않습니다
- 로그는 Coolify 대시보드에서 확인하거나 PocketBase의 `ScrapperLog` 컬렉션에서 확인 가능
- Health check가 설정되어 있어 컨테이너 상태를 자동으로 모니터링합니다

## 추가 리소스

- [Coolify 공식 문서](https://coolify.io/docs)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [프로젝트 README](./README.md)
