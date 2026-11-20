"""Live scanner and historical sample backtest. No order placements."""
import argparse
import json
import os
import time
from pathlib import Path
from .market import INTERVAL_MS, HOUR_MS, fetch_klines, parse_klines
from .strategy import find_signal
from .filters import hourly_trend
from .backtest import backtest
from .notifier import send_discord, format_signal, format_status, test_message, preview_message

STATE = Path(".state/last_signal.json")

def read_state(path=STATE):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"last_signal_id":None}

def write_state(path, signal_id, close_time):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_signal_id":signal_id,"last_signal_candle_close_utc":close_time},indent=2)+"\n",encoding="utf-8")

def candles_for(interval, limit, now):
    duration = HOUR_MS if interval == "1h" else INTERVAL_MS
    return parse_klines(fetch_klines(interval=interval, limit=limit), now_ms=now, interval_ms=duration)

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("test","dry-run","scan","backtest","status","preview"),default="scan")
    args=parser.parse_args(argv)
    webhook=os.environ.get("DISCORD_WEBHOOK_URL","")
    if args.mode == "test":
        send_discord(webhook,test_message())
        print("Discord test delivered")
        return 0
    if args.mode == "preview":
        send_discord(webhook,preview_message())
        print("Fictional SHORT alert preview delivered to Discord; no live market data, no trade")
        return 0
    if args.mode in ("scan","status") and not webhook:
        print("Discord webhook not configured; skipping alert/status.")
        return 0
    now=int(time.time()*1000)
    bars=candles_for("5m",1000 if args.mode == "backtest" else 300,now)
    time.sleep(1.2)  # BingX Kline API: rate limit 1 req/sec per IP
    hours=candles_for("1h",300,now)
    print(f"Closed candles: 5m={len(bars)}, 1h={len(hours)}")
    if args.mode == "backtest":
        report=backtest(bars,hours)
        Path("reports").mkdir(parents=True,exist_ok=True)
        path=Path("reports/latest_backtest.json")
        path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k!="trade_details"},indent=2))
        print(f"Full report saved: {path}")
        return 0
    if not bars:
        raise RuntimeError("No closed 5m candles; cannot provide status")
    signal=find_signal(bars,now_ms=now)
    if args.mode == "status":
        trend=hourly_trend(hours,bars[-1].time+INTERVAL_MS)
        confirmed=bool(signal and trend==signal.side)
        send_discord(webhook,format_status(bars[-1],trend,confirmed,now))
        print("Discord market status delivered (not a trade signal)")
        return 0
    if not signal:
        print("No fresh 5m breakout/retest setup")
        return 0
    trend=hourly_trend(hours,signal.candle_time+INTERVAL_MS)
    if trend != signal.side:
        print(f"5m {signal.side} blocked by closed 1h trend ({trend or 'NEUTRAL/UNAVAILABLE'})")
        return 0
    if read_state().get("last_signal_id")==signal.id:
        print("Already notified")
        return 0
    if args.mode=="dry-run":
        print("DRY RUN (not sent):\n"+format_signal(signal))
        return 0
    send_discord(webhook,format_signal(signal)+"\nConfirmed 1h EMA20/50 trend: "+trend)
    write_state(STATE,signal.id,signal.candle_close_utc)
    print("Alert delivered")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
