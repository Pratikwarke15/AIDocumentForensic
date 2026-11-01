import os
import sys
import io
import random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import cv2

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.forensic.preprocessing import load_and_preprocess_image
from app.forensic.ela import generate_ela_artifacts
from app.forensic.features import extract_ela_features, compile_feature_vector
from app.forensic.noise import extract_noise_features
from app.forensic.compression import extract_compression_features
from app.forensic.copymove import extract_copymove_features
from app.forensic.sharpness import extract_sharpness_features
from app.forensic.metadata import extract_image_metadata
from app.forensic.ocr_layout import extract_ocr_and_layout_features
from app.forensic.scoring import aggregate_forensic_evidence, combine_record_and_forensic_results
from app.ml.model_manager import ModelManager
from scripts.prepare_dataset import create_synthetic_base_document

MODELS_DIR = BASE_DIR / 'models'
TEMP_DIR = BASE_DIR / 'storage' / 'condition_tests'
TEMP_DIR.mkdir(parents=True, exist_ok=True)

model_mgr = ModelManager(MODELS_DIR)

def run_forensic_pipeline(img_path: Path, prefix: str):
    img_np, img_pil, _ = load_and_preprocess_image(img_path, max_dimension=800)
    
    ela_res = generate_ela_artifacts(img_np, img_pil, TEMP_DIR, prefix, quality=95, scale_factor=15.0)
    ela_feats = extract_ela_features(ela_res['gray_diff'], ela_res['raw_diff'], ela_res)
    
    noise_feats, _ = extract_noise_features(img_np, TEMP_DIR, prefix)
    comp_feats, _ = extract_compression_features(img_np, TEMP_DIR, prefix)
    copy_feats, _ = extract_copymove_features(img_np)
    sharp_feats = extract_sharpness_features(img_np)
    raw_meta, meta_feats = extract_image_metadata(img_path)
    _, layout_feats = extract_ocr_and_layout_features(img_np)
    
    feature_vector = compile_feature_vector(ela_feats, noise_feats, comp_feats, sharp_feats, copy_feats, meta_feats, layout_feats)
    rf_res = model_mgr.predict(feature_vector)
    
    eval_features = dict(feature_vector)
    eval_features.update({
        'ela_normalized_score': ela_res.get('ela_normalized_score', 0.0),
        'ela_severity': ela_res.get('ela_severity', 'NORMAL'),
        'noise_normalized_score': noise_feats.get('noise_normalized_score', 0.0),
        'noise_severity': noise_feats.get('noise_severity', 'NORMAL'),
        'copymove_normalized_score': copy_feats.get('copymove_normalized_score', 0.0),
        'copymove_severity': copy_feats.get('copymove_severity', 'NORMAL'),
        'copymove_raw_pairs': copy_feats.get('copymove_raw_pairs', 0.0),
        'compression_normalized_score': comp_feats.get('compression_normalized_score', 0.0),
        'compression_severity': comp_feats.get('compression_severity', 'NORMAL'),
        'metadata_normalized_score': meta_feats.get('metadata_normalized_score', 0.0),
        'metadata_severity': meta_feats.get('metadata_severity', 'NORMAL'),
        'metadata_editing_software_flag': meta_feats.get('metadata_editing_software_flag', 0.0)
    })
    
    agg = aggregate_forensic_evidence(
        rf_prediction=rf_res['prediction'],
        rf_probability=rf_res['probability'],
        features=eval_features,
        metadata=raw_meta,
        model_trained=rf_res['model_trained']
    )
    return agg

