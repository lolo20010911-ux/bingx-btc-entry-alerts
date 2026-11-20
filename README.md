# BingX BTC-USDT 5m Discord belépőfigyelő

A program GitHub Actionsből figyeli a BingX BTC-USDT perpetual futures **lezárt 5 perces gyertyáit**, és potenciális LONG/SHORT kitörés + visszateszt jelzést küld egy Discord-csatornába.

**Nem nyit pozíciót**, nincs szükség BingX API-kulcsra. A jelzéshez adott belépési ár, stop és célár becsült technikai referencia, nem garantált kereskedési ár. A stratégia nem igazoltan nyereséges, a tőkeáttétel különösen kockázatos.

## Beállítás Discorddal

1. Discordon nyiss egy saját szervert és válassz szöveges csatornát (pl. `#btc-alerts`).
2. A csatornánál: **Edit Channel → Integrations → Webhooks → New Webhook**. Hozz létre egy webhookot, és válaszd a **Copy Webhook URL** lehetőséget. A Discord felületén a pontos elnevezés változhat; a webhookhoz `Manage Webhooks` jogosultság kell.
3. GitHubon: **Settings → Secrets and variables → Actions → New repository secret**. A név legyen pontosan `DISCORD_WEBHOOK_URL`, a value mezőbe illeszd a webhook URL-t, majd **Add secret**. A webhook URL-t **soha ne posztold nyilvánosan** vagy a chatbe.
4. GitHubon: **Actions → BingX 5m entry monitor → Run workflow**, a mód legyen `test`, majd **Run workflow**. Ha sikerül, megjelenik a tesztüzenet a Discord-csatornádban.
5. Ezután a GitHub automatikusan próbálkozik az 5 percenkénti figyeléssel. A futtatás csúszhat vagy kimaradhat, tehát ez **nem valós idejű** monitoring.

A program csak akkor küld belépőjelzést, ha egy frissen lezárt gyertyán a breakout/retest és az EMA20/50, RSI14, ATR14, volumen-feltételek teljesülnek. A jelzést követő GitHub-commit tárolja az utolsó elküldött jel azonosítóját az ismétlések csökkentésére. GitHub Actions-költségek és korlátozások érvényesek.

## Helyi ellenőrzés (Python 3.12+)

```bash
python -m unittest discover -s tests -v
python -m src.main --mode dry-run
```

## Referenciák

- BingX API: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-market/api-reference.md
- GitHub Actions schedule: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule


## V2 – 1h trendfilter és visszateszt

A 5m LONG csak akkor jut el Discordra, ha az **utolsó teljesen lezárt 1 órás gyertyák** alapján az 1h EMA20 > EMA50, és az utolsó 1h záróár EMA20 felett van. SHORT esetén a fordítottja. Ha a trend semleges/hiányos, **nem küld jelzést**. Nem használ kialakuló 1h gyertyát.

**Ellenőrzés:** GitHub → Actions → BingX 5m entry monitor → Run workflow → `dry-run`. A `scan` küld Discordra csak akkor, ha minden feltétel teljesül. `test` mód egyszerű tesztüzenetet küld.

**Backtest:** ugyanitt válaszd a `backtest` módot. Nem küld Discordra. A futás naplójában látod a jelzések, szűrt jelzések, lezárt próbakötések, találati arány, nettó R és maximális R-visszaesés eredményét. A JSON-jelentés az Actions futás *Artifacts* szekciójából tölthető le, `btc-backtest-report` néven.

**Visszateszt korlátai:** 1000 utolsó 5m gyertya ≈ 3,5 nap, nem reprezentatív teljesítményértékelés. A belépő a jelzés UTÁNI gyertya nyitóárán történik szimulálva; 0,05% taker díj/oldal, 0,02% becsült csúszás/fill, egyszerre legfeljebb egy pozíció, max 48 gyertya tartás. Ha egy gyertyán stop és célár egyaránt érintett, a stop számít. A funding, likvidáció és valós order book nem szerepel. A kimutatás R-alapú, **nem** számla- vagy tőkeáttételes P&L. A múltbeli eredmény nem garantál jövőbeli nyereséget.

A bot soha nem nyit pozíciót. A GitHub Actions 5 perces ütemezése nem garantáltan pontos; futások késhetnek/kimaradhatnak.


## Állapotjelentés Discordra (V2.1)

Ha nem jön kereskedési jelzés, az **nem feltétlenül hiba**. A `dry-run` és `backtest` mód szándékosan nem küld üzenetet Discordra. Most hozzáadtuk a `status` módot:

