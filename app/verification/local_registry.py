import os
import json
import datetime
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.verification.base import VerificationProvider, RecordVerificationResult
from app.models import VerificationRecord

import difflib

DOCUMENT_TYPE_TO_FOLDER = {
    'Aadhaar': 'aadhaar',
    'PAN': 'pan',
    'Marksheet': 'marksheets',
    'Certificate': 'certificates',
    'Caste Certificate': 'caste_certificates',
    'Non-Creamy Layer': 'non_creamy_layer',
    'Caste Validity': 'caste_validity',
    'Income Certificate': 'income_certificates',
    'Domicile Certificate': 'domicile_certificates',
    'Driving Licence': 'driving_licence',
    'Other': 'other'
}

def normalize_string(s: Optional[str]) -> str:
    if not s:
        return ""
    return "".join(s.upper().split())

def is_name_match(name1: Optional[str], name2: Optional[str]) -> bool:
    """
    Robust name comparison allowing for minor spacing differences, middle initial abbreviations,
    or token permutations while strictly rejecting completely different names.
    """
    if not name1 or not name2:
        return False
    norm1 = normalize_string(name1)
    norm2 = normalize_string(name2)
    if norm1 == norm2:
        return True

    # Token overlap check
    tokens1 = set(name1.upper().split())
    tokens2 = set(name2.upper().split())
    if tokens1 and tokens2:
        intersection = tokens1.intersection(tokens2)
        if len(intersection) >= min(len(tokens1), len(tokens2)):
            return True

    # Fuzzy SequenceMatcher ratio
    ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    return ratio >= 0.85

