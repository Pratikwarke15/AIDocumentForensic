from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import cv2

def extract_compression_features(image_np: np.ndarray, 
                                 output_dir: Path, 
                                 prefix: str) -> Tuple[Dict[str, float], str]:
    """
    Analyzes JPEG block boundary artifacts (8x8 DCT grid) and frequency energy.
    Returns:
    - Dict of compression features (blockiness, DCT energy ratio, quality estimate)
    - Path to compression error map image
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if image_np.ndim == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY).astype(np.float32)
    else:
        gray = image_np.copy().astype(np.float32)

    h, w = gray.shape

    # 1. 8x8 Blockiness Metric
    # Evaluate pixel difference across block boundaries vs within-block differences
    diff_h = np.abs(gray[1:, :] - gray[:-1, :])
    diff_w = np.abs(gray[:, 1:] - gray[:, :-1])

    # Boundary differences (every 8th line)
    boundary_h = diff_h[7::8, :]
    internal_h = np.delete(diff_h, slice(7, None, 8), axis=0)

    boundary_w = diff_w[:, 7::8]
    internal_w = np.delete(diff_w, slice(7, None, 8), axis=1)

    mean_boundary = float((np.mean(boundary_h) + np.mean(boundary_w)) / 2.0) if boundary_h.size > 0 and boundary_w.size > 0 else 0.0
    mean_internal = float((np.mean(internal_h) + np.mean(internal_w)) / 2.0) if internal_h.size > 0 and internal_w.size > 0 else 1.0

    blockiness_score = float(mean_boundary / (mean_internal + 1e-5))

    # 2. DCT Frequency Energy Distribution
    # Compute 2D DCT on 8x8 blocks cropped to multiple of 8
    crop_h = (h // 8) * 8
    crop_w = (w // 8) * 8
    cropped = gray[:crop_h, :crop_w]

    high_freq_energies = []
    total_energies = []
    block_map = np.zeros((crop_h, crop_w), dtype=np.float32)

    for r in range(0, crop_h, 8):
        for c in range(0, crop_w, 8):
            block = cropped[r:r+8, c:c+8]
            dct_block = cv2.dct(block)
            
            # Energy calculation
            total_energy = np.sum(dct_block ** 2)
            # High frequency is bottom-right triangle of 8x8 DCT
            mask = np.triu(np.ones((8, 8), dtype=bool), k=4)
            hf_energy = np.sum((dct_block ** 2)[mask])
            
            hf_ratio = float(hf_energy / (total_energy + 1e-5))
            high_freq_energies.append(hf_ratio)
            total_energies.append(total_energy)
            block_map[r:r+8, c:c+8] = hf_ratio

    mean_dct_energy_ratio = float(np.mean(high_freq_energies)) if high_freq_energies else 0.0

    # 3. Estimated JPEG Quality (heuristic based on boundary & high freq ratio)
    # High compression (low Q) creates high blockiness (> 1.25) and low HF ratio (< 0.02)
    # High quality (Q > 90) has low blockiness (< 1.05) and higher HF preservation
    quality_estimate = float(np.clip(100.0 - (blockiness_score - 1.0) * 80.0, 30.0, 99.0))

    # Generate visual compression artifact map
    if np.max(block_map) > 0:
        norm_block_map = (block_map / np.max(block_map) * 255.0).astype(np.uint8)
    else:
        norm_block_map = np.zeros((crop_h, crop_w), dtype=np.uint8)

    colored_comp_map = cv2.applyColorMap(norm_block_map, cv2.COLORMAP_MAGMA)
    comp_map_path = output_dir / f"{prefix}_compression_map.jpg"
    cv2.imwrite(str(comp_map_path), colored_comp_map)

    # Calculate compression severity & normalized anomaly score
    # Low blockiness (< 1.0) is normal for high-quality scans, PNGs, and rasterized PDFs.
    # Elevated blockiness (> 1.25) indicates heavier compression or re-saving.
    if blockiness_score <= 1.22:
        comp_norm_score = round(max((blockiness_score - 1.0) * 0.4, 0.0), 3)
        comp_severity = 'NORMAL'
    elif blockiness_score <= 1.38:
        comp_norm_score = round(0.25 + (blockiness_score - 1.22) * 1.5, 3)
        comp_severity = 'LOW_ANOMALY'
    elif blockiness_score <= 1.58:
        comp_norm_score = round(0.50 + (blockiness_score - 1.38) * 1.2, 3)
        comp_severity = 'MODERATE_ANOMALY'
    else:
        comp_norm_score = round(min(0.75 + (blockiness_score - 1.58) * 0.5, 1.0), 3)
        comp_severity = 'HIGH_ANOMALY'

    features = {
        'jpeg_quality_estimate': quality_estimate,
        'compression_blockiness_score': blockiness_score,
        'dct_energy_ratio': mean_dct_energy_ratio,
        'compression_normalized_score': comp_norm_score,
        'compression_severity': comp_severity
    }

    return features, str(comp_map_path)
