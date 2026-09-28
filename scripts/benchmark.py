"""Repeatable pixel-to-control development benchmark. Never a camera/NPU claim.
python scripts/benchmark.py --backends orb xfeat marker --stride 2
"""
import argparse
import json
import platform
import sys
import time
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.engine import Engine
from backend.geometry import relative,angle

ROOT=Path(__file__).resolve().parents[1]


def summarize(v):
    return {'p50':float(np.median(v)),'p95':float(np.quantile(v,.95)),'max':float(max(v))} if len(v) else None


def evaluate(backend,kind,stride,manual=False):
    filename='marker' if backend=='marker' else kind
    truth=json.loads((ROOT/f'fixtures/{filename}.json').read_text())
    video=cv2.VideoCapture(str(ROOT/f'fixtures/{filename}.mp4'))
    engine=Engine(backend);errors=[];timings=[];inference=[];states=[];leak=[];proposal=None;setup_start=time.perf_counter()
    for row in truth['frames']:
        success,image=video.read()
        if not success:break
        i=row['frame']
        if i%stride:continue
        encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,84])[1].tobytes()
        result=engine.frame(encoded,i,i/truth['fps'])
        timings.append(result['timing']['processing_ms'])
        if i==0:
            engine.command({'type':'select','frame_id':i,'boxes':truth['boxes']})
            engine.command({'type':'learn'})
            setup_ms=(time.perf_counter()-setup_start)*1000
        if i>=180 and proposal is None:
            try:
                command={'type':'fit'}
                if manual:command.update(force=kind,pivot=[293.,223.] if kind=='hinge' else None,axis_deg=0 if kind=='slider' else None)
                proposal=engine.command(command)['proposal'];engine.command({'type':'confirm'})
            except ValueError as e:
                if i>210:raise
        states.append({'frame':i,'tracked':result['tracking']=='tracked','available':result['control']['available'],'visible':row['fully_visible']})
        if engine.control.calibration and result['control']['available']:
            c=engine.control.calibration
            true_rel=relative(np.array(row['a']),np.array(row['b']))
            physical=angle(true_rel) if c.kind=='hinge' else np.dot(true_rel[:2,2],c.axis)
            expected=float(np.clip((physical-c.low)/(c.high-c.low),0,1))
            errors.append(abs(result['control']['raw']-expected))
            if 11<=row['time']<14:leak.append(result['control']['raw'])
    video.release()
    visible=[s for s in states if s['visible'] and s['frame']>0]
    performance=[s for s in states if s['frame']>=192]
    recovery=next((s['frame']-425 for s in states if s['frame']>=425 and s['available']),None) if kind=='occlusion' else None
    return {'backend':backend,'fixture':filename,'joint_configuration':'manual ground-truth pivot/axis' if manual else 'automatic hypothesis fitting','input':'synthetic video, development (not held-out real props)',
            'source_fps':truth['fps'],'processed_source_fps':truth['fps']/stride,'frames_processed':len(states),
            'selection':'two ground-truth fixture boxes; markers automatically detected for marker baseline',
            'automatic_selection_compute_ms':setup_ms,'human_setup_effort_seconds':None,
            'processing_ms':summarize(timings),'raw_control_absolute_error':summarize(errors),
            'raw_control_mae':float(np.mean(errors)) if errors else None,
            'fully_visible_tracking_loss_fraction':sum(not s['tracked'] for s in visible)/len(visible),
            'post_learning_unavailable_fraction':sum(not s['available'] for s in performance)/len(performance) if performance else None,
            'whole_prop_only_raw_std':float(np.std(leak)) if leak else None,
            'whole_prop_only_raw_peak_to_peak':float(np.ptp(leak)) if leak else None,
            'recovery_after_cover_removed_ms':recovery/truth['fps']*1000 if recovery is not None else None,
            'proposal':proposal,'actual_backend':engine.last_info,
            'camera_to_display_ms':None,'power_watts':None,'render_fps':None,'npu_verified':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--backends',nargs='+',default=['orb','xfeat','marker']);p.add_argument('--stride',type=int,default=2);p.add_argument('--output',default='reports/baseline.json');p.add_argument('--include-manual',action='store_true');args=p.parse_args()
    if args.stride<1:raise ValueError('stride must be positive')
    rows=[]
    for backend in args.backends:
        for kind in (['hinge'] if backend=='marker' else ['hinge','slider','occlusion']):
            try:
                result=evaluate(backend,kind,args.stride);rows.append(result)
                print(backend,kind,'loss',round(result['fully_visible_tracking_loss_fraction'],3),'p95',round(result['processing_ms']['p95'],2),'MAE',result['raw_control_mae'],flush=True)
            except Exception as err:
                rows.append({'backend':backend,'fixture':kind,'error':str(err)});print(backend,kind,'FAILED',str(err),flush=True)
    if args.include_manual:
        for kind in ['hinge','slider']:
            try:
                result=evaluate('orb',kind,args.stride,True);rows.append(result);print('manual',kind,'p95',round(result['processing_ms']['p95'],2),flush=True)
            except Exception as err:rows.append({'backend':'orb','fixture':kind,'joint_configuration':'manual','error':str(err)})
    output={'environment':{'platform':platform.platform(),'machine':platform.machine(),'python':platform.python_version(),'opencv':cv2.__version__},'scope':'synthetic development video fixtures, CPU; no physical camera or Snapdragon present','results':rows}
    destination=ROOT/args.output;destination.parent.mkdir(exist_ok=True);destination.write_text(json.dumps(output,indent=2))


if __name__=='__main__':main()
