"""Aspect-preserving camera image processing for CamStudio Pro."""
from dataclasses import dataclass
import cv2
import numpy as np


@dataclass
class ImageSettings:
    brightness: int = 0
    contrast: int = 100
    saturation: int = 100
    sharpness: int = 0
    mirror: bool = False
    rotation: int = 0
    zoom: int = 100
    grayscale: bool = False
    warmth: int = 0
    show_grid: bool = False
    focus_x: float = 0.5  # 0..1 in the rotated video image
    focus_y: float = 0.5
    fit_mode: str = 'contain'  # contain (letterbox) or cover (crop to fill)


def _clamp(n, low, high):
    return max(low, min(high, n))


def rotated_dimensions(source_width, source_height, rotation):
    if rotation % 180 == 90:
        return source_height, source_width
    return source_width, source_height


def viewport(width, height, settings: ImageSettings, target_width=1280, target_height=720):
    """Source-space crop rectangle after rotation, never stretching the pixels."""
    if width < 2 or height < 2 or target_width < 1 or target_height < 1:
        raise ValueError('Invalid frame size')
    z = _clamp(float(settings.zoom), 100, 600) / 100
    cropw, croph = width, height
    if settings.fit_mode == 'cover':
        ar = target_width / target_height
        if width / height > ar:
            cropw = round(height * ar)
        else:
            croph = round(width / ar)
    cropw = int(_clamp(round(cropw / z), 2, width))
    croph = int(_clamp(round(croph / z), 2, height))
    fx = _clamp(float(settings.focus_x), 0.0, 1.0)
    fy = _clamp(float(settings.focus_y), 0.0, 1.0)
    x = int(_clamp(round(fx * width - cropw / 2), 0, width - cropw))
    y = int(_clamp(round(fy * height - croph / 2), 0, height - croph))
    return x, y, cropw, croph


def output_content_bounds(source_width, source_height, settings, output_width=1280, output_height=720):
    """Visible content rectangle in output coordinates (bars excluded)."""
    w, h = rotated_dimensions(source_width, source_height, settings.rotation)
    _, _, cw, ch = viewport(w, h, settings, output_width, output_height)
    if settings.fit_mode == 'cover':
        return 0, 0, output_width, output_height
    scale = min(output_width / cw, output_height / ch)
    ow, oh = min(output_width, max(1, round(cw * scale))), min(output_height, max(1, round(ch * scale)))
    return (output_width - ow) // 2, (output_height - oh) // 2, ow, oh


def source_point_from_output(u, v, source_width, source_height, settings, output_width=1280, output_height=720):
    """Map 0..1 output coordinates into a source image, accounting for letterbox."""
    rw, rh = rotated_dimensions(source_width, source_height, settings.rotation)
    x, y, cw, ch = viewport(rw, rh, settings, output_width, output_height)
    bx, by, bw, bh = output_content_bounds(source_width, source_height, settings, output_width, output_height)
    sx = _clamp((float(u) * output_width - bx) / bw, 0, 1)
    sy = _clamp((float(v) * output_height - by) / bh, 0, 1)
    return _clamp((x + sx * cw) / rw, 0, 1), _clamp((y + sy * ch) / rh, 0, 1)


def process_frame(frame: np.ndarray, s: ImageSettings, width: int = 1280, height: int = 720) -> np.ndarray:
    if frame is None or frame.size == 0:
        raise ValueError('Missing camera frame')
    rotation = int(s.rotation) % 360
    if rotation == 90:
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        frame = cv2.rotate(frame, cv2.ROTATE_180)
    elif rotation == 270:
        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if s.mirror:
        frame = cv2.flip(frame, 1)
    h, w = frame.shape[:2]
    x, y, cw, ch = viewport(w, h, s, width, height)
    frame = frame[y:y + ch, x:x + cw]
    if s.fit_mode == 'cover':
        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA if cw > width else cv2.INTER_LINEAR)
    else:
        # Use the actual cropped dimensions to preserve the correct aspect ratio.
        scale = min(width / cw, height / ch)
        ow = min(width, max(1, round(cw * scale)))
        oh = min(height, max(1, round(ch * scale)))
        bx, by = (width - ow) // 2, (height - oh) // 2
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        canvas[by:by + oh, bx:bx + ow] = cv2.resize(frame, (ow, oh), interpolation=cv2.INTER_AREA if cw > ow else cv2.INTER_LINEAR)
        frame = canvas
    if s.contrast != 100 or s.brightness:
        # 256-byte OpenCV LUT replaces multiple full-resolution float32 buffers.
        table = np.clip(
            np.arange(256, dtype=np.float32) * max(0, s.contrast / 100) + s.brightness,
            0, 255
        ).astype(np.uint8)
        frame = cv2.LUT(frame, table)
    if s.saturation != 100:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32) * (s.saturation / 100), 0, 255).astype(np.uint8)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    if s.warmth:
        values = np.arange(256, dtype=np.int16)
        # A channel-specific LUT keeps the same B/G/R adjustments without
        # converting the whole image to int16 or allocating extra 3-channel arrays.
        lookup = np.stack((
            np.clip(values - s.warmth, 0, 255),
            values,
            np.clip(values + s.warmth, 0, 255),
        ),axis=1).astype(np.uint8).reshape(1,256,3)
        frame = cv2.LUT(frame,lookup)
    if s.sharpness:
        blurred = cv2.GaussianBlur(frame, (0, 0), 1.1)
        frame = cv2.addWeighted(frame, 1 + s.sharpness / 60, blurred, -s.sharpness / 60, 0)
    if s.grayscale:
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
    if s.show_grid:
        col = (175, 175, 175)
        for xx in (width // 3, 2 * width // 3):
            cv2.line(frame, (xx, 0), (xx, height), col, 1)
        for yy in (height // 3, 2 * height // 3):
            cv2.line(frame, (0, yy), (width, yy), col, 1)
    return np.ascontiguousarray(frame)


PRESETS = {
    'Naturel': ImageSettings(),
    'Studio': ImageSettings(brightness=6, contrast=112, saturation=105, sharpness=22),
    'Cinéma': ImageSettings(brightness=-4, contrast=118, saturation=83, warmth=8),
    'Noir & blanc': ImageSettings(contrast=115, sharpness=15, grayscale=True),
    'Streaming': ImageSettings(brightness=8, contrast=110, saturation=115, sharpness=18),
}
