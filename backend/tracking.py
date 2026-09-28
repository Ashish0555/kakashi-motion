from dataclasses import dataclass
import cv2
import numpy as np
from .perception import match_features


def warp(points, matrix):
    return cv2.transform(np.asarray(points, np.float32).reshape(-1, 1, 2), matrix[:2]).reshape(-1, 2)


def robust_transform(ref, now):
    if len(ref) < 8:
        return None, None, 'Too few visible features'
    matrix, mask = cv2.estimateAffinePartial2D(ref, now, method=cv2.RANSAC, ransacReprojThreshold=2.4, maxIters=1000, confidence=.995)
    if matrix is None:
        return None, None, 'Unstable part pose'
    ok = mask.ravel().astype(bool)
    if ok.sum() < 8 or ok.mean() < .50:
        return None, None, 'Inconsistent visual matches'
    pts = ref[ok]
    spread = np.linalg.eigvalsh(np.cov(pts.T))
    if spread[0] < 12 or spread[0] / max(spread[1], 1) < .018:
        return None, None, 'Features are too close or nearly collinear'
    scale = np.sqrt(np.linalg.det(matrix[:, :2]))
    if not .65 < scale < 1.5:
        return None, None, 'Move closer to the original camera plane'
    if np.median(np.linalg.norm(warp(ref[ok], np.vstack([matrix, [0, 0, 1]])) - now[ok], axis=1)) > 2.2:
        return None, None, 'Part is bending or tracking has drifted'
    return np.vstack([matrix, [0., 0., 1.]]), ok, ''


@dataclass
class Part:
    box: list
    template_points: np.ndarray
    descriptors: np.ndarray
    reference: np.ndarray
    current: np.ndarray
    matrix: np.ndarray
    valid: bool = True
    reason: str = ''
    inliers: int = 0

    def polygon(self):
        x, y, w, h = self.box
        return warp([[x, y], [x+w, y], [x+w, y+h], [x, y+h]], self.matrix).tolist()


