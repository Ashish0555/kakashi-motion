"""Export a pinned official XFeat backbone; PyTorch is build-time only.

Run: pip install torch==2.7.1 onnx==1.18.0
     python scripts/export_xfeat.py
Upstream code + weights: Apache-2.0. All neural weights are unchanged.
Instance normalization is moved to CPU preprocessing for a simpler static graph.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import urllib.request
import numpy as np
import torch
import onnx
import onnxruntime as ort

ROOT=Path(__file__).resolve().parents[1]
# Filled with the inspected immutable revision; do not use a moving branch.
REVISION='e92685f57f8318b18725c5c8c0bd28c7fe188d9a'


def main():
    cache=ROOT/'models/source'
    cache.mkdir(parents=True,exist_ok=True)
    base=f'https://raw.githubusercontent.com/verlab/accelerated_features/{REVISION}'
    for name,url in [('model.py','modules/model.py'),('xfeat.pt','weights/xfeat.pt'),('LICENSE','LICENSE')]:
        destination=cache/name
        if not destination.exists():
            urllib.request.urlretrieve(f'{base}/{url}',destination)
    spec=importlib.util.spec_from_file_location('xfeat_architecture',cache/'model.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    torch.set_num_threads(2)
    model=module.XFeatModel().eval()
    model.load_state_dict(torch.load(cache/'xfeat.pt',map_location='cpu',weights_only=True))
    model.norm=torch.nn.Identity()
    sample=torch.from_numpy(np.random.default_rng(24).standard_normal((1,1,256,320)).astype(np.float32))
    out=ROOT/'models/xfeat.onnx'
    with torch.no_grad():
        torch.onnx.export(model,sample,str(out),input_names=['image'],output_names=['features','keypoints','reliability'],opset_version=17,dynamo=False)
        expected=model(sample)
    graph=onnx.load(str(out));onnx.checker.check_model(graph)
    session=ort.InferenceSession(str(out),providers=['CPUExecutionProvider'])
    actual=session.run(None,{'image':sample.numpy()})
    errors=[float(np.max(np.abs(a-e.numpy()))) for a,e in zip(actual,expected)]
    if max(errors)>.001:
        raise RuntimeError(f'Export parity failed: {errors}')
    manifest={'name':'XFeat','upstream':'https://github.com/verlab/accelerated_features','revision':REVISION,
              'license':'Apache-2.0','weights_sha256':hashlib.sha256((cache/'xfeat.pt').read_bytes()).hexdigest(),
              'onnx_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'opset':17,'input':[1,1,256,320],
              'preprocessing':'gray resize 320x256, /255, (x-mean)/sqrt(var+1e-5); NumPy biased variance',
              'quantization':'none; float32','operators':sorted(set(n.op_type for n in graph.graph.node)),
              'export_max_absolute_errors':errors,'target_npu_verified':False,
              'notes':'Sparse extraction only; fine matcher and LighterGlue not used. CPU postprocessing and matching.'}
    (ROOT/'models/manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
