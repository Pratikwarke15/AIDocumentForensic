from flask import Blueprint, render_template, request, abort, current_app
from flask_login import login_required, current_user
from app.models import Document, VerificationHistory

history_bp = Blueprint('history', __name__)

@history_bp.route('/history')
@login_required
def timeline():
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()

    session = current_app.session_factory()
    try:
        q = session.query(VerificationHistory).join(Document)
        if not current_user.is_admin:
            q = q.filter(VerificationHistory.user_id == current_user.id)

        if status_filter == 'verified':
            q = q.filter(VerificationHistory.record_status == 'VERIFIED')
        elif status_filter == 'manipulated':
            q = q.filter(VerificationHistory.forensic_status == 'POTENTIALLY MANIPULATED')
        elif status_filter == 'authentic':
            q = q.filter(VerificationHistory.forensic_status == 'AUTHENTIC')
        elif status_filter == 'inconclusive':
            q = q.filter(VerificationHistory.forensic_status == 'INCONCLUSIVE')

        if search_query:
            q = q.filter(
                (Document.document_number.ilike(f"%{search_query}%")) |
                (Document.holder_name.ilike(f"%{search_query}%"))
            )

        verifications = q.order_by(VerificationHistory.timestamp.desc()).all()

        return render_template(
            'history.html',
            verifications=verifications,
            status_filter=status_filter,
            search_query=search_query
        )
    finally:
        session.close()

@history_bp.route('/documents/<int:doc_id>')
@login_required
def document_detail(doc_id):
    session = current_app.session_factory()
    try:
        doc = session.query(Document).get(doc_id)
        if not doc:
            abort(404)

        if not current_user.is_admin and doc.created_by != current_user.id:
            abort(403)

        verifications = session.query(VerificationHistory).filter_by(
            document_id=doc_id
        ).order_by(VerificationHistory.timestamp.desc()).all()

        return render_template(
            'document_detail.html',
            document=doc,
            verifications=verifications
        )
    finally:
        session.close()
