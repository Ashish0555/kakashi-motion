"""Loopback-only service. The browser is the sole camera owner."""
import asyncio
import json
import os
import platform
import struct
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .engine import Engine

ROOT=Path(__file__).resolve().parents[1]
app=FastAPI(title='Kakashi local studio',docs_url=None,redoc_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','[::1]','testserver'])


@app.get('/api/health')
def health():
    import cv2
    try:
        import onnxruntime as ort
        providers=ort.get_available_providers()
    except ImportError:
        providers=[]
    return {'status':'ok','version':'0.1.0','os':platform.system(),'architecture':platform.machine(),
            'opencv':cv2.__version__,'providers':providers,'camera_owner':'browser',
            'xfeat_available':(ROOT/'models/xfeat.onnx').exists(),'npu_verified':False}


@app.websocket('/ws')
async def studio(ws:WebSocket):
    origin=ws.headers.get('origin','')
    from urllib.parse import urlparse
    if origin and urlparse(origin).hostname not in ('127.0.0.1','localhost','::1'):
        await ws.close(code=1008);return
    await ws.accept()
    engine=Engine()
    await ws.send_json({'type':'ready','backend':'orb'})
    try:
        while True:
            packet=await ws.receive()
            if packet['type']=='websocket.disconnect':
                break
            request_id=None
            try:
                if packet.get('bytes') is not None:
                    data=packet['bytes']
                    if len(data)<8 or len(data)>2_010_000:
                        raise ValueError('Invalid camera packet.')
                    size=struct.unpack('<I',data[:4])[0]
                    if not 0<size<1024 or size+4>=len(data):
                        raise ValueError('Invalid camera metadata.')
                    header=json.loads(data[4:4+size])
                    result=await asyncio.to_thread(engine.frame,data[4+size:],int(header['frame_id']),float(header['capture_t']))
                else:
                    text=packet.get('text','')
                    if len(text)>4_000_000:
                        raise ValueError('Profile exceeds the message limit.')
                    cmd=json.loads(text);request_id=cmd.get('request_id')
                    if cmd.get('type') in ('backend','reset'):
                        new=await asyncio.to_thread(Engine,cmd.get('backend','orb'))
                        engine=new
                        result={'type':'reset','backend':engine.backend,'phase':'show'}
                    else:
                        result=await asyncio.to_thread(engine.command,cmd)
                if request_id is not None:
                    result['request_id']=request_id
                await ws.send_json(result)
            except (ValueError,KeyError,TypeError,RuntimeError) as err:
                await ws.send_json({'type':'error','message':str(err),'request_id':request_id})
    except WebSocketDisconnect:
        pass


app.mount('/fixtures',StaticFiles(directory=ROOT/'fixtures',check_dir=False),name='fixtures')
app.mount('/assets-original',StaticFiles(directory=ROOT/'assets',check_dir=False),name='assets-original')
if (ROOT/'dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='studio')
else:
    @app.get('/')
    def missing_build():
        return {'message':'Build the interface with npm ci && npm run build, or use npm run dev.'}
