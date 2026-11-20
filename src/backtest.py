"""Fee-aware, single-position sample backtest. No trading orders."""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from .market import Candle,INTERVAL_MS
from .strategy import find_signal
from .filters import hourly_trend

def utc(ms:int)->str:
    return datetime.fromtimestamp(ms/1000,tz=timezone.utc).isoformat(timespec="minutes")

@dataclass(frozen=True)
class Trade:
    time_utc:str
    side:str
    entry:float
    exit:float
    exit_reason:str
    net_r:float

def backtest(bars:list[Candle],hourly:list[Candle],*,fee_rate:float=0.0005,slippage_rate:float=0.0002,max_hold_bars:int=48)->dict:
    """Next-open execution; conservative same-bar stop-first; net results in R units.
    
    Does not model funding, liquidations, the order book or actual latency.
    """
    if not (0<=fee_rate<.01 and 0<=slippage_rate<.01 and max_hold_bars>0):
        raise ValueError("Invalid backtest assumptions")
    if len(bars)<251:
        raise ValueError("Need at least 251 completed 5m bars")
    if any(b.time-a.time!=INTERVAL_MS for a,b in zip(bars,bars[1:])):
        raise ValueError("5m history contains gaps; backtest aborted")
    if any(b.time<=a.time for a,b in zip(hourly,hourly[1:])):
        raise ValueError("1h history must be strictly increasing")
    trades=[]
    matched=0
    trend_blocked=0
    skipped_fills=0
    index=250
    while index<len(bars)-1:
        end_ms=bars[index].time+INTERVAL_MS
        candidate=find_signal(bars[max(0,index-249):index+1],end_ms+10000)
        if candidate is None:
            index+=1
            continue
        matched+=1
        if hourly_trend(hourly,end_ms)!=candidate.side:
            trend_blocked+=1
            index+=1
            continue
        first=bars[index+1]
        base_entry=first.open
        if abs(base_entry-candidate.entry)>0.35*candidate.atr:
            skipped_fills+=1
            index+=1
            continue
        direction=1 if candidate.side=="LONG" else -1
        effective_entry=base_entry*(1+direction*slippage_rate)
        risk=direction*(effective_entry-candidate.stop)
        reward=direction*(candidate.target-effective_entry)
        if risk<=0 or reward<=0:
            skipped_fills+=1
            index+=1
            continue
        last_exit_index=min(index+max_hold_bars,len(bars)-1)
        exit_base=bars[last_exit_index].close
        reason="time"
        for k in range(index+1,last_exit_index+1):
            b=bars[k]
            touched_stop=(b.low<=candidate.stop) if direction==1 else (b.high>=candidate.stop)
            touched_target=(b.high>=candidate.target) if direction==1 else (b.low<=candidate.target)
            if touched_stop:
                exit_base=candidate.stop
                reason="stop"
                last_exit_index=k
                break
            if touched_target:
                exit_base=candidate.target
                reason="target"
                last_exit_index=k
                break
        effective_exit=exit_base*(1-direction*slippage_rate)
        pnl_per_unit=direction*(effective_exit-effective_entry)
        fees_per_unit=fee_rate*(effective_entry+effective_exit)
        net_r=(pnl_per_unit-fees_per_unit)/risk
        trades.append(Trade(utc(end_ms),candidate.side,round(effective_entry,2),round(effective_exit,2),reason,round(net_r,5)))
        index=last_exit_index+1
    results=[t.net_r for t in trades]
    wins=sum(r>0 for r in results)
    cumulative=0.
    peak=0.
    drawdown=0.
    loss_streak=0
    max_loss_streak=0
    for r in results:
        cumulative+=r
        peak=max(peak,cumulative)
        drawdown=max(drawdown,peak-cumulative)
        loss_streak=loss_streak+1 if r<=0 else 0
        max_loss_streak=max(max_loss_streak,loss_streak)
    profit=sum(r for r in results if r>0)
    loss=-sum(r for r in results if r<0)
    return {
        "data_start_utc":utc(bars[0].time),
        "data_end_utc":utc(bars[-1].time+INTERVAL_MS),
        "five_minute_candles":len(bars),
        "five_minute_setups":matched,
        "blocked_by_one_hour_trend":trend_blocked,
        "skipped_due_to_next_open":skipped_fills,
        "trades":len(trades),
        "wins":wins,
        "win_rate_percent":round(100*wins/len(trades),2) if trades else None,
        "total_net_r":round(sum(results),3),
        "average_net_r":round(sum(results)/len(trades),3) if trades else None,
        "profit_factor":round(profit/loss,3) if loss else None,
        "max_drawdown_r":round(drawdown,3),
        "max_consecutive_losses":max_loss_streak,
        "assumptions":{"taker_fee_per_side_percent":fee_rate*100,"slippage_per_fill_percent":slippage_rate*100,"max_hold_bars":max_hold_bars,"both_hit_same_bar":"stop first","entry":"next 5m open"},
        "warnings":["Very short sample (API gives at most 1000 5m bars, ~3.5 days).","R multiples are not account equity returns.","No funding, liquidation, position sizing or latency simulation.","Historical results do not predict future returns."],
        "trade_details":[asdict(trade) for trade in trades],
    }
