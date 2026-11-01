import json
import datetime
from typing import Optional, Dict, Any
from app.models import AuditLog

class AuditService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def log(self, 
            action: str, 
            user_id: Optional[int] = None, 
            target_type: Optional[str] = None, 
            target_id: Optional[str] = None, 
            details: Optional[Dict[str, Any]] = None,
            ip_address: Optional[str] = None):
        session = self.session_factory()
        try:
            audit = AuditLog(
                user_id=user_id,
                action=action,
                target_type=target_type,
                target_id=str(target_id) if target_id else None,
                details_json=json.dumps(details) if details else None,
                ip_address=ip_address,
                timestamp=datetime.datetime.utcnow()
            )
            session.add(audit)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"[AuditService] Failed to log action {action}: {e}")
        finally:
            session.close()
