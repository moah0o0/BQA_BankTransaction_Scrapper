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
