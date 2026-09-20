/* Rally Point return-state: local, durable, and safe when storage is blocked. */
(function(root,factory){
  const api=factory(root);
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.RallyPointTimelineState=api;
})(typeof window!=='undefined'?window:null,function(root){
  'use strict';
  const PREFIX='rp-timeline-v1:';
  const FOLLOW_KEY='rp-follows-v1';
  const cleanIds=ids=>[...new Set((ids||[]).filter(x=>typeof x==='string'&&x))];
  const storageAvailable=storage=>{try{const k=PREFIX+'probe';storage.setItem(k,'1');storage.removeItem(k);return true}catch(e){return false}};
  const readState=(storage,id)=>{if(!storageAvailable(storage))return null;try{const value=JSON.parse(storage.getItem(PREFIX+id)||'null');return value&&value.version===1?value:null}catch(e){return null}};
  const writeState=(storage,id,state)=>{if(!storageAvailable(storage))return false;try{storage.setItem(PREFIX+id,JSON.stringify({...state,version:1,timelineId:id}));return true}catch(e){return false}};
  const unseenIds=(current,state)=>state?cleanIds(current).filter(id=>!(state.seenUpdateIds||[]).includes(id)):[];
  const mergeSeen=(state,ids,at)=>({...state,version:1,seenUpdateIds:cleanIds([...(state.seenUpdateIds||[]),...ids]),lastMeaningfulVisitAt:at});
  const timelineId=()=>{const match=root.location.pathname.match(/^\/stories\/([a-f0-9]{12})\/?$/);return match&&match[1]};
  const trackOnce=(name,id,params)=>{try{const key=`rp-event:${name}:${id}`;if(root.sessionStorage.getItem(key))return;root.sessionStorage.setItem(key,'1');if(typeof root.gtag==='function')root.gtag('event',name,params||{})}catch(e){if(typeof root.gtag==='function')root.gtag('event',name,params||{})}};

  function initTimeline(){
    const id=timelineId(); if(!id||!root.document)return;
    const nodes=[...root.document.querySelectorAll('.timeline-update[data-update-id]')];
    const current=cleanIds(nodes.map(x=>x.dataset.updateId)); if(!current.length)return;
    const storage=root.localStorage; if(!storageAvailable(storage)){const button=root.document.querySelector('[data-follow-control]');if(button){button.disabled=true;button.textContent='Follow unavailable';button.setAttribute('aria-label','Follow unavailable because local browser storage is blocked')}return}
    initFollowControl(id,nodes,storage);
    let prior=readState(storage,id); const returning=Boolean(prior&&prior.lastMeaningfulVisitAt);
    let unseen=unseenIds(current,prior), meaningful=false, interacted=false, visibleSeconds=0;
    if(returning){
      trackOnce('timeline_return_visit',id,{timeline_id:id,new_update_count:unseen.length});
      trackOnce('timeline_repeat_session',id,{timeline_id:id});
    }
    const unseenSet=new Set(unseen); nodes.forEach(node=>{if(unseenSet.has(node.dataset.updateId))node.classList.add('is-new')});
    if(unseen.length){
      trackOnce('new_updates_available',id,{timeline_id:id,new_update_count:unseen.length});
      const firstNew=nodes.find(x=>unseenSet.has(x.dataset.updateId));if(firstNew&&firstNew.parentNode){const boundary=root.document.createElement('li');boundary.className='new-update-boundary';boundary.setAttribute('role','separator');boundary.textContent=`${unseen.length} meaningful development${unseen.length===1?'':'s'} since your last visit`;firstNew.parentNode.insertBefore(boundary,firstNew)}
      const box=root.document.createElement('aside'); box.className='return-state'; box.setAttribute('role','status');
      box.innerHTML=`<strong>${unseen.length} new development${unseen.length===1?'':'s'} since your last visit</strong><span>Your previous reading state stays on this device.</span><button type="button">Jump to first new update</button>`;
      const status=root.document.querySelector('.current-status'); if(status)status.insertAdjacentElement('afterend',box);
      box.querySelector('button').addEventListener('click',()=>{const target=nodes.find(x=>unseenSet.has(x.dataset.updateId));if(!target)return;const details=target.closest('details');if(details)details.open=true;target.scrollIntoView({behavior:'smooth',block:'start'});trackOnce('jump_to_new_updates',id,{timeline_id:id,new_update_count:unseen.length});interacted=true});
    }
    const mark=idToMark=>{
      if(!meaningful)return; prior=prior||{version:1,timelineId:id,seenUpdateIds:[]};
      if((prior.seenUpdateIds||[]).includes(idToMark))return;
      prior=mergeSeen(prior,[idToMark],new Date().toISOString()); writeState(storage,id,prior);
      const node=nodes.find(x=>x.dataset.updateId===idToMark);if(node)node.classList.remove('is-new');
      if(unseenSet.has(idToMark))trackOnce('new_updates_seen',id,{timeline_id:id,updates_seen_count:1});
    };
    const observers=new Map(),visible=new Set();
    if('IntersectionObserver' in root){
      const observer=new root.IntersectionObserver(entries=>entries.forEach(entry=>{const uid=entry.target.dataset.updateId;if(entry.isIntersecting&&entry.intersectionRatio>=.55){visible.add(uid);if(!observers.has(uid))observers.set(uid,root.setTimeout(()=>mark(uid),1200))}else{visible.delete(uid);if(observers.has(uid)){root.clearTimeout(observers.get(uid));observers.delete(uid)}}}),{threshold:[.55]});
      nodes.forEach(node=>observer.observe(node));
    }
    const activity=()=>{interacted=true}; root.addEventListener('scroll',activity,{once:true,passive:true});root.addEventListener('pointerdown',activity,{once:true,passive:true});root.addEventListener('keydown',activity,{once:true});
    const timer=root.setInterval(()=>{if(root.document.visibilityState==='visible')visibleSeconds+=1;if(!meaningful&&visibleSeconds>=10&&(interacted||visibleSeconds>=20)){meaningful=true;const stamp=new Date().toISOString();prior=prior||{version:1,timelineId:id,seenUpdateIds:[]};prior={...prior,lastMeaningfulVisitAt:stamp,lastSessionAt:stamp};if(!returning)prior=mergeSeen(prior,current,stamp);writeState(storage,id,prior);if(!returning)nodes.forEach(x=>x.classList.remove('is-new'));else visible.forEach(uid=>root.setTimeout(()=>mark(uid),1200));root.clearInterval(timer)}},1000);
  }

  const emptyFollows=()=>({version:1,stories:{}});
  const readFollows=storage=>{if(!storageAvailable(storage))return null;try{const value=JSON.parse(storage.getItem(FOLLOW_KEY)||'null');return value&&value.version===1&&value.stories&&typeof value.stories==='object'?value:emptyFollows()}catch(e){return emptyFollows()}};
  const writeFollows=(storage,value)=>{if(!storageAvailable(storage))return false;try{storage.setItem(FOLLOW_KEY,JSON.stringify({version:1,stories:{...(value&&value.stories||{})}}));return true}catch(e){return false}};
  const followStory=(storage,story,at)=>{const state=readFollows(storage);if(!state||!story||!story.timelineId)return false;state.stories[story.timelineId]={timelineId:story.timelineId,followedAt:at||new Date().toISOString(),title:story.title||'Followed story',currentStatus:story.currentStatus||'',lastKnownUpdateId:story.lastKnownUpdateId||null,lastKnownUpdateAt:story.lastKnownUpdateAt||null};return writeFollows(storage,state)};
  const unfollowStory=(storage,id)=>{const state=readFollows(storage);if(!state)return false;delete state.stories[id];return writeFollows(storage,state)};
  const isFollowed=(storage,id)=>{const state=readFollows(storage);return Boolean(state&&state.stories[id])};
  const followedStories=storage=>{const state=readFollows(storage);return state?Object.values(state.stories):[]};
  // Explicit export primitive for a future opt-in account/email/push sync.
  // Nothing calls or transmits this automatically.
  const exportFollowsForSync=storage=>({schemaVersion:1,source:'rp-follows-v1',stories:followedStories(storage).map(story=>({timelineId:story.timelineId,followedAt:story.followedAt,lastKnownUpdateId:story.lastKnownUpdateId||null,lastKnownUpdateAt:story.lastKnownUpdateAt||null}))});
  const unseenCount=(storage,id,updateIds)=>{const read=readState(storage,id);return read?unseenIds(updateIds||[],read).length:0};
  const mergeFollowIndex=(stored,index)=>{const live=index&&index[stored.timelineId];return {...stored,...(live||{}),timelineId:stored.timelineId,url:(live&&live.url)||`/stories/${stored.timelineId}/`,active:Boolean(live)}};
  const sortFollowed=(items,index)=>items.map(item=>mergeFollowIndex(item,index)).sort((a,b)=>{if(a.active!==b.active)return a.active?-1:1;return String(b.last_updated||b.lastKnownUpdateAt||b.followedAt||'').localeCompare(String(a.last_updated||a.lastKnownUpdateAt||a.followedAt||''))});

  function followConfig(id,nodes){
    const el=root.document.getElementById('timeline-follow-data');
    try{const data=JSON.parse(el&&el.textContent||'{}');return {timelineId:id,title:data.title,currentStatus:data.currentStatus,lastKnownUpdateId:(nodes[0]&&nodes[0].dataset.updateId)||null,lastKnownUpdateAt:(nodes[0]&&nodes[0].dataset.published)||data.lastUpdated||null}}catch(e){return {timelineId:id,lastKnownUpdateId:(nodes[0]&&nodes[0].dataset.updateId)||null,lastKnownUpdateAt:(nodes[0]&&nodes[0].dataset.published)||null}}
  }

  function initFollowControl(id,nodes,storage){
    const button=root.document.querySelector('[data-follow-control]');if(!button)return;
    const story=followConfig(id,nodes),render=()=>{const active=isFollowed(storage,id);button.setAttribute('aria-pressed',String(active));button.textContent=active?'Following':'Follow this story';button.classList.toggle('is-following',active)};
    render();button.addEventListener('click',()=>{const active=isFollowed(storage,id),ok=active?unfollowStory(storage,id):followStory(storage,story);if(!ok)return;render();if(typeof root.gtag==='function')root.gtag('event',active?'story_unfollow':'story_follow',{timeline_id:id});button.dispatchEvent(new root.CustomEvent('rallypoint:followchange',{bubbles:true,detail:{timelineId:id,following:!active}}))});
  }

  async function homepageIndex(){
    if(!root||!root.document||!storageAvailable(root.localStorage))return {};
    try{const response=await root.fetch(`/data/timeline_state_index.json?t=${Date.now()}`,{cache:'no-store'});if(!response.ok)return{};return (await response.json()).timelines||{}}catch(e){return{}}
  }

  const api={PREFIX,FOLLOW_KEY,cleanIds,storageAvailable,readState,writeState,unseenIds,mergeSeen,emptyFollows,readFollows,writeFollows,followStory,unfollowStory,isFollowed,followedStories,exportFollowsForSync,unseenCount,mergeFollowIndex,sortFollowed,initFollowControl,initTimeline,homepageIndex};
  if(root&&root.document)root.document.addEventListener('DOMContentLoaded',initTimeline,{once:true});
  return api;
});
