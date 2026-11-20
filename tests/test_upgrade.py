"""Upgrade tests: no look-ahead, closed 1h bars and conservative backtest."""
import unittest
from unittest.mock import patch
from src.market import Candle,INTERVAL_MS,HOUR_MS,parse_klines
from src.filters import hourly_trend
from src.backtest import backtest
from src.strategy import Signal

BASE=1700000000000//HOUR_MS*HOUR_MS

def hourbars(count=80,slope=0.5):
    return [Candle(BASE+(i-count)*HOUR_MS,100+i*slope,101+i*slope,99+i*slope,100+i*slope,100.) for i in range(count)]

def fivebars(count=270):
    return [Candle(BASE+i*INTERVAL_MS,100.,101.,99.,100.,100.) for i in range(count)]

class UpgradeTests(unittest.TestCase):
    def test_one_hour_long_and_short(self):
        h=hourbars()
        self.assertEqual(hourly_trend(h,h[-1].time+HOUR_MS),"LONG")
        h=hourbars(slope=-0.5)
        self.assertEqual(hourly_trend(h,h[-1].time+HOUR_MS),"SHORT")
    def test_hourly_no_lookahead(self):
        h=hourbars()
        end=h[-1].time+HOUR_MS
        future=Candle(h[-1].time+HOUR_MS,999.,999.,999.,999.,2.)
        self.assertEqual(hourly_trend(h+[future],end),"LONG")
        self.assertIsNone(hourly_trend(h+[future],end+2*HOUR_MS+1))
    def test_reject_missing_hour(self):
        h=hourbars()
        h.pop(45)
        self.assertIsNone(hourly_trend(h,h[-1].time+HOUR_MS))
    def test_parse_1h_excludes_unclosed(self):
        def raw(i):
            return dict(time=BASE+i*HOUR_MS,open="100",high="101",low="99",close="100",volume="1")
        bars=parse_klines({"code":0,"data":[raw(0),raw(1),raw(2)]},BASE+2*HOUR_MS+20000,interval_ms=HOUR_MS)
        self.assertEqual(len(bars),2)
    def test_stop_first_and_fees(self):
        bars=fivebars()
        s=bars[250]
        sig=Signal("x","LONG",s.time,100.,99.,102.,99.8,105.,103.,60.,3.,1.2,1.)
        def candidate(window,now_ms):
            return sig if window[-1].time==s.time else None
        with patch("src.backtest.find_signal",side_effect=candidate),patch("src.backtest.hourly_trend",return_value="LONG"):
            d=backtest(bars,hourbars())
        self.assertEqual(d["trades"],1)
        self.assertEqual(d["trade_details"][0]["exit_reason"],"stop")
        self.assertLess(d["trade_details"][0]["net_r"],-1)
    def test_rejects_wrong_hourly_direction(self):
        bars=fivebars()
        s=bars[250]
        sig=Signal("x","LONG",s.time,100.,99.,102.,99.8,105.,103.,60.,3.,1.2,1.)
        with patch("src.backtest.find_signal",return_value=sig),patch("src.backtest.hourly_trend",return_value="SHORT"):
            d=backtest(bars,hourbars())
        self.assertEqual(d["trades"],0)
        self.assertGreater(d["blocked_by_one_hour_trend"],0)
    def test_rejects_5m_gaps(self):
        bars=fivebars()
        del bars[20]
        with self.assertRaisesRegex(ValueError,"gaps"):
            backtest(bars,hourbars())
