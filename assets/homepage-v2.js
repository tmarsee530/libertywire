/* Progressive enhancement: server-side storyline intelligence for homepage. */
(async()=>{
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const age=d=>{if(!d)return'';const m=Math.max(0,Math.floor((Date.now()-new Date(d).getTime())/60000));return m<60?`${m}m ago`:m<1440?`${Math.floor(m/60)}h ago`:`${Math.floor(m/1440)}d ago`};
 try{
  const r=await fetch(`data/storylines.json?t=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw 0;const d=await r.json();
  const generated=new Date(d.generated_at||0);if(!d.storylines?.length||Date.now()-generated.getTime()>55*60000)throw 0;
  const multi=d.storylines.filter(x=>x.source_count>=2);if(!multi.length)return;
  const strip=document.createElement('div');strip.className='newsroom-strip';strip.innerHTML=`<span><b>${d.storyline_count}</b> active storylines</span><span><b>${d.multi_source_count}</b> multi-source</span><span><b>${d.developing_count}</b> developing</span><span>ranked by newsroom intelligence</span>`;
  const header=document.querySelector('header');header?.insertAdjacentElement('afterend',strip);
  const nav=document.createElement('nav');nav.className='newsroom-nav';nav.setAttribute('aria-label','Rally Point sections');nav.innerHTML='<a href="#lead-wrap">Top Story</a><a href="#grid">The Wire</a><a href="briefs/">Rally Briefs</a><a href="#briefing">Newsletter</a>';strip.insertAdjacentElement('afterend',nav);
  const lead=multi[0],c=lead.coverage||[],first=c[0];if(first){const el=document.getElementById('lead');if(el)el.innerHTML=`<div class="kicker">${lead.status==='developing'?'Developing':'Top Story'}</div><div class="lead-body"><div class="storyline-proof"><strong>${lead.source_count} sources</strong> covering this storyline</div><h1><a href="${esc(first.link)}" target="_blank" rel="noopener">${esc(lead.title)}</a></h1><div class="source-tag">${esc(first.source)} <span class="dot">•</span><span class="time">${age(first.date)}</span></div><div class="also-list">${c.slice(1,5).map(x=>`<div class="also-item"><span class="also-source">${esc(x.source)}</span><a href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.title)}</a></div>`).join('')}</div></div>`}
  document.querySelector('.newsletter-card')?.setAttribute('id','briefing');
  const count=document.getElementById('storyCount');if(count)count.textContent=`${d.storyline_count} storylines · ${d.multi_source_count} confirmed across multiple sources`;
 }catch(e){/* Existing newsroom UI remains the fallback. */}
})();
