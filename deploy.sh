#!/bin/bash

# Postbank Scrapper 배포 스크립트
# 사용법: ./deploy.sh [start|stop|restart|logs|status]

set -e

CONTAINER_NAME="postbank-scrapper"
COMPOSE_FILE="docker-compose.yml"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Docker 네트워크 확인 및 생성
ensure_network() {
    if ! docker network inspect app-network >/dev/null 2>&1; then
        print_info "app-network 네트워크 생성 중..."
        docker network create app-network
    else
        print_info "app-network 네트워크가 이미 존재합니다."
    fi
}

# 컨테이너 시작
start() {
    print_info "Postbank Scrapper 시작 중..."
    ensure_network

    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "docker-compose.yml 파일을 찾을 수 없습니다."
        exit 1
    fi

    docker-compose -f "$COMPOSE_FILE" up -d --build
    print_info "컨테이너가 시작되었습니다."
    sleep 3
    status
}

# 컨테이너 중지
stop() {
    print_info "Postbank Scrapper 중지 중..."
    docker-compose -f "$COMPOSE_FILE" down
    print_info "컨테이너가 중지되었습니다."
}

# 컨테이너 재시작
restart() {
    print_info "Postbank Scrapper 재시작 중..."
    stop
    sleep 2
    start
}

# 로그 확인
logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f "$CONTAINER_NAME"
}

# 상태 확인
status() {
    print_info "컨테이너 상태:"
    docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    print_info "리소스 사용량:"
    docker stats "$CONTAINER_NAME" --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

# 컨테이너 접속
shell() {
    print_info "컨테이너 쉘에 접속합니다..."
    docker exec -it "$CONTAINER_NAME" /bin/bash
}

# 컨테이너 정리 (이미지 포함)
clean() {
    print_warn "컨테이너와 이미지를 삭제합니다..."
    read -p "정말 삭제하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" down --rmi all -v
        print_info "정리 완료"
    else
        print_info "취소되었습니다."
    fi
}

# 메인 로직
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    shell)
        shell
        ;;
    clean)
        clean
        ;;
    help|*)
        echo "사용법: $0 {start|stop|restart|logs|status|shell|clean}"
        echo ""
        echo "명령어:"
        echo "  start    - 컨테이너 시작"
        echo "  stop     - 컨테이너 중지"
        echo "  restart  - 컨테이너 재시작"
        echo "  logs     - 로그 확인 (실시간)"
        echo "  status   - 컨테이너 상태 확인"
        echo "  shell    - 컨테이너 쉘 접속"
        echo "  clean    - 컨테이너 및 이미지 삭제"
        exit 1
        ;;
esac

exit 0
