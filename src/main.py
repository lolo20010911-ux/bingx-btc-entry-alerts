"""Run the read-only monitor through Python module interface."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from .market import fetch_klines, parse_klines
from .strategy import find_signal
from .notifier import send_telegram, format_signal, test_message

STATE = Path(".state/last_signal.json")

def read_state(path=STATE):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"last_signal_id":None}

def write_state(path, signal_id, close_time):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({"last_signal_id":signal_id,"last_signal_candle_close_utc":close_time},indent=2)+"\n",encoding="utf-8")

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("test","dry-run","scan"),default="scan")
    args=parser.parse_args(argv)
    token=os.environ.get("TELEGRAM_BOT_TOKEN","")
    chat=os.environ.get("TELEGRAM_CHAT_ID","")
    if args.mode == "test":
        send_telegram(token,chat,test_message())
        print("Telegram test delivered")
        return 0
    if args.mode == "scan" and (not token or not chat):
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID",file=sys.stderr)
        return 2
    now=int(time.time()*1000)
    bars=parse_klines(fetch_klines(),now_ms=now)
    print(f"Closed candles: {len(bars)}")
    signal=find_signal(bars,now_ms=now)
    if not signal:
        print("No fresh setup")
        return 0
    if read_state().get("last_signal_id")==signal.id:
        print("Already notified")
        return 0
    if args.mode=="dry-run":
        print("DRY RUN:\n"+format_signal(signal))
        return 0
    send_telegram(token,chat,format_signal(signal))
    write_state(STATE,signal.id,signal.candle_close_utc)
    print("Alert delivered")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
