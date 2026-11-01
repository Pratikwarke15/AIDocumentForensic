import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.forensic.features import FEATURE_NAMES

def evaluate():
    model_path = BASE_DIR / 'models' / 'random_forest.joblib'
    meta_path = BASE_DIR / 'models' / 'model_metadata.json'

    if not model_path.exists() or not meta_path.exists():
        print("[Evaluate] Model files do not exist. Please train the model first.")
        return

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    print("==================================================")
    print("AI FORENSICS RANDOM FOREST MODEL EVALUATION REPORT")
    print("==================================================")
    print(f"Model Version:   {meta.get('model_version')}")
    print(f"Training Date:   {meta.get('training_date')}")
    print(f"Algorithm:       {meta.get('algorithm')}")
    print(f"Total Samples:   {meta.get('dataset_samples')}")
    print("--------------------------------------------------")
    metrics = meta.get('metrics', {})
    print(f"Accuracy:        {metrics.get('accuracy', 0.0) * 100:.2f}%")
    print(f"Precision:       {metrics.get('precision', 0.0) * 100:.2f}%")
    print(f"Recall:          {metrics.get('recall', 0.0) * 100:.2f}%")
    print(f"F1-Score:        {metrics.get('f1_score', 0.0) * 100:.2f}%")
    print(f"ROC-AUC:         {metrics.get('roc_auc', 0.0):.4f}")
    print("--------------------------------------------------")
    print("Top Feature Importances:")
    for item in meta.get('top_features', [])[:8]:
        print(f"  • {item['feature']:<30} : {item['importance']:.4f}")
    print("==================================================")

if __name__ == '__main__':
    evaluate()
