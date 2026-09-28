"""Optional loopback tensor bridge for native ARM64 QNN + x64 OpenCV.

This is only needed on Windows ARM PCs without native OpenCV Python wheels.
No images, tensors, or inference are sent to the cloud.
"""
import json
import urllib.request
from urllib.parse import urlparse
from types import SimpleNamespace
import numpy as np

SHAPES=[(1,64,32,40),(1,65,32,40),(1,1,32,40)]


class RemoteSession:
    def __init__(self,url,expected_sha256):
        if urlparse(url).hostname not in ('127.0.0.1','localhost','::1') or urlparse(url).scheme!='http':
            raise ValueError('The inference worker must be on loopback HTTP.')
        self.url=url.rstrip('/')
        try:
            self.metadata=json.load(urllib.request.urlopen(self.url+'/health',timeout=3))
        except Exception as e:
            raise ValueError('Native inference worker is not running. Follow docs/snapdragon.md.') from e
        if self.metadata['model_sha256']!=expected_sha256:
            raise ValueError('Worker model differs from local model. Use the same model on both processes.')
        if self.metadata['requested_provider']!='qnn':
            raise ValueError('QNN mode requires a QNN worker; a CPU worker cannot be labelled NPU.')
        self.last_inference_ms=0.

    def get_inputs(self):return [SimpleNamespace(name='image')]
    def get_providers(self):return self.metadata['providers']

    def run(self,outputs,inputs):
        data=np.asarray(inputs['image'],dtype='<f4').tobytes()
        request=urllib.request.Request(self.url+'/infer',data=data,headers={'Content-Type':'application/octet-stream'},method='POST')
        try:
            with urllib.request.urlopen(request,timeout=3) as r:
                payload=r.read(665601);self.last_inference_ms=float(r.headers['X-Inference-Ms'])
        except Exception as e:
            raise ValueError('Native inference worker stopped or rejected a tensor. Control is held; check the worker.') from e
        if len(payload)!=665600:raise ValueError('Invalid inference worker tensor response.')
        flat=np.frombuffer(payload,dtype='<f4');out=[];offset=0
        for shape in SHAPES:
            n=int(np.prod(shape));out.append(flat[offset:offset+n].reshape(shape).copy());offset+=n
        return out
