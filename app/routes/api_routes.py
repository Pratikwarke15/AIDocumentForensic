from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_user, current_user
from app.models import User, Document, VerificationHistory, ForensicResult, VerificationRecord
from app.services.file_service import FileValidationError

api_bp = Blueprint('api', __name__)

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    session = current_app.session_factory()
    try:
        user = session.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                return jsonify({'error': 'Account deactivated'}), 403
            login_user(user)
            return jsonify({
                'message': 'Login successful',
                'user': {'id': user.id, 'username': user.username, 'role': user.role}
            })
        return jsonify({'error': 'Invalid credentials'}), 401
    finally:
        session.close()

@api_bp.route('/documents/search', methods=['GET'])
def api_search_documents():
    doc_number = request.args.get('document_number', '').strip()
    if not doc_number:
        return jsonify({'error': 'document_number parameter is required'}), 400

    reg_result = current_app.registry_provider.verify_document(
        document_type=request.args.get('document_type', 'Other'),
        document_number=doc_number,
        holder_name=request.args.get('holder_name'),
        issue_date=request.args.get('issue_date')
    )

    session = current_app.session_factory()
    try:
        docs = session.query(Document).filter(Document.document_number.ilike(f"%{doc_number}%")).all()
        history_list = []
        for d in docs:
            for v in d.verifications:
                history_list.append({
                    'verification_id': v.id,
                    'timestamp': v.timestamp.isoformat(),
                    'record_status': v.record_status,
                    'forensic_status': v.forensic_status,
                    'final_status': v.final_status,
                    'confidence': v.confidence
                })

        return jsonify({
            'query': doc_number,
            'registry': reg_result.to_dict(),
            'verification_count': len(history_list),
            'history': history_list
        })
    finally:
        session.close()

@api_bp.route('/verifications/<int:v_id>', methods=['GET'])
def api_get_verification(v_id):
    session = current_app.session_factory()
    try:
        v = session.query(VerificationHistory).get(v_id)
        if not v:
            return jsonify({'error': 'Verification not found'}), 404

        doc = v.document
        f_res = v.forensic_result

        return jsonify({
            'verification_id': v.id,
            'timestamp': v.timestamp.isoformat(),
            'document': {
                'id': doc.id,
                'number': doc.document_number,
                'type': doc.document_type,
                'holder': doc.holder_name,
                'sha256': doc.sha256
            },
            'record_status': v.record_status,
            'forensic_status': v.forensic_status,
            'final_status': v.final_status,
            'confidence': v.confidence,
            'tamper_ratio': v.tamper_ratio,
            'features': f_res.get_features() if f_res else {},
            'signals': f_res.get_signals() if f_res else {},
            'metadata': f_res.get_metadata() if f_res else {}
        })
    finally:
        session.close()

@api_bp.route('/registry/records', methods=['GET', 'POST'])
def api_registry_records():
    if request.method == 'GET':
        session = current_app.session_factory()
        try:
            records = session.query(VerificationRecord).filter_by(is_active=True).all()
            return jsonify([{
                'record_id': r.record_id,
                'document_type': r.document_type,
                'document_number': r.document_number,
                'document_name': r.document_name,
                'holder_name': r.holder_name,
                'issue_date': str(r.issue_date) if r.issue_date else None,
                'issuing_authority': r.issuing_authority,
                'status': r.status,
                'reference_file': r.reference_file
            } for r in records])
        finally:
            session.close()
            
    elif request.method == 'POST':
        data = request.get_json() or {}
        if not data.get('record_id') or not data.get('document_number'):
            return jsonify({'error': 'record_id and document_number are required'}), 400
        try:
            rec = current_app.registry_provider.add_or_update_record(data)
            return jsonify({'message': 'Record created/updated successfully', 'record_id': rec.record_id}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@api_bp.route('/registry/sync', methods=['POST'])
def api_registry_sync():
    try:
        stats = current_app.registry_provider.sync_folder()
        return jsonify({'message': 'Synchronization complete', 'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/dashboard', methods=['GET'])
def api_admin_stats():
    session = current_app.session_factory()
    try:
        total_verifs = session.query(VerificationHistory).count()
        verified = session.query(VerificationHistory).filter_by(record_status='VERIFIED').count()
        not_found = session.query(VerificationHistory).filter_by(record_status='RECORD NOT FOUND').count()
        authentic = session.query(VerificationHistory).filter_by(forensic_status='AUTHENTIC').count()
        manipulated = session.query(VerificationHistory).filter_by(forensic_status='POTENTIALLY MANIPULATED').count()
        inconclusive = session.query(VerificationHistory).filter_by(forensic_status='INCONCLUSIVE').count()

        return jsonify({
            'total_verifications': total_verifs,
            'verified_records': verified,
            'records_not_found': not_found,
            'authentic': authentic,
            'potentially_manipulated': manipulated,
            'inconclusive': inconclusive
        })
    finally:
        session.close()

@api_bp.route('/admin/model', methods=['GET'])
def api_admin_model():
    mgr = current_app.model_manager
    return jsonify({
        'is_trained': mgr.is_trained,
        'metadata': mgr.metadata,
        'feature_count': len(mgr.feature_names)
    })
