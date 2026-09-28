"""Time-based filtering and explicit loss/recovery; never extrapolates motion."""
from dataclasses import dataclass, asdict
import math
import numpy as np
from .geometry import angle, wrapped_delta


@dataclass
class Mapping:
    invert: bool = False
    sensitivity: float = 1.
    dead_zone: float = .012
    smoothing_ms: float = 55.

    @classmethod
    def from_dict(cls, data):
        m = cls(**data)
        if not (.25 <= m.sensitivity <= 3 and 0 <= m.dead_zone <= .15 and 0 <= m.smoothing_ms <= 500):
            raise ValueError('Mapping settings out of range.')
        return m

    def to_dict(self):
        return asdict(self)


class Control:
    def __init__(self, calibration=None, mapping=None):
        self.calibration = calibration
        self.mapping = mapping or Mapping()
        self.value = .0
        self.raw = .0
        self.filtered = .0
        self.previous_angle = None
        self.unwrapped = None
        self.last_t = None
        self.good = 0
        self.was_available = False
        self.recovery_start = None
        self.recovery_value = 0.

    def update(self, matrix, timestamp, reliable):
        dt = 1 / 30 if self.last_t is None else min(.2, max(0., timestamp - self.last_t))
        self.last_t = timestamp
        if not reliable or self.calibration is None:
            self.good = 0
            self.was_available = False
            self.recovery_start = None
            return self.state('lost' if self.calibration else 'uncalibrated', False)
        self.good += 1
        c = self.calibration
        if c.kind == 'hinge':
            a = angle(matrix)
            if self.previous_angle is None or self.good == 1:
                middle = (c.low + c.high) / 2
                self.unwrapped = a + round((middle - a) / (2 * np.pi)) * 2 * np.pi
            else:
                self.unwrapped += wrapped_delta(a, self.previous_angle)
            self.previous_angle = a
            physical = self.unwrapped
        else:
            physical = float(np.dot(matrix[:2, 2], c.axis))
        if self.good < 3:
            return self.state('reacquiring', False)
        raw = float(np.clip((physical - c.low) / (c.high - c.low), 0., 1.))
        if abs(raw - self.raw) >= self.mapping.dead_zone:
            self.raw = raw
        alpha = 1. if self.mapping.smoothing_ms == 0 else 1 - math.exp(-dt / (self.mapping.smoothing_ms / 1000))
        self.filtered += alpha * (self.raw - self.filtered)
        target = float(np.clip((self.filtered - .5) * self.mapping.sensitivity + .5, 0., 1.))
        if self.mapping.invert:
            target = 1 - target
        if not self.was_available:
            self.recovery_start, self.recovery_value = timestamp, self.value
        self.was_available = True
        blend = min(1., (timestamp - self.recovery_start) / .18)
        self.value = self.recovery_value * (1 - blend) + target * blend
        return self.state('blending' if blend < 1 else 'tracking', True, raw)

    def state(self, status, available, raw_measurement=None):
        return {'status': status, 'available': available, 'value': self.value,
                'raw': self.raw if raw_measurement is None else raw_measurement, 'filtered': self.filtered,
                'smoothing_ms': self.mapping.smoothing_ms}
