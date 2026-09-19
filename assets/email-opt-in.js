/* Explicit email opt-in for one locally followed story. No local follows are uploaded. */
(function(root){
  'use strict';
  if(!root||!root.document)return;
  const panel=root.document.querySelector('[data-email-pilot]');
  if(!panel)return;
  const form=panel.querySelector('form'),input=form.querySelector('input[type="email"]'),status=panel.querySelector('[data-email-status]');
  const timelineId=()=>{const match=root.location.pathname.match(/^\/stories\/([a-f0-9]{12})\/?$/);return match&&match[1]};
  const following=()=>Boolean(root.RallyPointTimelineState&&root.RallyPointTimelineState.isFollowed(root.localStorage,timelineId()));
  const track=(name,params)=>{if(typeof root.gtag==='function')root.gtag('event',name,params||{})};
  const render=()=>{panel.hidden=!following()};
  fetch('/data/email_pilot_config.json',{credentials:'omit'}).then(r=>r.ok?r.json():null).then(config=>{
    if(!config||config.enabled!==true||!/^https:\/\//.test(config.api_base||''))return;
    panel.dataset.apiBase=config.api_base.replace(/\/$/,'');panel.dataset.ready='true';render();
  }).catch(()=>{});
  root.document.addEventListener('rallypoint:followchange',render);
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(panel.dataset.ready!=='true'||!following())return;
    const email=input.value.trim(),newest=root.document.querySelector('.timeline-update[data-update-id]');
    if(!input.checkValidity()){input.reportValidity();return}
    const button=form.querySelector('button');button.disabled=true;status.textContent='Sending confirmation…';
    track('email_opt_in_started',{timeline_id:timelineId()});
    try{
      const response=await fetch(panel.dataset.apiBase+'/v1/email/opt-in',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,timeline_id:timelineId(),baseline_material_update_id:newest&&newest.dataset.updateId,website:form.elements.website.value})});
      const body=await response.json();status.textContent=response.ok?(body.message||'Check your inbox to confirm.'):(body.error==='rate_limited'?'Please wait before trying again.':'Email alerts are temporarily unavailable.');
      if(response.ok){input.value='';form.hidden=true}
    }catch(_){status.textContent='Email alerts are temporarily unavailable. Your local follow is unchanged.'}
    finally{button.disabled=false}
  });
})(typeof window!=='undefined'?window:null);
