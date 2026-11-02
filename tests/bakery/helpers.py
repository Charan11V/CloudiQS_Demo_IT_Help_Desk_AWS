"""Shared HTTP helpers for Bakery integration tests."""
from __future__ import annotations

import http.cookiejar
import json
import os
import urllib.error
import urllib.request
from typing import Any

BASE = os.environ.get("BAKERY_API_URL", "http://127.0.0.1:8002")


class ApiSession:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            f"{BASE}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with self.opener.open(req, timeout=90) as resp:
                raw = resp.read().decode()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                payload = json.loads(raw) if raw else {"detail": str(e)}
            except json.JSONDecodeError:
                payload = {"detail": raw or str(e)}
            return e.code, payload

    def login(self, user_id: str) -> dict:
        code, data = self.request("POST", "/api/auth/demo-login", {"user_id": user_id})
        assert code == 200, data
        assert data.get("success") is True
        return data
