import datetime
import json
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Date
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user', nullable=False)  # 'user' or 'admin'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    documents = relationship('Document', back_populates='creator')
    verifications = relationship('VerificationHistory', back_populates='user')
    audit_logs = relationship('AuditLog', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login compatibility
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == 'admin'


class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    document_number = Column(String(100), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)
    document_name = Column(String(150), nullable=False)
    holder_name = Column(String(150), nullable=False)
    issue_date = Column(Date, nullable=True)
    issuing_authority = Column(String(200), nullable=True)
    
    original_file_path = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    creator = relationship('User', back_populates='documents')
    verifications = relationship('VerificationHistory', back_populates='document', order_by='desc(VerificationHistory.timestamp)')


class VerificationRecord(Base):
    """
    Indexed local database cache of /verification_records/ JSON files.
    The folder remains the source of truth for Phase-1 records.
    """
    __tablename__ = 'verification_records'
    
    id = Column(Integer, primary_key=True)
    record_id = Column(String(100), unique=True, nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)
    document_number = Column(String(100), nullable=False, index=True)
    document_name = Column(String(150), nullable=False)
    holder_name = Column(String(150), nullable=False)
    issue_date = Column(Date, nullable=True)
    issuing_authority = Column(String(200), nullable=False)
    status = Column(String(50), default='VERIFIED', nullable=False)
    reference_file = Column(String(255), nullable=True)
    
    source_file_path = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, default=datetime.datetime.utcnow)


class VerificationHistory(Base):
    __tablename__ = 'verification_history'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    record_status = Column(String(50), nullable=False)     # 'VERIFIED', 'RECORD NOT FOUND', 'NOT CHECKED'
    forensic_status = Column(String(50), nullable=False)   # 'AUTHENTIC', 'POTENTIALLY MANIPULATED', 'INCONCLUSIVE'
    final_status = Column(String(150), nullable=False)    # e.g., 'VERIFIED & FORENSICALLY CONSISTENT'
    confidence = Column(Float, nullable=False)             # 0.0 - 100.0
    tamper_ratio = Column(Float, default=0.0)
    
    report_path = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    document = relationship('Document', back_populates='verifications')
    user = relationship('User', back_populates='verifications')
    forensic_result = relationship('ForensicResult', back_populates='verification', uselist=False)


class ForensicResult(Base):
    __tablename__ = 'forensic_results'
    
    id = Column(Integer, primary_key=True)
    verification_id = Column(Integer, ForeignKey('verification_history.id'), nullable=False, unique=True)
    
    ela_path = Column(String(500), nullable=True)
    mask_path = Column(String(500), nullable=True)
    highlighted_path = Column(String(500), nullable=True)
    noise_map_path = Column(String(500), nullable=True)
    compression_map_path = Column(String(500), nullable=True)
    
    tamper_ratio = Column(Float, default=0.0)
    feature_vector_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    ocr_json = Column(Text, nullable=True)
    signals_json = Column(Text, nullable=True)
    model_version = Column(String(50), default='v1.0')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    verification = relationship('VerificationHistory', back_populates='forensic_result')

    def get_features(self):
        return json.loads(self.feature_vector_json) if self.feature_vector_json else {}

    def get_metadata(self):
        return json.loads(self.metadata_json) if self.metadata_json else {}

    def get_ocr(self):
        return json.loads(self.ocr_json) if self.ocr_json else {}

    def get_signals(self):
        return json.loads(self.signals_json) if self.signals_json else {}


class ModelVersion(Base):
    __tablename__ = 'model_versions'
    
    id = Column(Integer, primary_key=True)
    version = Column(String(50), unique=True, nullable=False)
    algorithm = Column(String(100), default='RandomForestClassifier')
    file_path = Column(String(500), nullable=False)
    metrics_json = Column(Text, nullable=True)
    feature_names_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def get_metrics(self):
        return json.loads(self.metrics_json) if self.metrics_json else {}


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(100), nullable=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    user = relationship('User', back_populates='audit_logs')
