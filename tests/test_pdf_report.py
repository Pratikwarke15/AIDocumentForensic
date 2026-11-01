import os
import datetime
from pathlib import Path
from app.reports.pdf_generator import PDFReportGenerator
from app.models import Document, VerificationHistory, ForensicResult
from app.verification.base import RecordVerificationResult

def test_pdf_report_generation(tmp_path):
    gen = PDFReportGenerator()
    
    doc = Document(
        document_number="MH/INC/2026/0001",
        document_type="Income Certificate",
        document_name="Annual Income Certificate",
        holder_name="Demo User",
        issuing_authority="Revenue Dept",
        original_file_path="",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size=1024,
        mime_type="image/jpeg",
        created_at=datetime.datetime.utcnow()
    )

    verif = VerificationHistory(
        id=999,
        record_status="VERIFIED",
        forensic_status="AUTHENTIC",
        final_status="VERIFIED RECORD & FORENSICALLY CONSISTENT",
        confidence=94.5,
        tamper_ratio=0.005,
        timestamp=datetime.datetime.utcnow()
    )

    f_res = ForensicResult(
        verification_id=999,
        ela_path="",
        mask_path="",
        highlighted_path="",
        tamper_ratio=0.005,
        feature_vector_json="{}",
        metadata_json="{}",
        ocr_json="{}",
        signals_json="{}",
        model_version="v1.0"
    )

    rec_res = RecordVerificationResult(
        status="VERIFIED",
        matched=True,
        document_number="MH/INC/2026/0001",
        document_type="Income Certificate",
        holder_name="Demo User",
        issuing_authority="Revenue Dept"
    )

    agg = {
        'forensic_status': 'AUTHENTIC',
        'confidence': 94.5,
        'rf_probability': 5.5,
        'indicators': ['No digital tampering anomalies detected.'],
        'signals': {'ela': 'NORMAL', 'noise': 'NORMAL', 'compression': 'NORMAL', 'random_forest': 'AUTHENTIC'}
    }

    feature_vec = {'ela_tamper_ratio': 0.005, 'ela_mean': 10.2, 'noise_disparity_ratio': 1.1}

    out_pdf = gen.generate_report(
        verification=verif,
        document=doc,
        record_result=rec_res,
        forensic_result=f_res,
        aggregation=agg,
        feature_vector=feature_vec,
        output_dir=tmp_path
    )

    assert os.path.exists(out_pdf)
    assert os.path.getsize(out_pdf) > 1000  # Multi-page PDF
