"""Classical and learned descriptor extraction behind the same small interface.

XFeat is an ONNX export of the official Apache-2.0 architecture/weights.
Selection remains user-assisted. Geometry and LK tracking are CPU operations.
"""
from pathlib import Path
import hashlib
import time
import os
from collections import deque
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class ORBFeatures:
    name = 'ORB + LK · CPU (classical)'
    binary = True

    def __init__(self):
        self.orb = cv2.ORB_create(nfeatures=2200, edgeThreshold=12, fastThreshold=9, nlevels=8)
        self.last_ms = 0.

    def extract(self, gray):
        start = time.perf_counter()
        k, d = self.orb.detectAndCompute(gray, None)
        self.last_ms = (time.perf_counter() - start) * 1000
        return np.array([p.pt for p in k], np.float32).reshape(-1, 2), d

    def info(self):
        return {'name': self.name, 'model': None, 'provider': 'CPU / OpenCV', 'npu_verified': False,
                'model_ms': None, 'features_ms': self.last_ms, 'quantization': 'not applicable'}


def preprocess(gray):
    x = cv2.resize(gray, (320, 256), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.
    # Matches InstanceNorm2d's biased variance and epsilon; outside neural graph.
    x = (x - x.mean()) / np.sqrt(x.var() + 1e-5)
    return x[None, None].astype(np.float32)


class XFeatFeatures:
    binary = False

    def __init__(self, provider='cpu', model_path=None, profile=False):
        import onnxruntime as ort
        path = Path(model_path) if model_path else ROOT / 'models/xfeat.onnx'
        if not path.exists():
            raise ValueError('XFeat model is missing. Run scripts/export_xfeat.py or choose the classical backend.')
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        opts.inter_op_num_threads = 1
        opts.enable_profiling = profile
        worker = os.environ.get('KAKASHI_QNN_WORKER') if provider == 'qnn' else None
        if provider == 'qnn' and not worker:
            if 'QNNExecutionProvider' not in ort.get_available_providers():
                raise ValueError('QNN is not installed on this machine. No CPU fallback was substituted.')
            opts.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
            providers = [('QNNExecutionProvider', {'backend_path': 'QnnHtp.dll', 'profiling_level': 'detailed'})]
        else:
            providers = ['CPUExecutionProvider']
        if worker:
            from .remote_inference import RemoteSession
            self.session = RemoteSession(worker, hashlib.sha256(path.read_bytes()).hexdigest())
        else:
            self.session = ort.InferenceSession(str(path), sess_options=opts, providers=providers)
        self.provider = provider
        self.name = f'XFeat + LK · {"QNN HTP (placement unverified)" if provider == "qnn" else "CPU"}'
        self.name += " · QDQ" if "qdq" in path.name else ""
        self.model_path = path
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        self.last_ms = 0.
        self.model_ms = 0.
        self.inference_times = deque(maxlen=120)

    def extract(self, gray):
        start = time.perf_counter()
        x = preprocess(gray)
        t = time.perf_counter()
        feat, logits, reliability = self.session.run(None, {self.session.get_inputs()[0].name: x})
        feat /= np.maximum(np.linalg.norm(feat, axis=1, keepdims=True), 1e-8)
        self.model_ms = getattr(self.session, 'last_inference_ms', (time.perf_counter() - t) * 1000)
        self.inference_times.append(time.perf_counter())
        logits = logits[0] - logits[0].max(axis=0, keepdims=True)
        probs = np.exp(logits)
        probs /= probs.sum(axis=0, keepdims=True)
        h, w = probs.shape[1:]
        heat = probs[:64].transpose(1, 2, 0).reshape(h, w, 8, 8).transpose(0, 2, 1, 3).reshape(h * 8, w * 8)
        rel = cv2.resize(reliability[0, 0], (w * 8, h * 8), interpolation=cv2.INTER_LINEAR)
        score = heat * rel
        nms = (heat == cv2.dilate(heat, np.ones((5, 5), np.uint8))) & (heat > .04)
        nms[:5] = nms[-5:] = False
        nms[:, :5] = nms[:, -5:] = False
        ys, xs = np.where(nms)
        order = np.argsort(score[ys, xs])[::-1][:1600]
        pts = np.stack([xs[order], ys[order]], axis=1).astype(np.float32)
        if len(pts) == 0:
            return pts, None
        # Upstream normalizes positions by image (W-1,H-1), then samples with
        # grid_sample(align_corners=False). Convert that grid to map pixel centers.
        fx = pts[:, 0] / (w * 8 - 1) * w - .5
        fy = pts[:, 1] / (h * 8 - 1) * h - .5
        # OpenCV cubic remap supports at most four channels; remap each group.
        field = feat[0].transpose(1, 2, 0)
        desc = np.concatenate([cv2.remap(field[:, :, i:i+4], fx[:, None], fy[:, None], cv2.INTER_CUBIC).reshape(len(pts), 4)
                               for i in range(0, 64, 4)], axis=1)
        desc /= np.maximum(np.linalg.norm(desc, axis=1, keepdims=True), 1e-8)
        pts *= np.array([gray.shape[1] / (w * 8), gray.shape[0] / (h * 8)], np.float32)
        self.last_ms = (time.perf_counter() - start) * 1000
        return pts, desc.astype(np.float32)

    def info(self):
        now = time.perf_counter()
        recent = [t for t in self.inference_times if now-t<2]
        refresh_hz = (len(recent)-1)/(recent[-1]-recent[0]) if len(recent)>1 else 0.
        return {'name': self.name, 'model': self.model_path.name, 'sha256': self.sha256,
                'provider': self.session.get_providers(), 'npu_verified': False,
                'model_ms': self.model_ms, 'features_ms': self.last_ms,
                'neural_refresh_hz': refresh_hz,
                'quantization': 'QDQ candidate' if 'qdq' in self.model_path.name else 'FP32',
                'input': '1×1×256×320; grayscale /255, instance normalization on CPU'}


def create_features(name):
    if name == 'xfeat':
        return XFeatFeatures()
    if name == 'xfeat-qdq':
        return XFeatFeatures(model_path=ROOT / 'models/xfeat.qdq.onnx')
    if name == 'qnn':
        return XFeatFeatures('qnn', ROOT / 'models/xfeat.qdq.onnx')
    if name == 'orb':
        return ORBFeatures()
    raise ValueError('Unknown perception backend.')


def match_features(reference, current, binary):
    if reference is None or current is None or len(reference) < 4 or len(current) < 4:
        return np.array([], int), np.array([], int)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING if binary else cv2.NORM_L2)
    pairs = matcher.knnMatch(reference, current, k=2)
    reverse = matcher.match(current, reference)
    rev = {m.queryIdx: m.trainIdx for m in reverse}
    good = [m for p in pairs if len(p) == 2 for m, n in [p]
            if m.distance < (.77 if binary else .85) * n.distance and rev.get(m.trainIdx) == m.queryIdx]
    return np.array([m.queryIdx for m in good], int), np.array([m.trainIdx for m in good], int)
