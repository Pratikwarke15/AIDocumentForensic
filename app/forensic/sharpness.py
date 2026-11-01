from typing import Dict, Any, Tuple
import numpy as np
import cv2

def extract_sharpness_features(image_np: np.ndarray, grid_size: int = 8) -> Dict[str, float]:
    """
    Measures sharpness consistency using Laplacian variance across the image and grid patches.
    Also extracts Canny edge density.
    """
    if image_np.ndim == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np.copy()

    # 1. Global Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    global_sharpness = float(np.var(laplacian))

    # 2. Local patch sharpness disparity
    h, w = gray.shape
    cell_h = h // grid_size
    cell_w = w // grid_size
    patch_sharpness = []

    for i in range(grid_size):
        for j in range(grid_size):
            y1 = i * cell_h
            y2 = (i + 1) * cell_h if i < grid_size - 1 else h
            x1 = j * cell_w
            x2 = (j + 1) * cell_w if j < grid_size - 1 else w

            patch_lap = cv2.Laplacian(gray[y1:y2, x1:x2], cv2.CV_64F)
            patch_sharpness.append(float(np.var(patch_lap)))

    p_np = np.array(patch_sharpness)
    min_sharp = float(np.min(p_np))
    max_sharp = float(np.max(p_np))
    sharpness_disparity = float(max_sharp / (min_sharp + 1e-4))

    # 3. Edge density via Canny
    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.count_nonzero(edges) / (h * w))

    return {
        'sharpness_laplacian_var': global_sharpness,
        'sharpness_disparity_ratio': sharpness_disparity,
        'edge_density': edge_density
    }
