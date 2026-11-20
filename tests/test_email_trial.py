"""Tests for a strictly time-limited 10-minute Gmail status experiment."""
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from src import email_trial as trial

def utc(s):
    return datetime.fromisoformat(s.replace("Z","+00:00"))

class EmailTrialTests(unittest.TestCase):
    def test_window_is_exactly_one_hour(self):
        self.assertFalse(trial.allowed_window(utc("2026-11-20T21:17:59Z")))
        self.assertTrue(trial.allowed_window(utc("2026-11-20T21:18:00Z")))
        self.assertTrue(trial.allowed_window(utc("2026-11-20T22:17:59Z")))
        self.assertFalse(trial.allowed_window(utc("2026-11-20T22:18:00Z")))
        self.assertFalse(trial.allowed_window(utc("2026-11-21T21:30:00Z")))

    def test_window_accepts_budapest_local_time(self):
        local=datetime(2026,11,20,22,30,tzinfo=timezone(timedelta(hours=1)))
        self.assertTrue(trial.allowed_window(local))

    def test_closed_window_never_reads_secrets_or_sends(self):
        with patch.object(trial,"send_email") as send,patch.object(trial,"status_report") as report:
            rc=trial.run(utc("2026-11-20T22:19:00Z"))
        self.assertEqual(rc,0)
        send.assert_not_called()
        report.assert_not_called()

    def test_missing_secrets_never_sends(self):
        with patch.dict("os.environ",{},clear=True):
            with patch.object(trial,"send_email") as send,patch.object(trial,"status_report") as report:
                rc=trial.run(utc("2026-11-20T21:20:00Z"))
        self.assertEqual(rc,2)
        send.assert_not_called()
        report.assert_not_called()

    def test_configured_email_sends_one_status(self):
        e={"GMAIL_USERNAME":"example@gmail.com","GMAIL_APP_PASSWORD":"fixture",
           "EMAIL_TO":"receiver@gmail.com"}
        with patch.dict("os.environ",e,clear=True):
            with patch.object(trial,"send_email") as send,patch.object(trial,"status_report",
                return_value=("NINCS MEGERŐSÍTETT BELÉPŐ","Test market status")):
                rc=trial.run(utc("2026-11-20T21:20:00Z"))
        self.assertEqual(rc,0)
        self.assertEqual(send.call_count,1)
        self.assertIn("NINCS MEGERŐSÍTETT BELÉPŐ",send.call_args.args[3])
