/* Rally Point News — stripped-down Top Stories + The Wire front page. */
(async()=>{
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const age=d=>{if(!d)return'';const m=Math.max(0,Math.floor((Date.now()-new Date(d).getTime())/60000));return m<60?`${m}m ago`:m<1440?`${Math.floor(m/60)}h ago`:`${Math.floor(m/1440)}d ago`};
 const norm=u=>{try{const x=new URL(u,location.href);x.hash='';return x.href.replace(/\/$/,'')}catch{return String(u||'')}};
 const track=(name,params={})=>{try{if(typeof window.gtag==='function')window.gtag('event',name,params)}catch(e){}};
 document.addEventListener('click',e=>{const a=e.target.closest('[data-rp-event]');if(a)track(a.dataset.rpEvent||'link_click',{link_url:a.href||'',link_text:(a.textContent||'').trim().slice(0,100)})});
 // Enforce the intentionally minimal front page even before the next generated index lands.
 document.querySelectorAll('.ai-newsroom-home,.latest-brief,.method-note,.newsroom-strip,.newsletter-card,.ad-slot').forEach(x=>x.remove());
 const nav=document.querySelector('.newsroom-nav');if(nav)nav.innerHTML='<a href="#lead">Top Stories</a><a href="#grid">The Wire</a>';
 const section=document.querySelector('.section-label span');if(section)section.textContent='The Wire';const sectionLabel=document.querySelector('.section-label');if(sectionLabel){const small=sectionLabel.querySelector('small');if(small)small.textContent='Headlines from across the news landscape'}
 try{
  const r=await fetch(`data/storylines.json?t=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw 0;const d=await r.json();const generated=new Date(d.generated_at||0);if(!d.storylines?.length||Date.now()-generated.getTime()>180*60000)throw 0;const multi=d.storylines.filter(x=>x.source_count>=2);if(!multi.length)return;
  const lead=multi[0],c=lead.coverage||[],first=c[0];if(first){const el=document.getElementById('lead');if(el)el.innerHTML=`<div class="kicker">Top Story</div><div class="lead-body"><h1><a href="${esc(first.link)}" target="_blank" rel="noopener">${esc(lead.title)}</a></h1><div class="source-tag">${esc(first.source)} <span class="dot">•</span><span class="time">${age(first.date)}</span></div><div class="also-list">${c.slice(1,5).map(x=>`<div class="also-item"><span class="also-source">${esc(x.source)}</span><a href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.title)}</a></div>`).join('')}</div></div>`}
  const byLink=new Map();for(const story of d.storylines)for(const item of(story.coverage||[]))byLink.set(norm(item.link),story);
  const grid=document.getElementById('grid');if(grid){const cards=[...grid.querySelectorAll('.story')];cards.sort((a,b)=>{const sa=byLink.get(norm(a.querySelector('h3 a')?.href)),sb=byLink.get(norm(b.querySelector('h3 a')?.href));return Number(sb?.importance_score||0)-Number(sa?.importance_score||0)});cards.forEach(card=>grid.appendChild(card));}
 }catch(e){}
})();
