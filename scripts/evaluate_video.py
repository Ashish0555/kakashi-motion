"""Evaluate a real or synthetic recorded input against a saved controller.
python scripts/evaluate_video.py --video prop.mp4 --session prop-session.json --output reports/prop.json
Optional CSV ground truth columns: time_s,control (normalized using this profile).
Preserve the original reference frame/prop face and camera geometry when recording.
"""
import argparse
import csv
import json
import platform
import sys
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.engine import Engine


def main():
    p=argparse.ArgumentParser();p.add_argument('--video',required=True);p.add_argument('--session',required=True);p.add_argument('--output',required=True);p.add_argument('--truth');p.add_argument('--stride',type=int,default=1);p.add_argument('--notes',help='JSON evaluation metadata from docs/held-out-protocol.md');args=p.parse_args()
    session=json.loads(Path(args.session).read_text());engine=Engine();engine.command({'type':'load','profile':session['profile']})
    cap=cv2.VideoCapture(args.video);fps=cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps<=0:raise ValueError('Cannot decode this video or determine frame rate.')
    rows=[];i=0
    while True:
        ok,im=cap.read()
        if not ok:break
        if i%args.stride:i+=1;continue
        # Match canonical dimensions used during profile creation.
        im=cv2.resize(im,(session['profile']['width'],session['profile']['height']))
        jpeg=cv2.imencode('.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,84])[1].tobytes()
        r=engine.frame(jpeg,i,i/fps)
        rows.append({'frame':i,'time_s':i/fps,'available':r['control']['available'],'raw':r['control']['raw'],'control':r['control']['value'],'processing_ms':r['timing']['processing_ms'],'status':r['control']['status'],'reason':r['reason']})
        i+=1
    cap.release()
    if not rows:raise ValueError('Video contained no usable frames.')
    timings=np.array([r['processing_ms'] for r in rows]);errors=[]
    if args.truth:
        truth=list(csv.DictReader(open(args.truth,newline='')))
        times=np.array([float(r['time_s']) for r in truth]);values=np.array([float(r['control']) for r in truth])
        for r in rows:
            if r['available'] and times.min()<=r['time_s']<=times.max():errors.append(abs(r['raw']-float(np.interp(r['time_s'],times,values))))
    result={'video':args.video,'session':args.session,'environment':platform.platform(),'backend':engine.last_info,
            'notes':json.loads(Path(args.notes).read_text()) if args.notes else None,'input_fps':fps,'processed_source_fps':fps/args.stride,
            'frames':len(rows),'unavailable_fraction':sum(not r['available'] for r in rows)/len(rows),
            'processing_p50_ms':float(np.median(timings)),'processing_p95_ms':float(np.quantile(timings,.95)),
            'raw_control_mae':float(np.mean(errors)) if errors else None,
            'physical_latency_ms':None,'whole_system_power_watts':None,'npu_verified':False,
            'caution':'Offline video processing is not a live camera-to-display latency measurement.'}
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2))
    with out.with_suffix('.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
