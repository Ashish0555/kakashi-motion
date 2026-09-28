"""Prepare a QDQ candidate, not proof of NPU compatibility or execution.
python scripts/quantize_qnn.py --videos fixtures/hinge.mp4 fixtures/slider.mp4
Use representative development CAMERA footage before target qualification.
Never use the held-out evaluation props for quantization calibration.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader,QuantType,quantize
from onnxruntime.quantization.execution_providers.qnn import get_qnn_qdq_config,qnn_preprocess_model
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.perception import preprocess


class Reader(CalibrationDataReader):
    def __init__(self,arrays):self.arrays=arrays;self.iterator=iter(arrays)
    def get_next(self):
        a=next(self.iterator,None)
        return None if a is None else {'image':a}
    def rewind(self):self.iterator=iter(self.arrays)


def main():
    p=argparse.ArgumentParser();p.add_argument('--videos',nargs='+',required=True);p.add_argument('--model',default='models/xfeat.onnx');p.add_argument('--output',default='models/xfeat.qdq.onnx');args=p.parse_args()
    arrays=[]
    for file in args.videos:
        cap=cv2.VideoCapture(file);i=0
        while True:
            ok,frame=cap.read()
            if not ok:break
            if i%30==0:arrays.append(preprocess(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)))
            i+=1
        cap.release()
    if len(arrays)<10:raise ValueError('Provide at least 10 representative calibration frames.')
    pre=str(Path(args.output).with_suffix('.preprocessed.onnx'))
    changed=qnn_preprocess_model(args.model,pre)
    model=pre if changed else args.model
    config=get_qnn_qdq_config(model,Reader(arrays),activation_type=QuantType.QUInt16,weight_type=QuantType.QUInt8)
    quantize(model,args.output,config)
    cpu=ort.InferenceSession(args.model,providers=['CPUExecutionProvider']);qdq=ort.InferenceSession(args.output,providers=['CPUExecutionProvider'])
    errors=[]
    for a in arrays[::max(1,len(arrays)//10)]:
        f=cpu.run(None,{'image':a});q=qdq.run(None,{'image':a})
        errors.append([float(np.mean(np.abs(x-y))) for x,y in zip(f,q)])
    manifest={'calibration_videos':args.videos,'calibration_frames':len(arrays),'activation':'QUInt16','weights':'QUInt8',
              'model_sha256':hashlib.sha256(Path(args.output).read_bytes()).hexdigest(),
              'cpu_output_mean_absolute_errors':np.mean(errors,axis=0).tolist(),
              'scope':'CPU QDQ numerical check only; NPU compilation/execution and control quality unverified',
              'npu_verified':False}
    Path(args.output+'.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
