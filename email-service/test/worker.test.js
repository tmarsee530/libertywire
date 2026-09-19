import test from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeEmail, validEmail, validTimelineId, validCanonicalUrl,
  eventIdentity, deliveryIdentity, retryDelaySeconds, providerFailure,
  publicMetric, eligibleIngestEvent, renderAlertEmail, purposeToken,
  verifyPurposeToken
} from '../src/worker.js';

const event={eligible:true,timeline_id:'abc123def456',material_update_id:'update-1',title:'Court issues ruling',classification:'BREAKING',summary:'The court issued its ruling.',canonical_url:'https://rallypointnews.com/stories/abc123def456/',published_at:'2026-09-19T00:00:00Z',significance_reason:'breaking_material_development'};

test('email normalization is stable and minimal',()=>assert.equal(normalizeEmail(' Reader@Example.COM '),'reader@example.com'));
test('valid email accepted',()=>assert.equal(validEmail('reader@example.com'),true));
test('invalid email rejected',()=>assert.equal(validEmail('not-an-address'),false));
test('overlong email rejected',()=>assert.equal(validEmail('a'.repeat(250)+'@x.com'),false));
test('timeline IDs must be durable canonical IDs',()=>{assert.equal(validTimelineId('abc123def456'),true);assert.equal(validTimelineId('../bad'),false)});
test('canonical URL cannot be redirected off site',()=>{assert.equal(validCanonicalUrl(event.canonical_url,event.timeline_id),true);assert.equal(validCanonicalUrl('https://evil.test/',event.timeline_id),false)});
test('eligible foundation event is accepted',()=>assert.equal(eligibleIngestEvent(event),true));
test('CONTEXT is rejected by delivery ingest',()=>assert.equal(eligibleIngestEvent({...event,classification:'CONTEXT'}),false));
test('event identity is durable across wording changes',()=>assert.equal(eventIdentity(event.timeline_id,event.material_update_id),eventIdentity(event.timeline_id,event.material_update_id)));
test('delivery identity is follower specific',()=>assert.notEqual(deliveryIdentity('sub-a','event-1'),deliveryIdentity('sub-b','event-1')));
test('transient provider errors retry',()=>{assert.equal(providerFailure(429),'transient');assert.equal(providerFailure(503),'transient')});
test('permanent provider errors stop',()=>{assert.equal(providerFailure(400),'permanent');assert.equal(providerFailure(422),'permanent')});
test('retry backoff is bounded',()=>{assert.equal(retryDelaySeconds(1),30);assert.equal(retryDelaySeconds(20),21600)});
test('public analytics strips email and unknown identifiers',()=>assert.deepEqual(publicMetric('email_notification_sent',{timeline_id:'abc123def456',email:'private@example.com',subscriber_ref:'private'}),{event_name:'email_notification_sent',timeline_id:'abc123def456'}));
test('email derives only from the published event and has both unsubscribe scopes',()=>{
  const message=renderAlertEmail(event,{click:event.canonical_url,storyUnsubscribe:'https://alerts.test/u/story',allUnsubscribe:'https://alerts.test/u/all'});
  assert.match(message.html,/Court issues ruling/);assert.match(message.html,/Stop alerts for this story/);assert.match(message.html,/Stop all Rally Point alerts/);assert.doesNotMatch(message.html,/javascript:/);
});
test('email HTML escapes publisher material',()=>assert.match(renderAlertEmail({...event,title:'<script>alert(1)</script>'},{click:'#',storyUnsubscribe:'#',allUnsubscribe:'#'}).html,/&lt;script&gt;/));
test('single-purpose tokens cannot cross scopes',async()=>{
  const env={TOKEN_SECRET:'a sufficiently long test secret'};
  const token=await purposeToken(env,'unsubscribe-story','delivery-1');
  assert.equal(await verifyPurposeToken(env,'unsubscribe-story','delivery-1',token),true);
  assert.equal(await verifyPurposeToken(env,'unsubscribe-all','delivery-1',token),false);
});
