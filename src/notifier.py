"""Discord webhook presentation for read-only BingX BTC-USDT alerts.

All demo prices are fictional; never reveal the webhook URL in logs.
"""
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

GREEN = 0x2ECC71
RED = 0xED4245
BLUE = 0x5865F2
AMBER = 0xF1C40F

def field(name, value, inline=True):
    return {"name": name, "value": value, "inline": inline}

def format_signal(signal):
    """Plain text retained for dry-run logging and backwards compatibility."""
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

def preview_signal():
    """Fixed sample signal, independent of BingX market data."""
    from .strategy import Signal
    return Signal(
        id="DEMO-ONLY", side="SHORT", candle_time=1735689600000,
        entry=60000.0, stop=60120.0, target=59760.0,
        breakout_level=60060.0, ema_fast=59940.0, ema_slow=60100.0,
        rsi=40.5, atr=90.0, volume_ratio=1.35, risk_percent=0.20,
    )

def preview_message():
    """Legacy text preview; the actual Discord preview is now an embed."""
    return (
        "TEST / DEMO ONLY — FICTIONAL PRICES. DO NOT TRADE THIS.\n"
        + format_signal(preview_signal())
        + "\nConfirmed 1h EMA20/50 trend: SHORT (FICTIONAL)\n"
        + "TEST / DEMO ONLY — no real setup detected, no order placed."
    )

def build_signal_embed(signal, trend=None, demo=False):
    """Native Discord embed for real trade candidate or unmistakable demo."""
    if signal.side not in ("LONG", "SHORT"):
        raise ValueError("Invalid signal side")
    price = lambda n: f"**{n:,.2f} USDT**"
    title = f"{'🧪 DEMO • ' if demo else 'BTC/USDT • '}{signal.side}"
    if demo:
        title = "🧪 DEMO ONLY • BTC/USDT SHORT"
        description = (
            "🚫 **KITALÁLT ÁRAK – NEM VALÓDI BELÉPŐ!**\n"
            "A jelzés kinézetének tesztje. Ne nyiss pozíciót ezekkel az értékekkel."
        )
    else:
        description = (
            "**5m kitörés + visszateszt** • BingX perpetual\n"
            "Technikai figyelmeztetés, nem garantált belépő. Ellenőrizd az aktuális árat."
        )
    candle_iso = datetime.fromtimestamp(
        (signal.candle_time + 300000) / 1000, tz=timezone.utc
    ).isoformat()
    return {
        "title": title,
        "description": description,
        "color": BLUE if demo else (GREEN if signal.side == "LONG" else RED),
        "fields": [
            field("🎯 BELÉPŐ (5m záró)", price(signal.entry)),
            field("🛑 STOP-LOSS", price(signal.stop)),
            field("✅ TAKE-PROFIT · 2R", price(signal.target)),
            field("Visszateszt szint", f"`{signal.breakout_level:,.2f}`"),
            field("Árfolyam-kockázat", f"`{signal.risk_percent:.2f}%`"),
            field("Risk / Reward", "`1 : 2`"),
            field("1H trend", f"`{trend or 'N/A'}{' · DEMO' if demo else ''}`"),
            field("RSI14 / ATR14", f"`{signal.rsi:.1f} / {signal.atr:.2f}`"),
            field("Volumen", f"`{signal.volume_ratio:.2f}×`"),
            field("EMA20 / EMA50", f"`{signal.ema_fast:,.2f} / {signal.ema_slow:,.2f}`", inline=False),
            field("Jelző gyertya (UTC)", f"`{signal.candle_close_utc}`", inline=False),
        ],
        "footer": {
            "text": (
                "DEMO ONLY • Kitalált árak • Nincs pozíciónyitás"
                if demo else
                "Csak technikai jelzés • Nincs pozíciónyitás • Ellenőrizd a díjakat és a live árat"
            )
        },
        "timestamp": candle_iso,
    }

def preview_embed():
    """Standalone demo without real market API calls."""
    return build_signal_embed(preview_signal(), trend="SHORT", demo=True)

