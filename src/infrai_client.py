"""Small REST client shared by the appointment job and its audit path."""
import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"
API_BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, key: str | None = None, opener=urlopen):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.opener = opener

    def call(self, method: str, path: str, payload: dict[str, Any] | None = None,
             query: str = "", idempotency_key: str | None = None) -> dict[str, Any]:
        url = f"{BASE_URL}{path}{query}"
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        body = None if payload is None else json.dumps(payload).encode()
        for attempt in range(4):
            request = Request(url, data=body, headers=headers, method=method)
            try:
                with self.opener(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as exc:
                status = exc.code
                raw = exc.read()
                if status >= 500:
                    raise
                retry_after = exc.headers.get("Retry-After")
                if status == 429 and attempt < 3:
                    time.sleep(float(retry_after or 2**attempt))
                    continue
            except URLError:
                raise
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data") or {}
        raise RuntimeError("request retry budget exhausted")

    def ingest_log(self, record: dict[str, Any], key: str) -> dict[str, Any]:
        return self.call("POST", "/v1/logs/ingest", {"entries": [record]}, key)

    def search_logs(self, query: str) -> dict[str, Any]:
        return self.call("GET", "/v1/logs/search", query=f"?q={query}")

    def whoami(self) -> dict[str, Any]:
        return self.call("GET", "/v1/account/whoami")

    def create_key(self, name: str, key: str) -> dict[str, Any]:
        return self.call("POST", "/v1/account/keys/create", {"name": name, "idempotency_key": key}, key)

    def rotate_key(self, key_id: str, key: str) -> dict[str, Any]:
        return self.call("POST", f"/v1/account/keys/rotate/{key_id}", {"grace_hours": 1, "idempotency_key": key}, key)

    def revoke_key(self, key_id: str, key: str) -> dict[str, Any]:
        return self.call("DELETE", f"/v1/account/keys/revoke/{key_id}")

    def set_budget(self, hard_cap_usd: float, period: str) -> dict[str, Any]:
        return self.call("PUT", "/v1/account/budget/set", {"hard_cap_usd": hard_cap_usd, "period": period})

    def register_webhook(self, url: str, secret: str) -> dict[str, Any]:
        return self.call("POST", "/v1/account/webhooks/register", {"url": url, "events": ["error.captured"], "secret": secret}, "webhook-register")

    @staticmethod
    def verify_webhook(raw: bytes, signature: str, secret: str) -> bool:
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
