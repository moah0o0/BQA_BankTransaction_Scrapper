import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:
    pb_url: str
    pb_user: str
    pb_pass: str
    thread_pool_size: int = 8
    default_interval: int = 60


# ============================================
# 설정 (환경변수 우선, 없으면 기본값 사용)
# ============================================

config = Config(
    pb_url=os.getenv("PB_URL") or "",
    pb_user=os.getenv("PB_USER") or "",
    pb_pass=os.getenv("PB_PASS") or "",
    thread_pool_size=int(os.getenv("THREAD_POOL_SIZE", "8")),
    default_interval=int(os.getenv("DEFAULT_INTERVAL", "60")),
)


def validate(cfg: Config) -> None:
    """필수 환경변수 누락 시 즉시 종료 (조용히 Heartbeat만 실패하는 것 방지)"""
    missing = [name for name, value in (
        ("PB_URL", cfg.pb_url), ("PB_USER", cfg.pb_user), ("PB_PASS", cfg.pb_pass),
    ) if not value]
    if missing:
        raise SystemExit(f"필수 환경변수 누락: {', '.join(missing)}")
