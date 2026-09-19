const SCHEMA_VERSION = 1;
const MAX_ATTEMPTS = 5;
const VERIFY_HOURS = 24;
const BURST_MINUTES = 15;
const SITE = "https://rallypointnews.com";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const json = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), {
  status, headers: { "content-type": "application/json; charset=utf-8", ...headers },
});
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const nowIso = () => new Date().toISOString();
const uuid = () => crypto.randomUUID();
const bytes = n => crypto.getRandomValues(new Uint8Array(n));
const b64url = input => {
  const data = input instanceof Uint8Array ? input : new Uint8Array(input);
  return btoa(String.fromCharCode(...data)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/g,"");
};
const standardB64 = input => { const data=input instanceof Uint8Array?input:new Uint8Array(input); return btoa(String.fromCharCode(...data)); };
const fromB64 = value => { const normalized=value.replace(/-/g,"+").replace(/_/g,"/"); return Uint8Array.from(atob(normalized+"=".repeat((4-normalized.length%4)%4)),c=>c.charCodeAt(0)); };
const digest = async value => b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));
const hmac = async (secret, value) => {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), {name:"HMAC",hash:"SHA-256"}, false, ["sign"]);
  return b64url(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value)));
};
const safeEqual = (a,b) => a.length === b.length && [...a].reduce((n,c,i)=>n | (c.charCodeAt(0)^b.charCodeAt(i)),0) === 0;

export function normalizeEmail(value) { return String(value || "").trim().toLowerCase(); }
export function validEmail(value) { const v=normalizeEmail(value); return v.length <= 254 && EMAIL_RE.test(v); }
export function validTimelineId(value) { return /^[a-f0-9]{12}$/.test(String(value || "")); }
export function validCanonicalUrl(value, timelineId) { return value === `${SITE}/stories/${timelineId}/`; }
export function eventIdentity(timelineId, updateId) { return `${timelineId}:${updateId}:notification-v1`; }
export function deliveryIdentity(subscriptionId, eventId) { return `${subscriptionId}:${eventId}:email-v1`; }
export function retryDelaySeconds(attempt) { return Math.min(21600, 30 * (2 ** Math.max(0, attempt - 1))); }
export function providerFailure(status) {
  if (status === 408 || status === 409 || status === 429 || status >= 500) return "transient";
  return "permanent";
}
export function publicMetric(eventName, fields={}) {
  const allowed = ["timeline_id","classification","status","reason","attempt","count"];
  return Object.fromEntries([["event_name",eventName], ...allowed.filter(k=>fields[k]!==undefined).map(k=>[k,fields[k]])]);
}
export function eligibleIngestEvent(event) {
  return Boolean(event && event.eligible === true && validTimelineId(event.timeline_id) && event.material_update_id &&
    ["BREAKING","MAJOR DEVELOPMENT","UPDATE"].includes(event.classification) &&
    validCanonicalUrl(event.canonical_url,event.timeline_id) && event.summary && event.title && event.published_at);
}

async function encryptionKey(env) {
  const raw = fromB64(env.EMAIL_ENCRYPTION_KEY || "");
  if (raw.length !== 32) throw new Error("EMAIL_ENCRYPTION_KEY must decode to 32 bytes");
  return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt","decrypt"]);
}
async function encryptEmail(env, email) {
  const iv=bytes(12), key=await encryptionKey(env);
  const ciphertext=await crypto.subtle.encrypt({name:"AES-GCM",iv},key,new TextEncoder().encode(email));
  return {ciphertext:b64url(ciphertext),iv:b64url(iv)};
}
async function decryptEmail(env, row) {
  const key=await encryptionKey(env);
  const plain=await crypto.subtle.decrypt({name:"AES-GCM",iv:fromB64(row.email_iv)},key,fromB64(row.email_ciphertext));
  return new TextDecoder().decode(plain);
}
async function emailHash(env,email){ return hmac(env.EMAIL_HASH_SECRET,email); }
async function purposeToken(env,purpose,id){ return hmac(env.TOKEN_SECRET,`${purpose}:${id}`); }
async function verifyPurposeToken(env,purpose,id,token){ return safeEqual(await purposeToken(env,purpose,id),String(token||"")); }

