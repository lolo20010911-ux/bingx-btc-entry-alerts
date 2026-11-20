import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import app,{frequencyMenu,verifyDiscordSignature,interact,heartbeatEmbed,sendIfDue} from "../src/index.js";
globalThis.crypto ??= webcrypto;

function state(){
  const data=new Map();
  return {get:async k=>data.get(k)||null,put:async(k,v)=>{data.set(k,v);},
    delete:async k=>{data.delete(k);}};
}
function env(){
  return {SETTINGS:state(),DISCORD_OWNER_ID:"111",DISCORD_CHANNEL_ID:"222",
    DISCORD_GUILD_ID:"333",DISCORD_WEBHOOK_URL:"https://discord.com/api/webhooks/12345/fictional"};
}
function interaction(type,data={},user="111"){
  return {type,data,member:{user:{id:user}},guild_id:"333",channel_id:"222"};
}
async function json(response){return JSON.parse(await response.text());}
test("dropdown has six options including off",()=>{
  assert.deepEqual(frequencyMenu()[0].components[0].options.map(x=>x.value),
    ["0","5","15","30","60","240"]);
});
test("owner opens private dropdown",async()=>{
  const e=env();await e.SETTINGS.put("btc:interval","15");
  const reply=await json(await interact(interaction(2,{name:"btc-ertesites"}),e));
  assert.equal(reply.type,4);
  assert.equal(reply.data.flags,64);
  assert.match(reply.data.content,/15 perc/);
});
test("stranger cannot change interval",async()=>{
  const e=env();
  const reply=await json(await interact(interaction(3,
    {custom_id:"btc_status_interval_v1",values:["30"]},"stranger"),e));
  assert.equal(reply.type,4);
  assert.equal(await e.SETTINGS.get("btc:interval"),null);
});
test("selection persists and resets last alert",async()=>{
  const e=env();await e.SETTINGS.put("btc:last_sent","1000");
  const reply=await json(await interact(interaction(3,
    {custom_id:"btc_status_interval_v1",values:["30"]}),e));
  assert.equal(reply.type,7);
  assert.equal(await e.SETTINGS.get("btc:interval"),"30");
  assert.equal(await e.SETTINGS.get("btc:last_sent"),null);
});
test("invalid selection is rejected",async()=>{
  const e=env();
  const reply=await json(await interact(interaction(3,
    {custom_id:"btc_status_interval_v1",values:["3"]}),e));
  assert.equal(reply.type,4);
  assert.equal(await e.SETTINGS.get("btc:interval"),null);
});
test("Discord signatures checked: valid signed PING, rejected unsigned",async()=>{
  const denied=await app.fetch(new Request("https://test.example/interactions",
    {method:"POST",body:'{"type":1}'}),env());
  assert.equal(denied.status,401);
  const keys=await crypto.subtle.generateKey("Ed25519",true,["sign","verify"]);
  const hex=data=>Array.from(new Uint8Array(data),n=>n.toString(16).padStart(2,"0")).join("");
  const pub=hex(await crypto.subtle.exportKey("raw",keys.publicKey));
  const stamp=String(Math.floor(Date.now()/1000)),body='{"type":1}';
  const sig=hex(await crypto.subtle.sign("Ed25519",keys.privateKey,
    new TextEncoder().encode(stamp+body)));
  assert.equal(await verifyDiscordSignature(body,sig,stamp,pub),true);
  assert.equal(await verifyDiscordSignature(body,sig,String(Number(stamp)-900),pub),false);
  const allowed=await app.fetch(new Request("https://test.example/interactions",
    {method:"POST",body,headers:{"x-signature-ed25519":sig,"x-signature-timestamp":stamp}}),
    {...env(),DISCORD_PUBLIC_KEY:pub});
  assert.deepEqual(await json(allowed),{type:1});
});
test("off by default: no notifications",async()=>{
  assert.equal(await sendIfDue(env(),Date.now(),{fetchFn:()=>{throw Error("unexpected");}}),"off");
});
test("not due: no notifications",async()=>{
  const e=env(),now=Date.now();
  await e.SETTINGS.put("btc:interval","60");
  await e.SETTINGS.put("btc:last_sent",String(now-4*60000));
  assert.equal(await sendIfDue(e,now,{fetchFn:()=>{throw Error("unexpected");}}),"not-due");
});
test("market API failure produces honest alert with no fabricated price",async()=>{
  const e=env(),now=Date.now();await e.SETTINGS.put("btc:interval","15");
  const requests=[];
  const result=await sendIfDue(e,now,{fetchFn:async(url,opts)=>{
    requests.push({url,opts});
    if(url.startsWith("https://open-api.bingx.com/"))throw Error("market unavailable");
    return {ok:true,status:204};
  },sleep:async()=>{}});
  assert.equal(result,"sent");
  assert.equal(requests.length,2);
  const sent=JSON.parse(requests.at(-1).opts.body).embeds[0];
  assert.match(sent.title,/nem elérhetők/);
  assert.equal(sent.fields[1].value,"NEM ELÉRHETŐ");
  assert.equal(await e.SETTINGS.get("btc:last_sent"),String(now));
});
test("uses only fully closed 5m data, not next incomplete candle",async()=>{
  const e=env(),now=Date.UTC(2026,10,20,20,40);
  await e.SETTINGS.put("btc:interval","5");
  const requests=[];
  const fetchFn=async(url,opts)=>{
    requests.push({url,opts});
    if(url.includes("interval=5m"))return {ok:true,json:async()=>({code:0,data:[
      {time:now-10*60000,close:"60000"},
      {time:now-5*60000,close:"99999"}
    ]})};
    if(url.includes("interval=1h")){
      const hourStart=Math.floor(now/3600000)*3600000;
      return {ok:true,json:async()=>({code:0,data:Array.from({length:80},(_,i)=>({
        time:hourStart-(80-i)*3600000,close:String(59000+i*20)
      }))})};
    }
    return {ok:true,status:204};
  };
  assert.equal(await sendIfDue(e,now,{fetchFn,sleep:async()=>{}}),"sent");
  assert.equal(requests.length,3);
  const embed=JSON.parse(requests.at(-1).opts.body).embeds[0];
  assert.match(embed.fields[0].value,/60,000.00/);
  assert.match(embed.description,/Nem kereskedési jelzés/);
  assert.match(embed.fields.at(-1).value,/külön működik/);
});
test("old market data status uses caution color",()=>{
  const b=heartbeatEmbed("60",Date.now(),
    {close:60000,closeAt:Date.now()-15*60000,age:15,trend:"SHORT"});
  assert.equal(b.color,0xF1C40F);
});