class PartsTracker:
    def __init__(self, features):
        self.features = features
        self.parts = []
        self.previous = None
        self.template_gray = None
        self.index = 0

    def appearance_agrees(self, part, gray):
        """Independent pixel check prevents coherent flow on an occluding hand.

        Normalized correlation tolerates exposure gain/offset, not invented texture.
        Sample only the inner selected patch; still requires a textured rigid face.
        """
        x,y,w,h=part.box
        xx,yy=np.meshgrid(np.linspace(x+5,x+w-5,24),np.linspace(y+5,y+h-5,24))
        ref=np.column_stack([xx.ravel(),yy.ravel()]).astype(np.float32)
        cur=warp(ref,part.matrix)
        a=cv2.remap(self.template_gray,ref[:,0:1],ref[:,1:2],cv2.INTER_LINEAR).ravel().astype(float)
        b=cv2.remap(gray,cur[:,0:1],cur[:,1:2],cv2.INTER_LINEAR).ravel().astype(float)
        a-=a.mean();b-=b.mean()
        denom=np.linalg.norm(a)*np.linalg.norm(b)
        return denom>100 and np.dot(a,b)/denom>.38

    def replenish(self, part, gray):
        mask=np.zeros_like(gray)
        cv2.fillConvexPoly(mask,np.asarray(part.polygon(),np.int32),255)
        mask=cv2.erode(mask,np.ones((7,7),np.uint8))
        corners=cv2.goodFeaturesToTrack(gray,110,.015,6,mask=mask)
        if corners is not None and len(corners)>=12:
            part.current=corners.reshape(-1,2)
            part.reference=warp(part.current,np.linalg.inv(part.matrix))
            part.inliers=len(part.current)

    def refine_alignment(self, part, gray):
        """Photometric subpixel anchoring after descriptor correspondence.

        Both backends use this same refinement. It corrects small keypoint
        localization biases before they can bias the learned pivot.
        """
        x,y,w,h=[int(v) for v in part.box]
        xx,yy=np.meshgrid(np.arange(x,x+w,dtype=np.float32),np.arange(y,y+h,dtype=np.float32))
        points=np.column_stack([xx.ravel(),yy.ravel()])
        moved=warp(points,part.matrix)
        aligned=cv2.remap(gray,moved[:,0].reshape(h,w),moved[:,1].reshape(h,w),cv2.INTER_LINEAR)
        template=self.template_gray[y:y+h,x:x+w]
        try:
            correlation,correction=cv2.findTransformECC(template,aligned,np.eye(2,3,dtype=np.float32),
                cv2.MOTION_EUCLIDEAN,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,20,1e-4),None,3)
        except cv2.error:
            return
        if correlation<.70 or np.linalg.norm(correction[:,2])>12 or abs(np.arctan2(correction[1,0],correction[0,0]))>np.deg2rad(8):
            return
        origin=np.array([[1.,0.,x],[0.,1.,y],[0.,0.,1.]])
        part.matrix=part.matrix@origin@np.vstack([correction,[0.,0.,1.]])@np.linalg.inv(origin)

    def select(self, gray, boxes):
        points, descriptors = self.features.extract(gray)
        parts = []
        for box in boxes:
            x, y, w, h = box
            inside = (points[:, 0] > x+3) & (points[:, 0] < x+w-3) & (points[:, 1] > y+3) & (points[:, 1] < y+h-3)
            chosen = points[inside]
            if len(chosen) < 12:
                raise ValueError('One part has too few distinctive details. Select a larger textured patch, add printed texture, or try the other backend.')
            mask = np.zeros_like(gray)
            cv2.rectangle(mask, (int(x+3), int(y+3)), (int(x+w-3), int(y+h-3)), 255, -1)
            corners = cv2.goodFeaturesToTrack(gray, 110, .015, 6, mask=mask)
            if corners is None or len(corners) < 12:
                raise ValueError('Add visible texture to both parts, then reselect.')
            ref = corners.reshape(-1, 2)
            parts.append(Part(box, chosen, descriptors[inside], ref.copy(), ref.copy(), np.eye(3), inliers=len(ref)))
        self.parts, self.previous, self.index = parts, gray.copy(), 0
        self.template_gray = gray.copy()

    def update(self, gray, discontinuity=False):
        self.index += 1
        refresh = discontinuity or self.index % 12 == 0 or any(not p.valid for p in self.parts)
        points, descriptors = self.features.extract(gray) if refresh else (None, None)
        for part in self.parts:
            found = False
            if refresh:
                ia, ib = match_features(part.descriptors, descriptors, self.features.binary)
                if len(ia) >= 8:
                    ref, cur = part.template_points[ia], points[ib]
                    if not self.features.binary:
                        # Learned descriptors locate correspondences coarsely. Refine
                        # their image alignment before fitting a precise joint.
                        seed = cur.reshape(-1, 1, 2).astype(np.float32).copy()
                        origin = ref.reshape(-1, 1, 2).astype(np.float32).copy()
                        refined, st, err = cv2.calcOpticalFlowPyrLK(self.template_gray, gray, origin, seed,
                            winSize=(15,15), maxLevel=1, flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
                        back, sb, _ = cv2.calcOpticalFlowPyrLK(gray, self.template_gray, refined, origin.copy(),
                            winSize=(15,15), maxLevel=1, flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
                        keep = st.ravel().astype(bool) & sb.ravel().astype(bool) & (err.ravel()<35)
                        keep &= np.linalg.norm(back-origin,axis=2).ravel()<1.2
                        ref, cur = ref[keep], refined.reshape(-1,2)[keep]
                    matrix, ok, why = robust_transform(ref, cur)
                    if matrix is not None:
                        part.matrix, part.reference, part.current = matrix, ref[ok], cur[ok]
                        part.valid, part.reason, part.inliers = True, '', int(ok.sum())
                        self.refine_alignment(part,gray)
                        self.replenish(part,gray)
                        found = True
            if not found and part.valid and self.previous is not None and not discontinuity and len(part.current) >= 8:
                p0 = part.current.reshape(-1, 1, 2).astype(np.float32)
                p1, st, err = cv2.calcOpticalFlowPyrLK(self.previous, gray, p0, None, winSize=(21,21), maxLevel=3)
                pback, sb, _ = cv2.calcOpticalFlowPyrLK(gray, self.previous, p1, None, winSize=(21,21), maxLevel=3)
                valid = st.ravel().astype(bool) & sb.ravel().astype(bool) & (np.linalg.norm(pback-p0, axis=2).ravel() < 1.0) & (err.ravel() < 24)
                valid &= (p1[:,0,0] >= 0) & (p1[:,0,0] < gray.shape[1]) & (p1[:,0,1] >= 0) & (p1[:,0,1] < gray.shape[0])
                ref, cur = part.reference[valid], p1.reshape(-1,2)[valid]
                matrix, ok, why = robust_transform(ref, cur)
                if matrix is not None:
                    part.matrix, part.reference, part.current = matrix, ref[ok], cur[ok]
                    part.valid, part.reason, part.inliers = True, '', int(ok.sum())
                    found = True
                else:
                    part.reason = why
            if found and not self.appearance_agrees(part,gray):
                found=False
                part.reason='Selected texture is hidden or changed. Show the original face.'
            if not found:
                part.valid, part.inliers = False, 0
                part.reason = part.reason or 'Part hidden or appearance changed; show its original textured face'
        self.previous = gray.copy()
        return self.parts


class MarkerTracker:
    """Explicit comparison baseline: ArUco DICT_4X4_50 IDs 0 and 1."""
    def __init__(self):
        self.detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50))
        self.reference = None
        self.parts = []

    def detect(self, gray):
        corners, ids, _ = self.detector.detectMarkers(gray)
        return {} if ids is None else {int(i): p.reshape(4,2) for i,p in zip(ids.ravel(),corners)}

    def select(self, gray, boxes=None):
        marks = self.detect(gray)
        if not all(i in marks for i in (0,1)):
            raise ValueError('Show ArUco 4×4/50 markers 0 and 1, one on each part. Printable markers are in assets/.')
        self.reference = marks
        self.parts = []
        for i in (0,1):
            pts=marks[i]
            lo,hi=pts.min(0),pts.max(0)
            self.parts.append(Part([*lo,*(hi-lo)],pts,None,pts,pts,np.eye(3),inliers=4))

    def update(self, gray, discontinuity=False):
        if self.reference is None:
            return []
        marks = self.detect(gray)
        for i,p in enumerate(self.parts):
            p.valid = i in marks
            if p.valid:
                m,_=cv2.estimateAffinePartial2D(self.reference[i],marks[i])
                if m is None:
                    p.valid=False
                else:
                    p.matrix=np.vstack([m,[0,0,1]])
                    p.current=marks[i]
            p.inliers=4 if p.valid else 0
            p.reason='' if p.valid else 'Marker hidden'
        return self.parts
