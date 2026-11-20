"""Closed-candle breakout/retest educational alerts; no orders."""
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from .market import Candle, INTERVAL_MS

@dataclass(frozen=True)
class Config:
    fast_ema: int = 20
    slow_ema: int = 50
    rsi_period: int = 14
    atr_period: int = 14
    breakout_lookback: int = 20
    breakout_max_age: int = 7
    retest_tolerance_atr: float = 0.25
    max_entry_distance_atr: float = 1.10
    min_volume_ratio: float = 0.85
    long_rsi_min: float = 50.0
    long_rsi_max: float = 75.0
    short_rsi_min: float = 25.0
    short_rsi_max: float = 50.0
    min_risk_atr: float = 0.50
    max_risk_atr: float = 2.50
    target_r_multiple: float = 2.0
    max_signal_age_minutes: float = 8.0

@dataclass(frozen=True)
class Signal:
    id: str
    side: str
    candle_time: int
    entry: float
    stop: float
    target: float
    breakout_level: float
    ema_fast: float
    ema_slow: float
    rsi: float
    atr: float
    volume_ratio: float
    risk_percent: float

    @property
    def candle_close_utc(self):
        return datetime.fromtimestamp((self.candle_time + INTERVAL_MS) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def ema(values, period):
    if len(values) < period: raise ValueError("Insufficient EMA data")
    out = mean(values[:period])
    for v in values[period:]:
        out = out + (2 / (period + 1)) * (v - out)
    return out

def rsi(values, period):
    if len(values) <= period: raise ValueError("Insufficient RSI data")
    diffs = [b-a for a,b in zip(values, values[1:])]
    gains = [max(0,d) for d in diffs]
    losses = [max(0,-d) for d in diffs]
    g, l = mean(gains[:period]), mean(losses[:period])
    for gain, loss in zip(gains[period:], losses[period:]):
        g = (g * (period - 1) + gain) / period
        l = (l * (period - 1) + loss) / period
    if g == l == 0: return 50.0
    if l == 0: return 100.0
    return 100 - 100 / (1 + g / l)

def atr(bars, period):
    if len(bars) <= period: raise ValueError("Insufficient ATR data")
    ranges = [max(b.high-b.low, abs(b.high-a.close), abs(b.low-a.close)) for a,b in zip(bars,bars[1:])]
    out = mean(ranges[:period])
    for x in ranges[period:]:
        out = (out * (period - 1) + x) / period
    return out

def find_signal(bars: list[Candle], now_ms: int, config: Config | None=None):
    cfg = config or Config()
    if len(bars) < 60: return None
    last = bars[-1]
    age = (now_ms - last.time - INTERVAL_MS) / 60000
    if not 0 <= age <= cfg.max_signal_age_minutes: return None
    if any(b.time - a.time != INTERVAL_MS for a,b in zip(bars,bars[1:])): return None
    close = [b.close for b in bars]
    fast, slow = ema(close,cfg.fast_ema), ema(close,cfg.slow_ema)
    strength, volatility = rsi(close,cfg.rsi_period), atr(bars,cfg.atr_period)
    if volatility <= 0: return None
    avg_volume = mean(b.volume for b in bars[-21:-1])
    volume_ratio = last.volume / avg_volume if avg_volume else 0
    if volume_ratio < cfg.min_volume_ratio: return None
    latest = len(bars)-1
    for back in range(1,cfg.breakout_max_age+1):
        idx = latest - back
        prev = bars[idx-cfg.breakout_lookback:idx]
        if len(prev) != cfg.breakout_lookback: continue
        upper, lower = max(b.high for b in prev), min(b.low for b in prev)
        breakout = bars[idx]
        for side, level in (("LONG",upper),("SHORT",lower)):
            middle = bars[idx+1:latest]
            tolerance = cfg.retest_tolerance_atr * volatility
            if side == "LONG":
                if not (fast > slow and cfg.long_rsi_min <= strength <= cfg.long_rsi_max): continue
                if not (breakout.close > level and bars[idx-1].close <= level): continue
                if not (last.low <= level + tolerance and last.close > level and last.close > last.open): continue
                if last.close-level > cfg.max_entry_distance_atr*volatility: continue
                if any(b.close < level-tolerance or (b.low <= level+tolerance and b.close > level and b.close > b.open) for b in middle): continue
                stop = min(last.low, level-0.4*volatility)-0.1*volatility
                stop = min(stop,last.close-cfg.min_risk_atr*volatility)
                risk = last.close-stop
                target = last.close + cfg.target_r_multiple*risk
            else:
                if not (fast < slow and cfg.short_rsi_min <= strength <= cfg.short_rsi_max): continue
                if not (breakout.close < level and bars[idx-1].close >= level): continue
                if not (last.high >= level-tolerance and last.close < level and last.close < last.open): continue
                if level-last.close > cfg.max_entry_distance_atr*volatility: continue
                if any(b.close > level+tolerance or (b.high >= level-tolerance and b.close < level and b.close < b.open) for b in middle): continue
                stop = max(last.high,level+0.4*volatility)+0.1*volatility
                stop = max(stop,last.close+cfg.min_risk_atr*volatility)
                risk = stop-last.close
                target = last.close-cfg.target_r_multiple*risk
                if target <= 0: continue
            if risk > cfg.max_risk_atr*volatility: continue
            return Signal(f"BTC-USDT:5m:{last.time}:{side}",side,last.time,last.close,stop,target,level,fast,slow,strength,volatility,volume_ratio,100*risk/last.close)
    return None
