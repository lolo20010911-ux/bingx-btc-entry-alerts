/**
 * Discord interactive schedule settings + independent periodic BTC status.
 * No exchange private keys and no order execution.
 * Off by default. Needs Cloudflare Worker + KV and a Discord application.
 */
const INTERVAL_KEY="btc:interval";
const LAST_KEY="btc:last_sent";
const CHOICES={"0":"Kikapcsolva","5":"5 perc","15":"15 perc","30":"30 perc","60":"1 óra","240":"4 óra"};
const MENU_ID="btc_status_interval_v1";
const MINUTE=60000, HOUR=3600000;
const KLINES="https://open-api.bingx.com/openApi/swap/v3/quote/klines";

export function frequencyMenu(current="0") {
  return [{type:1,components:[{
    type:3,custom_id:MENU_ID,placeholder:"BTC állapotértesítések gyakorisága",
    min_values:1,max_values:1,
    options:Object.entries(CHOICES).map(([value,label])=>({
      label,value,default:current===value,
      description:value==="0"?"Csak valódi belépőjelzések":"Státuszkártya belépő nélkül is"
    }))
  }]}];
}
function response(type,data){return new Response(JSON.stringify({type,data}),{
  headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}
});}
function ephemeral(content,components) {
  const data={content,flags:64,allowed_mentions:{parse:[]}};
  if(components)data.components=components;
  return response(4,data);
}
const fromHex=s=>Uint8Array.from(s.match(/.{2}/g),h=>parseInt(h,16));
export async function verifyDiscordSignature(body,sig,stamp,publicKey,now=Date.now()) {
  if(!/^[0-9a-f]{128}$/i.test(sig||"")||!/^\d{10}$/.test(stamp||"")||
    !/^[0-9a-f]{64}$/i.test(publicKey||""))return false;
  if(Math.abs(now-Number(stamp)*1000)>300000)return false;
  try {
    const key=await crypto.subtle.importKey("raw",fromHex(publicKey),"Ed25519",false,["verify"]);
    const message=new TextEncoder().encode(stamp+body);
    return await crypto.subtle.verify("Ed25519",key,fromHex(sig),message);
  }catch{return false;}
}
export async function interact(payload,env) {
  if(payload.type===1)return response(1);
  const user=payload.member?.user?.id||payload.user?.id;
  if(!env.SETTINGS||!env.DISCORD_OWNER_ID||!env.DISCORD_CHANNEL_ID||!env.DISCORD_GUILD_ID)
    return ephemeral("A beállító alkalmazás még nincs konfigurálva.");
  if(user!==env.DISCORD_OWNER_ID||payload.guild_id!==env.DISCORD_GUILD_ID||
    payload.channel_id!==env.DISCORD_CHANNEL_ID)
    return ephemeral("A menü csak a tulajdonosnak érhető el a #btc-alerts csatornában.");
  if(payload.type===2&&payload.data?.name==="btc-ertesites") {
    const current=await env.SETTINGS.get(INTERVAL_KEY)||"0";
    return ephemeral(
      "⚙️ **BTC/USDT – Értesítési gyakoriság**\n"+
      "**Jelenleg:** "+(CHOICES[current]||"Kikapcsolva")+"\n"+
      "Ezek a státuszjelentések akkor is érkeznek, ha nincs belépő. "+
      "A LONG/SHORT jelek továbbra is külön működnek.\n"+
      "**Válassz az alábbi menüből:**",frequencyMenu(current)
    );
  }
  if(payload.type===3&&payload.data?.custom_id===MENU_ID) {
    const value=payload.data?.values?.[0];
    if(!Object.hasOwn(CHOICES,value))return ephemeral("Ismeretlen időköz.");
    await env.SETTINGS.put(INTERVAL_KEY,value);
    await env.SETTINGS.delete(LAST_KEY);
    const message=value==="0"
      ? "🔕 **Kikapcsolva.** A külön LONG/SHORT belépőjelzések nem változtak."
      : "✅ **Mentve: "+CHOICES[value]+"**\n"+
        "Az első rendszeres státusz a következő kb. ötperces ellenőrzéskor érkezhet. "+
        "Az ütemezés kis mértékben késhet.";
    return response(7,{content:message+"\nA menüben bármikor módosíthatod.",
      components:frequencyMenu(value),allowed_mentions:{parse:[]}});
  }
  return ephemeral("Ismeretlen parancs: használd a /btc-ertesites parancsot.");
}

