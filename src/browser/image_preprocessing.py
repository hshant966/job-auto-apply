"""Image preprocessing pipeline for CAPTCHA solving.

Provides grayscale conversion, noise removal, adaptive thresholding,
morphological operations, contour-based character segmentation, color
filtering, and deskewing — all built on OpenCV + Pillow.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — avoid hard-crashing when cv2 / PIL are absent
# ---------------------------------------------------------------------------

def _cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        raise ImportError("opencv-python is required: pip install opencv-python-headless")

def _np():
    try:
        import numpy as np
        return np
    except ImportError:
        raise ImportError("numpy is required: pip install numpy")

def _pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        raise ImportError("Pillow is required: pip install Pillow")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PreprocessedImage:
    """Result of a preprocessing pipeline run."""
    original: any = None          # Original image array (BGR or grayscale)
    processed: any = None         # Final processed image array
    grayscale: any = None         # Intermediate grayscale
    binary: any = None            # Binary / thresholded image
    steps_applied: list[str] = field(default_factory=list)
    segments: list[any] = field(default_factory=list)  # Individual character crops


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def load_from_bytes(data: bytes) -> any:
    """Decode image bytes into a BGR numpy array."""
    cv2 = _cv2()
    np = _np()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image bytes")
    return img


def load_from_file(path: str) -> any:
    """Read an image file into a BGR numpy array."""
    cv2 = _cv2()
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img


def to_grayscale(img: any) -> any:
    """Convert BGR image to single-channel grayscale."""
    cv2 = _cv2()
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def gaussian_blur(img: any, kernel: int = 3) -> any:
    """Apply Gaussian blur for noise removal.  kernel must be odd."""
    cv2 = _cv2()
    k = max(3, kernel | 1)  # ensure odd
    return cv2.GaussianBlur(img, (k, k), 0)


def median_blur(img: any, kernel: int = 3) -> any:
    """Median blur — excellent for salt-and-pepper noise."""
    cv2 = _cv2()
    k = max(3, kernel | 1)
    return cv2.medianBlur(img, k)


def bilateral_filter(img: any, d: int = 9, sigma: int = 75) -> any:
    """Edge-preserving bilateral filter."""
    cv2 = _cv2()
    return cv2.bilateralFilter(img, d, sigma, sigma)


def threshold_binary(img: any, thresh: int = 128, max_val: int = 255) -> any:
    """Simple binary threshold."""
    cv2 = _cv2()
    _, binary = cv2.threshold(img, thresh, max_val, cv2.THRESH_BINARY)
    return binary


def threshold_otsu(img: any) -> any:
    """Otsu's automatic thresholding."""
    cv2 = _cv2()
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def adaptive_threshold(img: any, block_size: int = 11, C: int = 2) -> any:
    """Adaptive Gaussian threshold — handles uneven lighting."""
    cv2 = _cv2()
    bs = max(3, block_size | 1)
    return cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, bs, C,
    )


def invert(img: any) -> any:
    """Invert a binary image (white ↔ black)."""
    cv2 = _cv2()
    return cv2.bitwise_not(img)


# ---------------------------------------------------------------------------
# Morphological operations
# ---------------------------------------------------------------------------

def erode(img: any, kernel_size: int = 1, iterations: int = 1) -> any:
    cv2 = _cv2()
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.erode(img, k, iterations=iterations)


def dilate(img: any, kernel_size: int = 1, iterations: int = 1) -> any:
    cv2 = _cv2()
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.dilate(img, k, iterations=iterations)


def opening(img: any, kernel_size: int = 2) -> any:
    """Morphological opening (erosion → dilation) — removes small noise."""
    cv2 = _cv2()
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    return cv2.morphologyEx(img, cv2.MORPH_OPEN, k)


def closing(img: any, kernel_size: int = 2) -> any:
    """Morphological closing (dilation → erosion) — fills small holes."""
    cv2 = _cv2()
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    return cv2.morphologyEx(img, cv2.MORPH_CLOSE, k)


