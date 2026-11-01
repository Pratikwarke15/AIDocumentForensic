import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.test_document_conditions import run_forensic_pipeline, TEMP_DIR

test_files = [
    ("Test 1 (HQ)", "test1_high_quality.jpg"),
    ("Test 2 (Scanned)", "test2_scanned.jpg"),
    ("Test 3 (Compressed)", "test3_jpeg_compressed.jpg"),
    ("Test 4 (Photographed)", "test4_photographed.jpg"),
    ("Test 5 (Stamp/QR)", "test5_stamp_qr.jpg"),
    ("Test 6 (Spliced)", "test6_spliced_manip.jpg"),
    ("Test 7 (Cloned)", "test7_cloned_seal.jpg"),
]

for label, filename in test_files:
    img_path = TEMP_DIR / filename
    if img_path.exists():
        res = run_forensic_pipeline(img_path, f"dbg_{filename[:5]}")
        print(f"=== {label}: {filename} ===")
        print(f"  Forensic Status: {res['forensic_status']} (Display: {res['display_status']})")
        print(f"  Confidence: {res['confidence']}% | RF prob: {res['rf_probability']}%")
        print(f"  Composite Score: {res['composite_score']}")
        print(f"  Severities: {res['severities']}")
        dbg = res['debug_info']
        print(f"  ELA: norm={dbg['ela']['normalized_score']}, sev={dbg['ela']['severity']}, ratio={dbg['ela']['raw_tamper_ratio']}, count={dbg['ela']['raw_component_count']}")
        print(f"  Noise: norm={dbg['noise']['normalized_score']}, sev={dbg['noise']['severity']}, disp={dbg['noise']['raw_disparity_ratio']}")
        print(f"  CopyMove: norm={dbg['copymove']['normalized_score']}, sev={dbg['copymove']['severity']}, pairs={dbg['copymove']['raw_pairs']}, clusters={dbg['copymove']['coherent_clusters']}")
        print(f"  Compression: norm={dbg['compression']['normalized_score']}, sev={dbg['compression']['severity']}, blockiness={dbg['compression']['raw_blockiness']}")
        print(f"  Indicators: {res['indicators']}")
        print()
