import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-forensics-security-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{BASE_DIR / 'forensics.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATES_AUTO_RELOAD = True
    
    BASE_DIR = BASE_DIR
    STORAGE_DIR = BASE_DIR / 'storage'
    VERIFICATION_RECORDS_DIR = BASE_DIR / 'verification_records'
    MODELS_DIR = BASE_DIR / 'models'
    DATASET_DIR = BASE_DIR / 'dataset'
    
    # Upload limits & rules
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'application/pdf'
    }
    
    # Forensic parameters
    ELA_QUALITY = 95
    ELA_SCALE = 15.0
    TAMPER_THRESHOLD_RATIO = 0.02
    ANALYSIS_MAX_DIMENSION = 800
    
    # Model configuration
    ACTIVE_MODEL_FILE = MODELS_DIR / 'random_forest.joblib'
    FEATURE_SCHEMA_FILE = MODELS_DIR / 'feature_schema.json'
    MODEL_METADATA_FILE = MODELS_DIR / 'model_metadata.json'
