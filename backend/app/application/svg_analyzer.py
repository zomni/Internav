"""Deterministic SVG floor-plan analysis for grid walkability.

The analyzer treats every non-white pixel as an obstacle (structural walls,
partitions, doors, furniture) and marks a cell as non-walkable when it touches
an obstacle or lies entirely outside the bounding box of all obstacles. The
bounding-box exterior only excludes the blank canvas margin around the
building, so the SVG does not need a closed building outline and doorways in
the walls do not cause the interior to be misclassified as exterior.

The implementation is dependency-free (stdlib + numpy) and fully deterministic
so grid generation is reproducible.
"""

from __future__ import annotations

import itertools
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.domain.errors import DomainValidationError

_BoolArray = np.ndarray[Any, np.dtype[np.bool_]]

_WHITE = {"white", "#fff", "#ffffff"}
_NUM = re.compile(r"-?\d*\.?\d+(?:e[-+]?\d+)?", re.IGNORECASE)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _is_white(value: str | None) -> bool:
    return (value or "").strip().lower() in _WHITE


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_svg_dimensions(svg_bytes: bytes) -> tuple[int, int]:
    """Extract the declared width/height (in px) from the root <svg> element."""
    try:
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as exc:
        raise DomainValidationError("Could not parse SVG floor plan.") from exc
    width = root.get("width")
    height = root.get("height")
    if width is None or height is None:
        raise DomainValidationError("SVG must declare width and height attributes.")
    try:
        width_value = int(float(width))
        height_value = int(float(height))
    except ValueError as exc:
        raise DomainValidationError("SVG width and height must be numeric.") from exc
    if width_value <= 0 or height_value <= 0:
        raise DomainValidationError("SVG width and height must be positive.")
    return width_value, height_value


@dataclass(frozen=True)
class WalkabilityMask:
    rows: int
    cols: int
    walkable: list[bool]

    def get(self, row: int, col: int) -> bool:
        return self.walkable[row * self.cols + col]


def _draw_line(
    mask: _BoolArray, x0: float, y0: float, x1: float, y1: float, downscale: int
) -> None:
    height, width = mask.shape
    x, y = round(x0 / downscale), round(y0 / downscale)
    x_end, y_end = round(x1 / downscale), round(y1 / downscale)
    dx = abs(x_end - x)
    sx = 1 if x < x_end else -1
    dy = -abs(y_end - y)
    sy = 1 if y < y_end else -1
    err = dx + dy
    while True:
        if 0 <= x < width and 0 <= y < height:
            mask[y, x] = True
        if x == x_end and y == y_end:
            break
        twice = 2 * err
        if twice >= dy:
            err += dy
            x += sx
        if twice <= dx:
            err += dx
            y += sy


