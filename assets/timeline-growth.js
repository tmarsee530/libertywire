/* Flagship timeline experiment: no account identifiers or free-text queries. */
(function(){
  'use strict';
  const id=location.pathname.match(/^\/stories\/([a-f0-9]{12})\/?$/)?.[1];
  if(!id)return;
  const featured=Boolean(document.querySelector('.event-guide'));
  const params={timeline_id:id,experiment_id:'flagship-timelines-2026-10',featured_timeline:featured};
  const track=(name,extra={})=>{if(typeof window.gtag==='function')window.gtag('event',name,{...params,...extra})};
  track('timeline_open');
  let visibleSeconds=0,engaged=false;
  const timer=setInterval(()=>{if(document.visibilityState==='visible')visibleSeconds++;
    if(visibleSeconds>=20&&!engaged){engaged=true;track('timeline_engaged');clearInterval(timer)}},1000);
  document.addEventListener('click',event=>{
    const share=event.target.closest('[data-share-timeline]');
    if(share){event.preventDefault();const url=location.origin+location.pathname+'?utm_source=reader&utm_medium=share&utm_campaign=flagship_timeline';
      if(navigator.share){navigator.share({title:share.dataset.shareTitle,url}).then(()=>track('timeline_share',{share_method:'native'})).catch(()=>{});}
      else if(navigator.clipboard){navigator.clipboard.writeText(url).then(()=>{share.textContent='Link copied';track('timeline_share',{share_method:'copy'})}).catch(()=>{share.textContent='Copy this page’s address to share'});}
      return;
    }
    const source=event.target.closest('.update-sources a,.status-source a,.event-guide a');
    if(source&&new URL(source.href).origin!==location.origin)track('timeline_source_open',{source_host:new URL(source.href).hostname});
  });
  const finish=document.querySelector('.end-card');
  if(finish&&'IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){track('timeline_end_reached');observer.disconnect()}},{threshold:.5});observer.observe(finish)}
})();
