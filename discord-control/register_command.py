#!/usr/bin/env python3
"""Register /btc-ertesites in the selected Discord server."""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError
app=os.environ.get("DISCORD_APPLICATION_ID","")
guild=os.environ.get("DISCORD_GUILD_ID","")
token=os.environ.get("DISCORD_BOT_TOKEN","")
if not app.isdigit() or not guild.isdigit() or not token:
    raise SystemExit("Missing DISCORD_APPLICATION_ID, DISCORD_GUILD_ID or DISCORD_BOT_TOKEN")
url=f"https://discord.com/api/v10/applications/{app}/guilds/{guild}/commands"
payload={"name":"btc-ertesites","description":"BTC statuszertesites gyakorisaganak beallitasa","type":1}
req=Request(url,method="POST",data=json.dumps(payload).encode("utf-8"),
 headers={"Authorization":"Bot "+token,"Content-Type":"application/json",
 "User-Agent":"DiscordBot (https://github.com/lolo20010911-ux/bingx-btc-entry-alerts, 1.0)"})
try:
    with urlopen(req,timeout=20) as res:
        obj=json.load(res)
    print("Registered Discord command:",obj.get("name"))
except HTTPError as e:
    raise SystemExit(f"Discord registration failed (HTTP {e.code}). Check installation and credentials.") from None