function formatMoney(n){return n.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});}
async function klines(interval,period,count,now,fetchFn) {
  const u=KLINES+"?symbol=BTC-USDT&interval="+interval+"&limit="+count;
  const resp=await fetchFn(u,{headers:{"Accept":"application/json","User-Agent":"btc-alerts-status/1"}});
  if(!resp.ok)throw Error("BingX API rejected request");
  const data=await resp.json();
  if(String(data.code)!=="0"||!Array.isArray(data.data))throw Error("Invalid market response");
  return data.data.map(b=>({time:Number(b.time),close:Number(b.close)}))
    .filter(b=>b.time%period===0&&Number.isFinite(b.close)&&b.close>0&&b.time+period+10000<=now)
    .sort((a,b)=>a.time-b.time);
}
function ema(prices,period){
  if(prices.length<period)throw Error("Insufficient data");
  let value=prices.slice(0,period).reduce((a,b)=>a+b,0)/period;
  for(const v of prices.slice(period))value+=(2/(period+1))*(v-value);
  return value;
}
export function hourTrend(hours,now){
  if(hours.length<60)return "NINCS ELÉG ADAT";
  const last=hours.at(-1);
  if(now-last.time-HOUR>=HOUR)return "RÉGI ADAT";
  const recent=hours.slice(-120);
  if(recent.slice(1).some((c,i)=>c.time-recent[i].time!==HOUR))return "HIÁNYOS ADAT";
  const prices=recent.map(b=>b.close), fast=ema(prices,20),slow=ema(prices,50);
  return fast>slow&&last.close>fast?"LONG":fast<slow&&last.close<fast?"SHORT":"SEMLEGES";
}
export async function snapshot(now,fetchFn=fetch,sleep=ms=>new Promise(r=>setTimeout(r,ms))){
  const five=await klines("5m",5*MINUTE,6,now,fetchFn);
  await sleep(1100); // public BingX API pacing
  const hours=await klines("1h",HOUR,120,now,fetchFn);
  if(!five.length)throw Error("No closed 5m candle");
  const last=five.at(-1);
  return {close:last.close,closeAt:last.time+5*MINUTE,
    age:Math.max(0,(now-last.time-5*MINUTE)/MINUTE),
    trend:hourTrend(hours,now)};
}
export function heartbeatEmbed(interval,now,market) {
  const title="📊 BTC/USDT • Rendszeres piaci állapot";
  const common={footer:{text:"STATUS ONLY • Nem belépőjelzés • Nincs pozíciónyitás"},
    timestamp:new Date(now).toISOString()};
  if(!market)return {...common,title:"⚠️ BTC/USDT • Piaci adatok nem elérhetők",
    color:0xE67E22,description:"Ez státuszértesítés, nem kereskedési jelzés.",
    fields:[
      {name:"Időköz",value:CHOICES[String(interval)],inline:true},
      {name:"BTC árfolyam",value:"NEM ELÉRHETŐ",inline:true}
    ]};
  return {...common,title,color:market.age<=8?0x5865F2:0xF1C40F,
    description:"Állapotjelentés **belépőtől függetlenül**. Nem kereskedési jelzés.",
    fields:[
      {name:"5m záróár",value:"**"+formatMoney(market.close)+" USDT**",inline:true},
      {name:"1H trend",value:"**"+market.trend+"**",inline:true},
      {name:"Értesítés",value:CHOICES[String(interval)],inline:true},
      {name:"Gyertya késése",value:market.age.toFixed(1)+" perc",inline:true},
      {name:"Lezárt gyertya (UTC)",value:new Date(market.closeAt).toISOString().slice(0,16).replace("T"," ")+" UTC",inline:false},
      {name:"Belépési feltételek",value:"Ez nem a teljes kitörés–visszateszt stratégia eredménye. A GitHub LONG/SHORT belépőfigyelő külön működik.",inline:false}
    ]};
}
async function sendWebhook(url,embed,fetchFn) {
  let u;try{u=new URL(url);}catch{throw Error("Invalid Discord webhook");}
  if(u.protocol!=="https:"||!["discord.com","discordapp.com"].includes(u.hostname)||
    !/^\/api\/webhooks\/[0-9]+\/[^/]+$/.test(u.pathname))throw Error("Invalid Discord webhook");
  const res=await fetchFn(url,{
    method:"POST",
    headers:{"Content-Type":"application/json",
      "User-Agent":"DiscordBot (https://github.com/lolo20010911-ux/bingx-btc-entry-alerts, 1.0)"},
    body:JSON.stringify({embeds:[embed],allowed_mentions:{parse:[]}})
  });
  if(!res.ok)throw Error("Discord rejected status: HTTP "+res.status);
}
export async function sendIfDue(env,now=Date.now(),deps={}){
  if(!env.SETTINGS||!env.DISCORD_WEBHOOK_URL)return "not-configured";
  const interval=await env.SETTINGS.get(INTERVAL_KEY);
  if(!Object.hasOwn(CHOICES,interval||"")||interval==="0")return "off";
  const before=Number(await env.SETTINGS.get(LAST_KEY)||0);
  if(before>now||(before>0&&now-before<Number(interval)*MINUTE))return "not-due";
  const fetchFn=deps.fetchFn||fetch, sleep=deps.sleep|| (ms=>new Promise(r=>setTimeout(r,ms)));
  let market=null;
  try{market=await snapshot(now,fetchFn,sleep);}catch{ /* Show outage, never invent prices. */ }
  await sendWebhook(env.DISCORD_WEBHOOK_URL,heartbeatEmbed(interval,now,market),fetchFn);
  await env.SETTINGS.put(LAST_KEY,String(now));
  return "sent";
}
export default {
  async fetch(request,env){
    const path=new URL(request.url).pathname;
    if(path==="/health"&&request.method==="GET")
      return new Response('{"ok":true}',{headers:{"content-type":"application/json"}});
    if(path!=="/interactions"||request.method!=="POST")
      return new Response("Not found",{status:404});
    const body=await request.text();
    const valid=await verifyDiscordSignature(body,
      request.headers.get("x-signature-ed25519"),
      request.headers.get("x-signature-timestamp"),env.DISCORD_PUBLIC_KEY);
    if(!valid)return new Response("Invalid signature",{status:401});
    let payload;try{payload=JSON.parse(body);}catch{return new Response("Bad JSON",{status:400});}
    return interact(payload,env);
  },
  async scheduled(event,env,ctx){
    ctx.waitUntil(sendIfDue(env).catch(()=>"failed"));
  }
};
