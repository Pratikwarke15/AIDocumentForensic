import numpy as np
from typing import Dict, Any, List

FEATURE_NAMES = [
    'ela_mean',
    'ela_std',
    'ela_var',
    'ela_max',
    'ela_median',
    'ela_p75',
    'ela_p90',
    'ela_p95',
    'ela_p99',
    'ela_tamper_ratio',
    'ela_num_components',
    'ela_max_component_area_ratio',
    'ela_component_density',
    'ela_skewness',
    'ela_kurtosis',
    'noise_variance_mean',
    'noise_variance_std',
    'noise_disparity_ratio',
    'jpeg_quality_estimate',
    'compression_blockiness_score',
    'dct_energy_ratio',
    'sharpness_laplacian_var',
    'sharpness_disparity_ratio',
    'edge_density',
    'copymove_match_count',
    'color_channel_disparity',
    'metadata_editing_software_flag',
    'metadata_date_inconsistency',
    'layout_text_alignment_variance',
    'ocr_confidence_variance',
    'ocr_suspicious_box_count'
]

def calculate_statistical_moments(data: np.ndarray) -> Dict[str, float]:
    flat = data.flatten().astype(np.float64)
    if len(flat) == 0:
        return {'mean': 0.0, 'std': 0.0, 'var': 0.0, 'skew': 0.0, 'kurt': 0.0}
    
    mean = float(np.mean(flat))
    std = float(np.std(flat))
    var = float(np.var(flat))
    
    # Skewness and Kurtosis
    if std > 1e-6:
        skew = float(np.mean(((flat - mean) / std) ** 3))
        kurt = float(np.mean(((flat - mean) / std) ** 4) - 3.0)  # Excess kurtosis
    else:
        skew = 0.0
        kurt = 0.0
        
    return {
        'mean': mean,
        'std': std,
        'var': var,
        'skew': skew,
        'kurt': kurt
    }

def extract_ela_features(gray_diff: np.ndarray, raw_diff: np.ndarray, ela_meta: Dict[str, Any]) -> Dict[str, float]:
    """
    Extracts numerical statistical and localization features from ELA difference images.
    """
    moments = calculate_statistical_moments(gray_diff)
    flat = gray_diff.flatten()
    
    p75, p90, p95, p99 = np.percentile(flat, [75, 90, 95, 99])
    
    # Component statistics
    suspicious_regions = ela_meta.get('suspicious_regions', [])
    num_components = len(suspicious_regions)
    total_pixels = ela_meta.get('total_pixels', gray_diff.size)
    
    if num_components > 0:
        max_area = max(r['area'] for r in suspicious_regions)
        max_component_area_ratio = float(max_area / total_pixels)
        sum_bbox_area = sum(r['w'] * r['h'] for r in suspicious_regions)
        component_density = float(ela_meta.get('tamper_pixel_count', 0) / max(sum_bbox_area, 1))
    else:
        max_component_area_ratio = 0.0
        component_density = 0.0
        
    # Color channel disparity in ELA
    if raw_diff.ndim == 3 and raw_diff.shape[2] == 3:
        r_var = np.var(raw_diff[:, :, 0])
        g_var = np.var(raw_diff[:, :, 1])
        b_var = np.var(raw_diff[:, :, 2])
        color_channel_disparity = float(max(r_var, g_var, b_var) - min(r_var, g_var, b_var))
    else:
        color_channel_disparity = 0.0

    return {
        'ela_mean': moments['mean'],
        'ela_std': moments['std'],
        'ela_var': moments['var'],
        'ela_max': float(np.max(flat)),
        'ela_median': float(np.median(flat)),
        'ela_p75': float(p75),
        'ela_p90': float(p90),
        'ela_p95': float(p95),
        'ela_p99': float(p99),
        'ela_tamper_ratio': float(ela_meta.get('tamper_ratio', 0.0)),
        'ela_num_components': float(num_components),
        'ela_max_component_area_ratio': max_component_area_ratio,
        'ela_component_density': component_density,
        'ela_skewness': moments['skew'],
        'ela_kurtosis': moments['kurt'],
        'color_channel_disparity': color_channel_disparity
    }

def compile_feature_vector(ela_feats: Dict[str, float],
                           noise_feats: Dict[str, float],
                           comp_feats: Dict[str, float],
                           sharp_feats: Dict[str, float],
                           copy_feats: Dict[str, float],
                           meta_feats: Dict[str, float],
                           layout_feats: Dict[str, float]) -> Dict[str, float]:
    """
    Combines all individual signal features into a complete dictionary
    matching FEATURE_NAMES.
    """
    full_dict = {}
    full_dict.update(ela_feats)
    full_dict.update(noise_feats)
    full_dict.update(comp_feats)
    full_dict.update(sharp_feats)
    full_dict.update(copy_feats)
    full_dict.update(meta_feats)
    full_dict.update(layout_feats)
    
    # Ensure all features exist with fallback 0.0
    return {k: float(full_dict.get(k, 0.0)) for k in FEATURE_NAMES}

def feature_dict_to_array(feature_dict: Dict[str, float]) -> np.ndarray:
    """
    Returns 1D numpy array ordered exactly according to FEATURE_NAMES.
    """
    return np.array([feature_dict.get(k, 0.0) for k in FEATURE_NAMES], dtype=np.float32)
