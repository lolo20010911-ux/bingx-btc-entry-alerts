"""Telegram-only alert delivery. Do not log bot secrets."""
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

def send_telegram(token, chat_id, message):
    if not token or not chat_id: raise RuntimeError("Missing Telegram secrets")
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    data = json.dumps({"chat_id":chat_id,"text":message,"disable_web_page_preview":True}).encode()
    request = Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
    except HTTPError as e:
        raise RuntimeError(f"Telegram HTTP {e.code}; verify bot token/chat ID") from None
    except (URLError,TimeoutError,json.JSONDecodeError):
        raise RuntimeError("Telegram network or response error") from None
    if not isinstance(result,dict) or result.get("ok") is not True:
        raise RuntimeError("Telegram rejected message")

def test_message():
    return "BingX alert TEST " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "\nTelegram connected. No order created."