class LocalRegistryProvider(VerificationProvider):
    """
    Active Phase 1 provider: Reads from the local verification_records directory
    and synchronized database cache.
    """

    def __init__(self, records_dir: Path, session_factory):
        self.records_dir = Path(records_dir)
        self.session_factory = session_factory

    def _get_category_folder(self, doc_type: str) -> Path:
        folder_name = DOCUMENT_TYPE_TO_FOLDER.get(doc_type, 'other')
        path = self.records_dir / folder_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def verify_document(self, 
                        document_type: str, 
                        document_number: str, 
                        holder_name: Optional[str] = None, 
                        issue_date: Optional[str] = None) -> RecordVerificationResult:
        normalized_num = normalize_string(document_number)
        
        session = self.session_factory()
        try:
            # Query active records
            records = session.query(VerificationRecord).filter_by(is_active=True).all()
            matched_record = None
            for rec in records:
                if normalize_string(rec.document_number) == normalized_num:
                    matched_record = rec
                    break

            if not matched_record:
                return RecordVerificationResult(
                    status="RECORD NOT FOUND",
                    matched=False,
                    document_number=document_number,
                    document_type=document_type,
                    message="This document number does not exist in the current local verification registry.",
                    source="Local Verification Registry (Phase 1)",
                    is_live_government_source=False
                )

            matched_fields = {
                'document_number': matched_record.document_number,
                'document_type': matched_record.document_type,
                'issuing_authority': matched_record.issuing_authority
            }
            mismatched_fields = {}

            # Check holder name match
            if holder_name:
                if is_name_match(holder_name, matched_record.holder_name):
                    matched_fields['holder_name'] = matched_record.holder_name
                else:
                    mismatched_fields['holder_name'] = {
                        'provided': holder_name,
                        'record': matched_record.holder_name
                    }

            # Check document type match
            if document_type and normalize_string(document_type) != normalize_string(matched_record.document_type):
                mismatched_fields['document_type'] = {
                    'provided': document_type,
                    'record': matched_record.document_type
                }

            # Check issue date match if provided
            if issue_date and matched_record.issue_date:
                record_date_str = matched_record.issue_date.strftime('%Y-%m-%d')
                if issue_date.strip() == record_date_str:
                    matched_fields['issue_date'] = record_date_str
                else:
                    mismatched_fields['issue_date'] = {
                        'provided': issue_date,
                        'record': record_date_str
                    }

            if mismatched_fields:
                status = "MISMATCH"
                matched = False
                message = f"Document number located in registry, but {len(mismatched_fields)} field(s) mismatched official registry record ({', '.join(mismatched_fields.keys())})."
            else:
                status = "VERIFIED"
                matched = True
                message = "Record verified successfully against the local verification registry."

            return RecordVerificationResult(
                status=status,
                matched=matched,
                record_id=matched_record.record_id,
                document_number=matched_record.document_number,
                document_type=matched_record.document_type,
                holder_name=matched_record.holder_name,
                issue_date=matched_record.issue_date.strftime('%Y-%m-%d') if matched_record.issue_date else None,
                issuing_authority=matched_record.issuing_authority,
                reference_file=matched_record.reference_file,
                matched_fields=matched_fields,
                mismatched_fields=mismatched_fields,
                message=message,
                source="Local Verification Registry (Phase 1)",
                is_live_government_source=False
            )
        finally:
            session.close()

    def sync_folder(self) -> Dict[str, Any]:
        """
        Scans /verification_records/ and synchronizes JSON files into DB.
        """
        session = self.session_factory()
        stats = {'added': 0, 'updated': 0, 'deactivated': 0, 'total_active': 0, 'errors': []}
        found_record_ids = set()

        try:
            for root, _, files in os.walk(self.records_dir):
                for file in files:
                    if not file.endswith('.json'):
                        continue
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        record_id = data.get('record_id') or file_path.stem
                        doc_number = data.get('document_number')
                        if not doc_number:
                            continue

                        found_record_ids.add(record_id)
                        
                        # Parse date
                        issue_date = None
                        if data.get('issue_date'):
                            try:
                                issue_date = datetime.datetime.strptime(data['issue_date'], '%Y-%m-%d').date()
                            except ValueError:
                                issue_date = None

                        existing = session.query(VerificationRecord).filter_by(record_id=record_id).first()
                        if existing:
                            existing.document_type = data.get('document_type', 'Other')
                            existing.document_number = doc_number
                            existing.document_name = data.get('document_name', existing.document_type)
                            existing.holder_name = data.get('holder_name', 'Unknown')
                            existing.issue_date = issue_date
                            existing.issuing_authority = data.get('issuing_authority', 'Authorized Agency')
                            existing.status = data.get('status', 'VERIFIED')
                            existing.reference_file = data.get('reference_file')
                            existing.source_file_path = str(file_path)
                            existing.is_active = True
                            existing.last_synced_at = datetime.datetime.utcnow()
                            stats['updated'] += 1
                        else:
                            new_rec = VerificationRecord(
                                record_id=record_id,
                                document_type=data.get('document_type', 'Other'),
                                document_number=doc_number,
                                document_name=data.get('document_name', 'Document'),
                                holder_name=data.get('holder_name', 'Unknown'),
                                issue_date=issue_date,
                                issuing_authority=data.get('issuing_authority', 'Authorized Agency'),
                                status=data.get('status', 'VERIFIED'),
                                reference_file=data.get('reference_file'),
                                source_file_path=str(file_path),
                                is_active=True,
                                last_synced_at=datetime.datetime.utcnow()
                            )
                            session.add(new_rec)
                            stats['added'] += 1
                    except Exception as e:
                        stats['errors'].append(f"Error parsing {file}: {str(e)}")

            # Deactivate records no longer present in folder
            all_records = session.query(VerificationRecord).filter_by(is_active=True).all()
            for r in all_records:
                if r.record_id not in found_record_ids:
                    r.is_active = False
                    stats['deactivated'] += 1

            session.commit()
            stats['total_active'] = session.query(VerificationRecord).filter_by(is_active=True).count()
            return stats
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def add_or_update_record(self, record_data: Dict[str, Any], reference_filename: Optional[str] = None) -> VerificationRecord:
        record_id = record_data['record_id']
        doc_type = record_data['document_type']
        target_folder = self._get_category_folder(doc_type)
        json_path = target_folder / f"{record_id}.json"

        # Update dict with reference file if given
        if reference_filename:
            record_data['reference_file'] = reference_filename

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(record_data, f, indent=4)

        # Sync this record immediately
        self.sync_folder()
        
        session = self.session_factory()
        try:
            return session.query(VerificationRecord).filter_by(record_id=record_id).first()
        finally:
            session.close()

    def delete_record(self, record_id: str) -> bool:
        session = self.session_factory()
        try:
            record = session.query(VerificationRecord).filter_by(record_id=record_id).first()
            if record:
                # Remove file from disk
                if os.path.exists(record.source_file_path):
                    os.remove(record.source_file_path)
                record.is_active = False
                session.commit()
                return True
            return False
        finally:
            session.close()
