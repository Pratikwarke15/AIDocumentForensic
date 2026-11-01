from typing import Dict, Any, List, Tuple
import numpy as np
import cv2

def extract_copymove_features(image_np: np.ndarray, max_features: int = 2000) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    """
    Detects duplicated or cloned regions (copy-move forgery) using ORB keypoint matching
    and spatial distance clustering.
    Returns:
    - Dict with 'copymove_match_count'
    - List of suspicious duplicate coordinate pairs
    """
    if image_np.ndim == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np.copy()

    orb = cv2.ORB_create(nfeatures=max_features)
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if descriptors is None or len(keypoints) < 10:
        return {'copymove_match_count': 0.0}, []

    # Match descriptors to find similar features across different parts of the same image
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(descriptors, descriptors, k=10)

    duplicate_pairs = []
    min_spatial_dist = 60.0  # Must be at least 60px apart to avoid self-match / near neighbor

    for i, m_list in enumerate(matches):
        pt1 = keypoints[i].pt
        for m in m_list[1:]:
            pt2 = keypoints[m.trainIdx].pt
            spatial_dist = float(np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1]))
            if spatial_dist > min_spatial_dist:
                if m.distance <= 32:
                    duplicate_pairs.append({
                        'pt1': (float(pt1[0]), float(pt1[1])),
                        'pt2': (float(pt2[0]), float(pt2[1])),
                        'distance': float(m.distance),
                        'spatial_dist': spatial_dist
                    })
                    break

    # Group duplicate pairs by translation vector to find coherent transform candidates
    # In authentic text documents, repeated letters ("e", "t", "a") produce micro-matches
    # but lack a single coherent rigid displacement across a dense localized region.
    # True copy-move forgery involves a cohesive 2D cluster (e.g. cloned seal, signature,
    # or forged text box) where multiple keypoints are co-located in BOTH source and target regions.
    genuine_clone_clusters = []
    
    if len(duplicate_pairs) >= 6:
        pts1 = np.array([p['pt1'] for p in duplicate_pairs])
        pts2 = np.array([p['pt2'] for p in duplicate_pairs])
        vectors = pts2 - pts1
        
        visited = np.zeros(len(vectors), dtype=bool)
        for i in range(len(vectors)):
            if visited[i]:
                continue
            diffs = np.linalg.norm(vectors - vectors[i], axis=1)
            group_indices = np.where(diffs < 16.0)[0]
            
            if len(group_indices) >= 6:  # Coherent displacement cluster
                dx = abs(vectors[i][0])
                dy = abs(vectors[i][1])
                
                # Require significant spatial displacement (at least 75px apart)
                if np.hypot(dx, dy) < 75.0:
                    continue

                # Filter tabular line repeats: if dy matches standard document line height intervals
                is_line_repeat = False
                for line_h in [44.4, 88.9, 133.3, 177.8, 222.2, 266.7]:
                    if abs(dy - line_h) < 6.5:
                        is_line_repeat = True
                        break
                if is_line_repeat:
                    continue

                group_pts1 = pts1[group_indices]
                group_pts2 = pts2[group_indices]
                
                # Check affine geometric consistency with RANSAC
                M, inliers = cv2.estimateAffinePartial2D(group_pts1, group_pts2, method=cv2.RANSAC, ransacReprojThreshold=3.0)
                inlier_count = int(np.sum(inliers)) if inliers is not None else 0
                
                sp1 = np.max(group_pts1, axis=0) - np.min(group_pts1, axis=0)
                sp2 = np.max(group_pts2, axis=0) - np.min(group_pts2, axis=0)
                
                # Must be a 2D patch (both width and height >= 12px), ruling out 1D single-line font matches
                if sp1[0] < 12.0 or sp1[1] < 12.0 or sp2[0] < 12.0 or sp2[1] < 12.0:
                    continue

                # Must be localized within a reasonable cloned element bounding size (seal, signature, forged text box)
                # Multi-row table columns span > 110px vertically, so max_spread <= 110 filters them out
                max_spread = max(sp1[0], sp1[1], sp2[0], sp2[1])
                if max_spread < 16.0 or max_spread > 110.0:
                    continue

                # Filter repeated table columns / grid dividers (purely horizontal or vertical shift with large orthogonal span)
                if abs(vectors[i][1]) < 6.0 and (sp1[1] > 60.0 or sp2[1] > 60.0):
                    continue
                if abs(vectors[i][0]) < 6.0 and (sp1[0] > 60.0 or sp2[0] > 60.0):
                    continue

                # Require robust inlier count (>= 8)
                if inlier_count >= 8:
                    genuine_clone_clusters.append({
                        'vector': (float(vectors[i][0]), float(vectors[i][1])),
                        'match_count': inlier_count,
                        'spread1': [float(s) for s in sp1],
                        'spread2': [float(s) for s in sp2],
                        'source_center': [float(c) for c in np.mean(group_pts1, axis=0)],
                        'target_center': [float(c) for c in np.mean(group_pts2, axis=0)]
                    })
                    visited[group_indices] = True

    # Filter reverse symmetric duplicate clusters (source<->target)
    unique_clusters = []
    for c in genuine_clone_clusters:
        vx, vy = c['vector']
        if not any(abs(vx + uc['vector'][0]) < 10.0 and abs(vy + uc['vector'][1]) < 10.0 for uc in unique_clusters):
            unique_clusters.append(c)

    valid_cluster_count = len(unique_clusters)
    total_cloned_points = sum(c['match_count'] for c in unique_clusters)

    # Classify severity
    if valid_cluster_count == 0:
        copymove_norm_score = 0.0
        copymove_severity = 'NORMAL'
    elif valid_cluster_count == 1 and total_cloned_points < 12:
        copymove_norm_score = 0.50
        copymove_severity = 'MODERATE_ANOMALY'
    else:
        copymove_norm_score = 0.90
        copymove_severity = 'HIGH_ANOMALY'

    features = {
        'copymove_match_count': float(valid_cluster_count),
        'copymove_raw_pairs': float(len(duplicate_pairs)),
        'copymove_normalized_score': copymove_norm_score,
        'copymove_severity': copymove_severity,
        'copymove_clusters': unique_clusters
    }

    return features, duplicate_pairs