function cors(env, request) {
  const origin=request.headers.get("origin") || "";
  const allowed=origin === (env.SITE_ORIGIN || SITE);
  return allowed ? {"access-control-allow-origin":origin,"vary":"Origin","access-control-allow-headers":"content-type","access-control-allow-methods":"POST,OPTIONS"} : {};
}
async function parseJson(request){ try{return await request.json()}catch{return null} }
async function metric(env,eventName,fields={}){
  const safe=publicMetric(eventName,fields);
  await env.DB.prepare("INSERT INTO email_metrics(id,event_name,subscriber_ref,timeline_id,delivery_id,event_at,metadata_json) VALUES(?,?,?,?,?,?,?)")
    .bind(uuid(),eventName,fields.subscriber_ref||null,fields.timeline_id||null,fields.delivery_id||null,nowIso(),JSON.stringify(safe)).run();
}
async function rateLimit(env,key,limit,minutes){
  const size=minutes*60*1000, start=new Date(Math.floor(Date.now()/size)*size).toISOString();
  await env.DB.prepare("INSERT INTO rate_limits(key,window_start,count) VALUES(?,?,1) ON CONFLICT(key,window_start) DO UPDATE SET count=count+1").bind(key,start).run();
  const row=await env.DB.prepare("SELECT count FROM rate_limits WHERE key=? AND window_start=?").bind(key,start).first();
  return Number(row?.count||0) <= limit;
}
async function resend(env,payload,idempotencyKey){
  if (!env.RESEND_API_KEY) return {ok:false,status:503,error:"provider_not_configured"};
  const response=await fetch("https://api.resend.com/emails",{method:"POST",headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,"content-type":"application/json","idempotency-key":idempotencyKey},body:JSON.stringify(payload)});
  let body={}; try{body=await response.json()}catch{}
  return {ok:response.ok,status:response.status,id:body.id||null,error:body.message||body.name||`provider_${response.status}`};
}

export function renderAlertEmail(event, links){
  const classification=esc(event.classification), title=esc(event.title), summary=esc(event.summary);
  return {
    subject:`${event.classification === "BREAKING" ? "Breaking: " : "Important update: "}${event.title}`.slice(0,180),
    html:`<!doctype html><html><body style="margin:0;background:#f4f5f7;color:#111;font-family:Arial,sans-serif"><main style="max-width:620px;margin:auto;background:#fff;padding:28px"><p style="font-size:12px;font-weight:700;letter-spacing:.12em">RALLY POINT NEWS</p><p style="color:#8f1720;font-size:12px;font-weight:700">${classification}</p><h1 style="font:700 28px/1.15 Georgia,serif">${title}</h1><p style="font:17px/1.5 Georgia,serif">${summary}</p><p><a href="${esc(links.click)}" style="display:inline-block;background:#12213a;color:#fff;padding:12px 18px;text-decoration:none;font-weight:700">Open the live timeline</a></p><hr style="border:0;border-top:1px solid #ddd;margin:28px 0"><p style="font-size:12px;color:#666">You received this because you explicitly followed this story and confirmed email alerts. Rally Point sends alerts only for material developments.</p><p style="font-size:12px"><a href="${esc(links.storyUnsubscribe)}">Stop alerts for this story</a> · <a href="${esc(links.allUnsubscribe)}">Stop all Rally Point alerts</a></p></main></body></html>`,
    text:`${event.classification}\n\n${event.title}\n\n${event.summary}\n\nOpen the live timeline: ${links.click}\n\nYou received this because you followed this story and confirmed email alerts.\nStop this story: ${links.storyUnsubscribe}\nStop all alerts: ${links.allUnsubscribe}`
  };
}

