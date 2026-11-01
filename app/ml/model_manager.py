import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import joblib
import numpy as np

class ModelManager:
    """
    Manages the lifecycle, loading, and inspection of the RandomForestClassifier.
    """
    _instance = None

    def __init__(self, models_dir: Path):
        self.models_dir = Path(models_dir)
        self.model_path = self.models_dir / 'random_forest.joblib'
        self.schema_path = self.models_dir / 'feature_schema.json'
        self.meta_path = self.models_dir / 'model_metadata.json'
        
        self.model = None
        self.feature_names = []
        self.metadata = {}
        self.is_trained = False
        
        self.reload()

    def reload(self):
        """Loads or reloads model files from disk."""
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
            except Exception as e:
                print(f"[ModelManager] Warning: failed to load model: {e}")
                self.model = None
                self.is_trained = False
        else:
            self.model = None
            self.is_trained = False

        if self.schema_path.exists():
            try:
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    self.feature_names = json.load(f)
            except Exception:
                self.feature_names = []
        else:
            self.feature_names = []

        if self.meta_path.exists():
            try:
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except Exception:
                self.metadata = {}
        else:
            self.metadata = {
                'status': 'UNTRAINED',
                'algorithm': 'RandomForestClassifier',
                'training_date': None,
                'metrics': None
            }

    def predict(self, feature_dict: Dict[str, float]) -> Dict[str, Any]:
        """
        Executes prediction on input features.
        Returns:
        - prediction: 0 (Authentic) or 1 (Manipulated)
        - probability: float (0.0 to 1.0)
        - model_trained: bool
        """
        if not self.is_trained or self.model is None:
            # Untrained fallback
            return {
                'prediction': 0,
                'probability': 0.0,
                'model_trained': False,
                'model_version': 'untrained'
            }

        # Build ordered vector
        from app.forensic.features import FEATURE_NAMES
        ordered_names = self.feature_names if self.feature_names else FEATURE_NAMES
        vector = np.array([[feature_dict.get(name, 0.0) for name in ordered_names]], dtype=np.float32)

        # Replace any NaNs or Infs
        vector = np.nan_to_num(vector, nan=0.0, posinf=1.0, neginf=0.0)

        pred = int(self.model.predict(vector)[0])
        # Probability of class 1 (Manipulated)
        if hasattr(self.model, 'predict_proba'):
            proba = float(self.model.predict_proba(vector)[0][1])
        else:
            proba = 1.0 if pred == 1 else 0.0

        return {
            'prediction': pred,
            'probability': proba,
            'model_trained': True,
            'model_version': self.metadata.get('model_version', 'v1.0')
        }
