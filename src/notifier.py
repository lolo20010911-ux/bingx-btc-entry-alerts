"""Deliver BTC alerts via Discord webhook. Never log secret webhook URLs."""
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def format_signal(signal):
    return (
        f"BingX BTC-USDT PERPETUAL | 5m | {signal.side}\n"
        f"Breakout + first retest | Candle: {signal.candle_close_utc}\n"
        f"Indicative entry: {signal.entry:,.2f} USDT\n"
        f"Retest: {signal.breakout_level:,.2f}\n"
        f"Stop-loss reference: {signal.stop:,.2f}\n"
        f"Take-profit reference (2R): {signal.target:,.2f}\n"
        f"Entry-to-stop: {signal.risk_percent:.2f}% (not account risk)\n"
        f"EMA20/50: {signal.ema_fast:,.2f} / {signal.ema_slow:,.2f}\n"
        f"RSI14: {signal.rsi:.1f}, ATR14: {signal.atr:.2f}\n"
        f"Volume ratio: {signal.volume_ratio:.2f}x\n\n"
        "Signal only, NO ORDER. Check the live price and costs; this is not a guaranteed entry."
    )

def preview_message():
    """A clearly fictional SHORT alert to preview the real Discord layout.

    Fixed demo values; never obtains market data, never generates a trading order.
    """
    from .strategy import Signal
    example = Signal(
        id="DEMO-ONLY",
        side="SHORT",
        candle_time=1735689600000,   # historical sample label: 2025-01-01 00:05 UTC
        entry=60000.0,
        stop=60120.0,
        target=59760.0,
        breakout_level=60060.0,
        ema_fast=59940.0,
        ema_slow=60100.0,
        rsi=40.5,
        atr=90.0,
        volume_ratio=1.35,
        risk_percent=0.20,
    )
    return (
        "TEST / DEMO ONLY — FICTIONAL PRICES. DO NOT TRADE THIS.\\n"
        + format_signal(example)
        + "\\nConfirmed 1h EMA20/50 trend: SHORT (FICTIONAL)\\n"
        + "TEST / DEMO ONLY — no real setup detected, no order placed."
    )

def format_status(last_closed_5m, hourly_direction, qualified, now_ms):
    """Human-readable heartbeat that does not imply a trade recommendation."""
    from .market import INTERVAL_MS
    last_close_ms = last_closed_5m.time + INTERVAL_MS
    age_minutes = (now_ms - last_close_ms) / 60000
    dt = datetime.fromtimestamp(last_close_ms / 1000, tz=timezone.utc)
    trend = hourly_direction or "NEUTRAL / no confirmed trend"
    setup = "QUALIFIED CANDIDATE - check current chart before considering a trade" if qualified else "No confirmed entry on latest closed candle"
    warning = "CAUTION: 5m data may be stale" if age_minutes > 8 else "5m data is recent"
    return (
        "BingX BTC/USDT BOT STATUS (not a trading alert)\n"
        f"Last completed 5m candle: {dt:%Y-%m-%d %H:%M} UTC\n"
        f"5m close: {last_closed_5m.close:,.2f} USDT\n"
        f"1h EMA20/50 direction: {trend}\n"
        f"Entry setup: {setup}\n"
        f"Data: {warning}; delay {max(0, age_minutes):.1f} min\n"
        "Read-only monitoring. No order created. Strategy not validated for live futures trading."
    )

def send_discord(webhook_url, message):
    """Post a plain message to a Discord channel using a secret webhook."""
    from urllib.parse import urlparse
    parts = urlparse(webhook_url)
    if parts.scheme != "https" or parts.hostname not in ("discord.com", "discordapp.com") or not parts.path.startswith("/api/webhooks/"):
        raise RuntimeError("Invalid Discord webhook URL")
    data = json.dumps({"content": message, "allowed_mentions": {"parse": []}}).encode("utf-8")
    request = Request(webhook_url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "DiscordBot (https://github.com/lolo20010911-ux/bingx-btc-entry-alerts, 1.0)"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Discord HTTP {response.status}")
    except HTTPError as e:
        # Never print the webhook URL or raw response body: both can contain secrets.
        if e.code == 403:
            raise RuntimeError("Discord HTTP 403: access denied. Check webhook channel permissions or Discord network/Cloudflare restrictions.") from None
        if e.code == 404:
            raise RuntimeError("Discord HTTP 404: webhook no longer exists; create a new webhook secret.") from None
        raise RuntimeError(f"Discord HTTP {e.code}: message not delivered.") from None
    except (URLError, TimeoutError):
        raise RuntimeError("Discord connection failed") from None

def test_message():
    return "BingX alert TEST " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "\nDiscord connected. No order created."