# ---------------------------------------------------------------------------
# Color filtering (remove coloured noise lines)
# ---------------------------------------------------------------------------

def remove_colored_lines(img: any, line_color_lower: tuple = (0, 0, 100),
                          line_color_upper: tuple = (180, 80, 255),
                          fill_value: int = 255) -> any:
    """Detect and remove coloured noise lines from a BGR image.

    Default range catches red-ish lines common on Indian govt CAPTCHAs.
    """
    cv2 = _cv2()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, line_color_lower, line_color_upper)
    # Dilate mask slightly to cover anti-aliased edges
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.dilate(mask, k, iterations=1)
    result = img.copy()
    result[mask > 0] = fill_value
    return result


def remove_lines_by_color(img: any, hue_ranges: list[tuple[int, int]],
                           sat_min: int = 50, val_min: int = 100) -> any:
    """Remove pixels within specific hue ranges (useful for multi-colour noise)."""
    cv2 = _cv2()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    full_mask = _np().zeros(hsv.shape[:2], dtype=_np().uint8)
    for h_lo, h_hi in hue_ranges:
        lower = (h_lo, sat_min, val_min)
        upper = (h_hi, 255, 255)
        mask = cv2.inRange(hsv, lower, upper)
        full_mask = cv2.bitwise_or(full_mask, mask)
    result = img.copy()
    result[full_mask > 0] = 255
    return result


# ---------------------------------------------------------------------------
# Deskewing
# ---------------------------------------------------------------------------

def deskew(img: any, max_angle: float = 15.0) -> any:
    """Deskew a binary image using Hough line detection.

    Only corrects angles up to *max_angle* degrees to avoid wild rotations.
    """
    cv2 = _cv2()
    np = _np()

    # Ensure binary
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                            minLineLength=gray.shape[1] // 4, maxLineGap=10)
    if lines is None:
        return img

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        if abs(angle) <= max_angle:
            angles.append(angle)

    if not angles:
        return img

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return img

    h, w = img.shape[:2]
    centre = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(centre, median_angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE,
                              borderValue=(255, 255, 255))
    return rotated


# ---------------------------------------------------------------------------
# Contour-based character segmentation
# ---------------------------------------------------------------------------

def segment_characters(img: any, min_area: int = 30, max_area: int = 5000,
                       min_aspect: float = 0.1, max_aspect: float = 5.0,
                       padding: int = 2) -> list[any]:
    """Detect contours and return sorted (left→right) character crops.

    Parameters
    ----------
    img : binary image (white text on black background)
    min_area, max_area : contour area bounds in pixels
    min_aspect, max_aspect : width/height ratio bounds
    padding : pixels of padding around each crop
    """
    cv2 = _cv2()
    np = _np()

    # Ensure white-on-black
    if img.mean() > 127:
        img = cv2.bitwise_not(img)

    contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    h_img, w_img = img.shape[:2]
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area < min_area or area > max_area:
            continue
        aspect = w / max(h, 1)
        if aspect < min_aspect or aspect > max_aspect:
            continue
        # Clip to image bounds
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(w_img, x + w + padding)
        y2 = min(h_img, y + h + padding)
        boxes.append((x1, y1, x2, y2))

    # Sort left-to-right
    boxes.sort(key=lambda b: b[0])

    crops = [img[y1:y2, x1:x2] for x1, y1, x2, y2 in boxes]
    return crops


# ---------------------------------------------------------------------------
# High-level pipeline
# ---------------------------------------------------------------------------

@dataclass
class PipelineStep:
    """Describes a single preprocessing step."""
    name: str
    func: str            # method name on this module
    kwargs: dict = field(default_factory=dict)


