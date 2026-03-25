from __future__ import annotations

import copy
import threading


class DashboardCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._summary_by_user: dict[int, dict] = {}
        self._transactions_by_user: dict[int, dict] = {}

    def get_summary(self, user_id: int) -> dict | None:
        with self._lock:
            payload = self._summary_by_user.get(user_id)
            return copy.deepcopy(payload) if payload else None

    def get_transactions(self, user_id: int) -> dict | None:
        with self._lock:
            payload = self._transactions_by_user.get(user_id)
            return copy.deepcopy(payload) if payload else None

    def set(self, user_id: int, summary_payload: dict, transactions_payload: dict) -> None:
        with self._lock:
            self._summary_by_user[user_id] = copy.deepcopy(summary_payload)
            self._transactions_by_user[user_id] = copy.deepcopy(transactions_payload)

    def clear(self, user_id: int | None = None) -> None:
        with self._lock:
            if user_id is None:
                self._summary_by_user.clear()
                self._transactions_by_user.clear()
                return
            self._summary_by_user.pop(user_id, None)
            self._transactions_by_user.pop(user_id, None)


dashboard_cache = DashboardCache()
