"""Optional native ARM64 inference process; no OpenCV/SciPy/torch needed.
python scripts/inference_worker.py --model models/xfeat.qdq.onnx --provider qnn
Linux protocol check: --model models/xfeat.onnx --provider cpu
"""
import argparse
import hashlib
import json
import platform
import time
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import numpy as np
import onnxruntime as ort


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--provider',choices=['cpu','qnn'],default='qnn');p.add_argument('--port',type=int,default=8766);p.add_argument('--profile-dir',default='reports/qnn-profile');args=p.parse_args()
    path=Path(args.model);profile=Path(args.profile_dir);profile.mkdir(parents=True,exist_ok=True)
    opts=ort.SessionOptions();opts.enable_profiling=True;opts.profile_file_prefix=str(profile/'ort');opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
    if args.provider=='qnn':
        if 'QNNExecutionProvider' not in ort.get_available_providers():raise RuntimeError('QNN is not available. No CPU fallback is allowed.')
        opts.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        providers=[('QNNExecutionProvider',{'backend_path':'QnnHtp.dll','profiling_level':'detailed','profiling_file_path':str(profile/'qnn.csv')})]
    else:providers=['CPUExecutionProvider']
    session=ort.InferenceSession(str(path),sess_options=opts,providers=providers)
    # Fail before advertising readiness if the graph cannot execute.
    outputs=session.run(None,{session.get_inputs()[0].name:np.zeros((1,1,256,320),np.float32)})
    if [tuple(v.shape) for v in outputs]!=[(1,64,32,40),(1,65,32,40),(1,1,32,40)]:raise ValueError('Unexpected XFeat outputs')
    metadata={'requested_provider':args.provider,'providers':session.get_providers(),'platform':platform.platform(),'architecture':platform.machine(),
              'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'runtime':ort.__version__,'npu_verified':False,
              'placement':'Strict QNN requested; review saved execution profile before claiming NPU' if args.provider=='qnn' else 'CPU only'}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path!='/health':self.send_error(404);return
            data=json.dumps(metadata).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_POST(self):
            if self.headers.get('Origin') or self.path!='/infer':self.send_error(403);return
            if self.headers.get('Content-Length')!=str(1*1*256*320*4):self.send_error(400);return
            array=np.frombuffer(self.rfile.read(327680),dtype='<f4').reshape(1,1,256,320)
            if not np.isfinite(array).all():self.send_error(400);return
            try:
                t=time.perf_counter();values=session.run(None,{session.get_inputs()[0].name:array});ms=(time.perf_counter()-t)*1000
                data=b''.join(np.asarray(v,dtype='<f4').tobytes() for v in values)
                self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(len(data)));self.send_header('X-Inference-Ms',str(ms));self.end_headers();self.wfile.write(data)
            except Exception as e:self.send_error(500,str(e))
        def log_message(self,*a):pass
    server=HTTPServer(('127.0.0.1',args.port),Handler)
    print(json.dumps(metadata,indent=2),flush=True)
    print(f'Loopback tensor worker on 127.0.0.1:{args.port}; Ctrl+C saves placement evidence.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        server.server_close();profile_path=session.end_profiling()
        metadata['ort_profile']=profile_path;(profile/'environment.json').write_text(json.dumps(metadata,indent=2))
        print('Profile:',profile_path,flush=True)


if __name__=='__main__':main()
