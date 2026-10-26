import logging
import signal
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime

import psutil
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from pocketbase import PocketBase
from zoneinfo import ZoneInfo

from config import Config, config, validate
from scrapper import PostbankScrapper

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Seoul")


@dataclass
class BankAccount:
    """PocketBase BankSetting에서 로드된 계정 정보"""
    id: str
    account_number: str
    account_password: str
    owner_birth: str
    init_date: str
    update_period: str
    interval_seconds: int
    remove_list: tuple[int, ...]


class App:
    def __init__(self, config: Config):
        self.config = config
        self.scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(config.thread_pool_size)},
            job_defaults={"max_instances": 1, "coalesce": True},
        )
        self.heartbeat_id: str | None = None
        self.host = socket.gethostname()
        self.active_jobs: dict[str, BankAccount] = {}

    def _get_pb(self) -> PocketBase:
        pb = PocketBase(self.config.pb_url)
        pb.collection("users").auth_with_password(self.config.pb_user, self.config.pb_pass)
        return pb

    def _parse_account(self, record) -> BankAccount:
        """BankSetting 레코드를 BankAccount로 변환"""
        remove_str = getattr(record, "remove_list", "") or ""
        remove_list = tuple(int(x) for x in str(remove_str).split(",") if x.strip())

        return BankAccount(
            id=record.id,
            account_number=getattr(record, "account_number", ""),
            account_password=getattr(record, "account_password", ""),
            owner_birth=getattr(record, "owner_birth", ""),
            init_date=getattr(record, "init_date", ""),
            update_period=getattr(record, "update_period", "month"),
            # 빈 숫자 필드는 0으로 오므로 기본값 사용 (0이면 APScheduler가 1초마다 실행함)
            interval_seconds=int(getattr(record, "interval_seconds", 0) or self.config.default_interval),
            remove_list=remove_list,
        )

    def _run(self, account: BankAccount) -> None:
        try:
            scrapper = PostbankScrapper(account, self._get_pb())
            scrapper.update()
        except Exception as e:
            log.error(f"[{account.id}] 실패: {e}")

    def _sync_accounts(self, pb: PocketBase) -> None:
        """BankSetting에서 enabled된 계정을 동기화"""
        try:
            # enabled=true인 계정만 조회
            records = pb.collection("BankSetting").get_full_list(query_params={
                "filter": "scraping_enabled=true"
            })
            enabled_ids = {r.id for r in records}

            # 비활성화된 job 제거
            for job_id in list(self.active_jobs.keys()):
                if job_id not in enabled_ids:
                    self.scheduler.remove_job(job_id)
                    del self.active_jobs[job_id]
                    log.info(f"[{job_id}] 스크래핑 비활성화")

            # 새 계정 추가 또는 기존 계정 업데이트
            for record in records:
                account = self._parse_account(record)
                existing = self.active_jobs.get(account.id)

                if existing is None:
                    # 새 계정 추가
                    self.scheduler.add_job(
                        self._run, "interval",
                        args=[account],
                        seconds=account.interval_seconds,
                        id=account.id,
                        replace_existing=True,
                    )
                    self.active_jobs[account.id] = account
                    log.info(f"[{account.id}] 스크래핑 활성화 (매 {account.interval_seconds}초)")
                    # 즉시 첫 실행
                    self._run(account)

                elif existing.interval_seconds != account.interval_seconds:
                    # 주기 변경
                    self.scheduler.reschedule_job(
                        account.id,
                        trigger="interval",
                        seconds=account.interval_seconds,
                    )
                    self.active_jobs[account.id] = account
                    log.info(f"[{account.id}] 주기 변경: {existing.interval_seconds}초 → {account.interval_seconds}초")

        except Exception as e:
            log.warning(f"계정 동기화 실패: {e}")

    def _heartbeat(self) -> None:
        try:
            pb = self._get_pb()
            now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
            proc = psutil.Process()
            memory_mb = proc.memory_info().rss / 1024 / 1024
            cpu_percent = proc.cpu_percent(interval=0.1)

            # 계정 동기화
            self._sync_accounts(pb)

            if self.heartbeat_id:
                pb.collection("ScrapperHeartbeat").update(self.heartbeat_id, {
                    "status": "running",
                    "last_ping": now,
                    "memory_mb": round(memory_mb, 2),
                    "cpu_percent": round(cpu_percent, 2),
                    "active_jobs": len(self.active_jobs),
                })
            else:
                record = pb.collection("ScrapperHeartbeat").create({
                    "host": self.host,
                    "status": "running",
                    "started_at": now,
                    "last_ping": now,
                    "memory_mb": round(memory_mb, 2),
                    "cpu_percent": round(cpu_percent, 2),
                    "active_jobs": len(self.active_jobs),
                })
                self.heartbeat_id = record.id
        except Exception as e:
            log.warning(f"Heartbeat 실패: {e}")

    def _stop_heartbeat(self) -> None:
        if not self.heartbeat_id:
            return
        try:
            pb = self._get_pb()
            pb.collection("ScrapperHeartbeat").update(self.heartbeat_id, {
                "status": "stopped",
                "last_ping": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            })
        except Exception:
            pass

    def start(self) -> None:
        log.info("스크래퍼 시작")

        # 초기 동기화 및 Heartbeat
        self._heartbeat()
        self.scheduler.add_job(
            self._heartbeat, "interval",
            seconds=60,
            id="heartbeat",
        )

        self.scheduler.start()

    def stop(self) -> None:
        self._stop_heartbeat()
        self.scheduler.shutdown(wait=False)


def main() -> None:
    validate(config)
    app = App(config)

    def shutdown(*_):
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    app.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        app.stop()


if __name__ == "__main__":
    main()
