from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from app.models import Document, VerificationHistory, VerificationRecord
from app.routes.verify_routes import DOCUMENT_TYPES

search_bp = Blueprint('search', __name__)

@search_bp.route('/search', methods=['GET'])
@login_required
def search_documents():
    doc_number = request.args.get('document_number', '').strip()
    doc_type = request.args.get('document_type', '').strip()
    holder_name = request.args.get('holder_name', '').strip()
    issue_date = request.args.get('issue_date', '').strip()

    searched = bool(doc_number)
    registry_match = None
    verification_history = []
    latest_verification = None

    if searched:
        # Check local registry
        registry_match = current_app.registry_provider.verify_document(
            document_type=doc_type or 'Other',
            document_number=doc_number,
            holder_name=holder_name or None,
            issue_date=issue_date or None
        )

        session = current_app.session_factory()
        try:
            # Query past verifications for this document number
            docs = session.query(Document).filter(Document.document_number.ilike(f"%{doc_number}%")).all()
            doc_ids = [d.id for d in docs]

            if doc_ids:
                verification_history = session.query(VerificationHistory).filter(
                    VerificationHistory.document_id.in_(doc_ids)
                ).order_by(VerificationHistory.timestamp.desc()).all()
                if verification_history:
                    latest_verification = verification_history[0]
        finally:
            session.close()

    return render_template(
        'search.html',
        searched=searched,
        doc_number=doc_number,
        doc_type=doc_type,
        holder_name=holder_name,
        issue_date=issue_date,
        document_types=DOCUMENT_TYPES,
        registry_match=registry_match,
        verification_history=verification_history,
        latest_verification=latest_verification
    )
