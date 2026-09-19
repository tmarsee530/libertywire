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

test('explicit follow persists and remains separate from visit state',()=>{
  const storage=new MemoryStorage();
  state.writeState(storage,'abc123def456',{seenUpdateIds:['old'],lastMeaningfulVisitAt:'then'});
  assert.equal(state.followStory(storage,{timelineId:'abc123def456',title:'Story',currentStatus:'Current',lastKnownUpdateId:'new'},'2026-09-19T00:00:00Z'),true);
  assert.equal(state.isFollowed(storage,'abc123def456'),true);
  assert.equal(state.followedStories(storage)[0].followedAt,'2026-09-19T00:00:00Z');
  assert.deepEqual(state.readState(storage,'abc123def456').seenUpdateIds,['old']);
});

test('unfollow persists without deleting ordinary read history',()=>{
  const storage=new MemoryStorage();
  state.writeState(storage,'abc123def456',{seenUpdateIds:['old']});
  state.followStory(storage,{timelineId:'abc123def456',title:'Story'});
  assert.equal(state.unfollowStory(storage,'abc123def456'),true);
  assert.equal(state.isFollowed(storage,'abc123def456'),false);
  assert.deepEqual(state.readState(storage,'abc123def456').seenUpdateIds,['old']);
});

test('multiple follows sort by live meaningful activity and retain inactive stories',()=>{
  const storage=new MemoryStorage();
  state.followStory(storage,{timelineId:'old111aaa222',title:'Archived',lastKnownUpdateAt:'2026-09-10T00:00:00Z'});
  state.followStory(storage,{timelineId:'new111aaa222',title:'New'});
  state.followStory(storage,{timelineId:'mid111aaa222',title:'Mid'});
  const sorted=state.sortFollowed(state.followedStories(storage),{
    new111aaa222:{title:'New live',last_updated:'2026-09-19T12:00:00Z',update_ids:['n']},
    mid111aaa222:{title:'Mid live',last_updated:'2026-09-18T12:00:00Z',update_ids:['m']}
  });
  assert.deepEqual(sorted.map(x=>x.timelineId),['new111aaa222','mid111aaa222','old111aaa222']);
  assert.equal(sorted[2].active,false);
  assert.equal(sorted[2].url,'/stories/old111aaa222/');
});

test('follow unseen counts use read state and blocked storage is safe',()=>{
  const storage=new MemoryStorage();
  state.writeState(storage,'abc123def456',{seenUpdateIds:['a']});
  assert.equal(state.followStory(storage,{timelineId:'abc123def456'}),true);
  assert.equal(state.unseenCount(storage,'abc123def456',['c','b','a']),2);
  const blocked=new MemoryStorage(true);
  assert.equal(state.readFollows(blocked),null);
  assert.equal(state.followStory(blocked,{timelineId:'abc123def456'}),false);
  assert.deepEqual(state.followedStories(blocked),[]);
});
