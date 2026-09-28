import base64
import time
from collections import deque
import cv2
import numpy as np
from .geometry import Calibration, EvidenceError, fit_mechanism, relative
from .control import Control, Mapping
from .perception import create_features
from .tracking import PartsTracker, MarkerTracker


class Engine:
    def __init__(self, backend='orb'):
        cv2.setNumThreads(2)
        self.backend = backend
        self.features = create_features('orb' if backend == 'marker' else backend)
        self.tracker = MarkerTracker() if backend == 'marker' else PartsTracker(self.features)
        self.control = Control()
        self.frame_id = -1
        self.capture_t = None
        self.gray = None
        self.jpeg = None
        self.reference_jpeg = None
        self.boxes = None
        self.phase = 'show'
        self.samples = deque(maxlen=1800)
        self.sample_times = deque(maxlen=1800)
        self.proposal = None
        self.last_relative = np.eye(3)
        self.processing = deque(maxlen=300)
        self.last_info = {}

    def frame(self, jpeg, frame_id, capture_t):
        start = time.perf_counter()
        if frame_id <= self.frame_id or not np.isfinite(capture_t) or (self.capture_t is not None and capture_t <= self.capture_t):
            raise ValueError('Stale or out-of-order frame discarded.')
        if len(jpeg) > 2_000_000:
            raise ValueError('Camera frame exceeds the 2 MB limit.')
        gray = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_GRAYSCALE)
        if gray is None or max(gray.shape) > 1280 or min(gray.shape) < 64:
            raise ValueError('Send a valid image between 64 and 1280 pixels per dimension.')
        if self.gray is not None and self.tracker.parts and gray.shape != self.gray.shape:
            raise ValueError('Camera dimensions changed. Reset and select the parts again.')
        gap = self.capture_t is not None and capture_t - self.capture_t > .25
        self.frame_id, self.capture_t, self.jpeg, self.gray = frame_id, capture_t, jpeg, gray
        decode_ms = (time.perf_counter() - start) * 1000
        track_start = time.perf_counter()
        parts = self.tracker.update(gray, discontinuity=gap) if self.tracker.parts else []
        tracking_ms = (time.perf_counter() - track_start) * 1000
        reliable = len(parts) == 2 and all(p.valid for p in parts)
        reason = ''
        if reliable:
            self.last_relative = relative(parts[0].matrix, parts[1].matrix)
            scale = np.sqrt(np.linalg.det(self.last_relative[:2,:2]))
            if not .92 < scale < 1.08:
                reliable, reason = False, 'Parts changed relative scale. Return to the original camera plane.'
            # A calibrated joint is an additional independent consistency check.
            # Reprojection can look locally plausible even when features drift.
            calibration=self.control.calibration
            if reliable and calibration is not None:
                r=self.last_relative[:2,:2]/scale
                t=self.last_relative[:2,2]
                if calibration.kind=='hinge':
                    error=np.linalg.norm((np.eye(2)-r)@np.asarray(calibration.pivot)-t)
                else:
                    axis=np.asarray(calibration.axis)
                    error=abs(np.dot(t,[-axis[1],axis[0]]))
                    if abs(np.arctan2(r[1,0],r[0,0]))>np.deg2rad(7):error=100
                if error>max(5.,calibration.residual_px*2.5):
                    reliable,reason=False,'Tracking no longer agrees with the learned joint. Show the original faces or recalibrate.'
        if reliable and self.phase == 'learn':
            self.samples.append(self.last_relative.copy())
            self.sample_times.append(capture_t)
        state = self.control.update(self.last_relative, capture_t, reliable and not gap)
        elapsed = (time.perf_counter() - start) * 1000
        self.processing.append(elapsed)
        info = self.features.info() if self.backend != 'marker' else {'name':'ArUco 0/1 · CPU (marker baseline)', 'provider':'CPU / OpenCV', 'npu_verified':False, 'model_ms':None}
        self.last_info = info
        return {'type': 'frame', 'frame_id': frame_id, 'capture_t': capture_t, 'phase': self.phase,
                'control':state, 'tracking': 'tracked' if reliable else 'lost' if parts else 'unselected',
                'reason':reason or next((p.reason for p in parts if not p.valid),'') or ('Frame gap: verifying reacquisition' if gap else ''),
                'parts':[{'polygon':p.polygon(), 'matrix':p.matrix.tolist(), 'valid':p.valid, 'inliers':p.inliers,
                          'points':p.current[::max(1,len(p.current)//32)].tolist() if p.valid else []} for p in parts],
                'samples':len(self.samples), 'relative': self.last_relative.tolist() if reliable else None,
                'timing':{'decode_ms':decode_ms,'tracking_ms':tracking_ms,'processing_ms':elapsed,
                          'p50_ms':float(np.median(self.processing)), 'p95_ms':float(np.quantile(self.processing,.95))},
                'backend':info}

    def validate_boxes(self, boxes, shape):
        if not isinstance(boxes, list) or len(boxes) != 2:
            raise ValueError('Select exactly two textured parts.')
        height, width = shape
        for box in boxes:
            if len(box) != 4 or not np.isfinite(box).all():
                raise ValueError('Invalid selection.')
            x,y,w,h = box
            if min(w,h) < 24 or min(x,y) < 0 or x+w > width+1 or y+h > height+1:
                raise ValueError('Draw two boxes at least 24 pixels wide and high, inside the camera frame.')
        a,b=boxes
        intersection=max(0,min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])) * max(0,min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1]))
        if intersection > .08 * min(a[2]*a[3],b[2]*b[3]):
            raise ValueError('Choose separate patches. Each box must contain only one rigid part.')

    def command(self, cmd):
        kind=cmd.get('type')
        if kind == 'select':
            if self.gray is None or cmd.get('frame_id') != self.frame_id:
                raise ValueError('Selection frame is no longer current. Freeze the camera and retry.')
            boxes = cmd.get('boxes',[])
            if self.backend != 'marker':
                self.validate_boxes(boxes,self.gray.shape)
            self.tracker.select(self.gray,boxes)
            self.boxes=boxes
            self.reference_jpeg=self.jpeg
            self.proposal=None
            self.control=Control(mapping=self.control.mapping)
            self.phase='selected'
            self.samples.clear(); self.sample_times.clear()
            return {'type':'selected','phase':self.phase,'counts':[p.inliers for p in self.tracker.parts]}
        if kind == 'learn':
            if len(self.tracker.parts)!=2:
                raise ValueError('Select both parts first.')
            self.samples.clear(); self.sample_times.clear()
            self.proposal=None
            self.control=Control(mapping=self.control.mapping)
            self.phase='learn'
            return {'type':'learning','phase':self.phase}
        if kind == 'fit':
            self.proposal=fit_mechanism(list(self.samples), list(self.sample_times), cmd.get('force'),cmd.get('axis_deg'),cmd.get('pivot'))
            self.phase='proposed'
            return {'type':'proposal','phase':self.phase,'proposal':self.proposal.to_dict()}
        if kind == 'confirm':
            if self.proposal is None:
                raise ValueError('Demonstrate and fit a mechanism first.')
            self.control=Control(self.proposal,self.control.mapping)
            self.phase='perform'
            return {'type':'confirmed','phase':self.phase,'proposal':self.proposal.to_dict()}
        if kind == 'mapping':
            self.control.mapping=Mapping.from_dict(cmd['mapping'])
            return {'type':'mapping','mapping':self.control.mapping.to_dict()}
        if kind == 'export':
            if self.control.calibration is None:
                raise ValueError('Confirm a learned control before saving.')
            return {'type':'profile','profile':{'version':1,'backend':self.backend,
                'calibration':self.control.calibration.to_dict(),'mapping':self.control.mapping.to_dict(),
                'boxes':self.boxes,'reference_jpeg':base64.b64encode(self.reference_jpeg).decode('ascii'),
                'width':int(self.gray.shape[1]),'height':int(self.gray.shape[0])}}
        if kind == 'load':
            p=cmd['profile']
            if p.get('version') != 1:
                raise ValueError('Unsupported profile version.')
            cal=Calibration.from_dict(p['calibration']); mapping=Mapping.from_dict(p['mapping'])
            jpeg=base64.b64decode(p['reference_jpeg'],validate=True)
            if len(jpeg)>2_000_000:
                raise ValueError('Profile reference image is too large.')
            gray=cv2.imdecode(np.frombuffer(jpeg,np.uint8),cv2.IMREAD_GRAYSCALE)
            if gray is None or max(gray.shape)>1280 or gray.shape != (p['height'],p['width']):
                raise ValueError('Invalid profile reference image.')
            if p['backend'] != 'marker':
                self.validate_boxes(p['boxes'],gray.shape)
            # Build a candidate first; malformed profiles do not destroy a working session.
            candidate=Engine(p['backend'])
            candidate.tracker.select(gray,p['boxes'])
            candidate.gray=gray
            candidate.boxes=p['boxes']; candidate.reference_jpeg=jpeg
            candidate.proposal=cal; candidate.control=Control(cal,mapping); candidate.phase='perform'
            self.__dict__.update(candidate.__dict__)
            return {'type':'loaded','phase':self.phase,'proposal':cal.to_dict(),'mapping':mapping.to_dict(),'backend':p['backend']}
        raise ValueError('Unknown command.')
