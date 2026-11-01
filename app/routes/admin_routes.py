import os
import json
import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import User, Document, VerificationHistory, ForensicResult, ModelVersion, AuditLog, VerificationRecord
from app.routes.verify_routes import DOCUMENT_TYPES
from app.verification.excel_manager import DOCUMENT_SCHEMAS

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        abort(403)

@admin_bp.route('/')
def dashboard():
    session = current_app.session_factory()
    try:
        total_users = session.query(User).count()
        total_docs = session.query(Document).count()
        total_verifs = session.query(VerificationHistory).count()
        verified_records = session.query(VerificationHistory).filter_by(record_status='VERIFIED').count()
        records_not_found = session.query(VerificationHistory).filter_by(record_status='RECORD NOT FOUND').count()
        authentic_count = session.query(VerificationHistory).filter_by(forensic_status='AUTHENTIC').count()
        manipulated_count = session.query(VerificationHistory).filter_by(forensic_status='POTENTIALLY MANIPULATED').count()
        inconclusive_count = session.query(VerificationHistory).filter_by(forensic_status='INCONCLUSIVE').count()

        # Document Type Breakdown
        doc_type_counts = session.query(
            Document.document_type, func.count(Document.id)
        ).group_by(Document.document_type).all()

        # Recent suspicious documents
        suspicious_verifs = session.query(VerificationHistory).filter_by(
            forensic_status='POTENTIALLY MANIPULATED'
        ).order_by(VerificationHistory.timestamp.desc()).limit(6).all()

        # Recent overall verifications
        recent_verifs = session.query(VerificationHistory).order_by(
            VerificationHistory.timestamp.desc()
        ).limit(8).all()

        stats = {
            'total_users': total_users,
            'total_docs': total_docs,
            'total_verifs': total_verifs,
            'verified_records': verified_records,
            'records_not_found': records_not_found,
            'authentic_count': authentic_count,
            'manipulated_count': manipulated_count,
            'inconclusive_count': inconclusive_count,
            'doc_types': {dt: count for dt, count in doc_type_counts}
        }

        category_counts = {}
        for dt in DOCUMENT_TYPES:
            category_counts[dt] = session.query(VerificationRecord).filter_by(document_type=dt, is_active=True).count()
        total_registry_records = sum(category_counts.values())

        return render_template(
            'admin/dashboard.html',
            stats=stats,
            suspicious_verifs=suspicious_verifs,
            recent_verifs=recent_verifs,
            document_types=DOCUMENT_TYPES,
            category_counts=category_counts,
            total_registry_records=total_registry_records,
            document_schemas=DOCUMENT_SCHEMAS
        )
    finally:
        session.close()

@admin_bp.route('/models', methods=['GET', 'POST'])
def model_management():
    model_mgr = current_app.model_manager
    session = current_app.session_factory()
    
    if request.method == 'POST' and request.form.get('action') == 'retrain':
        try:
            # Trigger model retraining script
            import subprocess
            import sys
            script_path = Path(current_app.config['BASE_DIR']) / 'scripts' / 'train_model.py'
            
            proc = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
            if proc.returncode == 0:
                model_mgr.reload()
                current_app.audit_service.log('MODEL_RETRAINED', user_id=current_user.id, details={'output': proc.stdout[:200]}, ip_address=request.remote_addr)
                flash('Random Forest model retrained and reloaded successfully!', 'success')
            else:
                flash(f"Retraining error: {proc.stderr[:300]}", 'danger')
        except Exception as e:
            flash(f"Retraining exception: {str(e)}", 'danger')
        return redirect(url_for('admin.model_management'))

    try:
        model_versions = session.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()
        return render_template(
            'admin/models.html',
            is_trained=model_mgr.is_trained,
            metadata=model_mgr.metadata,
            feature_names=model_mgr.feature_names,
            model_versions=model_versions
        )
    finally:
        session.close()

@admin_bp.route('/users')
def user_management():
    session = current_app.session_factory()
    try:
        users = session.query(User).order_by(User.created_at.desc()).all()
        return render_template('admin/users.html', users=users)
    finally:
        session.close()

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
def toggle_user_status(user_id):
    if user_id == current_user.id:
        flash('You cannot deactivate your own administrative account.', 'warning')
        return redirect(url_for('admin.user_management'))

    session = current_app.session_factory()
    try:
        user = session.query(User).get(user_id)
        if user:
            user.is_active = not user.is_active
            session.commit()
            current_app.audit_service.log('USER_STATUS_TOGGLED', user_id=current_user.id, target_type='USER', target_id=str(user.id), details={'is_active': user.is_active}, ip_address=request.remote_addr)
            flash(f"User '{user.username}' status updated to {'Active' if user.is_active else 'Deactivated'}.", 'info')
        return redirect(url_for('admin.user_management'))
    finally:
        session.close()

@admin_bp.route('/users/<int:user_id>/toggle-role', methods=['POST'])
def toggle_user_role(user_id):
    if user_id == current_user.id:
        flash('You cannot change your own role.', 'warning')
        return redirect(url_for('admin.user_management'))

    session = current_app.session_factory()
    try:
        user = session.query(User).get(user_id)
        if user:
            user.role = 'admin' if user.role == 'user' else 'user'
            session.commit()
            current_app.audit_service.log('USER_ROLE_CHANGED', user_id=current_user.id, target_type='USER', target_id=str(user.id), details={'role': user.role}, ip_address=request.remote_addr)
            flash(f"User '{user.username}' role changed to '{user.role}'.", 'info')
        return redirect(url_for('admin.user_management'))
    finally:
        session.close()

@admin_bp.route('/audit')
def audit_logs():
    session = current_app.session_factory()
    try:
        logs = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
        return render_template('admin/audit.html', logs=logs)
    finally:
        session.close()
