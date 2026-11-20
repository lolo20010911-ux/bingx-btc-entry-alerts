# BingX BTC-USDT 5m belépőfigyelő

Python + GitHub Actions + Telegram. A program 5 percenként megkísérli lekérni a BingX USDT-M BTC-USDT perpetual *lezárt* 5 perces gyertyáit. LONG/SHORT lehetőségeket keres 20 gyertyás kitörés és visszateszt, EMA20/50, RSI14, ATR14 és forgalmi szűrő alapján. Telegramon küld figyelmeztetést belépési, stop és célár-referenciával.

**Csak jelzés, nem kereskedés:** nem használ BingX API-kulcsot, nem nyit pozíciót. Nem bizonyítottan nyereséges stratégia. A belépőár a jelzést kiváltó gyertya záróára, nem garantált kötési ár. A tőkeáttételes futures különösen kockázatos.

## Beüzemelés

1. Telegramban keresd meg a hivatalos **@BotFather** botot, küldd neki a `/newbot` parancsot, és készíts botot. A kapott tokent NE oszd meg senkivel!
2. Nyisd meg az új botodat, és küldd neki a `/start` üzenetet. A chat ID-t a Telegram Bot API `getUpdates` végpontjával tudod megkeresni, vagy más, általad ellenőrzött módszerrel.
3. GitHub → repo → **Settings → Secrets and variables → Actions → New repository secret**: add meg külön a `TELEGRAM_BOT_TOKEN` és `TELEGRAM_CHAT_ID` titkokat. Soha ne tárold őket forráskódban.
4. GitHub → **Actions** → `BingX 5m entry monitor` → **Run workflow**, válaszd a `test` módot. Telegramon tesztüzenetet kell kapnod.
5. A `dry-run` mód ellenőrzi a piaci adatokat értesítés nélkül. A `scan` mód valódi belépőjelzést küldhet. A `schedule` körülbelül minden ötödik perc utáni első percben fut automatikusan.

A GitHub Actions ütemezés **nem valós idejű**, a futások késhetnek vagy kimaradhatnak. A kód kizárja a nem lezárt és túl régi gyertyákat. Egy jelet alaphelyzetben egyszer küld el; a legutóbbi jel azonosítóját a `.state/last_signal.json` fájlban tárolja.

## Helyi teszt

Python 3.12+, külső csomag nélkül:

```sh
python -m unittest discover -s tests -v
python -m src.main --mode dry-run
```

## Dokumentáció

- [BingX public swap market API](https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-market/api-reference.md)
- [GitHub Actions schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

A futures kereskedés kockázata magas. A jelzés nem biztos nyereség, az árcélok és stopok kizárólag technikai tájékoztatók.