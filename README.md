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
