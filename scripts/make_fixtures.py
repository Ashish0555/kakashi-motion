"""Original deterministic synthetic VIDEO fixtures, not real-prop evidence.
python scripts/make_fixtures.py --frames 600
Requires ffmpeg for browser-compatible H.264; no model outputs are prerecorded.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.geometry import transform

ROOT=Path(__file__).resolve().parents[1]
WIDTH,HEIGHT,FPS=640,480,30
BOXES=[[143,171,120,104],[321,175,147,94]]
PIVOT=np.array([293.,223.])


def texture(seed,color,label,box,marker=None):
    rng=np.random.default_rng(seed)
    img=np.zeros((HEIGHT,WIDTH,3),np.uint8)
    mask=np.zeros((HEIGHT,WIDTH),np.uint8)
    x,y,w,h=box
    cv2.rectangle(img,(x-7,y-7),(x+w+7,y+h+7),color,-1)
    cv2.rectangle(mask,(x-7,y-7),(x+w+7,y+h+7),255,-1)
    for _ in range(110):
        px=int(rng.integers(x+4,x+w-4));py=int(rng.integers(y+4,y+h-4))
        c=tuple(int(q) for q in rng.integers(40,235,3))
        if rng.random()<.5:cv2.circle(img,(px,py),int(rng.integers(2,7)),c,-1)
        else:cv2.line(img,(px,py),(min(x+w-2,px+int(rng.integers(3,15))),min(y+h-2,py+int(rng.integers(2,12)))),c,2)
    cv2.rectangle(img,(x+5,y+5),(x+w-5,y+h-5),(65,72,77),2)
    cv2.putText(img,label,(x+17,y+h-14),cv2.FONT_HERSHEY_DUPLEX,.6,(232,236,223),2,cv2.LINE_AA)
    if marker is not None:
        m=cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),marker,60)
        cv2.rectangle(img,(x+19,y+7),(x+88,y+76),(255,255,255),-1)
        img[y+12:y+72,x+24:x+84]=cv2.cvtColor(m,cv2.COLOR_GRAY2BGR)
    return img,mask


def scene_assets(seed=10,markers=False):
    return [texture(seed,(131,150,147),'A / 01',BOXES[0],0 if markers else None),
            texture(seed+17,(94,118,175),'B / 02',BOXES[1],1 if markers else None)]


def trajectory(index,kind):
    t=index/FPS
    active=max(0.,t-1.5)
    # 10–14 s: fixed internal joint with continued common translation/rotation.
    u=.5 if 10<=t<14 else .5-.5*np.cos(active*1.35)
    theta=np.deg2rad(48)*u
    internal=transform(theta, PIVOT - transform(theta)[:2,:2]@PIVOT) if kind!='slider' else transform(0,(u*78.,0.))
    phi=np.deg2rad(9)*np.sin(active*.66)
    r=transform(phi)[:2,:2]
    center=np.array([300.,240.])
    g=transform(phi,center-r@center+np.array([22*np.sin(active*.7),14*np.sin(active*.43)]))
    return g,g@internal,u


def render_frame(index,kind='hinge',assets=None):
    assets=assets or scene_assets(markers=kind=='marker')
    a,b,u=trajectory(index,kind)
    im=np.full((HEIGHT,WIDTH,3),(40,45,47),np.uint8)
    for x in range(0,WIDTH,40):cv2.line(im,(x,0),(x,HEIGHT),(43,49,50),1)
    for y in range(0,HEIGHT,40):cv2.line(im,(0,y),(WIDTH,y),(43,49,50),1)
    for (part,mask),matrix in zip(assets,[a,b]):
        moved=cv2.warpAffine(part,matrix[:2],(WIDTH,HEIGHT),flags=cv2.INTER_LINEAR)
        area=cv2.warpAffine(mask,matrix[:2],(WIDTH,HEIGHT),flags=cv2.INTER_NEAREST)
        im[area>0]=moved[area>0]
    visible=True
    if kind=='occlusion':
        if 330<=index<360:
            im=cv2.GaussianBlur(im,(13,13),5)
        if 390<=index<425:
            # A complete interruption. Nothing hidden is inferred.
            cv2.rectangle(im,(300,80),(620,430),(50,54,59),-1);visible=False
        elif 365<=index<385:
            cv2.rectangle(im,(390,200),(620,430),(50,54,59),-1);visible=False
    cv2.putText(im,'KAKASHI / SYNTHETIC VIDEO INPUT',(20,30),cv2.FONT_HERSHEY_SIMPLEX,.42,(153,166,160),1,cv2.LINE_AA)
    cv2.putText(im,f'{kind.upper()}  |  {index/FPS:05.1f}s',(20,454),cv2.FONT_HERSHEY_SIMPLEX,.4,(131,148,144),1,cv2.LINE_AA)
    return im,{'frame':index,'time':index/FPS,'a':a.tolist(),'b':b.tolist(),'u':float(u),'fully_visible':visible,'whole_prop_only':10<=index/FPS<14}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--frames',type=int,default=600);args=parser.parse_args()
    out=ROOT/'fixtures';out.mkdir(exist_ok=True)
    for kind in ['hinge','slider','occlusion','marker']:
        assets=scene_assets(markers=kind=='marker')
        process=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','bgr24','-video_size','640x480','-framerate','30','-i','-','-an','-c:v','libx264','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(out/f'{kind}.mp4')],stdin=subprocess.PIPE)
        truth=[]
        for i in range(args.frames):
            frame,metadata=render_frame(i,kind,assets)
            process.stdin.write(frame.tobytes());truth.append(metadata)
            if i==0:cv2.imwrite(str(out/f'{kind}-reference.png'),frame)
        process.stdin.close()
        if process.wait()!=0:raise RuntimeError('ffmpeg failed')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(out/f'{kind}.mp4'),'-c:v','libvpx-vp9','-crf','34','-b:v','0','-row-mt','1','-threads','2',str(out/f'{kind}.webm')],check=True)
        (out/f'{kind}.json').write_text(json.dumps({'source':'synthetic; never camera validation','seed':10,'fps':FPS,'boxes':BOXES,'frames':truth},separators=(',',':')))
        print(kind,len(truth),'frames',flush=True)
    dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for i in (0,1):
        marker=cv2.aruco.generateImageMarker(dictionary,i,500)
        page=cv2.copyMakeBorder(marker,60,100,60,60,cv2.BORDER_CONSTANT,value=255)
        cv2.putText(page,f'KAKASHI - PART {"AB"[i]} - ID {i}',(45,630),cv2.FONT_HERSHEY_SIMPLEX,.7,0,2)
        cv2.imwrite(str(ROOT/'assets'/f'marker-{i}.png'),page)


if __name__=='__main__':main()
