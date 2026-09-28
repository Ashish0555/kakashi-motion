import test from 'node:test';
import assert from 'node:assert/strict';
import {replayAt,validRecording,displayPoint} from '../src/timeline.js';
test('replay preserves samples and holds gaps instead of hallucinating hidden motion',()=>{
  const samples=[{t:0,value:0,raw:0,available:true},{t:1,value:1,raw:1,available:true},{t:2,value:1,raw:1,available:false},{t:3,value:.2,raw:.2,available:true}];
  assert.equal(replayAt(samples,.5).value,.5);assert.equal(replayAt(samples,1).value,1);
  assert.equal(replayAt(samples,2.5).value,1);assert.equal(replayAt(samples,3).value,.2);
  assert.deepEqual(JSON.parse(JSON.stringify(samples)),samples);
});
test('invalid or nonmonotonic recording is rejected',()=>{
  assert.equal(validRecording([{t:2,value:0,raw:0,available:true},{t:1,value:0,raw:0,available:true}]),false);
  assert.equal(validRecording([{t:0,value:NaN,raw:0,available:true}]),false);
});
test('display selection consistently scales to original unmirrored image coordinates',()=>{
  assert.deepEqual(displayPoint(150,100,{left:50,top:25,width:320,height:240},640,480),[200,150]);
  assert.deepEqual(displayPoint(-1,600,{left:0,top:0,width:320,height:240},640,480),[0,480]);
});
