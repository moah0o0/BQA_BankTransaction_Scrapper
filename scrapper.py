import time
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Any

import requests
from dateutil.relativedelta import relativedelta
from pocketbase import PocketBase
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from main import BankAccount

TZ = ZoneInfo("Asia/Seoul")

# 우체국 API
API_URL = "https://epostbank.go.kr/IHSICH00R02.do"
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://epostbank.go.kr",
    "Referer": "https://epostbank.go.kr/errorCustom.do",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
}
REQUEST_TIMEOUT = 30  # 응답 없을 때 job이 영원히 멈추는 것 방지 (max_instances=1)
TYPE_MAP = {"입금": "수입", "지급": "지출", "지급취소": "수입"}
PERIOD_DELTA = {
    "month": relativedelta(months=1) - relativedelta(days=1),
    "week": relativedelta(weeks=1) - relativedelta(days=1),
    "day": relativedelta(days=0),
}


class PostbankScrapper:
    def __init__(self, account: "BankAccount", pb: PocketBase):
        self.account = account
        self.pb = pb
        self.session = requests.Session()

    def _log(self, level: str, msg: str, error: Exception | None = None) -> None:
        try:
            self.pb.collection("ScrapperLog").create({
                "job_id": self.account.id,
                "level": level,
                "message": msg,
                "error_trace": traceback.format_exc() if error else None,
            })
        except Exception:
            pass

    def _fetch(self, start: str, end: str, cursor: str = "") -> dict[str, Any]:
        data = {
            "IHSICHloginYn": "",
            "IHSICHbfLastDlngNoS8": cursor,
            "IHSICHnextDatExistYnS1": "Y",
            "IHSICHdepsActno": self.account.account_number,
            "IHSICHinptEpwd": self.account.account_password,
            "IHSICHbrdt": self.account.owner_birth,
            "IHSICHinqBgngYmd": start,
            "IHSICHinqEndYmd": end,
            "IHSICHinqDvsnS1": "1",
            "IHSICHinqSeqCdS1": "1",
        }
        resp = self.session.post(API_URL, headers=HEADERS, data=data, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _format(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "no": row.get("dlngNo"),
            "bank": self.account.id,
            "bankAccountNumber": self.account.account_number,
            "type": TYPE_MAP.get(row.get("pbmpRnpyDvsnCdNm", ""), "기타"),
            "datetime": (row.get("dlngYmd", "") + row.get("dlngTm", ""))[:12],
            "description": row.get("txmnEnm") or "공란",
            "money": int(row.get("dlngAmt", 0)),
        }

    def _scrape(self, start_str: str, end_str: str) -> list[dict[str, Any]]:
        results = []
        cursor = ""

        while True:
            data = self._fetch(start_str, end_str, cursor)
            if data.get("failed") is not True:
                items = data.get("inqDatagrid") or []
                results.extend(items)
            if data.get("nextDatExistYnS1") == "N":
                break
            cursor = data.get("bfLastDlngNoS8", "")
            time.sleep(2)

        txs = [self._format(r) for r in results]
        txs = [t for t in txs if t["no"] not in self.account.remove_list]
        return sorted(txs, key=lambda x: x["datetime"])

    def _exists(self, tx: dict[str, Any]) -> bool:
        records = self.pb.collection("Transaction").get_full_list(query_params={
            "filter": f'bank.id="{self.account.id}" && no="{tx["no"]}" && datetime="{tx["datetime"]}" && money={tx["money"]}'
        })
        return len(records) > 0

    def update(self) -> int:
        self._log("info", "Update 시작")
        today = datetime.now(TZ).date()
        delta = PERIOD_DELTA.get(self.account.update_period, relativedelta(days=0))
        start = today - delta

        start_str = start.strftime("%Y.%m.%d.")
        end_str = today.strftime("%Y.%m.%d.")

        try:
            txs = self._scrape(start_str, end_str)
        except Exception as e:
            self._log("error", f"스크래핑 실패 ({start_str}~{end_str})", e)
            return 0

        self._log("info", f"{start_str}~{end_str} 스크래핑 완료: {len(txs)}건")

        new_count = 0
        for tx in txs:
            if not self._exists(tx):
                self.pb.collection("Transaction").create(tx)
                new_count += 1

        self._log("info", f"업로드 완료: {new_count}건 추가")
        return new_count