async function optIn(request,env){
  const headers=cors(env,request), body=await parseJson(request);
  if(!body || body.website) return json({ok:true,message:"Check your inbox if the address is eligible."},202,headers);
  const email=normalizeEmail(body.email), timelineId=String(body.timeline_id||"");
  if(!validEmail(email) || !validTimelineId(timelineId)) return json({ok:false,error:"invalid_request"},400,headers);
  const ipKey=await hmac(env.RATE_LIMIT_SECRET,request.headers.get("cf-connecting-ip")||"unknown");
  const eHash=await emailHash(env,email);
  if(!(await rateLimit(env,`optin-ip:${ipKey}`,8,60)) || !(await rateLimit(env,`optin-email:${eHash}`,4,60))) return json({ok:false,error:"rate_limited"},429,headers);
  const stamp=nowIso(), subscriberId=uuid(), subscriptionId=uuid(), encrypted=await encryptEmail(env,email);
  await env.DB.batch([
    env.DB.prepare("INSERT INTO subscribers(id,email_hash,email_ciphertext,email_iv,status,created_at,confirmation_sent_at,schema_version) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(email_hash) DO UPDATE SET email_ciphertext=excluded.email_ciphertext,email_iv=excluded.email_iv,confirmation_sent_at=excluded.confirmation_sent_at").bind(subscriberId,eHash,encrypted.ciphertext,encrypted.iv,"pending",stamp,stamp,SCHEMA_VERSION),
  ]);
  const subscriber=await env.DB.prepare("SELECT id,status FROM subscribers WHERE email_hash=?").bind(eHash).first();
  await env.DB.prepare("INSERT INTO subscriptions(id,subscriber_id,timeline_id,status,followed_at,baseline_material_update_id,schema_version) VALUES(?,?,?,?,?,?,?) ON CONFLICT(subscriber_id,timeline_id) DO UPDATE SET status=CASE WHEN subscriptions.status='active' THEN 'active' ELSE 'pending' END, baseline_material_update_id=excluded.baseline_material_update_id")
    .bind(subscriptionId,subscriber.id,timelineId,"pending",stamp,body.baseline_material_update_id||null,SCHEMA_VERSION).run();
  const subscription=await env.DB.prepare("SELECT id,status FROM subscriptions WHERE subscriber_id=? AND timeline_id=?").bind(subscriber.id,timelineId).first();
  if(subscription.status==="active") return json({ok:true,message:"Email alerts are already active for this story."},200,headers);
  const token=b64url(bytes(32)), tokenHash=await digest(token), expires=new Date(Date.now()+VERIFY_HOURS*3600000).toISOString();
  await env.DB.prepare("INSERT OR REPLACE INTO consent_tokens(token_hash,subscriber_id,subscription_id,purpose,created_at,expires_at,used_at) VALUES(?,?,?,?,?,?,NULL)").bind(tokenHash,subscriber.id,subscription.id,"verify_email",stamp,expires).run();
  const confirm=`${env.PUBLIC_ORIGIN}/confirm?token=${encodeURIComponent(token)}`;
  const sent=await resend(env,{from:env.EMAIL_FROM,to:[email],reply_to:env.EMAIL_REPLY_TO,subject:"Confirm Rally Point story alerts",html:`<p><strong>Rally Point News</strong></p><p>Confirm that you want email only when something important changes in the story you followed.</p><p><a href="${esc(confirm)}">Confirm story alerts</a></p><p>This link expires in 24 hours. If you did not request it, ignore this email.</p>`,text:`Confirm Rally Point story alerts: ${confirm}\n\nThis link expires in 24 hours. If you did not request it, ignore this email.`},`verify:${subscription.id}:${tokenHash}`);
  await metric(env,"email_opt_in_started",{subscriber_ref:subscriber.id,timeline_id:timelineId,status:sent.ok?"verification_sent":"verification_failed"});
  if(!sent.ok) return json({ok:false,error:"verification_unavailable"},503,headers);
  return json({ok:true,message:"Check your inbox and confirm email alerts."},202,headers);
}

async function confirm(request,env){
  const token=new URL(request.url).searchParams.get("token")||"", hash=await digest(token), stamp=nowIso();
  const row=await env.DB.prepare("SELECT * FROM consent_tokens WHERE token_hash=? AND purpose='verify_email'").bind(hash).first();
  if(!row || row.used_at || row.expires_at < stamp) return htmlPage("Confirmation link unavailable","This confirmation link is invalid, expired, or already used.",400);
  await env.DB.batch([
    env.DB.prepare("UPDATE consent_tokens SET used_at=? WHERE token_hash=? AND used_at IS NULL").bind(stamp,hash),
    env.DB.prepare("UPDATE subscribers SET status='active',confirmed_at=? WHERE id=? AND status!='suppressed'").bind(stamp,row.subscriber_id),
    env.DB.prepare("UPDATE subscriptions SET status='active',confirmed_at=? WHERE id=?").bind(stamp,row.subscription_id),
  ]);
  const sub=await env.DB.prepare("SELECT timeline_id FROM subscriptions WHERE id=?").bind(row.subscription_id).first();
  await metric(env,"email_opt_in_confirmed",{subscriber_ref:row.subscriber_id,timeline_id:sub?.timeline_id});
  return htmlPage("Email alerts confirmed","You will receive an email only when Rally Point publishes an eligible material development for this story.",200,`${env.SITE_ORIGIN}/stories/${sub.timeline_id}/`);
}

