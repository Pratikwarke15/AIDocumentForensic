from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import cv2

def extract_noise_features(image_np: np.ndarray, 
                           output_dir: Path, 
                           prefix: str, 
                           grid_size: int = 8) -> Tuple[Dict[str, float], str]:
    """
    Analyzes local noise inconsistency across the document.
    Calculates noise residual by subtracting median-filtered image from original.
    Evaluates variance across a grid of patches.
    Returns:
    - Dict of noise metrics
    - Path to visual noise map
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert to grayscale
    if image_np.ndim == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np.copy()

    # High-pass noise residual via median filter subtraction
    blurred = cv2.medianBlur(gray, 3)
    noise_residual = cv2.absdiff(gray, blurred).astype(np.float32)

    # In document forensics, high-contrast text characters and lines contaminate high-pass noise filters.
    # To measure authentic sensor/paper noise consistency, we mask out sharp structural edges.
    edges = cv2.Canny(gray, 30, 100)
    dilated_edges = cv2.dilate(edges, np.ones((5, 5), np.uint8))
    non_edge_mask = (dilated_edges == 0)

    h, w = gray.shape
    cell_h = h // grid_size
    cell_w = w // grid_size

    local_vars = []
    content_vars = []
    noise_map = np.zeros((h, w), dtype=np.float32)

    for i in range(grid_size):
        for j in range(grid_size):
            y1 = i * cell_h
            y2 = (i + 1) * cell_h if i < grid_size - 1 else h
            x1 = j * cell_w
            x2 = (j + 1) * cell_w if j < grid_size - 1 else w

            patch_residual = noise_residual[y1:y2, x1:x2]
            patch_mask = non_edge_mask[y1:y2, x1:x2]
            
            var = float(np.var(patch_residual))
            local_vars.append(var)
            noise_map[y1:y2, x1:x2] = var

            # Measure noise on non-edge paper background areas
            if np.sum(patch_mask) > 40:
                clean_patch_var = float(np.var(patch_residual[patch_mask]))
                content_vars.append(clean_patch_var)
            else:
                content_vars.append(var)

    local_vars_np = np.array(local_vars, dtype=np.float64)
    v_mean = float(np.mean(local_vars_np))
    v_std = float(np.std(local_vars_np))
    v_median = float(np.median(local_vars_np))
    v_max = float(np.max(local_vars_np))
    raw_disparity = float(v_max / (v_median + 1e-5))

    # Content-aware noise evaluation (filters out empty white margins)
    if len(content_vars) >= 4:
        c_np = np.array(content_vars, dtype=np.float64)
        c_mean = float(np.mean(c_np))
        c_std = float(np.std(c_np))
        noise_cv = float(c_std / (c_mean + 1e-5))
        c_p90 = float(np.percentile(c_np, 90))
        c_p10 = float(np.percentile(c_np, 10))
        content_disparity = float(c_p90 / max(c_p10, 0.5))
        c_median = float(np.median(c_np))
        c_max = float(np.max(c_np))
        outlier_disparity = float(c_max / max(c_median, 0.5))
    else:
        noise_cv = 0.15
        content_disparity = 1.0
        outlier_disparity = 1.0

    # Classify severity level based on content-area noise consistency
    # On typical document pages, white paper margins alongside text blocks naturally yield
    # a coefficient of variation around 1.0. Genuine splicing / alien noise injection produces CV > 2.2 or outlier > 16.0.
    if (c_std <= 2.0 or (c_p90 - c_p10 <= 5.0) or (noise_cv <= 1.25 and content_disparity <= 6.0)) and outlier_disparity <= 14.0:
        noise_norm_score = round(min(noise_cv * 0.15, 0.20), 3)
        noise_severity = 'NORMAL'
    elif (noise_cv <= 2.0 and content_disparity <= 12.0) and outlier_disparity <= 22.0:
        noise_norm_score = round(min(0.20 + (noise_cv - 1.25) * 0.25, 0.40), 3)
        noise_severity = 'LOW_ANOMALY'
    elif (noise_cv <= 3.20 and content_disparity <= 20.0) and outlier_disparity <= 35.0:
        noise_norm_score = round(min(0.40 + (noise_cv - 2.0) * 0.25, 0.70), 3)
        noise_severity = 'MODERATE_ANOMALY'
    else:
        noise_norm_score = round(min(0.70 + (noise_cv - 3.20) * 0.15, 1.0), 3)
        noise_severity = 'HIGH_ANOMALY'

    # Normalize noise map to 0-255 and apply colormap
    if np.max(noise_map) > 0:
        norm_map = (noise_map / np.max(noise_map) * 255.0).astype(np.uint8)
    else:
        norm_map = np.zeros((h, w), dtype=np.uint8)

    colored_noise_map = cv2.applyColorMap(norm_map, cv2.COLORMAP_VIRIDIS)
    noise_map_path = output_dir / f"{prefix}_noise_map.jpg"
    cv2.imwrite(str(noise_map_path), colored_noise_map)

    features = {
        'noise_variance_mean': v_mean,
        'noise_variance_std': v_std,
        'noise_disparity_ratio': raw_disparity
    }

    # Attach diagnostic metadata to return object
    features['noise_normalized_score'] = noise_norm_score
    features['noise_severity'] = noise_severity
    features['noise_cv'] = round(noise_cv, 3)

    return features, str(noise_map_path)
