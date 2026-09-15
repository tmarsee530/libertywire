/* Rally Point News — progressive enhancement for the AI-native newsroom. */
(async()=>{
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const age=d=>{if(!d)return'';const m=Math.max(0,Math.floor((Date.now()-new Date(d).getTime())/60000));return m<60?`${m}m ago`:m<1440?`${Math.floor(m/60)}h ago`:`${Math.floor(m/1440)}d ago`};
 const norm=u=>{try{const x=new URL(u,location.href);x.hash='';return x.href.replace(/\/$/,'')}catch{return String(u||'')}};
 const track=(name,params={})=>{try{if(typeof window.gtag==='function')window.gtag('event',name,params)}catch(e){}};
 document.addEventListener('click',e=>{const a=e.target.closest('[data-rp-event],.newsletter-native-cta');if(!a)return;track(a.dataset.rpEvent||'link_click',{link_url:a.href||'',link_text:(a.textContent||'').trim().slice(0,100)})});

 // The public product is Rally Point's own reporting. The source monitor remains
 // available as evidence/discovery infrastructure rather than the site's identity.
 document.querySelectorAll('.newsroom-nav a').forEach(a=>{
  const t=(a.textContent||'').trim();
  if(t==='The Wire'){a.textContent='AI Newsroom';a.href='briefs/';a.dataset.rpEvent='ai_newsroom_nav_click'}
  if(t==='Rally Briefs'){a.textContent='Brief Archive'}
  if(t==='Newsletter'){a.href='newsletter/';a.dataset.rpEvent='newsletter_nav_click'}
 });
 const section=document.querySelector('.section-label span');if(section&&section.textContent.trim()==='The Wire')section.textContent='Source Monitor';
 const sectionLabel=document.querySelector('.section-label');if(sectionLabel){const small=sectionLabel.querySelector('small');if(small)small.textContent='Publisher coverage feeding the Rally Point newsroom'}

 const newsletter=document.querySelector('.newsletter-card');
 if(newsletter){newsletter.id='briefing';const legacy=newsletter.querySelector('iframe[src*="substack.com"]');if(legacy)legacy.replaceWith(Object.assign(document.createElement('a'),{href:'newsletter/',className:'newsletter-native-cta',textContent:'Subscribe free to The Rally Brief →'}));const h=newsletter.querySelector('h2');if(h)h.textContent='Get The Rally Brief';const p=newsletter.querySelector('p');if(p)p.textContent='A concise email built around Rally Point reporting and source links you can inspect.'}

 // Put Rally Point reporting ahead of the external source monitor.
 try{
  const br=await fetch(`data/briefs.json?t=${Date.now()}`,{cache:'no-store'});
  if(br.ok){const bd=await br.json(),briefs=(bd.briefs||[]).slice(0,6);if(briefs.length){
   const old=document.querySelector('.ai-newsroom-home');if(old)old.remove();
   const wrap=document.createElement('section');wrap.className='ai-newsroom-home';wrap.setAttribute('aria-label','Latest Rally Point reporting');
   wrap.innerHTML=`<div class="ai-newsroom-head"><div><span>AI-Native Newsroom</span><h2>Reporting built from the sources up.</h2><p>Rally Point synthesizes multiple sources into original Briefs, with sourcing and uncertainty kept visible.</p></div><a href="briefs/" data-rp-event="ai_newsroom_archive_click">All reporting →</a></div><div class="ai-newsroom-grid">${briefs.map((b,i)=>`<article class="ai-brief ${i===0?'ai-brief-lead':''}"><div class="ai-brief-kicker">${i===0?'Latest Report':'Rally Brief'}${b.source_count?` · ${esc(b.source_count)} sources`:''}</div><h3><a href="${esc(b.url||'/briefs/')}" data-rp-event="ai_newsroom_story_click">${esc(b.title||'Rally Brief')}</a></h3><p>${esc(b.description||'Original source-based synthesis from Rally Point News.')}</p><a class="ai-brief-read" href="${esc(b.url||'/briefs/')}">Read report →</a></article>`).join('')}</div>`;
   const latest=document.querySelector('.latest-brief');const label=document.querySelector('.section-label');
   (latest||label)?.insertAdjacentElement('beforebegin',wrap);
  }}
 }catch(e){}

 try{
  const r=await fetch(`data/storylines.json?t=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw 0;const d=await r.json();
  const generated=new Date(d.generated_at||0);if(!d.storylines?.length||Date.now()-generated.getTime()>55*60000)throw 0;
  const multi=d.storylines.filter(x=>x.source_count>=2);if(!multi.length)return;
  let strip=document.querySelector('.newsroom-strip');if(!strip){strip=document.createElement('div');strip.className='newsroom-strip';strip.innerHTML=`<span><b>${d.storyline_count}</b> monitored storylines</span><span><b>${d.multi_source_count}</b> multi-source</span><span><b>${d.developing_count}</b> developing</span><span>source monitor</span>`;document.querySelector('header')?.insertAdjacentElement('afterend',strip)}
  const lead=multi[0],c=lead.coverage||[],first=c[0];if(first){const el=document.getElementById('lead');if(el)el.innerHTML=`<div class="kicker">Source Monitor · ${lead.status==='developing'?'Developing':'Top Story'}</div><div class="lead-body"><div class="storyline-proof"><strong>${lead.source_count} sources</strong> covering this storyline</div><h1><a href="${esc(first.link)}" target="_blank" rel="noopener">${esc(lead.title)}</a></h1><div class="source-tag">${esc(first.source)} <span class="dot">•</span><span class="time">${age(first.date)}</span></div><div class="also-list">${c.slice(1,5).map(x=>`<div class="also-item"><span class="also-source">${esc(x.source)}</span><a href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.title)}</a></div>`).join('')}</div></div>`}
  const count=document.getElementById('storyCount');if(count)count.textContent=`${d.storyline_count} monitored storylines · ${d.multi_source_count} covered across multiple sources`;
  const byLink=new Map();for(const s of multi)for(const item of(s.coverage||[]))byLink.set(norm(item.link),s);
  const decorate=()=>document.querySelectorAll('#grid .story').forEach(card=>{if(card.dataset.rpIntel==='1')return;const a=card.querySelector('h3 a');if(!a)return;const s=byLink.get(norm(a.href)),body=card.querySelector('.story-body');if(!s||!body)return;const badge=document.createElement('div');badge.className='storyline-proof wire-proof';badge.innerHTML=`<strong>${s.source_count} sources</strong><span>${s.status==='developing'?'developing':'multi-source'}</span>`;body.insertBefore(badge,body.firstChild);card.dataset.rpIntel='1'});decorate();const grid=document.getElementById('grid');if(grid)new MutationObserver(decorate).observe(grid,{childList:true,subtree:true});
 }catch(e){}
})();
