# 멀티스테이지 빌드로 최적화
FROM python:3.11-slim as base

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY config.py main.py scrapper.py ./

# 비root 사용자 생성 및 전환
RUN useradd -m -u 1000 scrapper && chown -R scrapper:scrapper /app
USER scrapper

# 헬스체크 (PocketBase 연결 확인)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; from pocketbase import PocketBase; from config import config; pb = PocketBase(config.pb_url); sys.exit(0 if pb else 1)" || exit 1

# 애플리케이션 실행
CMD ["python", "-u", "main.py"]
