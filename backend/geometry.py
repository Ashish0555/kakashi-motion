"""Planar reference-image -> current-image transforms; pixels x right, y down.

Column homogeneous vectors: p_current = T_part @ p_reference.
Both reference systems are the SAME image, so inv(T_A) @ T_B cancels
common in-plane motion. A hinge satisfies t = (I-R) @ pivot_reference.
No camera intrinsics, depth, physical distances, or mechanical limits inferred.
"""
from dataclasses import dataclass, asdict
import math
import numpy as np
from scipy.optimize import least_squares


class EvidenceError(ValueError):
    pass


def transform(theta=0.0, translation=(0., 0.)):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, translation[0]], [s, c, translation[1]], [0., 0., 1.]])


def relative(a, b):
    return np.linalg.solve(np.asarray(a), np.asarray(b))


def angle(t):
    return math.atan2(t[1, 0], t[0, 0])


def wrapped_delta(a, b):
    return (a - b + np.pi) % (2 * np.pi) - np.pi


@dataclass
class Calibration:
    kind: str
    low: float
    high: float
    axis: list[float]
    pivot: list[float] | None
    residual_px: float
    angle_span_deg: float
    travel_px: float
    samples: int
    manual: bool = False
    version: int = 1

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        c = cls(**data)
        if c.version != 1 or c.kind not in ('hinge', 'slider'):
            raise ValueError('Unsupported controller format.')
        nums = [c.low, c.high, c.residual_px, c.angle_span_deg, c.travel_px, *c.axis, *(c.pivot or [])]
        if not np.isfinite(nums).all() or c.high <= c.low or len(c.axis) != 2:
            raise ValueError('Invalid controller range or geometry.')
        if c.kind == 'slider' and abs(np.linalg.norm(c.axis) - 1) > .01:
            raise ValueError('Slide axis must have unit length.')
        if c.pivot is not None and len(c.pivot) != 2:
            raise ValueError('Invalid pivot.')
        return c


def fit_mechanism(matrices, times=None, force=None, axis_deg=None, pivot=None):
    ts = np.asarray(matrices, dtype=float)
    if len(ts) < 24:
        raise EvidenceError('Need at least 24 reliable observations. Move both parts through a larger range.')
    if times is not None and max(times) - min(times) < .7:
        raise EvidenceError('Demonstrate slowly for at least one second.')
    if ts.shape[1:] != (3, 3) or not np.isfinite(ts).all():
        raise EvidenceError('Invalid observations. Reselect the parts and retry.')
    scales = np.sqrt(np.linalg.det(ts[:, :2, :2]))
    if np.any(~np.isfinite(scales)) or np.quantile(np.abs(scales - 1), .9) > .08:
        raise EvidenceError('Parts changed apparent scale. Keep movement parallel to the camera.')
    rotations = ts[:, :2, :2] / scales[:, None, None]
    angles = np.unwrap(np.arctan2(rotations[:, 1, 0], rotations[:, 0, 0]))
    trans = ts[:, :2, 2]
    alo, ahi = np.quantile(angles, [.02, .98])
    arc = float(np.degrees(ahi - alo))
    center = np.median(trans, axis=0)
    _, singular, vt = np.linalg.svd(trans - center, full_matrices=False)
    axis = vt[0]
    # Deterministic direction across fitting/serialization.
    if axis[np.argmax(abs(axis))] < 0:
        axis = -axis
    if axis_deg is not None:
        axis = np.array([np.cos(np.deg2rad(axis_deg)), np.sin(np.deg2rad(axis_deg))])
    positions = trans @ axis
    plo, phi = np.quantile(positions, [.02, .98])
    travel = float(phi - plo)
    perp = np.array([-axis[1], axis[0]])
    slide_error = float(np.quantile(np.abs((trans - center) @ perp), .9))
    design = np.eye(2)[None] - rotations
    design_flat = design.reshape(-1, 2)
    joint0, _, _, _ = np.linalg.lstsq(design_flat, trans.ravel(), rcond=None)
    joint = least_squares(lambda p: (design @ p - trans).ravel(), joint0, loss='soft_l1', f_scale=2.).x
    if pivot is not None:
        joint = np.asarray(pivot, dtype=float)
    hinge_error = float(np.quantile(np.linalg.norm(design @ joint - trans, axis=1), .9))
    excitation = np.linalg.svd(design_flat, compute_uv=False)[-1] / np.sqrt(len(ts))
    hinge_ok = arc >= (6 if force == 'hinge' else 15) and excitation > .06 and hinge_error < 4 and np.linalg.norm(joint) < 2500
    slider_ok = travel >= 20 and arc < (8 if force == 'slider' else 4) and slide_error < max(3., travel * .035)
    if force not in (None, 'hinge', 'slider'):
        raise ValueError('Choose hinge or slider.')
    if (force in (None, 'hinge')) and hinge_ok:
        return Calibration('hinge', float(alo), float(ahi), [1., 0.], joint.tolist(), hinge_error, arc, travel, len(ts), force is not None)
    if (force in (None, 'slider')) and slider_ok:
        return Calibration('slider', float(plo), float(phi), axis.tolist(), None, slide_error, arc, travel, len(ts), force is not None)
    if arc < 3 and travel < 20:
        raise EvidenceError('Too little internal movement. Moving the whole prop does not teach a joint. Open at least 15° or slide at least 20 pixels.')
    if 3 <= arc < 15:
        raise EvidenceError('This small arc is ambiguous. Show a wider hinge opening; a short arc can resemble a slide.')
    raise EvidenceError(f'Motion does not fit one planar joint (hinge error {hinge_error:.1f}px; slide error {slide_error:.1f}px). Avoid bending, perspective changes, and occlusion; reselect and retry.')
