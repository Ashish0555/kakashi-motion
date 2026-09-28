/** Tests successful getUserMedia with Chromium's FAKE camera backed by a fixture.
 * This validates the webcam software path, NOT physical-camera robustness.
 * KAKASHI_PYTHON=.venv/bin/python node scripts/camera_smoke.mjs
 */
import {chromium} from 'playwright';
import {spawn,spawnSync} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
const root=path.resolve(import.meta.dirname,'..');
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'kakashi-camera-'));
const video=path.join(temp,'fake-camera.y4m');
const converted=spawnSync('ffmpeg',['-y','-loglevel','error','-i',path.join(root,'fixtures/hinge.mp4'),'-t','10','-pix_fmt','yuv420p',video]);
assert.equal(converted.status,0,'ffmpeg fake-camera fixture generation');
const server=spawn(process.env.KAKASHI_PYTHON||'python',['run.py','--no-browser'],{cwd:root,stdio:'ignore'});
let browser;
try{
  for(let i=0;i<50;i++){try{if((await fetch('http://127.0.0.1:8765/api/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,200))}
  browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',`--use-file-for-fake-video-capture=${video}`]});
  const page=await browser.newPage({viewport:{width:1440,height:1000},permissions:['camera']});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765');await page.getByText('Local studio',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Connect camera',exact:true}).click();
  await page.getByText('LIVE CAMERA',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Select parts',exact:true}).click();
  const box=await page.locator('.camera-overlay').boundingBox();assert.ok(box);
  for(const [x,y,w,h] of [[143,171,120,104],[321,175,147,94]]){
    await page.mouse.move(box.x+x/640*box.width,box.y+y/480*box.height);await page.mouse.down();await page.mouse.move(box.x+(x+w)/640*box.width,box.y+(y+h)/480*box.height,{steps:5});await page.mouse.up();
  }
  await page.getByRole('button',{name:'Use these two parts'}).click();await page.getByRole('button',{name:'Start learning',exact:true}).click();
  await page.waitForTimeout(5500);await page.getByRole('button',{name:'Finish demonstration'}).click();await page.getByRole('button',{name:'Confirm hinge'}).click();
  await page.getByText('Connected to Ember',{exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('.control-meter strong')?.textContent!=='0%');
  assert.deepEqual(errors,[]);
  const report={passed:true,source:'Chromium fake getUserMedia camera fed an original synthetic video',verified:['successful getUserMedia','frame capture','selection coordinates','camera-to-control-to-animation software path'],real_camera_verified:false,npu_verified:false,browser_errors:errors};
  await fs.writeFile(path.join(root,'reports/camera-smoke.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}finally{await browser?.close();server.kill();await fs.rm(temp,{recursive:true,force:true});}
