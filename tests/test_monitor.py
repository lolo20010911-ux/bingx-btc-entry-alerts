import unittest
from src.market import Candle, INTERVAL_MS, parse_klines
from src.strategy import ema, rsi, atr, find_signal
from src.notifier import test_message

START=1700000100000

def bar(i, price=100.0):
    return Candle(START+i*INTERVAL_MS,price,price+1,price-1,price,1.0)

class MonitorTests(unittest.TestCase):
    def test_unfinished_candle_is_excluded(self):
        def raw(i):
            return dict(time=START+i*INTERVAL_MS,open="100",high="101",low="99",close="100",volume="1")
        out=parse_klines({"code":0,"data":[raw(2),raw(1),raw(0)]},START+2*INTERVAL_MS+20000)
        self.assertEqual([c.time for c in out],[START,START+INTERVAL_MS])
    def test_bad_response_rejected(self):
        with self.assertRaises(ValueError):
            parse_klines({"code":1,"data":[]},START)
    def test_ema(self):
        self.assertAlmostEqual(ema([10.0]*50,20),10)
    def test_rsi(self):
        self.assertEqual(rsi([10.0]*30,14),50)
    def test_rising_rsi(self):
        self.assertEqual(rsi([float(i) for i in range(30)],14),100)
    def test_atr(self):
        self.assertGreater(atr([bar(i) for i in range(60)],14),0)
    def test_no_breakout(self):
        bars=[bar(i) for i in range(100)]
        self.assertIsNone(find_signal(bars,bars[-1].time+INTERVAL_MS+20000))
    def test_stale_bars(self):
        bars=[bar(i) for i in range(100)]
        self.assertIsNone(find_signal(bars,bars[-1].time+INTERVAL_MS+900000))
    def test_gap_rejected(self):
        bars=[bar(i) for i in range(100)]
        del bars[-20]
        self.assertIsNone(find_signal(bars,bars[-1].time+INTERVAL_MS+20000))
    def test_telegram_test(self):
        self.assertIn("TEST",test_message())

if __name__=="__main__":
    unittest.main()
