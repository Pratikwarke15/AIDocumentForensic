from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class RecordVerificationResult:
    status: str  # 'VERIFIED', 'RECORD NOT FOUND', 'NOT CHECKED', 'ERROR'
    matched: bool
    record_id: Optional[str] = None
    document_number: Optional[str] = None
    document_type: Optional[str] = None
    holder_name: Optional[str] = None
    issue_date: Optional[str] = None
    issuing_authority: Optional[str] = None
    reference_file: Optional[str] = None
    matched_fields: Dict[str, Any] = field(default_factory=dict)
    mismatched_fields: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    source: str = "Local Document Registry"
    is_live_government_source: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'matched': self.matched,
            'record_id': self.record_id,
            'document_number': self.document_number,
            'document_type': self.document_type,
            'holder_name': self.holder_name,
            'issue_date': self.issue_date,
            'issuing_authority': self.issuing_authority,
            'reference_file': self.reference_file,
            'matched_fields': self.matched_fields,
            'mismatched_fields': self.mismatched_fields,
            'message': self.message,
            'source': self.source,
            'is_live_government_source': self.is_live_government_source
        }

class VerificationProvider(ABC):
    """
    Abstract interface for document record verification.
    Phase 1 uses LocalRegistryProvider.
    Future phases can swap this with GovernmentVerificationProvider (API Setu, DigiLocker).
    """

    @abstractmethod
    def verify_document(self, 
                        document_type: str, 
                        document_number: str, 
                        holder_name: Optional[str] = None, 
                        issue_date: Optional[str] = None) -> RecordVerificationResult:
        """
        Verify if a document record exists and matches provided details.
        """
        pass
