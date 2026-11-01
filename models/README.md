# Model Artifacts: AI Forensics Random Forest Classifier

- **Model Version:** v2.0-rf-diverse-govdocs
- **Training Date:** 2026-09-28T10:48:56.152465
- **Algorithm:** RandomForestClassifier
- **Total Dataset Size:** 102 samples (51 Authentic, 51 Manipulated)
- **Train / Val / Test:** 70 / 14 / 18
- **Test Accuracy:** 83.33%
- **Test Precision:** 87.50%
- **Test Recall:** 77.78%
- **Test F1 Score:** 82.35%
- **Test ROC-AUC:** 0.9136

## Model Format
Serialized using `joblib` as `random_forest.joblib`. Loaded into application memory via `app/ml/model_manager.py`. PyTorch `.pt` files are not applicable to standard decision forest ensembles.
