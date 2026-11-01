import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image

from app.services.file_service import FileService, FileValidationError
from app.verification.base import VerificationProvider
from app.forensic.preprocessing import load_and_preprocess_image, save_standardized_copy
from app.forensic.ela import generate_ela_artifacts
from app.forensic.features import extract_ela_features, compile_feature_vector
from app.forensic.noise import extract_noise_features
from app.forensic.compression import extract_compression_features
from app.forensic.copymove import extract_copymove_features
from app.forensic.sharpness import extract_sharpness_features
from app.forensic.metadata import extract_image_metadata
from app.forensic.pdf_forensics import analyze_pdf_structure, render_pdf_page_to_image
from app.forensic.ocr_layout import extract_ocr_and_layout_features
from app.forensic.template_validator import validate_document_template
from app.forensic.scoring import aggregate_forensic_evidence, combine_record_and_forensic_results
from app.models import Document, VerificationHistory, ForensicResult

class VerificationService:
    def __init__(self, 
                 storage_dir: Path, 
                 session_factory, 
                 registry_provider: VerificationProvider, 
                 model_manager,
                 pdf_report_generator):
        self.storage_dir = Path(storage_dir)
        self.session_factory = session_factory
        self.registry_provider = registry_provider
        self.model_manager = model_manager
        self.pdf_report_generator = pdf_report_generator
        self.file_service = FileService(storage_dir)

    def process_and_verify_document(self,
                                    file_storage,
                                    doc_type: str,
                                    doc_number: str,
                                    doc_name: str,
                                    holder_name: str,
                                    issue_date_str: Optional[str] = None,
                                    user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes complete verification pipeline:
        1. Layer A: Record verification
        2. File preservation & validation
        3. Layer B: Digital Forensics
        4. Evidence aggregation
        5. Database record creation
        6. PDF report generation
        """
        # STEP 1: Layer A - Document Record Verification (Local Registry)
        record_res = self.registry_provider.verify_document(
            document_type=doc_type,
            document_number=doc_number,
            holder_name=holder_name,
            issue_date=issue_date_str
        )

        # STEP 2: File Validation and Cryptographic Preservation
        file_info = self.file_service.validate_and_preserve_file(file_storage)
        saved_file_path = Path(file_info['saved_path'])
        sha256 = file_info['sha256']
        file_type = file_info['file_type']

        # Date parsing
        parsed_issue_date = None
        if issue_date_str:
            try:
                parsed_issue_date = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            except ValueError:
                parsed_issue_date = None

        # STEP 3: Layer B - Digital Forensic Analysis
        unique_prefix = f"{sha256[:12]}_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        pdf_metadata = {}
        img_metadata = {}
        meta_features = {}

        # Path A / B routing
        if file_type == 'pdf':
            # Path A: PDF-native forensics
            pdf_metadata, meta_features = analyze_pdf_structure(saved_file_path)
            # Path B: Rasterize Page 1 for computer vision
            analysis_pil = render_pdf_page_to_image(saved_file_path, page_num=0, dpi=200)
            analysis_np = np.array(analysis_pil)
            # Resize if needed
            if max(analysis_np.shape[0], analysis_np.shape[1]) > 800:
                h, w = analysis_np.shape[:2]
                scale = 800.0 / max(h, w)
                new_size = (int(w * scale), int(h * scale))
                analysis_pil = analysis_pil.resize(new_size, Image.Resampling.LANCZOS)
                analysis_np = np.array(analysis_pil)
        else:
            # Image input
            analysis_np, analysis_pil, _ = load_and_preprocess_image(saved_file_path, max_dimension=800)
            img_metadata, meta_features = extract_image_metadata(saved_file_path)

        # Save standardized analysis copy
        proc_copy_path = self.storage_dir / 'processed' / f"{unique_prefix}_std.jpg"
        save_standardized_copy(analysis_pil, proc_copy_path, quality=95)

        # 1. Error Level Analysis (ELA)
        ela_res = generate_ela_artifacts(
            image_np=analysis_np,
            image_pil=analysis_pil,
            output_dir=self.storage_dir / 'ela',
            prefix=unique_prefix,
            quality=95,
            scale_factor=15.0
        )
        ela_features = extract_ela_features(ela_res['gray_diff'], ela_res['raw_diff'], ela_res)

        # 2. Local Noise Inconsistency
        noise_features, noise_map_path = extract_noise_features(
            image_np=analysis_np,
            output_dir=self.storage_dir / 'noise',
            prefix=unique_prefix
        )

        # 3. Compression & DCT Frequency Domain
        comp_features, comp_map_path = extract_compression_features(
            image_np=analysis_np,
            output_dir=self.storage_dir / 'compression',
            prefix=unique_prefix
        )

        # 4. Copy-Move Duplication Analysis
        copymove_features, copymove_pairs = extract_copymove_features(image_np=analysis_np)

        # 5. Sharpness & Edge Consistency
        sharp_features = extract_sharpness_features(image_np=analysis_np)

        # 6. OCR / Typography Layout Analysis
        ocr_data, layout_features = extract_ocr_and_layout_features(image_np=analysis_np)

        # 6.5. Semantic Template & Non-Document Validation (Pillar 1)
        pdf_text = ""
        if file_type == 'pdf':
            try:
                import fitz
                _doc = fitz.open(str(saved_file_path))
                pdf_text = " ".join([page.get_text("text") for page in _doc])
                _doc.close()
            except Exception:
                pass

        combined_extracted_text = (pdf_text + " " + ocr_data.get('extracted_text_preview', '')).strip()
        template_res = validate_document_template(
            image_np=analysis_np,
            doc_type=doc_type,
            doc_number=doc_number,
            holder_name=holder_name,
            extracted_text=combined_extracted_text
        )

        # Compile Full Feature Vector (28+ features)
        feature_vector = compile_feature_vector(
            ela_feats=ela_features,
            noise_feats=noise_features,
            comp_feats=comp_features,
            sharp_feats=sharp_features,
            copy_feats=copymove_features,
            meta_feats=meta_features,
            layout_feats=layout_features
        )

        # 7. Machine Learning Forensic Inference
        rf_result = self.model_manager.predict(feature_vector)

        # 8. Evidence Aggregation & Final Scoring (3-Pillar Architecture)
        eval_features = dict(feature_vector)
        eval_features.update({
            'ela_normalized_score': ela_res.get('ela_normalized_score', 0.0),
            'ela_severity': ela_res.get('ela_severity', 'NORMAL'),
            'noise_normalized_score': noise_features.get('noise_normalized_score', 0.0),
            'noise_severity': noise_features.get('noise_severity', 'NORMAL'),
            'copymove_normalized_score': copymove_features.get('copymove_normalized_score', 0.0),
            'copymove_severity': copymove_features.get('copymove_severity', 'NORMAL'),
            'copymove_raw_pairs': copymove_features.get('copymove_raw_pairs', 0.0),
            'compression_normalized_score': comp_features.get('compression_normalized_score', 0.0),
            'compression_severity': comp_features.get('compression_severity', 'NORMAL'),
            'metadata_normalized_score': meta_features.get('metadata_normalized_score', 0.0),
            'metadata_severity': meta_features.get('metadata_severity', 'NORMAL')
        })

        combined_metadata = {**pdf_metadata, **img_metadata}
        aggregation = aggregate_forensic_evidence(
            rf_prediction=rf_result['prediction'],
            rf_probability=rf_result['probability'],
            features=eval_features,
            metadata=combined_metadata,
            model_trained=rf_result['model_trained'],
            template_validation=template_res,
            record_verification=record_res
        )

        # Layer A: Original Document Match Calculation
        original_document_match = None
        ref_file_matched = False
        if record_res.matched:
            ref_file_name = getattr(record_res, 'reference_file', None)
            ref_path = None
            if ref_file_name:
                records_dir = getattr(self.registry_provider, 'records_dir', Path('verification_records'))
                for root, _, files in os.walk(records_dir):
                    if ref_file_name in files:
                        ref_path = Path(root) / ref_file_name
                        break
            if ref_path and ref_path.exists():
                import hashlib
                with open(ref_path, 'rb') as rf:
                    ref_sha256 = hashlib.sha256(rf.read()).hexdigest()
                if ref_sha256 == sha256:
                    original_document_match = 100.0
                    ref_file_matched = True
                else:
                    original_document_match = 0.0
            else:
                original_document_match = 100.0
        elif record_res.status == 'RECORD NOT FOUND':
            original_document_match = None
        else:
            original_document_match = 0.0

        aggregation['original_document_match'] = original_document_match
        aggregation['ref_file_matched'] = ref_file_matched

        final_status_text = combine_record_and_forensic_results(
            record_status=record_res.status,
            forensic_status=aggregation['forensic_status']
        )

        # STEP 4: Database Persistence
        session = self.session_factory()
        try:
            # Check or create Document entity
            doc = session.query(Document).filter_by(sha256=sha256).first()
            if not doc:
                doc = Document(
                    document_number=doc_number,
                    document_type=doc_type,
                    document_name=doc_name,
                    holder_name=holder_name,
                    issue_date=parsed_issue_date,
                    issuing_authority=record_res.issuing_authority or "Self-Reported",
                    original_file_path=file_info['saved_path'],
                    sha256=sha256,
                    file_size=file_info['file_size'],
                    mime_type=file_info['mime_type'],
                    created_by=user_id,
                    created_at=datetime.datetime.utcnow()
                )
                session.add(doc)
                session.flush()

            # Create VerificationHistory record
            verification = VerificationHistory(
                document_id=doc.id,
                user_id=user_id,
                record_status=record_res.status,
                forensic_status=aggregation['forensic_status'],
                final_status=final_status_text,
                confidence=aggregation['confidence'],
                tamper_ratio=ela_res['tamper_ratio'],
                timestamp=datetime.datetime.utcnow()
            )
            session.add(verification)
            session.flush()

            # Create ForensicResult record
            f_result = ForensicResult(
                verification_id=verification.id,
                ela_path=ela_res['ela_heatmap_path'],
                mask_path=ela_res['tamper_mask_path'],
                highlighted_path=ela_res['highlighted_path'],
                noise_map_path=noise_map_path,
                compression_map_path=comp_map_path,
                tamper_ratio=ela_res['tamper_ratio'],
                feature_vector_json=json.dumps(feature_vector),
                metadata_json=json.dumps(combined_metadata),
                ocr_json=json.dumps(ocr_data),
                signals_json=json.dumps(aggregation),
                model_version=rf_result.get('model_version', 'v1.0')
            )
            session.add(f_result)
            session.commit()

            # STEP 5: Generate 5-Page PDF Forensic Report
            report_pdf_path = self.pdf_report_generator.generate_report(
                verification=verification,
                document=doc,
                record_result=record_res,
                forensic_result=f_result,
                aggregation=aggregation,
                feature_vector=feature_vector,
                output_dir=self.storage_dir / 'reports'
            )
            
            verification.report_path = report_pdf_path
            session.commit()

            return {
                'verification_id': verification.id,
                'document_id': doc.id,
                'document_number': doc.document_number,
                'document_type': doc.document_type,
                'holder_name': doc.holder_name,
                'record_status': record_res.status,
                'record_result': record_res.to_dict(),
                'forensic_status': aggregation['forensic_status'],
                'final_status': final_status_text,
                'confidence': aggregation['confidence'],
                'original_document_match': original_document_match,
                'authenticity_confidence': aggregation.get('authenticity_confidence', aggregation['confidence']),
                'manipulation_score': aggregation.get('manipulation_score', aggregation.get('risk_score', 0.0)),
                'suspicious_region_percentage': aggregation.get('suspicious_region_percentage', round(ela_res['tamper_ratio'] * 100.0, 2)),
                'tamper_ratio': ela_res['tamper_ratio'],
                'indicators': aggregation['indicators'],
                'signals': aggregation['signals'],
                'ela_heatmap_path': ela_res['ela_heatmap_path'],
                'tamper_mask_path': ela_res['tamper_mask_path'],
                'highlighted_path': ela_res['highlighted_path'],
                'noise_map_path': noise_map_path,
                'compression_map_path': comp_map_path,
                'report_path': report_pdf_path,
                'feature_vector': feature_vector,
                'metadata': combined_metadata,
                'ocr': ocr_data,
                'rf_result': rf_result
            }
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