function htmlPage(title,message,status=200,returnUrl=null){
  return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>${esc(title)} · Rally Point News</title></head><body style="font:16px/1.5 Arial,sans-serif;max-width:640px;margin:48px auto;padding:0 18px;color:#12213a"><p style="font-weight:700;letter-spacing:.12em">RALLY POINT NEWS</p><h1>${esc(title)}</h1><p>${esc(message)}</p>${returnUrl?`<p><a href="${esc(returnUrl)}">Return to the live timeline</a></p>`:""}</body></html>`,{status,headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store"}});
}

async function ingest(request,env){
  if(request.headers.get("authorization") !== `Bearer ${env.INGEST_SECRET}`) return json({ok:false,error:"unauthorized"},401);
  const body=await parseJson(request), events=Array.isArray(body?.events)?body.events:[];
  if(events.length>200 || events.some(e=>!eligibleIngestEvent(e))) return json({ok:false,error:"invalid_events"},400);
  let created=0,queued=0,deduped=0; const stamp=nowIso();
  for(const event of events){
    const eventId=await digest(eventIdentity(event.timeline_id,event.material_update_id));
    const insert=await env.DB.prepare("INSERT OR IGNORE INTO notification_events(id,timeline_id,material_update_id,title,classification,summary,canonical_url,published_at,significance_reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)")
      .bind(eventId,event.timeline_id,event.material_update_id,event.title,event.classification,event.summary,event.canonical_url,event.published_at,event.significance_reason||"foundation_eligible",stamp).run();
    if(!insert.meta?.changes){deduped++;continue} created++;
    const subscriptions=await env.DB.prepare("SELECT s.id,s.subscriber_id,s.last_sent_at FROM subscriptions s JOIN subscribers p ON p.id=s.subscriber_id WHERE s.timeline_id=? AND s.status='active' AND p.status='active'").bind(event.timeline_id).all();
    for(const sub of subscriptions.results||[]){
      const key=await digest(deliveryIdentity(sub.id,eventId)), notBefore=sub.last_sent_at && Date.now()-Date.parse(sub.last_sent_at)<BURST_MINUTES*60000 ? new Date(Date.parse(sub.last_sent_at)+BURST_MINUTES*60000).toISOString() : stamp;
      const delivery=await env.DB.prepare("INSERT OR IGNORE INTO email_deliveries(id,dedupe_key,subscriber_id,subscription_id,event_id,status,not_before,created_at) VALUES(?,?,?,?,?,'pending',?,?)").bind(uuid(),key,sub.subscriber_id,sub.id,eventId,notBefore,stamp).run();
      queued+=Number(delivery.meta?.changes||0);
    }
  }
  await metric(env,"email_notification_queued",{count:queued,status:"accepted"});
  return json({ok:true,events_created:created,deliveries_queued:queued,events_deduped:deduped});
}

async function processQueue(env){
  if(String(env.DELIVERY_ENABLED)!=="true") return {state:"disabled",processed:0};
  const stamp=nowIso(), rows=await env.DB.prepare("SELECT d.*,e.timeline_id,e.material_update_id,e.title,e.classification,e.summary,e.canonical_url,p.email_ciphertext,p.email_iv,p.status subscriber_status,s.status subscription_status FROM email_deliveries d JOIN notification_events e ON e.id=d.event_id JOIN subscribers p ON p.id=d.subscriber_id JOIN subscriptions s ON s.id=d.subscription_id WHERE d.status IN ('pending','retry') AND d.not_before<=? AND (d.lease_until IS NULL OR d.lease_until<?) ORDER BY d.created_at LIMIT 25").bind(stamp,stamp).all();
  let processed=0;
  for(const row of rows.results||[]){
    if(row.subscriber_status!=="active"||row.subscription_status!=="active"){
      await env.DB.prepare("UPDATE email_deliveries SET status='cancelled',last_error_code='unsubscribed_before_delivery' WHERE id=? AND status IN ('pending','retry')").bind(row.id).run(); continue;
    }
    const lease=new Date(Date.now()+120000).toISOString();
    const claimed=await env.DB.prepare("UPDATE email_deliveries SET status='processing',lease_until=?,attempts=attempts+1 WHERE id=? AND status IN ('pending','retry') AND (lease_until IS NULL OR lease_until<?)").bind(lease,row.id,stamp).run();
    if(!claimed.meta?.changes)continue;
    processed++;
    const newer=await env.DB.prepare("SELECT id FROM email_deliveries WHERE subscription_id=? AND status IN ('pending','retry') AND created_at>? ORDER BY created_at DESC LIMIT 1").bind(row.subscription_id,row.created_at).first();
    if(newer){await env.DB.prepare("UPDATE email_deliveries SET status='suppressed',last_error_code='coalesced_by_newer_development' WHERE id=?").bind(row.id).run();continue}
    let email; try{email=await decryptEmail(env,row)}catch{await failDelivery(env,row,"decrypt_failed",true);continue}
    const clickToken=await purposeToken(env,"click",row.id), storyToken=await purposeToken(env,"unsubscribe-story",row.id), allToken=await purposeToken(env,"unsubscribe-all",row.id);
    const base=env.PUBLIC_ORIGIN, links={click:`${base}/r/${row.id}?token=${clickToken}`,storyUnsubscribe:`${base}/unsubscribe?delivery=${row.id}&scope=story&token=${storyToken}`,allUnsubscribe:`${base}/unsubscribe?delivery=${row.id}&scope=all&token=${allToken}`};
    const content=renderAlertEmail(row,links);
    const sent=await resend(env,{from:env.EMAIL_FROM,to:[email],reply_to:env.EMAIL_REPLY_TO,subject:content.subject,html:content.html,text:content.text,headers:{"List-Unsubscribe":`<${links.storyUnsubscribe}>`,"List-Unsubscribe-Post":"List-Unsubscribe=One-Click"}},row.dedupe_key);
    if(sent.ok){
      const delivered=nowIso(); await env.DB.batch([
        env.DB.prepare("UPDATE email_deliveries SET status='sent',provider_message_id=?,delivered_at=?,lease_until=NULL,last_error=NULL,last_error_code=NULL WHERE id=?").bind(sent.id,delivered,row.id),
        env.DB.prepare("UPDATE subscriptions SET last_delivered_material_update_id=?,last_sent_at=? WHERE id=?").bind(row.material_update_id,delivered,row.subscription_id),
      ]); await metric(env,"email_notification_sent",{subscriber_ref:row.subscriber_id,timeline_id:row.timeline_id,delivery_id:row.id,classification:row.classification});
    }else await failDelivery(env,row,sent.error,providerFailure(sent.status)==="permanent");
  }
  return {state:"ready",processed};
}
async function failDelivery(env,row,error,permanent){
  const terminal=permanent || Number(row.attempts||0)+1>=MAX_ATTEMPTS, stamp=nowIso();
  if(terminal) await env.DB.prepare("UPDATE email_deliveries SET status='failed',failed_at=?,lease_until=NULL,last_error_code=?,last_error=? WHERE id=?").bind(stamp,permanent?"permanent_provider_failure":"retry_exhausted",String(error).slice(0,300),row.id).run();
  else await env.DB.prepare("UPDATE email_deliveries SET status='retry',not_before=?,lease_until=NULL,last_error_code='transient_provider_failure',last_error=? WHERE id=?").bind(new Date(Date.now()+retryDelaySeconds(Number(row.attempts||0)+1)*1000).toISOString(),String(error).slice(0,300),row.id).run();
  await metric(env,"email_notification_failed",{subscriber_ref:row.subscriber_id,timeline_id:row.timeline_id,delivery_id:row.id,status:terminal?"failed":"retry",attempt:Number(row.attempts||0)+1});
}

async function unsubscribe(request,env){
  const url=new URL(request.url), deliveryId=url.searchParams.get("delivery")||"", scope=url.searchParams.get("scope")==="all"?"all":"story", token=url.searchParams.get("token")||"";
  if(!(await verifyPurposeToken(env,`unsubscribe-${scope}`,deliveryId,token))) return htmlPage("Unsubscribe link unavailable","This unsubscribe link is invalid.",400);
  const row=await env.DB.prepare("SELECT d.subscriber_id,d.subscription_id,p.status subscriber_status,s.status subscription_status FROM email_deliveries d JOIN subscribers p ON p.id=d.subscriber_id JOIN subscriptions s ON s.id=d.subscription_id WHERE d.id=?").bind(deliveryId).first();
  if(!row)return htmlPage("Unsubscribe link unavailable","This unsubscribe link is invalid.",400);
  if(request.method==="GET") return new Response(`<!doctype html><html><body style="font:16px/1.5 Arial,sans-serif;max-width:640px;margin:48px auto;padding:0 18px"><h1>Stop ${scope==="all"?"all Rally Point email alerts":"email alerts for this story"}?</h1><form method="post"><button type="submit" style="padding:12px 18px">Confirm unsubscribe</button></form></body></html>`,{headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store"}});
  const alreadyStopped=scope==="all"?row.subscriber_status==="unsubscribed":row.subscription_status==="unsubscribed";
  if(alreadyStopped)return htmlPage("Email alerts already stopped",scope==="all"?"All Rally Point email alerts were already stopped.":"Email alerts for this story were already stopped. Your browser follow remains unchanged.");
  const stamp=nowIso();
  if(scope==="all") await env.DB.batch([
    env.DB.prepare("UPDATE subscribers SET status='unsubscribed',unsubscribed_at=? WHERE id=? AND status!='suppressed'").bind(stamp,row.subscriber_id),
    env.DB.prepare("UPDATE subscriptions SET status='unsubscribed',unsubscribed_at=? WHERE subscriber_id=?").bind(stamp,row.subscriber_id),
    env.DB.prepare("UPDATE email_deliveries SET status='cancelled',last_error_code='unsubscribed_before_delivery' WHERE subscriber_id=? AND status IN ('pending','retry')").bind(row.subscriber_id),
  ]); else await env.DB.batch([
    env.DB.prepare("UPDATE subscriptions SET status='unsubscribed',unsubscribed_at=? WHERE id=?").bind(stamp,row.subscription_id),
    env.DB.prepare("UPDATE email_deliveries SET status='cancelled',last_error_code='unsubscribed_before_delivery' WHERE subscription_id=? AND status IN ('pending','retry')").bind(row.subscription_id),
  ]);
  await metric(env,"email_notification_unsubscribed",{subscriber_ref:row.subscriber_id,delivery_id:deliveryId,status:scope});
  return htmlPage("Email alerts stopped",scope==="all"?"All Rally Point email alerts have been stopped.":"Email alerts for this story have been stopped. Your browser follow remains unchanged.");
}

async function clickThrough(request,env,id){
  const token=new URL(request.url).searchParams.get("token")||"";
  if(!(await verifyPurposeToken(env,"click",id,token)))return htmlPage("Link unavailable","This alert link is invalid.",400);
  const row=await env.DB.prepare("SELECT d.click_at,e.canonical_url,e.timeline_id,d.subscriber_id FROM email_deliveries d JOIN notification_events e ON e.id=d.event_id WHERE d.id=?").bind(id).first();
  if(!row)return htmlPage("Link unavailable","This alert link is invalid.",400);
  if(!row.click_at){await env.DB.prepare("UPDATE email_deliveries SET click_at=? WHERE id=? AND click_at IS NULL").bind(nowIso(),id).run();await metric(env,"email_notification_click",{subscriber_ref:row.subscriber_id,timeline_id:row.timeline_id,delivery_id:id})}
  return Response.redirect(row.canonical_url,302);
}

async function verifyWebhook(request,env,body){
  const id=request.headers.get("svix-id")||"", timestamp=request.headers.get("svix-timestamp")||"", signatures=request.headers.get("svix-signature")||"";
  if(!id||!timestamp||Math.abs(Date.now()/1000-Number(timestamp))>300)return false;
  const secret=String(env.RESEND_WEBHOOK_SECRET||"").replace(/^whsec_/,"");
  if(!secret)return false;
  const key=await crypto.subtle.importKey("raw",fromB64(secret),{name:"HMAC",hash:"SHA-256"},false,["sign"]);
  const expected=standardB64(await crypto.subtle.sign("HMAC",key,new TextEncoder().encode(`${id}.${timestamp}.${body}`)));
  return signatures.split(" ").some(part=>safeEqual(part.replace(/^v1,/,""),expected));
}
async function webhook(request,env){
  const raw=await request.text(); if(!(await verifyWebhook(request,env,raw)))return json({ok:false,error:"invalid_signature"},401);
  const event=JSON.parse(raw), providerId=event.data?.email_id||event.data?.id||null, eventId=event.id||request.headers.get("svix-id"), type=event.type||"unknown", stamp=nowIso();
  const inserted=await env.DB.prepare("INSERT OR IGNORE INTO provider_events(provider_event_id,event_type,payload_hash,received_at) VALUES(?,?,?,?)").bind(eventId,type,await digest(raw),stamp).run();
  if(!inserted.meta?.changes)return json({ok:true,deduped:true});
  if(providerId && ["email.bounced","email.complained","email.delivery_delayed"].includes(type)){
    const delivery=await env.DB.prepare("SELECT subscriber_id FROM email_deliveries WHERE provider_message_id=?").bind(providerId).first();
    if(delivery && type!=="email.delivery_delayed") await env.DB.batch([
      env.DB.prepare("UPDATE subscribers SET status='suppressed',suppression_reason=? WHERE id=?").bind(type,delivery.subscriber_id),
      env.DB.prepare("UPDATE subscriptions SET status='unsubscribed',unsubscribed_at=? WHERE subscriber_id=?").bind(stamp,delivery.subscriber_id),
      env.DB.prepare("UPDATE email_deliveries SET status='cancelled',last_error_code=? WHERE subscriber_id=? AND status IN ('pending','retry')").bind(type,delivery.subscriber_id),
    ]);
  }
  await env.DB.prepare("UPDATE provider_events SET processed_at=? WHERE provider_event_id=?").bind(nowIso(),eventId).run();
  return json({ok:true});
}

async function health(env){
  const counts=await env.DB.prepare("SELECT status,COUNT(*) count FROM email_deliveries GROUP BY status").all();
  const subscribers=await env.DB.prepare("SELECT COUNT(*) count FROM subscribers WHERE status='active'").first();
  const subscriptions=await env.DB.prepare("SELECT COUNT(*) count FROM subscriptions WHERE status='active'").first();
  const oldest=await env.DB.prepare("SELECT MIN(created_at) oldest FROM email_deliveries WHERE status IN ('pending','retry','processing')").first();
  return json({schema_version:1,state:"READY",delivery_enabled:String(env.DELIVERY_ENABLED)==="true",provider_configured:Boolean(env.RESEND_API_KEY),active_subscribers:Number(subscribers?.count||0),active_story_subscriptions:Number(subscriptions?.count||0),delivery_counts:Object.fromEntries((counts.results||[]).map(x=>[x.status,Number(x.count)])),oldest_pending_at:oldest?.oldest||null,generated_at:nowIso()});
}

export default {
  async fetch(request,env){
    const url=new URL(request.url), path=url.pathname;
    if(request.method==="OPTIONS")return new Response(null,{status:204,headers:cors(env,request)});
    try{
      if(path==="/v1/email/opt-in"&&request.method==="POST")return optIn(request,env);
      if(path==="/confirm"&&request.method==="GET")return confirm(request,env);
      if(path==="/v1/events"&&request.method==="POST")return ingest(request,env);
      if(path==="/v1/webhooks/resend"&&request.method==="POST")return webhook(request,env);
      if(path==="/unsubscribe"&&["GET","POST"].includes(request.method))return unsubscribe(request,env);
      if(path.startsWith("/r/")&&request.method==="GET")return clickThrough(request,env,path.slice(3));
      if(path==="/v1/health"&&request.method==="GET")return health(env);
      return json({ok:false,error:"not_found"},404);
    }catch(error){console.error("email-pilot",error?.message||"unknown_error");return json({ok:false,error:"service_unavailable"},503,cors(env,request))}
  },
  async scheduled(_controller,env,ctx){ctx.waitUntil(processQueue(env));}
};

export { processQueue, purposeToken, verifyPurposeToken };
