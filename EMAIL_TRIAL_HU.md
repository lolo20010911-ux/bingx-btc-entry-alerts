# 1 órás BTC e-mail teszt – 2026. november 20.

**Cél:** 10 percenként státuszlevelet küldeni a saját Gmail-fiókodba, akkor is, ha nincs LONG/SHORT belépő. A levelek az utolsó lezárt 5 perces BTC/USDT gyertyát és az 1 órás EMA trendet mutatják.

## Aktív időszak

- Kezdés: **2026-11-20 22:18 magyar idő** (21:18 UTC)
- Leállás: **2026-11-20 23:18 magyar idő** (22:18 UTC)
- GitHub cron céloidőpontok: **22:20, 22:30, 22:40, 22:50, 23:00, 23:10**, magyar idő.
- GitHub ütemezés csúszhat vagy kimaradhat. A kód a lejárat után akkor sem küld levelet, ha a cron késve indul. Nincs garantált hat darab email.

## A levélküldés elindításához

A GitHub projektben nyisd meg: **Settings → Secrets and variables → Actions → New repository secret**. Hozd létre a következő 3 beállítást, mindegyiket külön:

1. `GMAIL_USERNAME` = annak a Gmail-fióknak az e-mail címe, amelyikből a leveleket küldeni szeretnéd (lehet ugyanaz, mint a címzett).
2. `GMAIL_APP_PASSWORD` = a Gmail-fiók **Google alkalmazásjelszava** (nem a normál Gmail-jelszavad). Kétlépcsős azonosítás kellhet, és bizonyos fiókoknál az alkalmazásjelszó nem érhető el. Google oldal: https://myaccount.google.com/apppasswords
3. `EMAIL_TO` = a cél e-mail címed.

**Soha ne küldd el nekem a jelszót!** A megadott cím és az alkalmazásjelszó csak GitHub Secrets mezőkbe kerüljön.

Ha elkészültél, GitHub → **Actions → BTC 1-hour email trial → Run workflow**. A futás akkor küld levelet, ha az egyórás időablakon belül van. Ellenőrizd a Beérkező levelek és a Spam mappát. Az SMTP-t még nem teszteltük éles Gmail-fiókkal; a kód automatikus tesztje nem jelent tényleges elküldött levelet.

## Visszavonás

A határidőn túl semmilyen email nem indulhat. Ha korábban le szeretnéd állítani, GitHub → Actions → **BTC 1-hour email trial** → **Disable workflow**, illetve törölheted a három e-mail secretet. A GitHub Actions schedule technikailag a lejárat után is elindíthatja a workflow-t, de a program ekkor küldés nélkül kilép.

A korábbi Discordos GitHub automatikus szkennelést kikapcsoltuk (kézi workflow futtatás megmaradt). Nincs automatikus pozíciónyitás, az árak nem valós idejű ajánlati árak, a stratégia korábbi visszatesztje nem bizonyított eredményességet.
