const test=require('node:test');
const assert=require('node:assert/strict');
const state=require('../assets/timeline-state.js');

class MemoryStorage{
  constructor(blocked=false){this.blocked=blocked;this.data=new Map()}
  setItem(k,v){if(this.blocked)throw new Error('blocked');this.data.set(k,String(v))}
  getItem(k){if(this.blocked)throw new Error('blocked');return this.data.has(k)?this.data.get(k):null}
  removeItem(k){if(this.blocked)throw new Error('blocked');this.data.delete(k)}
}

test('first visit has no manufactured unseen updates',()=>{
  assert.deepEqual(state.unseenIds(['a','b'],null),[]);
});

test('return visit counts one or several durable unseen ids',()=>{
  const prior={version:1,seenUpdateIds:['a']};
  assert.deepEqual(state.unseenIds(['b','a'],prior),['b']);
  assert.deepEqual(state.unseenIds(['c','b','a'],prior),['c','b']);
});

test('reclassification and corroboration do not manufacture new state',()=>{
  const prior={version:1,seenUpdateIds:['stable-id']};
  assert.deepEqual(state.unseenIds(['stable-id'],prior),[]);
});

test('state merges without consuming unseen ids prematurely',()=>{
  const prior={version:1,seenUpdateIds:['old']};
  const next=state.mergeSeen(prior,['new-1'],'2026-09-18T12:00:00Z');
  assert.deepEqual(next.seenUpdateIds,['old','new-1']);
  assert.deepEqual(state.unseenIds(['new-2','new-1','old'],next),['new-2']);
});

test('cleared or unavailable storage degrades safely',()=>{
  const clear=new MemoryStorage();
  assert.equal(state.readState(clear,'story'),null);
  assert.equal(state.storageAvailable(new MemoryStorage(true)),false);
  assert.equal(state.writeState(new MemoryStorage(true),'story',{}),false);
});

test('browser refresh preserves stored visit state',()=>{
  const storage=new MemoryStorage();
  assert.equal(state.writeState(storage,'story',{seenUpdateIds:['a'],lastMeaningfulVisitAt:'then'}),true);
  assert.deepEqual(state.readState(storage,'story').seenUpdateIds,['a']);
});
