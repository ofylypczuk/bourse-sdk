"""Bourse API client - https://www.bourse.pl/api/

    from bourse import Bourse
    b = Bourse("bk_...")            # or the BOURSE_KEY environment variable
    b.get("congress", ticker="NVDA")
    b.all("house", from_="2026-01-01")   # every page (follows "next")
    b.df("tv-picks", person="Cramer")    # pandas DataFrame (pip install pandas)
    b.bulk("insiders", format="ndjson")  # Premium: up to 50,000 rows at once

    Webhooks: Bourse.verify_webhook(secret, request.headers["Bourse-Signature"], raw_body)
"""
import hashlib
import hmac
import os
import time

import requests

__version__ = "1.3.0"
BASE = "https://api.bourse.pl/v1"


class BourseError(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code, self.message = status, code, message


class Bourse:
    def __init__(self, key=None, base=BASE, timeout=60):
        self.key = key or os.environ.get("BOURSE_KEY")
        if not self.key:
            raise ValueError("Pass your API key or set BOURSE_KEY (Bourse app: Settings -> API key).")
        self.base, self.timeout = base.rstrip("/"), timeout
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {self.key}", "User-Agent": f"bourse-python/{__version__}"})
        self.remaining_today = None

    @staticmethod
    def _params(params):
        # from_ -> from (Python keyword), skip None
        return {k.rstrip("_"): v for k, v in params.items() if v is not None}

    def get(self, endpoint, **params):
        """One request: /v1/<endpoint>, e.g. get("trump-trades/NVDA") or get("congress", ticker="NVDA")."""
        for proba in range(4):
            r = self.s.get(f"{self.base}/{endpoint.strip('/')}", params=self._params(params), timeout=self.timeout)
            self.remaining_today = r.headers.get("X-RateLimit-Remaining-Day", self.remaining_today)
            if r.status_code == 429 and "minute" in r.text and proba < 3:
                time.sleep(15 * (proba + 1))
                continue
            if r.status_code >= 400:
                try:
                    e = r.json()["error"]
                    raise BourseError(r.status_code, e.get("code"), e.get("message"))
                except (ValueError, KeyError):
                    raise BourseError(r.status_code, "http_error", r.text[:200])
            return r.json()
        raise BourseError(429, "rate_limited", "Too many requests")

    def all(self, dataset, max_rows=100000, **params):
        """Every row of a dataset (pages of 1000, follows "next")."""
        params.setdefault("limit", 1000)
        rows, offset = [], int(params.pop("offset", 0))
        while len(rows) < max_rows:
            page = self.get(dataset, offset=offset, **params)
            rows.extend(page.get("data", []))
            if not page.get("next") or not page.get("data"):
                break
            offset += len(page["data"])
        return rows[:max_rows]

    def df(self, dataset, **params):
        """pandas DataFrame with every row of a dataset (or the "data" of an analytics endpoint)."""
        import pandas as pd
        if "/" in dataset or dataset in ("ticker",):
            return pd.json_normalize(self.get(dataset, **params))
        try:
            return pd.DataFrame(self.all(dataset, **params))
        except BourseError as e:
            if e.code != "bad_sort":
                raise
            return pd.DataFrame(self.get(dataset, **params).get("data", []))

    def ticker(self, symbol):
        """Everything about one ticker in a single request."""
        return self.get(f"ticker/{symbol}")

    def strategy(self, strategy_id):
        return self.get(f"strategies/{strategy_id}")

    def usage(self):
        return self.get("usage")

    def bulk(self, dataset, format="csv", **params):
        """Premium / API Pro: the whole dataset at once as CSV text or a list of dicts (format="ndjson")."""
        r = self.s.get(f"{self.base}/bulk/{dataset}", params={**self._params(params), "format": format}, timeout=max(self.timeout, 180))
        if r.status_code >= 400:
            try:
                e = r.json()["error"]
                raise BourseError(r.status_code, e.get("code"), e.get("message"))
            except (ValueError, KeyError):
                raise BourseError(r.status_code, "http_error", r.text[:200])
        if format == "ndjson":
            import json
            return [json.loads(line) for line in r.text.splitlines() if line.strip()]
        return r.text

    @staticmethod
    def verify_webhook(secret, signature_header, body, tolerance=300):
        """True if a webhook request really comes from Bourse.

        signature_header: the "Bourse-Signature" header ("t=<unix>,v1=<hex>"), body: the raw request body (bytes or str).
        """
        try:
            parts = dict(p.split("=", 1) for p in signature_header.split(","))
            t, v1 = int(parts["t"]), parts["v1"]
        except (ValueError, KeyError, AttributeError):
            return False
        if tolerance and abs(time.time() - t) > tolerance:
            return False
        if isinstance(body, str):
            body = body.encode()
        expected = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)