def _cubic_segments(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 16,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    points: list[tuple[float, float]] = []
    for index in range(steps + 1):
        t = index / steps
        mt = 1.0 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return list(itertools.pairwise(points))


def _rasterize_path(mask: _BoolArray, d: str, downscale: int) -> None:
    tokens: list[tuple[str, str | float]] = []
    index = 0
    length = len(d)
    while index < length:
        char = d[index]
        if char in " \t\r\n,":
            index += 1
        elif char.isalpha():
            tokens.append(("cmd", char))
            index += 1
        else:
            match = _NUM.match(d, index)
            if match:
                tokens.append(("num", float(match.group(0))))
                index = match.end()
            else:
                index += 1

    commands: list[tuple[str, list[float]]] = []
    current: str | None = None
    for kind, value in tokens:
        if kind == "cmd":
            assert isinstance(value, str)
            current = value
            commands.append((value, []))
        elif current is not None and commands:
            assert isinstance(value, float)
            commands[-1][1].append(value)

    x = 0.0
    y = 0.0
    sub_start = (0.0, 0.0)
    previous: tuple[str, bool] | None = None
    control: tuple[float, float] | None = None

    def absolute(rel: bool, value: float) -> float:
        return value + (x if rel else 0.0)

    for cmd, args in commands:
        lowered = cmd.lower()
        rel = cmd.islower()
        pos = 0
        arg_count = len(args)
        if lowered == "m":
            first = True
            while pos < arg_count - 1:
                nx = args[pos] + (x if rel and not first else 0.0)
                ny = args[pos + 1] + (y if rel and not first else 0.0)
                if first:
                    x, y = nx, ny
                    sub_start = (x, y)
                    previous = ("m", rel)
                else:
                    _draw_line(mask, x, y, nx, ny, downscale)
                    x, y = nx, ny
                    previous = ("l", rel)
                first = False
                pos += 2
        elif lowered == "l":
            while pos < arg_count - 1:
                nx = absolute(rel, args[pos])
                ny = absolute(rel, args[pos + 1])
                _draw_line(mask, x, y, nx, ny, downscale)
                x, y = nx, ny
                pos += 2
            previous = ("l", rel)
        elif lowered == "h":
            while pos < arg_count:
                nx = absolute(rel, args[pos])
                _draw_line(mask, x, y, nx, y, downscale)
                x = nx
                pos += 1
            previous = ("h", rel)
        elif lowered == "v":
            while pos < arg_count:
                ny = absolute(rel, args[pos])
                _draw_line(mask, x, y, x, ny, downscale)
                y = ny
                pos += 1
            previous = ("v", rel)
        elif lowered == "c":
            while pos < arg_count - 5:
                c1 = (absolute(rel, args[pos]), absolute(rel, args[pos + 1]))
                c2 = (absolute(rel, args[pos + 2]), absolute(rel, args[pos + 3]))
                end = (absolute(rel, args[pos + 4]), absolute(rel, args[pos + 5]))
                for start, stop in _cubic_segments((x, y), c1, c2, end):
                    _draw_line(mask, start[0], start[1], stop[0], stop[1], downscale)
                x, y = end
                control = c2
                previous = ("c", rel)
                pos += 6
        elif lowered == "s":
            while pos < arg_count - 3:
                if (
                    previous is not None
                    and previous[0] in ("c", "s")
                    and previous[1] == rel
                    and control is not None
                ):
                    c1 = (2 * x - control[0], 2 * y - control[1])
                else:
                    c1 = (x, y)
                c2 = (absolute(rel, args[pos]), absolute(rel, args[pos + 1]))
                end = (absolute(rel, args[pos + 2]), absolute(rel, args[pos + 3]))
                for start, stop in _cubic_segments((x, y), c1, c2, end):
                    _draw_line(mask, start[0], start[1], stop[0], stop[1], downscale)
                x, y = end
                control = c2
                previous = ("s", rel)
                pos += 4
        elif lowered == "z":
            _draw_line(mask, x, y, sub_start[0], sub_start[1], downscale)
            x, y = sub_start
            previous = None


def _fill_rect(
    mask: _BoolArray,
    x: float,
    y: float,
    rect_width: float,
    rect_height: float,
    downscale: int,
) -> None:
    height, width = mask.shape
    x0 = max(0, int(x / downscale))
    y0 = max(0, int(y / downscale))
    x1 = min(width, math.ceil((x + rect_width) / downscale))
    y1 = min(height, math.ceil((y + rect_height) / downscale))
    mask[y0:y1, x0:x1] = True


def _dilate(mask: _BoolArray) -> _BoolArray:
    dilated = mask.copy()
    dilated[1:, :] |= mask[:-1, :]
    dilated[:-1, :] |= mask[1:, :]
    dilated[:, 1:] |= mask[:, :-1]
    dilated[:, :-1] |= mask[:, 1:]
    return dilated


def _obstacle_bbox(obstacle: _BoolArray) -> tuple[int, int, int, int] | None:
    rows = np.any(obstacle, axis=1)
    if not rows.any():
        return None
    cols = np.any(obstacle, axis=0)
    row_min = int(np.argmax(rows))
    row_max = int(rows.shape[0] - 1 - np.argmax(rows[::-1]))
    col_min = int(np.argmax(cols))
    col_max = int(cols.shape[0] - 1 - np.argmax(cols[::-1]))
    return row_min, row_max, col_min, col_max


def compute_walkability(
    svg_bytes: bytes,
    width: int,
    height: int,
    cell_size: int,
    downscale: int = 4,
) -> WalkabilityMask:
    if width <= 0 or height <= 0:
        raise DomainValidationError("FloorPlan width and height must be positive.")
    if cell_size <= 0:
        raise DomainValidationError("Cell size must be positive.")
    if downscale <= 0:
        raise DomainValidationError("downscale must be positive.")

    try:
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as exc:
        raise DomainValidationError("Could not parse SVG floor plan.") from exc

    coarse_width = math.ceil(width / downscale)
    coarse_height = math.ceil(height / downscale)
    obstacle = np.zeros((coarse_height, coarse_width), dtype=bool)

    for element in root.iter():
        tag = _local(element.tag)
        if tag == "rect":
            x = _parse_float(element.get("x"), 0.0)
            y = _parse_float(element.get("y"), 0.0)
            rect_width = _parse_float(element.get("width"), 0.0)
            rect_height = _parse_float(element.get("height"), 0.0)
            fill = element.get("fill")
            stroke = element.get("stroke")
            if fill is not None and fill != "none" and not _is_white(fill):
                _fill_rect(obstacle, x, y, rect_width, rect_height, downscale)
            if stroke is not None and stroke != "none" and not _is_white(stroke):
                _draw_line(mask=obstacle, x0=x, y0=y, x1=x + rect_width, y1=y, downscale=downscale)
                _draw_line(
                    mask=obstacle,
                    x0=x,
                    y0=y + rect_height,
                    x1=x + rect_width,
                    y1=y + rect_height,
                    downscale=downscale,
                )
                _draw_line(mask=obstacle, x0=x, y0=y, x1=x, y1=y + rect_height, downscale=downscale)
                _draw_line(
                    mask=obstacle,
                    x0=x + rect_width,
                    y0=y,
                    x1=x + rect_width,
                    y1=y + rect_height,
                    downscale=downscale,
                )
        elif tag == "path":
            d = element.get("d")
            stroke = element.get("stroke")
            if d and stroke is not None and stroke != "none" and not _is_white(stroke):
                _rasterize_path(obstacle, d, downscale)

    bbox = _obstacle_bbox(obstacle)
    obstacle = _dilate(obstacle)

    rows = math.ceil(height / cell_size)
    cols = math.ceil(width / cell_size)
    step = cell_size / downscale
    walkable: list[bool] = []
    for row in range(rows):
        y0 = min(coarse_height, int(row * step))
        y1 = min(coarse_height, int((row + 1) * step))
        for col in range(cols):
            x0 = min(coarse_width, int(col * step))
            x1 = min(coarse_width, int((col + 1) * step))
            exterior = (
                bbox is None or x1 <= bbox[2] or x0 > bbox[3] or y1 <= bbox[0] or y0 > bbox[1]
            )
            blocked = exterior or bool(obstacle[y0:y1, x0:x1].any())
            walkable.append(not blocked)

    return WalkabilityMask(rows=rows, cols=cols, walkable=walkable)
