import numpy as np
import pytest
from backend.control import Control,Mapping
from backend.geometry import Calibration,transform


def controller():
    return Control(Calibration('slider',0.,100.,[1.,0.],None,0.,0.,100.,50),Mapping(smoothing_ms=0,dead_zone=0))


def test_holds_on_loss_and_blends_after_three_consistent_frames():
    c=controller()
    for i in range(30):s=c.update(transform(0,(30,0)),i/30,True)
    assert s['value']==pytest.approx(.3)
    for i in range(30,50):
        s=c.update(transform(0,(99,0)),i/30,False)
        assert not s['available'] and s['value']==pytest.approx(.3)
    for i in range(50,52):assert not c.update(transform(0,(90,0)),i/30,True)['available']
    s=c.update(transform(0,(90,0)),52/30,True)
    assert s['status']=='blending' and s['value']==pytest.approx(.3)
    for i in range(53,62):s=c.update(transform(0,(90,0)),i/30,True)
    assert s['value']==pytest.approx(.9)


def test_mapping_invert_gain_clamp_and_smoothing():
    c=controller();c.mapping=Mapping(invert=True,sensitivity=2.,dead_zone=.01,smoothing_ms=50)
    for i in range(90):s=c.update(transform(0,(75,0)),i/30,True)
    assert s['value']<1e-6
    assert s['raw']==pytest.approx(.75)
    assert Mapping.from_dict(c.mapping.to_dict())==c.mapping


def test_angle_wrap_during_live_control():
    c=Control(Calibration('hinge',2.9,3.9,[1.,0.],[1,1],0,57,0,100),Mapping(smoothing_ms=0,dead_zone=0))
    vals=[]
    for i,a in enumerate(np.linspace(2.9,3.9,100)):
        vals.append(c.update(transform(a),i/30,True)['value'])
    # Exclude the documented initial recovery blend; inspect the actual ±pi crossing.
    assert max(np.diff(vals[10:]))<.011
    assert vals[-1]==pytest.approx(1)
