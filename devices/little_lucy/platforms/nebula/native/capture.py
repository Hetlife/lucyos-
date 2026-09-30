"""Nebula input bridge capture geometry and frame metadata helpers."""

from math import isfinite

NATIVE_WIDTH = 480
NATIVE_HEIGHT = 272
DEFAULT_TTL_SECONDS = 5.0


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_finite_number(value, name):
    if not _is_number(value) or not isfinite(value):
        raise ValueError("%s must be a finite number" % name)
    return float(value)


class Geometry:
    def __init__(self, x=0, y=0, width=1920, height=1080, scale=1.0, display_id='primary'):
        self.x = _validate_finite_number(x, 'x')
        self.y = _validate_finite_number(y, 'y')
        self.width = _validate_finite_number(width, 'width')
        self.height = _validate_finite_number(height, 'height')
        self.scale = _validate_finite_number(scale, 'scale')
        if self.width <= 0 or self.height <= 0:
            raise ValueError('width and height must be positive')
        if self.scale <= 0:
            raise ValueError('scale must be positive')
        self.display_id = display_id

    @classmethod
    def from_dict(cls, data):
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError('geometry data must be a mapping')
        return cls(
            x=data.get('x', 0),
            y=data.get('y', 0),
            width=data.get('width', 1920),
            height=data.get('height', 1080),
            scale=data.get('scale', 1.0),
            display_id=data.get('display_id', 'primary'),
        )

    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'scale': self.scale,
            'display_id': self.display_id,
        }


def _validate_geometry(geometry):
    if not isinstance(geometry, Geometry):
        raise ValueError('invalid geometry')
    return geometry


def _validate_point(point):
    if (not isinstance(point, (tuple, list))) or len(point) != 2:
        raise ValueError('point must be a pair')
    nx, ny = point
    if not _is_number(nx) or not _is_number(ny):
        raise ValueError('point must contain numeric values')
    if not isfinite(nx) or not isfinite(ny):
        raise ValueError('point must be finite')
    return float(nx), float(ny)


def map_native_to_pc(point, geometry):
    geometry = _validate_geometry(geometry)
    nx, ny = _validate_point(point)
    nx = max(0.0, min(float(NATIVE_WIDTH), nx))
    ny = max(0.0, min(float(NATIVE_HEIGHT), ny))
    pc_x = geometry.x + (nx / NATIVE_WIDTH) * geometry.width
    pc_y = geometry.y + (ny / NATIVE_HEIGHT) * geometry.height
    return pc_x, pc_y


def native_to_region(point, geometry):
    geometry = _validate_geometry(geometry)
    nx, ny = _validate_point(point)
    nx = max(0.0, min(float(NATIVE_WIDTH), nx))
    ny = max(0.0, min(float(NATIVE_HEIGHT), ny))
    return nx / NATIVE_WIDTH, ny / NATIVE_HEIGHT


class Frame:
    def __init__(self, image_bytes, timestamp, geometry, width, height, display_id=None):
        self.image_bytes = image_bytes
        self.timestamp = _validate_finite_number(timestamp, 'timestamp')
        self.geometry = _validate_geometry(geometry)
        self.width = _validate_finite_number(width, 'width')
        self.height = _validate_finite_number(height, 'height')
        self.display_id = display_id if display_id is not None else self.geometry.display_id

    def age(self, now=None):
        if now is None:
            import time
            now = time.time()
        now = _validate_finite_number(now, 'now')
        return now - self.timestamp

    def is_fresh(self, now=None, ttl=DEFAULT_TTL_SECONDS):
        ttl = _validate_finite_number(ttl, 'ttl')
        if ttl < 0:
            raise ValueError('ttl must be non-negative')
        return self.age(now=now) <= ttl


def is_fresh(frame, now=None, ttl=DEFAULT_TTL_SECONDS):
    if not isinstance(frame, Frame):
        raise ValueError('invalid frame')
    return frame.is_fresh(now=now, ttl=ttl)


def frame_metadata(frame):
    if not isinstance(frame, Frame):
        raise ValueError('invalid frame')
    return {
        'timestamp': frame.timestamp,
        'display_id': frame.display_id,
        'width': frame.width,
        'height': frame.height,
        'geometry': frame.geometry.to_dict(),
        'bytes': len(frame.image_bytes) if frame.image_bytes is not None else 0,
    }
