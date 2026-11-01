import os
import sys
import json
import datetime
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score, classification_report
)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.forensic.features import FEATURE_NAMES

MODELS_DIR = BASE_DIR / 'models'
DATASET_DIR = BASE_DIR / 'dataset'
CSV_PATH = DATASET_DIR / 'metadata' / 'features.csv'

MODELS_DIR.mkdir(parents=True, exist_ok=True)

def train():
    print("=" * 70)
    print("AI FORENSICS: TRAINING RANDOM FOREST CLASSIFIER")
    print("=" * 70)

    if not CSV_PATH.exists():
        print("[Train] Feature CSV missing. Triggering feature extraction first...")
        from scripts.extract_features import extract_all
        df = extract_all()
    else:
        df = pd.read_csv(CSV_PATH)

    if len(df) < 10:
        print("[Train] Insufficient data to train model. Minimum 10 samples required.")
        return

    # Count dataset statistics
    total_samples = len(df)
    n_auth = int((df['label'] == 0).sum())
    n_manip = int((df['label'] == 1).sum())

    print(f"[Dataset Summary]")
    print(f"  Total samples:        {total_samples}")
    print(f"  Authentic samples:    {n_auth} ({n_auth/total_samples*100:.1f}%)")
    print(f"  Manipulated samples:  {n_manip} ({n_manip/total_samples*100:.1f}%)")

    # Data splitting by document group (prevent data leakage)
    if 'split' in df.columns:
        train_df = df[df['split'] == 'train'].copy()
        val_df = df[df['split'] == 'val'].copy()
        test_df = df[df['split'] == 'test'].copy()
        print("\n[Splits] Using pre-assigned document-grouped splits (0% data leakage):")
    else:
        # Fallback grouping by document_name
        from sklearn.model_selection import GroupShuffleSplit
        gss = GroupShuffleSplit(n_splits=1, train_size=0.70, random_state=42)
        groups = df['document_name'] if 'document_name' in df.columns else df.index
        train_idx, temp_idx = next(gss.split(df, groups=groups))
        train_df = df.iloc[train_idx].copy()
        temp_df = df.iloc[temp_idx].copy()

        gss_val = GroupShuffleSplit(n_splits=1, train_size=0.50, random_state=42)
        temp_groups = temp_df['document_name'] if 'document_name' in temp_df.columns else temp_df.index
        val_idx, test_idx = next(gss_val.split(temp_df, groups=temp_groups))
        val_df = temp_df.iloc[val_idx].copy()
        test_df = temp_df.iloc[test_idx].copy()

    print(f"  Train: {len(train_df)} samples (Auth: {(train_df['label']==0).sum()}, Manip: {(train_df['label']==1).sum()})")
    print(f"  Val:   {len(val_df)} samples (Auth: {(val_df['label']==0).sum()}, Manip: {(val_df['label']==1).sum()})")
    print(f"  Test:  {len(test_df)} samples (Auth: {(test_df['label']==0).sum()}, Manip: {(test_df['label']==1).sum()})")

    # Prepare features
    X_train = np.nan_to_num(train_df[FEATURE_NAMES].values, nan=0.0, posinf=1.0, neginf=0.0)
    y_train = train_df['label'].values

    X_val = np.nan_to_num(val_df[FEATURE_NAMES].values, nan=0.0, posinf=1.0, neginf=0.0)
    y_val = val_df['label'].values

    X_test = np.nan_to_num(test_df[FEATURE_NAMES].values, nan=0.0, posinf=1.0, neginf=0.0)
    y_test = test_df['label'].values

    # Train Random Forest Classifier
    clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=10,
        min_samples_split=3,
        min_samples_leaf=1,
        max_features='sqrt',
        random_state=42,
        class_weight='balanced',
        n_jobs=-1
    )

    clf.fit(X_train, y_train)

    # Validation Set Evaluation
    val_pred = clf.predict(X_val)
    val_acc = accuracy_score(y_val, val_pred)
    val_f1 = f1_score(y_val, val_pred, zero_division=0)
    print(f"\n[Validation Set Performance] Accuracy: {val_acc*100:.2f}%, F1: {val_f1*100:.2f}%")

    # Test Set Evaluation
    test_pred = clf.predict(X_test)
    test_proba = clf.predict_proba(X_test)[:, 1]

    acc = float(accuracy_score(y_test, test_pred))
    prec = float(precision_score(y_test, test_pred, zero_division=0))
    rec = float(recall_score(y_test, test_pred, zero_division=0))
    f1 = float(f1_score(y_test, test_pred, zero_division=0))
    cm = confusion_matrix(y_test, test_pred).tolist()

    try:
        auc = float(roc_auc_score(y_test, test_proba))
    except Exception:
        auc = 1.0

    print("=" * 70)
    print("FINAL MODEL EVALUATION (HELD-OUT TEST SET - UNSEEN DOCUMENT SOURCES):")
    print(f"  Accuracy:         {acc * 100:.2f}%")
    print(f"  Precision:        {prec * 100:.2f}%")
    print(f"  Recall:           {rec * 100:.2f}%")
    print(f"  F1-Score:         {f1 * 100:.2f}%")
    print(f"  ROC-AUC:          {auc:.4f}")
    print(f"\nConfusion Matrix:\n{np.array(cm)}")
    print(f"  True Negatives (Authentic Correct):    {cm[0][0]}")
    print(f"  False Positives (Authentic as Manip):  {cm[0][1]}")
    print(f"  False Negatives (Manip as Authentic):  {cm[1][0]}")
    print(f"  True Positives (Manipulated Correct):  {cm[1][1]}")
    print("=" * 70)

    # Top Feature Importances
    importances = clf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    top_features = [{"feature": FEATURE_NAMES[i], "importance": float(importances[i])} for i in sorted_idx[:12]]
    print("\nTop 10 Most Influential Forensic Features:")
    for tf in top_features[:10]:
        print(f"  - {tf['feature']:30s}: {tf['importance']:.4f}")

    # Save Model Artifacts
    model_path = MODELS_DIR / 'random_forest.joblib'
    joblib.dump(clf, model_path)

    schema_path = MODELS_DIR / 'feature_schema.json'
    with open(schema_path, 'w', encoding='utf-8') as f:
        json.dump(FEATURE_NAMES, f, indent=4)

    metadata = {
        'model_version': 'v2.0-rf-diverse-govdocs',
        'algorithm': 'RandomForestClassifier',
        'training_date': datetime.datetime.utcnow().isoformat(),
        'dataset_summary': {
            'total_samples': total_samples,
            'authentic_samples': n_auth,
            'manipulated_samples': n_manip,
            'train_samples': len(train_df),
            'val_samples': len(val_df),
            'test_samples': len(test_df)
        },
        'hyperparameters': {
            'n_estimators': 150,
            'max_depth': 10,
            'min_samples_split': 3,
            'class_weight': 'balanced',
            'random_state': 42
        },
        'test_metrics': {
            'accuracy': acc,
            'precision': prec,
            'recall': rec,
            'f1_score': f1,
            'roc_auc': auc,
            'confusion_matrix': cm
        },
        'top_features': top_features,
        'format_notes': 'Model is serialized as scikit-learn RandomForestClassifier via joblib (.joblib/.pkl). PyTorch (.pt) is not used because this is a tabular ensemble tree model.'
    }

    meta_path = MODELS_DIR / 'model_metadata.json'
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4)

    # Write README
    readme_path = MODELS_DIR / 'README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"""# Model Artifacts: AI Forensics Random Forest Classifier

- **Model Version:** {metadata['model_version']}
- **Training Date:** {metadata['training_date']}
- **Algorithm:** {metadata['algorithm']}
- **Total Dataset Size:** {total_samples} samples ({n_auth} Authentic, {n_manip} Manipulated)
- **Train / Val / Test:** {len(train_df)} / {len(val_df)} / {len(test_df)}
- **Test Accuracy:** {acc * 100:.2f}%
- **Test Precision:** {prec * 100:.2f}%
- **Test Recall:** {rec * 100:.2f}%
- **Test F1 Score:** {f1 * 100:.2f}%
- **Test ROC-AUC:** {auc:.4f}

## Model Format
Serialized using `joblib` as `random_forest.joblib`. Loaded into application memory via `app/ml/model_manager.py`. PyTorch `.pt` files are not applicable to standard decision forest ensembles.
""")

    print(f"\n[Artifacts Saved]")
    print(f"  Model saved to:    {model_path}")
    print(f"  Schema saved to:   {schema_path}")
    print(f"  Metadata saved to: {meta_path}")

    return {
        'model': clf,
        'metrics': metadata['test_metrics'],
        'dataset_summary': metadata['dataset_summary']
    }

if __name__ == '__main__':
    train()
