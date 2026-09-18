/* Rally Point return-state: local, durable, and safe when storage is blocked. */
(function(root,factory){
  const api=factory(root);
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.RallyPointTimelineState=api;
})(typeof window!=='undefined'?window:null,function(root){
  'use strict';
  const PREFIX='rp-timeline-v1:';
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
    const storage=root.localStorage; if(!storageAvailable(storage))return;
    let prior=readState(storage,id); const returning=Boolean(prior&&prior.lastMeaningfulVisitAt);
    let unseen=unseenIds(current,prior), meaningful=false, interacted=false, visibleSeconds=0;
    if(returning){
      trackOnce('timeline_return_visit',id,{timeline_id:id,new_update_count:unseen.length});
      trackOnce('timeline_repeat_session',id,{timeline_id:id});
    }
    const unseenSet=new Set(unseen); nodes.forEach(node=>{if(unseenSet.has(node.dataset.updateId))node.classList.add('is-new')});
    if(unseen.length){
      trackOnce('new_updates_available',id,{timeline_id:id,new_update_count:unseen.length});
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

  async function homepageIndex(){
    if(!root||!root.document||!storageAvailable(root.localStorage))return {};
    try{const response=await root.fetch(`/data/timeline_state_index.json?t=${Date.now()}`,{cache:'no-store'});if(!response.ok)return{};return (await response.json()).timelines||{}}catch(e){return{}}
  }

  const api={PREFIX,cleanIds,storageAvailable,readState,writeState,unseenIds,mergeSeen,initTimeline,homepageIndex};
  if(root&&root.document)root.document.addEventListener('DOMContentLoaded',initTimeline,{once:true});
  return api;
});
