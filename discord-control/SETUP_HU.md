# Discordon választható BTC-értesítések – telepítés

A **/btc-ertesites** Discord-parancs egy privát legördülő menüt ad: **Kikapcsolva / 5 perc / 15 perc / 30 perc / 1 óra / 4 óra**. A választott időközben a rendszer akkor is küld piaci állapotkártyát, ha a GitHub belépőfigyelő nem talál LONG/SHORT setupot.

**Fontos:** A GitHubra feltöltött kód még nem jelenti azt, hogy a Discord menü már működik. Ehhez új Discord Application és Cloudflare Worker telepítés szükséges. A meglevő Captain Hook webhook változatlanul használható.

## 1. Új Discord Application

Nyisd meg: https://discord.com/developers/applications → **New Application**, neve lehet **BTC Alerts Controls**. Másold ki a **General Information** fülön a **Public Key** és **Application ID** értékeket. A **Bot** részen készíts **Bot Token**-t (titkos). **Installation** alatt engedélyezd a **Guild Install** lehetőséget, az `applications.commands` scope-ot, és telepítsd az alkalmazást a saját Discord szerveredre.

Discord → Felhasználói beállítások → Haladó → Fejlesztői mód. Másold ki saját felhasználód **User ID**, a **#btc-alerts** csatorna **Channel ID**, és a szerver **Server ID / Guild ID** értékét. A #btc-alerts → Csatorna szerkesztése → Integrációk → Webhookok alatt a régi **Captain Hook webhook URL** is szükséges (ez titkos!).

## 2. Cloudflare Worker és KV

Cloudflare-fiók: https://dash.cloudflare.com/ . A számítógépeden szükség lesz Node.js-re és Gitre. A GitHub-projekt letöltése vagy klónozása után nyiss terminált a `discord-control` mappában.

```bash
npx wrangler login
npx wrangler kv namespace create SETTINGS
```

A kapott namespace **ID** kerüljön a `discord-control/wrangler.toml` `REPLACE_WITH_YOUR_KV_NAMESPACE_ID` szövege helyére. Majd:

```bash
npx wrangler deploy
npx wrangler secret put DISCORD_PUBLIC_KEY
npx wrangler secret put DISCORD_OWNER_ID
npx wrangler secret put DISCORD_CHANNEL_ID
npx wrangler secret put DISCORD_GUILD_ID
npx wrangler secret put DISCORD_WEBHOOK_URL
```

Minden `secret put` parancsnál a hozzá tartozó értéket privát módon add meg. A **DISCORD_PUBLIC_KEY** a Discord Application Public Key; az **OWNER_ID** a saját Discord User ID, **CHANNEL_ID** a #btc-alerts csatorna ID, **GUILD_ID** a szerver ID, **WEBHOOK_URL** a korábbi Captain Hook webhook címe. Tokeneket és webhookokat ne tegyél GitHub fájlba, ne küldj el chatben.

A deploy után kapsz egy publikus `https://...workers.dev` URL-t. Discord Developer Portal → az alkalmazás **General Information / Interactions Endpoint URL** mezőjébe ezt írd `/interactions` végződéssel. A Discord ellenőrzi az aláírt PING kérést. Ha elfogadja, a Worker elérhető.

## 3. Slash parancs regisztrálása

A GitHub-repo **Settings → Secrets and variables → Actions** alatt hozz létre egy **DISCORD_BOT_TOKEN** nevű repository secretet, az értéke a Discord Application bot tokenje. A titkot ne oszd meg.

Nyisd meg a GitHub → **Actions → Register Discord settings command → Run workflow** menüt. Add meg az **Application ID** és a **Server/Guild ID** értékeit, és indítsd el. Sikeres futás után a Discord **#btc-alerts** csatornájában használd a `/btc-ertesites` parancsot.

## 4. Használat

A menüből válassz például **15 perc** időközt. A következő Cloudflare 5 perces ütemezett ellenőrzéskor kék BTC STATUS kártyát küldhet a meglévő Captain Hook webhook. A státuszkártya az **utolsó lezárt 5 perces gyertya záróárát**, az **1 órás EMA trendet**, az adatok késését és a választott gyakoriságot mutatja. **Nem elemez újra minden belépőfeltételt.**

A **Kikapcsolva** leállítja az automatikus státuszkártyákat; a GitHub LONG/SHORT belépőjelzéseket nem kapcsolja ki. A GitHub korábbi fix napi státuszküldése megszűnt a választó által szabályozott státuszok miatt, de a kézi `status` futás megmaradt.

## Biztonság, megbízhatóság, költség

- Csak az engedélyezett Discord-felhasználó állíthatja, egyetlen kijelölt csatornában. A kérések Ed25519 aláírását ellenőrzi.
- A KV tárolja a választott időközt és a legutóbbi sikeres küldés időpontját. A KV elosztott működése miatt ritkán duplikált értesítés is előfordulhat.
- A Cloudflare Cron 5 percenként próbálkozik, **nem pontos idejű, garantált rendszer**. A piaci API hibája esetén figyelmeztetést küld kitalált ár helyett.
- A Cloudflare Workers / KV ingyenes keretei és platformkorlátai érvényesek. A menü **alapból ki van kapcsolva**.
- A GitHub piaci jelzései továbbra sem igazoltan nyereségesek, futures pozíciót a rendszer nem nyit.

Technikai tesztek: `node --test discord-control/test/*.test.mjs` a repo gyökeréből.

Dokumentáció: https://docs.discord.com/developers/interactions/receiving-and-responding • https://developers.cloudflare.com/kv/get-started/ • https://developers.cloudflare.com/workers/configuration/cron-triggers/
