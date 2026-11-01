from app.ml.model_manager import ModelManager
from app.forensic.features import FEATURE_NAMES

def test_rf_model_inference(app):
    mgr = app.model_manager
    assert mgr.is_trained is True
    assert mgr.model is not None
    assert len(mgr.feature_names) == len(FEATURE_NAMES)

    # Synthetic clean feature vector
    sample_clean = {fn: 0.0 for fn in FEATURE_NAMES}
    res_clean = mgr.predict(sample_clean)
    assert 'prediction' in res_clean
    assert 'probability' in res_clean
    assert res_clean['model_trained'] is True
    assert 0.0 <= res_clean['probability'] <= 1.0
