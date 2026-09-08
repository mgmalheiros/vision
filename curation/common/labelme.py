from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

def load_labelme(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or not isinstance(value.get("shapes"), list):
        raise ValueError(f"Not a LabelMe annotation: {path}")
    return value

def _outside_amount(x: float, y: float, width: int, height: int) -> float:
    return max(0.0, -x, -y, x - width, y - height)

def _polygon_area(points: np.ndarray) -> float:
    x = points[:, 0]
    y = points[:, 1]
    return abs(float(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))) / 2

def normalize_labelme_shapes(
    annotation: Mapping[str, Any],
    *,
    relative_path: str,
    annotation_relative_path: str,
    image_width: int,
    image_height: int,
    boundary_tolerance_px: float = 2.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize LabelMe circle/polygon geometry and report review findings."""
    records: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    def finding(index: int, label: str, shape_type: str, severity: str, kind: str, detail: str) -> None:
        findings.append(
            {
                "relative_path": relative_path,
                "annotation_relative_path": annotation_relative_path,
                "shape_index": index,
                "label": label,
                "shape_type": shape_type,
                "severity": severity,
                "finding_type": kind,
                "detail": detail,
            }
        )

    for index, shape in enumerate(annotation.get("shapes", [])):
        label = str(shape.get("label", "") or "").strip()
        shape_type = str(shape.get("shape_type", "") or "").strip().lower()
        points_raw = shape.get("points") or []
        try:
            points = np.asarray(points_raw, dtype=float).reshape(-1, 2)
        except (TypeError, ValueError):
            points = np.empty((0, 2), dtype=float)

        record = {
            "annotation_id": f"{relative_path}::shape-{index}",
            "relative_path": relative_path,
            "annotation_relative_path": annotation_relative_path,
            "shape_index": index,
            "label": label,
            "shape_type": shape_type,
            "n_points": len(points),
            "points_json": json.dumps(points_raw, ensure_ascii=False),
            "image_width": image_width,
            "image_height": image_height,
            "bbox_xmin": np.nan,
            "bbox_ymin": np.nan,
            "bbox_xmax": np.nan,
            "bbox_ymax": np.nan,
            "bbox_width": np.nan,
            "bbox_height": np.nan,
            "shape_area": np.nan,
            "bbox_area": np.nan,
            "bbox_area_ratio": np.nan,
            "max_point_boundary_excess_px": np.nan,
            "circle_extends_beyond_frame": False,
        }

        if not label:
            finding(index, label, shape_type, "error", "empty_label", "Shape has an empty label.")
        if shape_type not in {"circle", "polygon"}:
            finding(index, label, shape_type, "warning", "unexpected_shape_type", f"Unexpected LabelMe shape type: {shape_type!r}.")

        max_excess = max(
            (_outside_amount(x, y, image_width, image_height) for x, y in points),
            default=float("nan"),
        )
        record["max_point_boundary_excess_px"] = max_excess

        if shape_type == "circle":
            if len(points) < 2:
                finding(index, label, shape_type, "error", "invalid_circle_points", "Circle requires center and radius-defining point.")
            else:
                (cx, cy), (px, py) = points[:2]
                radius = float(np.hypot(px - cx, py - cy))
                xmin, ymin, xmax, ymax = cx - radius, cy - radius, cx + radius, cy + radius
                bbox_area = (2 * radius) ** 2
                record.update(
                    bbox_xmin=xmin,
                    bbox_ymin=ymin,
                    bbox_xmax=xmax,
                    bbox_ymax=ymax,
                    bbox_width=2 * radius,
                    bbox_height=2 * radius,
                    shape_area=math.pi * radius * radius,
                    bbox_area=bbox_area,
                    bbox_area_ratio=bbox_area / (image_width * image_height),
                    circle_extends_beyond_frame=bool(
                        xmin < 0 or ymin < 0 or xmax > image_width or ymax > image_height
                    ),
                )
                center_excess = _outside_amount(cx, cy, image_width, image_height)
                if center_excess > boundary_tolerance_px:
                    finding(index, label, shape_type, "error", "circle_center_outside_image", f"Circle center exceeds image boundary by {center_excess:.3f}px.")
                elif center_excess > 0:
                    finding(index, label, shape_type, "warning", "circle_center_near_boundary", f"Circle center is {center_excess:.3f}px outside the image, within tolerance.")
                if radius <= 0:
                    finding(index, label, shape_type, "error", "non_positive_circle_radius", "Circle radius is zero or negative.")

        elif shape_type == "polygon":
            if len(points) < 3:
                finding(index, label, shape_type, "error", "invalid_polygon_points", "Polygon requires at least three points.")
            else:
                xmin, ymin = points.min(axis=0)
                xmax, ymax = points.max(axis=0)
                area = _polygon_area(points)
                bbox_area = float((xmax - xmin) * (ymax - ymin))
                record.update(
                    bbox_xmin=float(xmin),
                    bbox_ymin=float(ymin),
                    bbox_xmax=float(xmax),
                    bbox_ymax=float(ymax),
                    bbox_width=float(xmax - xmin),
                    bbox_height=float(ymax - ymin),
                    shape_area=area,
                    bbox_area=bbox_area,
                    bbox_area_ratio=bbox_area / (image_width * image_height),
                )
                if max_excess > boundary_tolerance_px:
                    finding(index, label, shape_type, "error", "polygon_point_outside_image", f"A polygon point exceeds the image boundary by up to {max_excess:.3f}px.")
                elif max_excess > 0:
                    finding(index, label, shape_type, "warning", "polygon_point_near_boundary", f"A polygon point exceeds the image boundary by {max_excess:.3f}px, within tolerance.")
                if area <= 0:
                    finding(index, label, shape_type, "error", "non_positive_polygon_area", "Polygon area is zero.")

        records.append(record)
    return records, findings

def crop_bbox(image: Any, row: Mapping[str, Any], padding_fraction: float = 0.0) -> Any:
    """Crop and clamp a bounding box; return None for an empty crop."""
    x1, y1 = float(row["bbox_xmin"]), float(row["bbox_ymin"])
    x2, y2 = float(row["bbox_xmax"]), float(row["bbox_ymax"])
    pad_x = (x2 - x1) * padding_fraction
    pad_y = (y2 - y1) * padding_fraction
    x1 = max(0, math.floor(x1 - pad_x))
    y1 = max(0, math.floor(y1 - pad_y))
    x2 = min(image.width, math.ceil(x2 + pad_x))
    y2 = min(image.height, math.ceil(y2 + pad_y))
    if x2 <= x1 or y2 <= y1:
        return None
    return image.crop((x1, y1, x2, y2)).copy()