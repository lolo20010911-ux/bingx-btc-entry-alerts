"""Temporary, read-only BTC/USDT email status (Gmail SMTP).

This is a capped, opt-in experiment. Credentials are GitHub secrets.
No exchange authentication or order execution. No fabricated price signals.
"""
import os
import smtplib
import sys
import time
from datetime import datetime, timezone
from email.message import EmailMessage

from .market import INTERVAL_MS, HOUR_MS, fetch_klines, parse_klines
from .strategy import find_signal
from .filters import hourly_trend

# One hour only, requested 20 November 2026 around 22:18 Budapest (UTC+1).
START_UTC = datetime.fromisoformat("2026-11-20T21:18:00+00:00")
END_UTC = datetime.fromisoformat("2026-11-20T22:18:00+00:00")
VALID_SLOTS = ((21, 20), (21, 30), (21, 40), (21, 50), (22, 0), (22, 10))

def allowed_window(now: datetime) -> bool:
    """Only run during the requested one-hour window, even if cron remains enabled."""
    if now.tzinfo is None:
        raise ValueError("now must have a timezone")
    utc = now.astimezone(timezone.utc)
    return START_UTC <= utc < END_UTC

def status_report(now: datetime):
    """Get only completed BingX candles. Inform honestly about failed data requests."""
    now_ms = int(now.timestamp() * 1000)
    try:
        raw_5m = fetch_klines(interval="5m", limit=300)
        bars = parse_klines(raw_5m, now_ms=now_ms)
        time.sleep(1.2)
        raw_1h = fetch_klines(interval="1h", limit=300)
        hours = parse_klines(raw_1h, now_ms=now_ms, interval_ms=HOUR_MS)
        if not bars:
            raise ValueError("No completed 5-minute bars")
        last = bars[-1]
        lag = max(0, (now_ms - (last.time + INTERVAL_MS)) / 60000)
        trend = hourly_trend(hours, last.time + INTERVAL_MS)
        signal = find_signal(bars, now_ms=now_ms)
        confirmed = bool(signal and signal.side == trend)
        date = datetime.fromtimestamp((last.time + INTERVAL_MS)/1000, tz=timezone.utc)
        status = "VAN TECHNIKAI JELÖLT" if confirmed else "NINCS MEGERŐSÍTETT BELÉPŐ"
        lines = [
            "BTC/USDT PERPETUAL – 10 perces e-mail állapotjelentés",
            "",
            f"Ellenőrzés: {now:%Y-%m-%d %H:%M UTC}",
            f"Utolsó lezárt 5m gyertya: {date:%Y-%m-%d %H:%M UTC}",
            f"BTC 5m záróár: {last.close:,.2f} USDT",
            f"Adatok késése: {lag:.1f} perc",
            f"1 órás trend: {trend or 'NINCS / SEMLEGES'}",
            f"Belépő: {status}",
        ]
        if confirmed:
            lines += [
                f"Jelölt irány: {signal.side}",
                f"Referenciabelépő (nem jelenlegi ajánlat): {signal.entry:,.2f} USDT",
                f"Stop referencia: {signal.stop:,.2f} USDT",
                f"Célár referencia: {signal.target:,.2f} USDT",
                "Ez technikai jelzés, nem garantált nyereség; ellenőrizd az aktuális árat.",
            ]
        elif signal:
            lines += [f"5m jelölt: {signal.side}; 1h szűrő: {trend or 'semleges'} – ELUTASÍTVA."]
        if lag > 8:
            lines.append("FIGYELEM: az adat több mint 8 perce lezárt gyertyából származik.")
        lines += [
            "",
            "Csak megfigyelés. Nincs automatikus kötés.",
            "Az 5m stratégia rövid visszatesztje korábban negatív volt.",
            "Az e-mail 10 percenként tervezett, a GitHub ütemezése késhet.",
        ]
        return status, "\n".join(lines)
    except (ValueError, RuntimeError, TimeoutError) as exc:
        # Report failure; never make up last prices or entry.
        return "PIACI ADAT NEM ELÉRHETŐ", (
            f"BTC/USDT ellenőrzés: {now:%Y-%m-%d %H:%M UTC}\n"
            "A BingX piaci adatok lekérése nem sikerült; nem adok kitalált árat vagy belépőt.\n"
            f"Ok: {type(exc).__name__}\n"
            "Nincs kereskedési jelzés vagy automatikus kötés."
        )

def send_email(sender: str, app_password: str, recipient: str, subject: str, body: str):
    if not (sender and app_password and recipient):
        raise RuntimeError("Gmail SMTP secrets are missing")
    if not (sender.lower().endswith("@gmail.com") and recipient.strip().lower().endswith("@gmail.com")):
        raise RuntimeError("Expected Gmail addresses")
    mail = EmailMessage()
    mail["Subject"] = subject
    mail["From"] = sender
    mail["To"] = recipient
    mail.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
        server.login(sender, app_password)
        server.send_message(mail)

def run(now=None, *, allow_test=False):
    now = now or datetime.now(timezone.utc)
    if not allowed_window(now):
        print("Trial window closed/not started; skipping safely.")
        return 0
    if not allow_test and (now.hour, now.minute) not in VALID_SLOTS:
        # GitHub can launch late; a scheduled run within the overall window is still valid.
        print("Processing scheduled status in time window.")
    sender = os.getenv("GMAIL_USERNAME", "").strip()
    recipient = os.getenv("EMAIL_TO", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "")
    if not all((sender, recipient, password)):
        print("Email not configured: add GMAIL_USERNAME, GMAIL_APP_PASSWORD and EMAIL_TO as GitHub Actions secrets.", file=sys.stderr)
        return 2
    title, report = status_report(now)
    send_email(sender, password, recipient, f"BTC/USDT – {title} – {now:%H:%M} UTC", report)
    print(f"BTC status email sent at {now:%Y-%m-%d %H:%M UTC} (recipient redacted)")
    return 0

if __name__ == "__main__":
    raise SystemExit(run())
