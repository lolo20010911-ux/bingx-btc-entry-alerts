"""Discord embed UI payload and mode safety tests."""
import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from src.market import Candle, INTERVAL_MS
from src.strategy import Signal
from src.notifier import (
    build_signal_embed, build_status_embed, build_test_embed,
    preview_embed, preview_message, send_discord,
)

class DiscordEmbedTests(unittest.TestCase):
    def make_signal(self, side="LONG"):
        return Signal(
            id="test", side=side, candle_time=1735689600000,
            entry=60000., stop=59900. if side=="LONG" else 60100.,
            target=60200. if side=="LONG" else 59800.,
            breakout_level=59975., ema_fast=60100., ema_slow=60000.,
            rsi=55., atr=90., volume_ratio=1.4, risk_percent=0.16
        )

    def test_long_color_and_fields(self):
        e=build_signal_embed(self.make_signal("LONG"),trend="LONG")
        self.assertEqual(e["color"],0x2ECC71)
        self.assertIn("LONG",e["title"])
        self.assertTrue(any(f["name"].startswith("🎯") for f in e["fields"]))
        self.assertEqual(len(e["fields"]),11)
        self.assertTrue(e["timestamp"].endswith("+00:00"))

    def test_short_color(self):
        e=build_signal_embed(self.make_signal("SHORT"),trend="SHORT")
        self.assertEqual(e["color"],0xED4245)
        self.assertIn("SHORT",e["title"])

    def test_demo_is_unmistakable(self):
        e=preview_embed()
        self.assertEqual(e["color"],0x5865F2)
        self.assertIn("DEMO ONLY",e["title"])
        self.assertIn("KITALÁLT",e["description"])
        self.assertIn("DEMO",e["footer"]["text"])
        self.assertIn("60,000.00",str(e["fields"]))
        self.assertIn("TEST / DEMO ONLY",preview_message())

    def test_status_clearly_not_an_entry(self):
        t=1735689600000
        bar=Candle(t,60000.,60100.,59900.,60020.,12.)
        recent=build_status_embed(bar,None,False,t+INTERVAL_MS+20000)
        old=build_status_embed(bar,"SHORT",True,t+INTERVAL_MS+900000)
        self.assertEqual(recent["color"],0x5865F2)
        self.assertEqual(old["color"],0xF1C40F)
        self.assertIn("nem kereskedési jelzés",recent["description"])
        self.assertIn("Nincs megerősített belépő",str(recent["fields"]))

    def test_test_embed(self):
        e=build_test_embed()
        self.assertEqual(e["color"],0x2ECC71)
        self.assertIn("kapcsolat sikeres",e["title"])

    def test_webhook_json_has_embeds_and_disables_mentions(self):
        response=MagicMock()
        response.status=204
        response.__enter__.return_value=response
        with patch("src.notifier.urlopen",return_value=response) as post:
            send_discord(
                "https://discord.com/api/webhooks/123456/test_token",
                content="DEMO ONLY",embeds=[preview_embed()],
            )
        req=post.call_args.args[0]
        data=json.loads(req.data.decode("utf-8"))
        self.assertEqual(data["allowed_mentions"]["parse"],[])
        self.assertEqual(data["content"],"DEMO ONLY")
        self.assertEqual(len(data["embeds"]),1)
        self.assertTrue(req.get_header("User-agent").startswith("DiscordBot"))

    def test_preview_mode_does_not_fetch_market_data(self):
        from src import main as runner
        with patch.dict("os.environ",{"DISCORD_WEBHOOK_URL":"https://discord.com/api/webhooks/123/demo"}):
            with patch.object(runner,"send_discord") as send, patch.object(runner,"fetch_klines") as fetch:
                rc=runner.main(["--mode","preview"])
        self.assertEqual(rc,0)
        fetch.assert_not_called()
        self.assertEqual(send.call_count,1)
        self.assertIn("DEMO",send.call_args.kwargs["content"])
        self.assertEqual(send.call_args.kwargs["embeds"][0]["color"],0x5865F2)

    def test_webhook_blocks_non_discord_domain(self):
        with self.assertRaises(RuntimeError):
            send_discord("https://not-discord.com/api/webhooks/123/demo",embeds=[preview_embed()])
