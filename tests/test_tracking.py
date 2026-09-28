import cv2
import numpy as np
import pytest
from backend.engine import Engine
from backend.geometry import angle
from scripts.make_fixtures import render_frame,scene_assets,BOXES


def jpeg(im):return cv2.imencode('.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,88])[1].tobytes()


@pytest.mark.parametrize('kind',['hinge','slider'])
def test_camera_pixels_to_learned_control(kind):
    # Regression fixture, not held-out physical-camera evaluation.
    engine=Engine();assets=scene_assets()
    first,_=render_frame(0,kind,assets)
    engine.frame(jpeg(first),0,0.)
    engine.command({'type':'select','frame_id':0,'boxes':BOXES})
    engine.command({'type':'learn'})
    results=[]
    for i in range(1,190,2):
        im,truth=render_frame(i,kind,assets)
        r=engine.frame(jpeg(im),i,i/30)
        results.append(r)
    assert sum(r['tracking']=='tracked' for r in results)/len(results)>.90
    proposal=engine.command({'type':'fit'})['proposal']
    assert proposal['kind']==kind
    assert proposal['residual_px']<4
    engine.command({'type':'confirm'})
    for i in range(191,218):
        im,_=render_frame(i,kind,assets);r=engine.frame(jpeg(im),i,i/30)
    assert r['control']['available']
    saved=engine.command({'type':'export'})['profile']
    second=Engine();second.command({'type':'load','profile':saved})
    assert second.control.calibration.to_dict()==engine.control.calibration.to_dict()


def test_occlusion_reacquisition_and_frame_order():
    engine=Engine();assets=scene_assets()
    im,_=render_frame(0,'hinge',assets);engine.frame(jpeg(im),0,0.)
    engine.command({'type':'select','frame_id':0,'boxes':BOXES})
    for i in range(1,35):
        im,_=render_frame(i,'hinge',assets);engine.frame(jpeg(im),i,i/30)
    r=engine.frame(jpeg(np.full_like(im,48)),36,36/30)
    assert r['tracking']=='lost' and not r['control']['available']
    for i in range(37,47):
        im,_=render_frame(i,'hinge',assets);r=engine.frame(jpeg(im),i,i/30)
    assert r['tracking']=='tracked'
    with pytest.raises(ValueError,match='Stale'):engine.frame(jpeg(im),45,45/30)
    with pytest.raises(ValueError,match='current'):engine.command({'type':'select','frame_id':0,'boxes':BOXES})


def test_bad_selection_does_not_replace_working_selection():
    e=Engine();im,_=render_frame(0);e.frame(jpeg(im),0,0.)
    e.command({'type':'select','frame_id':0,'boxes':BOXES})
    with pytest.raises(ValueError):e.command({'type':'select','frame_id':0,'boxes':[[1,1,5,5],[3,3,9,9]]})
    assert len(e.tracker.parts)==2


def test_dropped_frames_hold_then_require_consistent_recovery():
    from backend.control import Control
    from backend.geometry import Calibration
    e=Engine();im=render_frame(0)[0];encoded=jpeg(im)
    e.frame(encoded,0,0.)
    e.command({'type':'select','frame_id':0,'boxes':BOXES})
    e.control=Control(Calibration('hinge',0.,.8,[1.,0.],[293.,223.],1.,45.,0.,100))
    for i in range(1,15):r=e.frame(encoded,i,i/30)
    assert r['control']['available']
    previous=r['control']['value']
    r=e.frame(encoded,50,50/30)
    assert not r['control']['available'] and r['control']['value']==previous
    for i in range(51,53):assert not e.frame(encoded,i,i/30)['control']['available']
    assert e.frame(encoded,53,53/30)['control']['available']
