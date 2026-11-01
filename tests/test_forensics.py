import os
import numpy as np
from PIL import Image
from pathlib import Path
from app.forensic.preprocessing import load_and_preprocess_image
from app.forensic.ela import generate_ela_artifacts
from app.forensic.features import extract_ela_features, compile_feature_vector, FEATURE_NAMES
from app.forensic.noise import extract_noise_features
from app.forensic.compression import extract_compression_features
from app.forensic.copymove import extract_copymove_features
from app.forensic.sharpness import extract_sharpness_features
from app.forensic.scoring import aggregate_forensic_evidence, combine_record_and_forensic_results

def test_preprocessing_and_ela(tmp_path):
    # Create test image
    test_img = Image.new('RGB', (1200, 900), color=(240, 240, 240))
    img_path = tmp_path / 'test_orig.jpg'
    test_img.save(img_path, 'JPEG', quality=95)

    img_np, img_pil, orig_size = load_and_preprocess_image(img_path, max_dimension=800)
    assert max(img_np.shape[0], img_np.shape[1]) <= 800
    assert orig_size == (1200, 900)

    # ELA Execution
    ela_res = generate_ela_artifacts(img_np, img_pil, tmp_path, 'test_prefix', quality=95, scale_factor=15.0)
    assert os.path.exists(ela_res['ela_heatmap_path'])
    assert os.path.exists(ela_res['tamper_mask_path'])
    assert os.path.exists(ela_res['highlighted_path'])
    assert 0.0 <= ela_res['tamper_ratio'] <= 1.0

def test_feature_vector_schema(tmp_path):
    test_img = Image.new('RGB', (400, 400), color=(200, 200, 200))
    img_np = np.array(test_img)
    prefix = 'feat_test'

    ela_res = generate_ela_artifacts(img_np, test_img, tmp_path, prefix)
    ela_feats = extract_ela_features(ela_res['gray_diff'], ela_res['raw_diff'], ela_res)
    noise_feats, _ = extract_noise_features(img_np, tmp_path, prefix)
    comp_feats, _ = extract_compression_features(img_np, tmp_path, prefix)
    copy_feats, _ = extract_copymove_features(img_np)
    sharp_feats = extract_sharpness_features(img_np)

    feats = compile_feature_vector(ela_feats, noise_feats, comp_feats, sharp_feats, copy_feats, {}, {})
    assert len(feats) == len(FEATURE_NAMES)
    for fn in FEATURE_NAMES:
        assert fn in feats
        assert isinstance(feats[fn], float)

def test_evidence_aggregator():
    # Test authentic case
    clean_features = {
        'ela_tamper_ratio': 0.005,
        'ela_num_components': 0,
        'noise_disparity_ratio': 1.2,
        'compression_blockiness_score': 1.05,
        'copymove_match_count': 0,
        'metadata_editing_software_flag': 0.0
    }
    agg = aggregate_forensic_evidence(
        rf_prediction=0,
        rf_probability=0.08,
        features=clean_features,
        metadata={},
        model_trained=True
    )
    assert agg['forensic_status'] == 'AUTHENTIC'
    assert agg['confidence'] >= 80.0

    # Test inconclusive / review required case (isolated anomaly)
    review_features = {
        'ela_tamper_ratio': 0.045,
        'ela_num_components': 3,
        'ela_severity': 'MODERATE_ANOMALY',
        'noise_disparity_ratio': 2.0,
        'noise_severity': 'NORMAL',
        'compression_blockiness_score': 1.05,
        'compression_severity': 'NORMAL',
        'copymove_match_count': 0,
        'copymove_severity': 'NORMAL',
        'metadata_editing_software_flag': 0.0,
        'metadata_severity': 'NORMAL'
    }
    agg_review = aggregate_forensic_evidence(
        rf_prediction=0,
        rf_probability=0.25,
        features=review_features,
        metadata={},
        model_trained=True
    )
    assert agg_review['forensic_status'] in ('AUTHENTIC', 'REVIEW REQUIRED')
    assert 'debug_info' in agg_review
    assert 'analysis_consistency' in agg_review
    assert 'composite_score' in agg_review

    # Test local registry decoupling
    rec_not_found_res = combine_record_and_forensic_results('RECORD NOT FOUND', 'AUTHENTIC')
    assert 'POTENTIAL DIGITAL TAMPERING' not in rec_not_found_res
    assert 'FORENSICALLY CONSISTENT' in rec_not_found_res
