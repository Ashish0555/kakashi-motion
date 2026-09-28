/** Full creator workflow against a real local service + decoded synthetic video.
 * npm ci && npx playwright install chromium
 * KAKASHI_PYTHON=.venv/bin/python node scripts/ui_smoke.mjs
 * Camera and Snapdragon performance are NOT established by this test.
 */
import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=path.resolve(import.meta.dirname,'..');
const python=process.env.KAKASHI_PYTHON||'python';
const server=spawn(python,['run.py','--no-browser','--port','8765'],{cwd:root,stdio:['ignore','pipe','pipe']});
const logs=[];server.stderr.on('data',b=>logs.push(b.toString()));
let browser;
try{
  let ready=false;
  for(let i=0;i<50;i++){try{ready=(await fetch('http://127.0.0.1:8765/api/health')).ok;if(ready)break}catch{}await new Promise(r=>setTimeout(r,200))}
  assert.ok(ready,'Local service started');
  browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765');
  await page.getByText('Local studio',{exact:true}).waitFor();
  await page.screenshot({path:path.join(root,'reports/studio-empty.png'),fullPage:true});
  await page.getByRole('button',{name:'Try a recorded example'}).click();
  await page.getByText('RECORDED INPUT',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Select parts',exact:true}).click();
  const overlay=page.locator('.camera-overlay');
  const rect=await overlay.boundingBox();assert.ok(rect);
  for(const [x,y,w,h] of [[143,171,120,104],[321,175,147,94]]){
    await page.mouse.move(rect.x+x/640*rect.width,rect.y+y/480*rect.height);await page.mouse.down();
    await page.mouse.move(rect.x+(x+w)/640*rect.width,rect.y+(y+h)/480*rect.height,{steps:8});await page.mouse.up();
  }
  await page.getByRole('button',{name:'Use these two parts'}).click();
  await page.getByRole('button',{name:'Start learning',exact:true}).click();
  await page.waitForTimeout(5500);
  await page.getByRole('button',{name:'Finish demonstration'}).click();
  await page.getByRole('button',{name:'Confirm hinge'}).click();
  await page.getByText('Connected to Ember',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Record',exact:true}).click();
  await page.waitForTimeout(1200);
  await page.getByRole('button',{name:'Stop',exact:true}).click();
  await page.getByRole('button',{name:'Bind Opening flower'}).click();
  await page.getByText('Connected to Bloom',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Bind Mechanical claw'}).click();
  await page.getByText('Connected to Grasp',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Bind Dragon wings'}).click();
  await page.getByLabel('Invert movement').check();
  await page.getByLabel('Invert movement').uncheck();
  await page.getByRole('button',{name:'Bring your own drawing'}).click();
  const drawing=page.locator('.draw-surface canvas'),dr=await drawing.boundingBox();assert.ok(dr);
  for(const part of [0,1]){
    if(part)await page.getByRole('button',{name:'Part B · moving'}).click();
    await page.mouse.move(dr.x+dr.width*(part?.5:.25),dr.y+dr.height*.5);await page.mouse.down();
    await page.mouse.move(dr.x+dr.width*(part?.75:.48),dr.y+dr.height*(part?.23:.5),{steps:15});await page.mouse.up();
  }
  await page.getByRole('button',{name:'Save & bind drawing'}).click();
  await page.getByText('Connected to Your creation',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Bind Dragon wings'}).click();
  const savedPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Save session',exact:true}).click();
  const saved=await savedPromise;const savedPath=path.join(root,'reports/test-session.json');await saved.saveAs(savedPath);
  const session=JSON.parse(await fs.readFile(savedPath,'utf8'));
  assert.equal(session.profile.calibration.kind,'hinge');assert.ok(session.samples.length>10);assert.equal(session.drawing.parts.length,2);
  await page.getByRole('button',{name:'Replay',exact:true}).click();
  await page.getByText('RECORDED CONTROL REPLAY',{exact:true}).waitFor();
  await page.waitForTimeout(1500);
  await page.getByRole('button',{name:'Resume input',exact:true}).click();
  await page.getByRole('button',{name:/Diagnostics/}).click();
  await page.waitForTimeout(400);
  const telemetryPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export diagnostics'}).click();
  const telemetry=await telemetryPromise;await telemetry.saveAs(path.join(root,'reports/browser-diagnostics.json'));
  await page.screenshot({path:path.join(root,'reports/studio-performing.png'),fullPage:true});
  await page.locator('input[type=file][accept=".json,application/json"]').setInputFiles(savedPath);
  await page.getByText(/Controller loaded/).waitFor();
  assert.ok(await page.getByRole('button',{name:'Save session',exact:true}).isEnabled());
  // Responsive overflow and error recovery.
  const mobile=await browser.newPage({viewport:{width:390,height:844}});await mobile.goto('http://127.0.0.1:8765');
  assert.equal(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await mobile.getByRole('button',{name:'Connect camera',exact:true}).click();
  await mobile.getByRole('alert').waitFor();
  await mobile.screenshot({path:path.join(root,'reports/studio-mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  const report={passed:true,source:'decoded synthetic video through browser canvas, JPEG, WebSocket, OpenCV, geometry and original SVG rigs',
    verified:['box selection','controller learning and confirmation','three rig bindings','mapping','recording','replay','drawing','save/load','diagnostics','camera error state','responsive layout'],
    samples:session.samples.length,proposal:session.profile.calibration,browser_errors:errors,real_camera_verified:false,npu_verified:false};
  await fs.writeFile(path.join(root,'reports/ui-smoke.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}catch(e){console.error(e);console.error(logs.join('').slice(-6000));process.exitCode=1;}
finally{await browser?.close();server.kill();}
