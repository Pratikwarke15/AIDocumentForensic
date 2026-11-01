import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.forensic.preprocessing import load_and_preprocess_image
from app.forensic.ela import generate_ela_artifacts
from app.forensic.features import extract_ela_features, compile_feature_vector, FEATURE_NAMES
from app.forensic.noise import extract_noise_features
from app.forensic.compression import extract_compression_features
from app.forensic.copymove import extract_copymove_features
from app.forensic.sharpness import extract_sharpness_features
from app.forensic.metadata import extract_image_metadata
from app.forensic.ocr_layout import extract_ocr_and_layout_features

DATASET_DIR = BASE_DIR / 'dataset'
AUTH_DIR = DATASET_DIR / 'authentic'
MANIP_DIR = DATASET_DIR / 'manipulated'
TEMP_DIR = BASE_DIR / 'storage' / 'temp'
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def process_file(file_path: Path, label: int):
    try:
        img_np, img_pil, _ = load_and_preprocess_image(file_path, max_dimension=800)
        prefix = f"feat_{file_path.stem}"

        ela_res = generate_ela_artifacts(img_np, img_pil, TEMP_DIR, prefix, quality=95, scale_factor=15.0)
        ela_feats = extract_ela_features(ela_res['gray_diff'], ela_res['raw_diff'], ela_res)
        
        noise_feats, _ = extract_noise_features(img_np, TEMP_DIR, prefix)
        comp_feats, _ = extract_compression_features(img_np, TEMP_DIR, prefix)
        copy_feats, _ = extract_copymove_features(img_np)
        sharp_feats = extract_sharpness_features(img_np)
        _, meta_feats = extract_image_metadata(file_path)
        _, layout_feats = extract_ocr_and_layout_features(img_np)

        feats = compile_feature_vector(ela_feats, noise_feats, comp_feats, sharp_feats, copy_feats, meta_feats, layout_feats)
        feats['label'] = label
        feats['filename'] = file_path.name
        return feats
    except Exception as e:
        print(f"Error processing {file_path.name}: {e}")
        return None

def extract_all():
    rows = []
    auth_files = list(AUTH_DIR.glob('*.jpg'))
    manip_files = list(MANIP_DIR.glob('*.jpg'))
    
    print(f"[Extract] Extracting features from {len(auth_files)} authentic samples...")
    for f in auth_files:
        row = process_file(f, label=0)
        if row:
            rows.append(row)

    print(f"[Extract] Extracting features from {len(manip_files)} manipulated samples...")
    for f in manip_files:
        row = process_file(f, label=1)
        if row:
            rows.append(row)

    df = pd.DataFrame(rows)
    inv_csv = DATASET_DIR / 'metadata' / 'dataset_inventory.csv'
    if inv_csv.exists():
        inv_df = pd.read_csv(inv_csv)
        # Merge on filename to carry split, document_name, manipulation_type, etc.
        cols_to_merge = ['filename', 'split', 'document_name', 'document_category', 'manipulation_type', 'source_agency', 'dhash']
        cols_to_merge = [c for c in cols_to_merge if c in inv_df.columns]
        df = df.merge(inv_df[cols_to_merge], on='filename', how='left')

    out_csv = DATASET_DIR / 'metadata' / 'features.csv'
    df.to_csv(out_csv, index=False)
    print(f"[Extract] Features extracted and saved to {out_csv} ({len(df)} total rows).")
    return df

if __name__ == '__main__':
    extract_all()
