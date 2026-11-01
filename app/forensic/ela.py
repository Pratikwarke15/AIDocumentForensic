import io
import os
from pathlib import Path
from typing import Dict, Any, Tuple, List
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import cv2

def compute_ela(image_pil: Image.Image, quality: int = 95, scale_factor: float = 15.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes Error Level Analysis difference.
    Recompresses at quality factor Q (default 95).
    Returns:
    - Raw difference array (RGB, float/uint8)
    - Amplified difference array (RGB, uint8)
    """
    # 1. Save original to in-memory buffer as JPEG at target quality
    buffer = io.BytesIO()
    image_pil.save(buffer, 'JPEG', quality=quality)
    buffer.seek(0)
    recompressed_pil = Image.open(buffer)

    # 2. Pixel-wise difference
    diff_pil = ImageChops.difference(image_pil, recompressed_pil)
    diff_np = np.array(diff_pil, dtype=np.float32)

    # 3. Amplify difference
    amplified_np = np.clip(diff_np * scale_factor, 0, 255).astype(np.uint8)
    return diff_np.astype(np.uint8), amplified_np

def generate_ela_artifacts(image_np: np.ndarray, 
                           image_pil: Image.Image, 
                           output_dir: Path, 
                           prefix: str,
                           quality: int = 95, 
                           scale_factor: float = 15.0,
                           threshold_val: int = 25) -> Dict[str, Any]:
    """
    Executes ELA pipeline and saves:
    - ELA Color Heatmap
    - Binary Tamper Mask
    - Highlighted Suspicious Regions Overlay
    
    Returns paths and computed localization metrics.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    raw_diff, amplified_diff = compute_ela(image_pil, quality=quality, scale_factor=scale_factor)
    
    # 1. Grayscale intensity
    gray_diff = cv2.cvtColor(amplified_diff, cv2.COLOR_RGB2GRAY)
    
    # Apply slight Gaussian blur to smooth high-frequency noise
    smoothed_diff = cv2.GaussianBlur(gray_diff, (3, 3), 0)
    
    # 2. ELA Heatmap (Jet color map)
    heatmap_bgr = cv2.applyColorMap(smoothed_diff, cv2.COLORMAP_JET)
    heatmap_path = output_dir / f"{prefix}_ela_heatmap.jpg"
    cv2.imwrite(str(heatmap_path), heatmap_bgr)
    
    # 3. Binary Tamper Mask with Adaptive Thresholding
    # Text edges naturally have higher ELA response. We compute an adaptive threshold
    # that accounts for the document's baseline error distribution.
    diff_p75 = float(np.percentile(smoothed_diff, 75))
    diff_p90 = float(np.percentile(smoothed_diff, 90))
    # Threshold must significantly exceed typical text-edge recompression level
    effective_thresh = max(threshold_val, int(diff_p90 * 1.35), int(diff_p75 + 18))
    effective_thresh = min(effective_thresh, 180)  # Bound to sensible maximum
    
    _, binary_mask = cv2.threshold(smoothed_diff, effective_thresh, 255, cv2.THRESH_BINARY)
    
    # Text-preserving horizontal closing to bridge adjacent characters in modified words/dates
    # without destroying 1-2px thin text strokes
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    closed_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, h_kernel)
    
    H, W = binary_mask.shape
    total_pixels = H * W
    
    # Meaningful minimum component area: filters out tiny isolated pixel dust
    # while preserving altered letters, numbers, and dates
    min_component_area = max(40, int(total_pixels * 0.00008))
    
    # Connected components analysis: count actual anomalous pixels in the thresholded ELA mask
    # rather than enclosed polygon area of thin borders / wireframes
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(closed_mask, connectivity=8)
    suspicious_regions = []
    tamper_mask_final = np.zeros_like(closed_mask)
    
    # 4. Highlight Suspicious Regions onto original image
    highlighted_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    overlay = highlighted_bgr.copy()
    
    for i in range(1, num_labels):
        area = float(stats[i, cv2.CC_STAT_AREA])
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        
        # Filter outer page frames and thin gridline dividers (normal document structure)
        is_outer_border = (x <= 15 or y <= 15 or (x + w) >= W - 15 or (y + h) >= H - 15) and (w > 0.60 * W or h > 0.60 * H)
        is_thin_divider = (w > 25 and h <= 3 and w / max(h, 1) > 15) or (h > 25 and w <= 3 and h / max(w, 1) > 15)
        is_hollow_box = (w * h > 0.20 * total_pixels and area / max(w * h, 1) < 0.04)
        
        if is_outer_border or is_thin_divider or is_hollow_box:
            continue
            
        if area >= min_component_area:
            suspicious_regions.append({'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h), 'area': float(area)})
            tamper_mask_final[labels == i] = 255
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 255), -1)
            cv2.rectangle(highlighted_bgr, (x, y), (x + w, y + h), (0, 0, 255), 2)
    
    mask_path = output_dir / f"{prefix}_tamper_mask.png"
    cv2.imwrite(str(mask_path), tamper_mask_final)
    
    # Blend overlay with 35% opacity so modified text is clearly visible beneath highlight
    highlighted_final = cv2.addWeighted(overlay, 0.35, highlighted_bgr, 0.65, 0)
    highlight_path = output_dir / f"{prefix}_highlighted.jpg"
    cv2.imwrite(str(highlight_path), highlighted_final)
    
    tamper_pixels = int(np.count_nonzero(tamper_mask_final))
    tamper_ratio = float(tamper_pixels / total_pixels) if total_pixels > 0 else 0.0
    num_components = len(suspicious_regions)
    
    # Calculate Normalized ELA Anomaly Score (0.0 to 1.0) and Severity Level
    # In uniform compression (e.g. Q70/Q80 scan), small edge contours are scattered document-wide.
    # In genuine digital splicing, a concentrated, sizeable component exists (e.g. forged box, altered text/amount, pasted seal).
    max_comp_area = max([r['area'] for r in suspicious_regions], default=0.0)
    max_comp_ratio = float(max_comp_area / total_pixels) if total_pixels > 0 else 0.0
    
    # Check if artifacts are scattered uniform recompression vs concentrated splice
    is_uniform_recompression = (max_comp_ratio < 0.020 and tamper_ratio < 0.070)
    
    if num_components == 0 or (tamper_ratio < 0.025 and max_comp_ratio < 0.020):
        ela_norm_score = round(tamper_ratio * 4.0, 3)
        ela_severity = 'NORMAL'
    elif is_uniform_recompression or (tamper_ratio < 0.055 and max_comp_ratio < 0.035):
        # Uniform minor edge artifacts typical for scanned, photographed, or recompressed authentic documents
        ela_norm_score = round(min(0.15 + tamper_ratio * 3.5, 0.35), 3)
        ela_severity = 'LOW_ANOMALY'
    elif tamper_ratio < 0.090 or max_comp_ratio < 0.060:
        # Noticeable variation, warrants review
        ela_norm_score = round(min(0.40 + tamper_ratio * 3.0, 0.65), 3)
        ela_severity = 'MODERATE_ANOMALY'
    else:
        # Large concentrated component with high overall tamper ratio: genuine multi-compression splicing
        ela_norm_score = round(min(0.70 + tamper_ratio * 3.0, 1.0), 3)
        ela_severity = 'HIGH_ANOMALY'
    
    return {
        'ela_heatmap_path': str(heatmap_path),
        'tamper_mask_path': str(mask_path),
        'highlighted_path': str(highlight_path),
        'tamper_ratio': tamper_ratio,
        'tamper_pixel_count': tamper_pixels,
        'total_pixels': total_pixels,
        'suspicious_regions': suspicious_regions,
        'num_components': num_components,
        'raw_diff': raw_diff,
        'gray_diff': gray_diff,
        'cleaned_mask': tamper_mask_final,
        'effective_threshold': effective_thresh,
        'ela_normalized_score': ela_norm_score,
        'ela_severity': ela_severity
    }
