const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const code=fs.readFileSync(require('node:path').join(__dirname,'../assets/timeline-growth.js'),'utf8');
function setup(path='/stories/123456abcdef/',options={}){
  const events=[],listeners={},timers=[];let observer;
  const document={visibilityState:'visible',querySelector:s=>s==='.event-guide'?{}:s==='.end-card'?{}:null,
    addEventListener:(name,fn)=>listeners[name]=fn};
  const window={gtag:(...args)=>events.push(args),IntersectionObserver:function(fn){observer=fn;this.observe=()=>{};this.disconnect=()=>{};}};
  const context={document,window,location:{pathname:path,origin:'https://rallypointnews.com'},navigator:options.navigator||{},
    setInterval:fn=>(timers.push(fn),timers.length),clearInterval:()=>{},IntersectionObserver:window.IntersectionObserver,URL};
  vm.runInNewContext(code,context);
  return {events,listeners,timers,document,observer};
}
test('only real canonical timeline paths create experiment events',()=>{
  assert.equal(setup('/stories/').events.length,0);
  const h=setup();assert.equal(h.events[0][1],'timeline_open');
  assert.equal(h.events[0][2].timeline_id,'123456abcdef');
});
test('engagement requires visible reading time and fires once',()=>{
  const h=setup();h.document.visibilityState='hidden';for(let i=0;i<30;i++)h.timers[0]();
  assert.equal(h.events.length,1);h.document.visibilityState='visible';for(let i=0;i<21;i++)h.timers[0]();
  assert.equal(h.events.filter(e=>e[1]==='timeline_engaged').length,1);
});
test('a successful copy uses a tagged canonical URL without incoming private parameters',async()=>{
  let copied;const h=setup(undefined,{navigator:{clipboard:{writeText:url=>(copied=url,Promise.resolve())}}});
  const share={dataset:{shareTitle:'Event'},textContent:''};
  h.listeners.click({preventDefault(){},target:{closest:sel=>sel==='[data-share-timeline]'?share:null}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(copied,/utm_source=reader/);assert.match(copied,/utm_campaign=flagship_timeline/);
  assert.equal(h.events.at(-1)[1],'timeline_share');
});
test('cancelled native shares never count as successful distribution',async()=>{
  const h=setup(undefined,{navigator:{share:()=>Promise.reject(Error('cancelled'))}});
  h.listeners.click({preventDefault(){},target:{closest:()=>({dataset:{shareTitle:'Event'}})}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(h.events.filter(e=>e[1]==='timeline_share').length,0);
});
test('source instrumentation records the host without source query strings',()=>{
  const h=setup();h.listeners.click({target:{closest:sel=>sel==='[data-share-timeline]'?null:{href:'https://source.test/story?private=value'}}});
  const event=h.events.at(-1);assert.equal(event[1],'timeline_source_open');
  assert.equal(event[2].source_host,'source.test');assert.equal(JSON.stringify(event).includes('private'),false);
});