# Default pipelines — tried in order until OCR succeeds
DEFAULT_PIPELINES: list[list[PipelineStep]] = [
    # Pipeline A: simple grayscale + Otsu
    [
        PipelineStep("grayscale", "to_grayscale"),
        PipelineStep("otsu", "threshold_otsu"),
    ],
    # Pipeline B: grayscale + denoise + adaptive
    [
        PipelineStep("grayscale", "to_grayscale"),
        PipelineStep("gaussian_blur", "gaussian_blur", {"kernel": 3}),
        PipelineStep("adaptive_threshold", "adaptive_threshold", {"block_size": 11, "C": 2}),
    ],
    # Pipeline C: colour-filter + grayscale + median + Otsu + morph-open
    [
        PipelineStep("remove_colored_lines", "remove_colored_lines"),
        PipelineStep("grayscale", "to_grayscale"),
        PipelineStep("median_blur", "median_blur", {"kernel": 3}),
        PipelineStep("otsu", "threshold_otsu"),
        PipelineStep("opening", "opening", {"kernel_size": 2}),
    ],
    # Pipeline D: bilateral + adaptive + morph-close + deskew
    [
        PipelineStep("grayscale", "to_grayscale"),
        PipelineStep("bilateral", "bilateral_filter"),
        PipelineStep("adaptive_threshold", "adaptive_threshold", {"block_size": 15, "C": 4}),
        PipelineStep("closing", "closing", {"kernel_size": 2}),
        PipelineStep("deskew", "deskew"),
    ],
    # Pipeline E: heavy denoise + contrast + Otsu + invert
    [
        PipelineStep("grayscale", "to_grayscale"),
        PipelineStep("gaussian_blur", "gaussian_blur", {"kernel": 5}),
        PipelineStep("median_blur", "median_blur", {"kernel": 5}),
        PipelineStep("otsu", "threshold_otsu"),
        PipelineStep("invert", "invert"),
        PipelineStep("opening", "opening", {"kernel_size": 2}),
    ],
]

import sys as _sys


def run_pipeline(img: any, steps: list[PipelineStep]) -> PreprocessedImage:
    """Run a list of preprocessing steps on an image."""
    import sys
    mod = sys.modules[__name__]
    result = PreprocessedImage(original=img, processed=img.copy())
    current = img.copy()

    for step in steps:
        func = getattr(mod, step.func, None)
        if func is None:
            logger.warning(f"Unknown preprocessing function: {step.func}")
            continue
        try:
            current = func(current, **step.kwargs)
            result.steps_applied.append(step.name)
        except Exception as e:
            logger.warning(f"Pipeline step '{step.name}' failed: {e}")
            break

    result.processed = current
    if len(current.shape) == 2:
        result.grayscale = current
        result.binary = current
    else:
        result.grayscale = to_grayscale(current)
        result.binary = result.grayscale
    return result


def preprocess_all(img: any) -> list[PreprocessedImage]:
    """Run all default pipelines and return results."""
    return [run_pipeline(img, steps) for steps in DEFAULT_PIPELINES]


def auto_preprocess(img: bytes | any) -> PreprocessedImage:
    """Convenience: load from bytes (or array) → run first pipeline."""
    if isinstance(img, (bytes, bytearray)):
        img = load_from_bytes(img)
    return run_pipeline(img, DEFAULT_PIPELINES[0])


def preprocess_captcha(image_data: bytes) -> list[bytes]:
    """Run all default preprocessing pipelines on captcha image data.

    Returns a list of preprocessed image bytes, one per pipeline.
    """
    img = load_from_bytes(image_data)
    if img is None:
        return []
    results = []
    # Pipeline 1: grayscale + Otsu
    g = to_grayscale(img)
    results.append(to_bytes(otsu_threshold(g)))
    # Pipeline 2: contrast + sharpen
    results.append(to_bytes(gaussian_blur(g, 3)))
    # Pipeline 3: resize + denoise
    results.append(to_bytes(median_blur(g, 3)))
    # Pipeline 4: raw grayscale
    results.append(to_bytes(g))
    return results
