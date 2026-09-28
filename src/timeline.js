/** Replay uses captured control samples, never reruns vision or a smoothing filter. */
export function replayAt(samples, time){
  if(!samples.length)return {t:0,value:0,raw:0,available:false};
  if(time<=samples[0].t)return samples[0];
  let low=0,high=samples.length-1;
  while(low<high){const mid=Math.ceil((low+high)/2);if(samples[mid].t<=time)low=mid;else high=mid-1;}
  const a=samples[low],b=samples[Math.min(low+1,samples.length-1)];
  if(!a.available||!b.available||a.t===b.t)return a;
  const u=Math.min(1,Math.max(0,(time-a.t)/(b.t-a.t)));
  return {...a,t:time,value:a.value+(b.value-a.value)*u,raw:a.raw+(b.raw-a.raw)*u};
}
export function validRecording(value){
  return Array.isArray(value)&&value.length<=18000&&value.every((x,i)=>Number.isFinite(x.t)&&x.t>=0&&Number.isFinite(x.value)&&x.value>=0&&x.value<=1&&Number.isFinite(x.raw)&&typeof x.available==='boolean'&&(i===0||x.t>=value[i-1].t));
}
export function displayPoint(clientX,clientY,rect,width,height){
  return [Math.max(0,Math.min(width,(clientX-rect.left)/rect.width*width)),Math.max(0,Math.min(height,(clientY-rect.top)/rect.height*height))];
}