def format_status(last_closed_5m, hourly_direction, qualified, now_ms):
    """Plain text status for backwards compatibility."""
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

def build_status_embed(last_closed_5m, hourly_direction, qualified, now_ms):
    """Discord market heartbeat; never presents itself as a trade signal."""
    from .market import INTERVAL_MS
    close_ms = last_closed_5m.time + INTERVAL_MS
    age_minutes = max(0.0, (now_ms - close_ms) / 60000)
    trend = hourly_direction or "SEMLEGES / NINCS ADAT"
    freshness = "FRISS" if age_minutes <= 8 else "KÉSŐ / RÉGI ADAT"
    setup = "Lehetséges megerősített setup – ellenőrzés szükséges" if qualified else "Nincs megerősített belépő"
    return {
        "title": "📊 BTC/USDT • Piaci állapot",
        "description": "Állapotjelentés, **nem kereskedési jelzés**.",
        "color": AMBER if age_minutes > 8 else BLUE,
        "fields": [
            field("BTC 5m záróár", f"**{last_closed_5m.close:,.2f} USDT**"),
            field("1H trend", f"**{trend}**"),
            field("Belépő szűrő", setup, inline=False),
            field("Adatok", freshness),
            field("Adatkésés", f"`{age_minutes:.1f} perc`"),
            field("Utolsó lezárt gyertya", datetime.fromtimestamp(
                close_ms / 1000, tz=timezone.utc
            ).strftime("`%Y-%m-%d %H:%M UTC`"), inline=False),
        ],
        "timestamp": datetime.fromtimestamp(close_ms/1000, tz=timezone.utc).isoformat(),
        "footer": {"text": "STATUS ONLY • Nincs automatikus kötés • Nincs garantált beszálló"},
    }

def build_test_embed():
    """Connection test: no fictitious entry prices."""
    now = datetime.now(timezone.utc)
    return {
        "title": "✅ BTC Alert • Discord kapcsolat sikeres",
        "description": "A GitHub Actions webhook képes értesítést küldeni a csatornára.",
        "color": GREEN,
        "fields": [
            field("Teszt ideje", now.strftime("`%Y-%m-%d %H:%M UTC`")),
            field("Állapot", "**ONLINE – csak webhook teszt**"),
        ],
        "footer": {"text": "TEST ONLY • Nincs piaci jelzés • Nincs pozíciónyitás"},
        "timestamp": now.isoformat(),
    }

def test_message():
    return "BingX alert TEST " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "\nDiscord connected. No order created."

def send_discord(webhook_url, content=None, embeds=None):
    """Send Discord content, native rich embeds, or both without exposing secrets."""
    parts = urlparse(webhook_url)
    if (parts.scheme != "https" or parts.hostname not in ("discord.com", "discordapp.com")
            or not parts.path.startswith("/api/webhooks/")):
        raise RuntimeError("Invalid Discord webhook URL")
    if not content and not embeds:
        raise ValueError("Discord message requires content or embeds")
    payload = {"allowed_mentions": {"parse": []}}
    if content:
        if not isinstance(content, str) or len(content) > 2000:
            raise ValueError("Discord content must be text up to 2000 chars")
        payload["content"] = content
    if embeds:
        if not isinstance(embeds, list) or len(embeds) > 10:
            raise ValueError("Discord embeds must be a list of at most 10 items")
        payload["embeds"] = embeds
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        webhook_url, data=data, method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DiscordBot (https://github.com/lolo20010911-ux/bingx-btc-entry-alerts, 1.0)",
        }
    )
    try:
        with urlopen(request, timeout=15) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Discord HTTP {response.status}")
    except HTTPError as e:
        if e.code == 403:
            raise RuntimeError("Discord HTTP 403: check webhook permissions or network restrictions") from None
        if e.code == 404:
            raise RuntimeError("Discord HTTP 404: the webhook does not exist") from None
        raise RuntimeError(f"Discord HTTP {e.code}: message not delivered") from None
    except (URLError, TimeoutError):
        raise RuntimeError("Discord connection failed") from None