def test_all_7_conditions():
    print("=" * 70)
    print("AI FORENSICS: 7-CONDITION VALIDATION TEST SUITE (Requirement 16)")
    print("=" * 70)
    
    results = {}
    
    # -------------------------------------------------------------
    # Test 1: Original High-Quality Document
    # -------------------------------------------------------------
    base_doc = create_synthetic_base_document(doc_id="GOV-HQ-2026-001", name="Arjun Kapoor", doc_type="Domicile Certificate")
    t1_path = TEMP_DIR / "test1_high_quality.jpg"
    base_doc.save(t1_path, 'JPEG', quality=95)
    
    res1 = run_forensic_pipeline(t1_path, "test1")
    results['Test 1: Original High-Quality'] = res1['forensic_status']
    print(f"Test 1 [Original High-Quality]    -> {res1['forensic_status']} (Conf: {res1['confidence']}%) | ELA: {res1['severities']['ela']}, Noise: {res1['severities']['noise']}")

    # -------------------------------------------------------------
    # Test 2: Original Scanned Document
    # (Simulating flatbed scanner noise, subtle dust/blur, slight paper tint)
    # -------------------------------------------------------------
    scan_doc = create_synthetic_base_document(doc_id="GOV-SCAN-2026-002", name="Pooja Batra", doc_type="Income Certificate")
    # Add scanner blur & grain
    scan_doc = scan_doc.filter(ImageFilter.GaussianBlur(radius=0.4))
    scan_arr = np.array(scan_doc).astype(np.int16)
    # Scanner horizontal illumination gradient
    gradient = np.tile(np.linspace(-6, 6, scan_arr.shape[1], dtype=np.int16), (scan_arr.shape[0], 1))
    for c in range(3):
        scan_arr[:, :, c] = np.clip(scan_arr[:, :, c] + gradient, 0, 255)
    scan_doc = Image.fromarray(scan_arr.astype(np.uint8))
    t2_path = TEMP_DIR / "test2_scanned.jpg"
    scan_doc.save(t2_path, 'JPEG', quality=90)
    
    res2 = run_forensic_pipeline(t2_path, "test2")
    results['Test 2: Original Scanned'] = res2['forensic_status']
    print(f"Test 2 [Original Scanned]         -> {res2['forensic_status']} (Conf: {res2['confidence']}%) | ELA: {res2['severities']['ela']}, Noise: {res2['severities']['noise']}")

    # -------------------------------------------------------------
    # Test 3: Original JPEG-Compressed Document
    # (Recompressed at lower quality e.g. Q70, common on web portals)
    # -------------------------------------------------------------
    jpeg_doc = create_synthetic_base_document(doc_id="GOV-JPG-2026-003", name="Ramesh Pillai", doc_type="Caste Certificate")
    t3_path = TEMP_DIR / "test3_jpeg_compressed.jpg"
    jpeg_doc.save(t3_path, 'JPEG', quality=70)
    
    res3 = run_forensic_pipeline(t3_path, "test3")
    results['Test 3: JPEG Compressed'] = res3['forensic_status']
    print(f"Test 3 [Original JPEG Recompressed] -> {res3['forensic_status']} (Conf: {res3['confidence']}%) | ELA: {res3['severities']['ela']}, Blockiness: {res3['severities']['compression']}")

    # -------------------------------------------------------------
    # Test 4: Original Photographed Document
    # (Simulating mobile phone camera capture: vignette, slight angle, ambient warmth)
    # -------------------------------------------------------------
    photo_doc = create_synthetic_base_document(doc_id="GOV-PHOTO-2026-004", name="Meera Sen", doc_type="Identity Card")
    photo_arr = np.array(photo_doc).astype(np.float32)
    # Vignette effect (darker corners)
    h, w, _ = photo_arr.shape
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - w/2)**2 + (Y - h/2)**2)
    max_dist = np.sqrt((w/2)**2 + (h/2)**2)
    vignette = 1.0 - 0.12 * (dist_from_center / max_dist)
    for c in range(3):
        photo_arr[:, :, c] = np.clip(photo_arr[:, :, c] * vignette, 0, 255)
    # Slight warm lighting
    photo_arr[:, :, 0] = np.clip(photo_arr[:, :, 0] + 4, 0, 255)  # Red tint
    photo_doc = Image.fromarray(photo_arr.astype(np.uint8))
    t4_path = TEMP_DIR / "test4_photographed.jpg"
    photo_doc.save(t4_path, 'JPEG', quality=88)
    
    res4 = run_forensic_pipeline(t4_path, "test4")
    results['Test 4: Photographed'] = res4['forensic_status']
    print(f"Test 4 [Original Photographed]    -> {res4['forensic_status']} (Conf: {res4['confidence']}%) | ELA: {res4['severities']['ela']}, Noise: {res4['severities']['noise']}")

    # -------------------------------------------------------------
    # Test 5: Document with Stamp, Signature, and QR Code
    # (Official markings naturally contain repetitive concentric/dense elements)
    # -------------------------------------------------------------
    stamp_doc = create_synthetic_base_document(doc_id="GOV-STAMP-2026-005", name="Kiran Deshmukh", doc_type="Marksheet")
    draw = ImageDraw.Draw(stamp_doc)
    # Additional Blue stamp
    draw.ellipse([450, 650, 570, 770], outline=(0, 50, 160), width=3)
    draw.text((470, 700), "VERIFIED STAMP", fill=(0, 50, 160))
    # Simulated QR code pattern in top right
    qr_x, qr_y = 560, 40
    draw.rectangle([qr_x, qr_y, qr_x + 90, qr_y + 90], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    # QR positioning squares
    draw.rectangle([qr_x + 8, qr_y + 8, qr_x + 28, qr_y + 28], fill=(0, 0, 0))
    draw.rectangle([qr_x + 62, qr_y + 8, qr_x + 82, qr_y + 28], fill=(0, 0, 0))
    draw.rectangle([qr_x + 8, qr_y + 62, qr_x + 28, qr_y + 82], fill=(0, 0, 0))
    for rx in range(qr_x + 32, qr_x + 58, 6):
        for ry in range(qr_y + 32, qr_y + 58, 6):
            if (rx + ry) % 12 == 0:
                draw.rectangle([rx, ry, rx + 4, ry + 4], fill=(0, 0, 0))
    t5_path = TEMP_DIR / "test5_stamp_qr.jpg"
    stamp_doc.save(t5_path, 'JPEG', quality=95)
    
    res5 = run_forensic_pipeline(t5_path, "test5")
    results['Test 5: Stamp + QR Code'] = res5['forensic_status']
    print(f"Test 5 [Document with Stamp & QR] -> {res5['forensic_status']} (Conf: {res5['confidence']}%) | CopyMove: {res5['severities']['copymove']}, ELA: {res5['severities']['ela']}")

    # -------------------------------------------------------------
    # Test 6: Clearly Edited / Manipulated Document
    # (Spliced altered amount and forged certificate number)
    # -------------------------------------------------------------
    manip_doc = create_synthetic_base_document(doc_id="GOV-FORGED-2026-006", name="Vikram Singhania", doc_type="Income Certificate")
    buf_m = io.BytesIO()
    manip_doc.save(buf_m, 'JPEG', quality=80)
    buf_m.seek(0)
    base_m = Image.open(buf_m)

    # Spliced altered income amount patch with realistic noise
    pw, ph = 340, 35
    patch = Image.new('RGB', (pw, ph), (235, 240, 248))
    pd = ImageDraw.Draw(patch)
    pd.rectangle([1, 1, pw - 1, ph - 1], outline=(150, 150, 150))
    pd.text((10, 8), "INR 99,50,000 (Ninety Nine Lakhs)", fill=(0, 0, 0))
    p_np = np.array(patch)
    noise = np.random.normal(0, 4.0, p_np.shape).astype(np.int16)
    p_np = np.clip(p_np.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    base_m.paste(Image.fromarray(p_np), (275, 385))

    # Spliced altered certificate number patch
    pw2, ph2 = 210, 30
    patch2 = Image.new('RGB', (pw2, ph2), (240, 245, 250))
    pd2 = ImageDraw.Draw(patch2)
    pd2.text((8, 6), "FORGED-ID-9999", fill=(10, 10, 10))
    base_m.paste(patch2, (275, 185))

    exif = base_m.getexif()
    exif[0x0131] = 'Adobe Photoshop 24.1 (Windows)'
    t6_path = TEMP_DIR / "test6_spliced_manip.jpg"
    base_m.save(t6_path, 'JPEG', quality=90, exif=exif)
    
    res6 = run_forensic_pipeline(t6_path, "test6")
    results['Test 6: Spliced Manipulated'] = res6['forensic_status']
    print(f"Test 6 [Clearly Edited / Spliced] -> {res6['forensic_status']} (Conf: {res6['confidence']}%) | ELA: {res6['severities']['ela']}, RF: {res6['severities']['random_forest']}")

    # -------------------------------------------------------------
    # Test 7: Document with Copied Text / Image Region
    # (Duplicated official seal copied to second location)
    # -------------------------------------------------------------
    clone_doc = create_synthetic_base_document(doc_id="GOV-CLONE-2026-007", name="Deepak Chawla", doc_type="Income Certificate")
    # Clone the seal from bottom-left to top-right
    seal_crop = clone_doc.crop((90, clone_doc.height - 250, 190, clone_doc.height - 150))
    clone_doc.paste(seal_crop, (clone_doc.width - 200, 180))
    t7_path = TEMP_DIR / "test7_cloned_seal.jpg"
    clone_doc.save(t7_path, 'JPEG', quality=88)
    
    res7 = run_forensic_pipeline(t7_path, "test7")
    results['Test 7: Cloned Seal Region'] = res7['forensic_status']
    print(f"Test 7 [Cloned Seal / Region]     -> {res7['forensic_status']} (Conf: {res7['confidence']}%) | CopyMove: {res7['severities']['copymove']}, ELA: {res7['severities']['ela']}")

    print("=" * 70)
    print("SUMMARY OF VALIDATION RESULTS:")
    all_passed = True
    for test_name, status in results.items():
        if "Original" in test_name or "JPEG" in test_name or "Photographed" in test_name or "Stamp" in test_name:
            expected = "AUTHENTIC"
            passed = (status == "AUTHENTIC")
        else:
            expected = "POTENTIALLY MANIPULATED / REVIEW REQUIRED"
            passed = (status in ("POTENTIALLY MANIPULATED", "REVIEW REQUIRED"))
        
        status_symbol = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"  {status_symbol} {test_name}: Got '{status}' (Expected: {expected})")
        
    print("=" * 70)
    if all_passed:
        print("ALL 7 CONDITIONS PASSED! System eliminates false positives while preserving forgery detection.")
    else:
        print("Some tests did not match expectations.")

if __name__ == '__main__':
    test_all_7_conditions()
