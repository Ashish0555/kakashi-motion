from pathlib import Path
import cv2
import numpy as np
import pytest
from backend.perception import XFeatFeatures,preprocess,match_features
from scripts.make_fixtures import render_frame,BOXES
from backend.engine import Engine
from tests.test_tracking import jpeg


def test_xfeat_onnx_produces_distinctive_matches_on_cpu():
    if not Path('models/xfeat.onnx').exists():pytest.skip('Optional XFeat model not installed')
    f=XFeatFeatures()
    a=cv2.cvtColor(render_frame(0)[0],cv2.COLOR_BGR2GRAY)
    b=cv2.cvtColor(render_frame(75)[0],cv2.COLOR_BGR2GRAY)
    pa,da=f.extract(a);pb,db=f.extract(b)
    ia,ib=match_features(da,db,False)
    assert len(ia)>30
    assert f.info()['provider']==['CPUExecutionProvider']
    assert not f.info()['npu_verified']
    np.testing.assert_allclose(np.linalg.norm(da,axis=1),1.,atol=1e-5)


def test_xfeat_tracking_reacquires_reference_after_lost_frame():
    if not Path('models/xfeat.onnx').exists():pytest.skip('Optional XFeat model not installed')
    e=Engine('xfeat');im=render_frame(0)[0];e.frame(jpeg(im),0,0.)
    e.command({'type':'select','frame_id':0,'boxes':BOXES})
    for i in range(1,50):e.frame(jpeg(render_frame(i)[0]),i,i/30)
    assert e.frame(jpeg(np.full_like(im,25)),51,51/30)['tracking']=='lost'
    for i in range(52,59):r=e.frame(jpeg(render_frame(i)[0]),i,i/30)
    assert r['tracking']=='tracked'


def test_preprocessing_shape_normalization_and_flat_frame():
    a=preprocess(np.full((480,640),128,np.uint8));assert a.shape==(1,1,256,320)
    assert np.isfinite(a).all() and abs(a.mean())<1e-3


def test_qnn_request_never_silently_substitutes_cpu():
    import onnxruntime as ort
    if 'QNNExecutionProvider' in ort.get_available_providers():pytest.skip('This check needs a CPU-only environment')
    with pytest.raises(ValueError,match='No CPU fallback'):
        XFeatFeatures('qnn',Path('models/xfeat.qdq.onnx'))
