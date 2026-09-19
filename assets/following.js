/* Rally Point Your Stories: explicit, local follows only. */
(async()=>{
  const api=window.RallyPointTimelineState,status=document.getElementById('following-status'),list=document.getElementById('following-list');
  if(!api||!status||!list)return;
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const track=(name,key,params={})=>{try{const marker=`rp-event:${name}:${key}`;if(sessionStorage.getItem(marker))return;sessionStorage.setItem(marker,'1');if(typeof window.gtag==='function')window.gtag('event',name,params)}catch(e){if(typeof window.gtag==='function')window.gtag('event',name,params)}};
  const relative=value=>{const time=new Date(value).getTime();if(!time)return 'Activity time unavailable';const minutes=Math.max(0,Math.floor((Date.now()-time)/60000));return minutes<60?`Updated ${minutes}m ago`:minutes<1440?`Updated ${Math.floor(minutes/60)}h ago`:`Updated ${Math.floor(minutes/1440)}d ago`};
  if(!api.storageAvailable(localStorage)){status.textContent='Your browser is not allowing local story storage. Timelines remain available normally.';status.classList.add('is-warning');return}
  const index=await api.homepageIndex();
  const render=()=>{
    const items=api.sortFollowed(api.followedStories(localStorage),index);
    track('following_view','page',{followed_story_count:items.length});
    if(!items.length){status.innerHTML='No followed stories yet. <a href="/stories/">Browse live timelines</a> and choose <strong>Follow this story</strong>.';list.innerHTML='';return}
    status.textContent=`${items.length} followed stor${items.length===1?'y':'ies'} on this device`;
    list.innerHTML=items.map(item=>{const count=api.unseenCount(localStorage,item.timelineId,item.update_ids||[]);if(count)track('followed_story_new_updates_available',item.timelineId,{timeline_id:item.timelineId,new_update_count:count});const state=item.active?(item.currentStatus||'Rally Point is tracking this story.'):'This story is not in the current active index. Its canonical timeline remains available.';return `<article class="following-card${item.active?'':' is-inactive'}" data-timeline-id="${esc(item.timelineId)}"><p class="following-label">${item.active?esc(String(item.status||'developing').toUpperCase()):'INACTIVE / ARCHIVED'}</p><h2><a data-followed-open href="${esc(item.url)}">${esc(item.title||'Followed story')}</a></h2><p class="following-summary">${esc(state)}</p><div class="following-meta"><span>${esc(relative(item.last_updated||item.lastKnownUpdateAt))}</span>${count?`<strong>${count} unseen development${count===1?'':'s'}</strong>`:'<span>No unseen developments</span>'}</div><div class="following-actions"><a data-followed-open href="${esc(item.url)}">Open timeline →</a><button type="button" data-unfollow>Unfollow</button></div></article>`}).join('');
  };
  list.addEventListener('click',event=>{const card=event.target.closest('[data-timeline-id]');if(!card)return;const id=card.dataset.timelineId;if(event.target.closest('[data-followed-open]'))track('followed_story_open',`${id}:${Date.now()}`,{timeline_id:id});const button=event.target.closest('[data-unfollow]');if(button){event.preventDefault();if(api.unfollowStory(localStorage,id)){if(typeof window.gtag==='function')window.gtag('event','story_unfollow',{timeline_id:id,source:'following'});render()}}});
  render();
})();
