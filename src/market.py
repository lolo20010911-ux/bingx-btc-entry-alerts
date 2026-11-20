"""Public, read-only BingX 5m candles."""
import json
import math
import time
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

INTERVAL_MS = 300000
ENDPOINT = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

@dataclass(frozen=True)
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_api(cls, item):
        bar = cls(int(item["time"]), *(float(item[k]) for k in ("open", "high", "low", "close", "volume")))
        if (bar.time <= 0 or bar.time % INTERVAL_MS or
            not all(math.isfinite(x) for x in (bar.open, bar.high, bar.low, bar.close, bar.volume)) or
            bar.low <= 0 or bar.high < max(bar.open, bar.close, bar.low) or
            bar.low > min(bar.open, bar.close) or bar.volume < 0):
            raise ValueError("Invalid candle")
        return bar

def parse_klines(payload, now_ms, buffer_ms=10000):
    if not isinstance(payload, dict) or str(payload.get("code")) != "0" or not isinstance(payload.get("data"), list):
        raise ValueError("Invalid BingX response")
    bars = {b.time: b for b in (Candle.from_api(x) for x in payload["data"])}
    return [b for _, b in sorted(bars.items()) if b.time + INTERVAL_MS + buffer_ms <= now_ms]

def fetch_klines(symbol="BTC-USDT", limit=300, attempts=3):
    if symbol != "BTC-USDT" or not 100 <= limit <= 1000:
        raise ValueError("Unsupported symbol or limit")
    url = ENDPOINT + "?" + urlencode({"symbol": symbol, "interval": "5m", "limit": limit})
    for index in range(attempts):
        try:
            with urlopen(Request(url, headers={"Accept": "application/json", "User-Agent": "bingx-entry-monitor/1"}), timeout=18) as res:
                return json.load(res)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            if index == attempts - 1:
                raise RuntimeError("BingX market request failed") from None
            time.sleep(index + 1)