- GitHub → Actions → `BingX 5m entry monitor` → `Run workflow` → **status**.
- Ez **mindig küld egy ellenőrző üzenetet** a Discordra, ha működik a piaci adatlekérés és a webhook; megmutatja az utolsó lezárt 5m gyertya záróárát, az 1h trend irányát és hogy van-e megfelelő 5m jelzés.
- Egy **napi állapotjelentést** is megpróbálunk küldeni 08:17 UTC-kor. Az 5 perces ütemezett futások ezzel párhuzamosan továbbra is csak valós stratégiai jelzésre küldenek üzenetet. A GitHub Actions időzítés késhet vagy kimaradhat, nincs valós idejű SLA.
- A `status` nem valódi belépő, nem nyit pozíciót. Az itt látott 5m záróár nem a pillanatnyi kötési ár.

**Első backtest megfigyelés, 2026-11-17 – 2026-11-20:** 999 lezárt 5m gyertya, 8 mintabeli setup, 3 trend miatt szűrt, 5 szimulált ügylet, 1 pozitív, 20% találati arány, nettó -3,842R. Ez rövid, kis mintás és negatív eredmény: a stratégiát még nem szabad bizonyítottan nyereségesnek tekinteni, éles futures belépőket saját ellenőrzés nélkül nem ajánlott követni.

## Demo belépőjelzés Discordra (V2.2)

Ha meg szeretnéd nézni, milyen lesz egy valódi SHORT belépőjelzés:

1. GitHub → **Actions → BingX 5m entry monitor → Run workflow**.
2. A mode mezőben válaszd a **preview** opciót, majd indítsd el.
3. A Discord `#btc-alerts` csatornában megjelenik egy **egyértelműen DEMO** SHORT üzenet, például belépő 60 000 USDT, stop 60 120, célár 59 760. Az árak **kitaláltak**, a 2025-01-01 dátum **minta**, nincs mögöttük valós piaci setup.

A **preview** nem kér piaci adatot, nem módosítja az utolsó jelzés állapotát, és nem nyit pozíciót. Csak a Discord formátumot mutatja be. A **scan** mód külön működik, és továbbra is kizárólag teljesült indikátorfeltételek esetén jelez.

## V3 – Discord embed megjelenés (2026-11-20)

A `preview`, `scan`, `status` és `test` módok most már natív **Discord embed kártyákat** küldenek:

- **LONG:** zöld oldalsáv, belépő / stop / célár, 1h trend és indikátorok.
- **SHORT:** piros oldalsáv, ugyanilyen rendezett mezők.
- **preview:** kék, nagyméretű **DEMO ONLY / FICTIONAL** figyelmeztetés. A példában szereplő árak kitaláltak; ne köss rájuk.
- **status:** kék (friss adatok) vagy sárga (8 percnél régebbi 5m zárás), külön jelölve hogy nem kereskedési jelzés.
- **test:** egyszerű zöld kapcsolat-ellenőrző kártya.

A webhook Discord Secrets-ben marad. A kód továbbra sem nyit pozíciót és a belépőstratégia feltételei nem változtak. Tesztelés: GitHub → Actions → BingX 5m entry monitor → Run workflow → `preview`. A régi üzenetek nem változnak, csak az újak kapnak új formátumot.


## V4 – Discordban állítható státuszgyakoriság

A Discord `/btc-ertesites` menü és az önálló Cloudflare Worker kódja elkészült. Választható: kikapcsolva, 5, 15, 30, 60 vagy 240 perc. A **külön Discord alkalmazás és Cloudflare Worker telepítése még szükséges**; a GitHub-repository önmagában nem hozza létre a Discord-parancsot. A megvalósítás [magyar telepítési útmutatója](discord-control/SETUP_HU.md). A régi fix napi státuszát kikapcsoltuk, hogy a menü „Kikapcsolva” opciója valóban leállítsa az automatikus státuszt. A LONG/SHORT figyelő külön működik.

## Egyszeri e-mail próba (2026-11-20)

A Discordos automatikus szkennelést leállítottuk. Egy külön 10 percenkénti, legfeljebb egy órás e-mailes BTC státusz workflow hozzáadva, amely kizárólag **2026-11-20 21:18–22:18 UTC** között küldhet. Nem aktív hitelesített Gmail küldés, amíg a `GMAIL_USERNAME`, `GMAIL_APP_PASSWORD` és `EMAIL_TO` GitHub titkok nincsenek beállítva. [E-mail telepítési útmutató](EMAIL_TRIAL_HU.md).
