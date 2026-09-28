import numpy as np
import pytest
from backend.geometry import transform,relative,fit_mechanism,Calibration,EvidenceError


def hinge(theta,pivot=(270.,230.)):
    r=transform(theta)
    r[:2,2]=np.array(pivot)-r[:2,:2]@pivot
    return r


def test_common_translation_rotation_cancel():
    for a in np.linspace(-2,2,70):
        g=transform(a,(51*np.cos(a),37*np.sin(a)))
        rel=hinge(.6)
        np.testing.assert_allclose(relative(g,g@rel),rel,atol=1e-12)


def test_noisy_hinge_fit_with_common_motion():
    rng=np.random.default_rng(103);samples=[]
    for a in np.linspace(0,.9,100):
        g=transform(a*.8,(30*a,19*np.sin(a)))
        b=g@hinge(a)
        b[:2,2]+=rng.normal(0,.35,2)
        samples.append(relative(g,b))
    c=fit_mechanism(samples)
    assert c.kind=='hinge' and c.residual_px<1.5
    np.testing.assert_allclose(c.pivot,[270,230],atol=1.0)
    assert 45<c.angle_span_deg<52


def test_slider_axis_with_noise_and_whole_prop_motion():
    rng=np.random.default_rng(2);samples=[];v=np.array([.6,.8])
    for u in np.linspace(0,100,100):
        g=transform(u/100,(u*.2,-20))
        j=transform(0,v*u+rng.normal(0,.15,2))
        samples.append(relative(g,g@j))
    c=fit_mechanism(samples)
    assert c.kind=='slider'
    assert np.dot(c.axis,v)>.999
    assert 94<c.high-c.low<98


def test_wrapped_angles_are_continuous():
    c=fit_mechanism([hinge(t) for t in np.linspace(2.9,3.9,90)])
    assert c.kind=='hinge' and 50<c.angle_span_deg<60
    assert c.low>2.8 and c.high>3.8


@pytest.mark.parametrize('samples',[
    [np.eye(3)]*40,
    [transform(0,(x,0)) for x in np.linspace(0,8,40)],
    [hinge(a) for a in np.linspace(0,.09,40)],
])
def test_insufficient_evidence(samples):
    with pytest.raises(EvidenceError):fit_mechanism(samples)


def test_manual_does_not_override_no_motion():
    with pytest.raises(EvidenceError):fit_mechanism([np.eye(3)]*40,force='hinge',pivot=[1,2])


def test_nonjoint_trajectory_rejected():
    with pytest.raises(EvidenceError):fit_mechanism([transform(0,(60*np.sin(t),60*np.cos(t))) for t in np.linspace(0,6,100)])


def test_calibration_roundtrip_and_invalid_range():
    c=fit_mechanism([hinge(a) for a in np.linspace(0,1,50)])
    assert Calibration.from_dict(c.to_dict())==c
    d=c.to_dict();d['high']=d['low']
    with pytest.raises(ValueError):Calibration.from_dict(d)
