"""1h trend confirmation using only already CLOSED hourly candles."""
from .market import HOUR_MS, Candle
from .strategy import ema

def hourly_trend(hourly: list[Candle], signal_close_ms: int) -> str | None:
    """Fail closed: return None on neutral, missing or stale data."""
    closed=[bar for bar in hourly if bar.time+HOUR_MS <= signal_close_ms]
    if len(closed)<60:
        return None
    last=closed[-1]
    if not 0<=signal_close_ms-(last.time+HOUR_MS)<HOUR_MS:
        return None
    recent=closed[-200:]
    if any(b.time-a.time != HOUR_MS for a,b in zip(recent,recent[1:])):
        return None
    close=[bar.close for bar in recent]
    fast,slow=ema(close,20),ema(close,50)
    if fast>slow and last.close>fast:
        return "LONG"
    if fast<slow and last.close<fast:
        return "SHORT"
    return None
