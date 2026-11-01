from typing import Dict, Any
from app.ml.model_manager import ModelManager

def predict_document_manipulation(model_mgr: ModelManager, features: Dict[str, float]) -> Dict[str, Any]:
    """Convenience helper for model prediction."""
    return model_mgr.predict(features)
