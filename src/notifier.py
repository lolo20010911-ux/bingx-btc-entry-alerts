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

def send_discord(webhook_url, message):
    """Post a plain message to a Discord channel using a secret webhook."""
    from urllib.parse import urlparse
    parts = urlparse(webhook_url)
    if parts.scheme != "https" or parts.hostname not in ("discord.com", "discordapp.com") or not parts.path.startswith("/api/webhooks/"):
        raise RuntimeError("Invalid Discord webhook URL")
    data = json.dumps({"content": message, "allowed_mentions": {"parse": []}}).encode("utf-8")
    request = Request(webhook_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Discord HTTP {response.status}")
    except HTTPError as e:
        raise RuntimeError(f"Discord HTTP {e.code}; check your webhook secret") from None
    except (URLError, TimeoutError):
        raise RuntimeError("Discord connection failed") from None

def test_message():
    return "BingX alert TEST " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "\nDiscord connected. No order created."
