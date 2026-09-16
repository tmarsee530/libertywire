/* Rally Point News — Top Stories + Drudge-style topical Wire. */
(async()=>{
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const age=d=>{if(!d)return'';const m=Math.max(0,Math.floor((Date.now()-new Date(d).getTime())/60000));return m<60?`${m}m ago`:m<1440?`${Math.floor(m/60)}h ago`:`${Math.floor(m/1440)}d ago`};
 const track=(name,params={})=>{try{if(typeof window.gtag==='function')window.gtag('event',name,params)}catch(e){}};
 document.addEventListener('click',e=>{const a=e.target.closest('[data-rp-event]');if(a)track(a.dataset.rpEvent||'link_click',{link_url:a.href||'',link_text:(a.textContent||'').trim().slice(0,100)})});
 document.querySelectorAll('.ai-newsroom-home,.latest-brief,.method-note,.newsroom-strip,.newsletter-card,.ad-slot').forEach(x=>x.remove());
 const nav=document.querySelector('.newsroom-nav');if(nav)nav.innerHTML='<a href="#lead">Top Stories</a><a href="#grid">The Wire</a>';
 const section=document.querySelector('.section-label span');if(section)section.textContent='The Wire';const sectionLabel=document.querySelector('.section-label');if(sectionLabel){const small=sectionLabel.querySelector('small');if(small)small.textContent='Grouped by developing story'}
 try{
  const [sr,nr]=await Promise.all([fetch(`data/storylines.json?t=${Date.now()}`,{cache:'no-store'}),fetch(`data/news.json?t=${Date.now()}`,{cache:'no-store'})]);
  if(!sr.ok||!nr.ok)throw 0;const d=await sr.json(),news=await nr.json();const generated=new Date(d.generated_at||0);if(!d.storylines?.length||Date.now()-generated.getTime()>180*60000)throw 0;
  const imageByLink=new Map((news.stories||[]).map(x=>[x.link,x.image]));
  const multi=d.storylines.filter(x=>x.source_count>=2);if(!multi.length)return;
  const lead=multi[0],c=lead.coverage||[],first=c[0];if(first){const el=document.getElementById('lead');if(el)el.innerHTML=`<div class="kicker">Top Story</div><div class="lead-body"><h1><a href="${esc(first.link)}" target="_blank" rel="noopener">${esc(lead.title)}</a></h1><div class="source-tag">${esc(first.source)} <span class="dot">•</span><span class="time">${age(first.date)}</span></div><div class="also-list">${c.slice(1,5).map(x=>`<div class="also-item"><span class="also-source">${esc(x.source)}</span><a href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.title)}</a></div>`).join('')}</div></div>`}
  const grid=document.getElementById('grid');if(!grid)return;
  const groups=[];const used=new Set();
  for(const story of d.storylines){
   const coverage=(story.coverage||[]).filter(x=>x.link&&!used.has(x.link));if(!coverage.length)continue;
   coverage.forEach(x=>used.add(x.link));
   // Coverage is the storyline's source ordering. Use the first source that actually
   // supplied an image; never manufacture a placeholder and never show >1 image/topic.
   const imageItem=coverage.find(x=>imageByLink.get(x.link));
   groups.push({story,coverage,imageItem});
  }
  // Keep fresh headlines that did not form a storyline as plain single-headline groups.
  for(const item of(news.stories||[])){if(used.has(item.link))continue;groups.push({story:{title:item.title,importance_score:0},coverage:[item],imageItem:null});used.add(item.link)}
  groups.sort((a,b)=>Number(b.story.importance_score||0)-Number(a.story.importance_score||0));
  grid.innerHTML=groups.map((g,i)=>{const main=g.coverage[0],img=g.imageItem&&imageByLink.get(g.imageItem.link);return `<section class="wire-topic${i<3?' wire-topic-major':''}">${img?`<a class="wire-topic-image" href="${esc(g.imageItem.link)}" target="_blank" rel="noopener"><img src="${esc(img)}" alt="" loading="lazy" decoding="async"></a>`:''}<h3><a href="${esc(main.link)}" target="_blank" rel="noopener">${esc(main.title)}</a></h3>${g.coverage.slice(1).map(x=>`<div class="wire-related"><a href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.title)}</a> <span>${esc(x.source)}</span></div>`).join('')}</section>`}).join('');
 }catch(e){}
})();
