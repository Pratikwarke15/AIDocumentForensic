import os
import json
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import VerificationRecord
from app.routes.verify_routes import DOCUMENT_TYPES
from app.verification.excel_manager import generate_excel_template, import_records_to_registry, DOCUMENT_SCHEMAS

registry_bp = Blueprint('registry', __name__)

@registry_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        abort(403)

@registry_bp.route('/')
def list_records():
    session = current_app.session_factory()
    try:
        category_filter = request.args.get('category', '').strip()
        search_query = request.args.get('q', '').strip()

        query = session.query(VerificationRecord).filter_by(is_active=True)
        if category_filter:
            query = query.filter_by(document_type=category_filter)
        if search_query:
            query = query.filter(
                (VerificationRecord.document_number.ilike(f"%{search_query}%")) |
                (VerificationRecord.holder_name.ilike(f"%{search_query}%")) |
                (VerificationRecord.record_id.ilike(f"%{search_query}%"))
            )

        records = query.order_by(VerificationRecord.last_synced_at.desc()).all()
        inactive_count = session.query(VerificationRecord).filter_by(is_active=False).count()

        # Group counts by document type
        category_counts = {}
        for dt in DOCUMENT_TYPES:
            category_counts[dt] = session.query(VerificationRecord).filter_by(document_type=dt, is_active=True).count()

        return render_template(
            'admin/registry.html',
            records=records,
            inactive_count=inactive_count,
            document_types=DOCUMENT_TYPES,
            category_counts=category_counts,
            current_category=category_filter,
            search_query=search_query
        )
    finally:
        session.close()

@registry_bp.route('/template/<doc_type>')
def download_template(doc_type):
    """
    Generates and returns an official Excel template (.xlsx) with pre-filled headers
    and realistic sample records for the requested document category.
    """
    try:
        buffer, filename = generate_excel_template(doc_type)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if filename.endswith('.xlsx') else 'text/csv'
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
    except Exception as e:
        flash(f"Error generating template for '{doc_type}': {str(e)}", 'danger')
        return redirect(url_for('registry.list_records'))

@registry_bp.route('/upload-excel', methods=['POST'])
def upload_excel():
    """
    Parses and synchronizes records from an uploaded Excel (.xlsx, .xls) or .csv file
    into the database and filesystem registry.
    """
    doc_type = request.form.get('document_type', '').strip()
    file_obj = request.files.get('excel_file')

    if not doc_type or not file_obj or not file_obj.filename:
        flash('Please select a Document Category and an Excel/CSV file to upload.', 'danger')
        return redirect(url_for('registry.list_records'))

    filename = secure_filename(file_obj.filename)
    if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
        flash('Only .xlsx, .xls, and .csv spreadsheet formats are supported.', 'danger')
        return redirect(url_for('registry.list_records'))

    try:
        file_bytes = file_obj.read()
        stats = import_records_to_registry(
            file_bytes=file_bytes,
            filename=filename,
            doc_type=doc_type,
            session_factory=current_app.session_factory,
            registry_provider=getattr(current_app, 'registry_provider', None)
        )

        current_app.audit_service.log(
            'REGISTRY_EXCEL_IMPORTED',
            user_id=current_user.id,
            target_type='DOCUMENT_REGISTRY',
            target_id=doc_type,
            details=stats,
            ip_address=request.remote_addr
        )

        success_msg = f"Excel Import Complete for '{doc_type}': {stats['added']} records added, {stats['updated']} updated."
        if stats['errors']:
            flash(f"{success_msg} (Notice: {len(stats['errors'])} rows skipped due to missing required fields).", 'warning')
        else:
            flash(success_msg, 'success')

    except Exception as e:
        flash(f"Failed to import Excel file: {str(e)}", 'danger')

    return redirect(url_for('registry.list_records'))

@registry_bp.route('/add', methods=['POST'])
def add_record():
    record_id = request.form.get('record_id', '').strip()
    doc_type = request.form.get('document_type', '').strip()
    doc_number = request.form.get('document_number', '').strip()
    doc_name = request.form.get('document_name', '').strip() or doc_type
    holder_name = request.form.get('holder_name', '').strip()
    issue_date = request.form.get('issue_date', '').strip()
    issuing_authority = request.form.get('issuing_authority', '').strip()
    
    ref_file = request.files.get('reference_file')
    ref_filename = None
    if ref_file and ref_file.filename:
        ref_filename = secure_filename(ref_file.filename)
        folder = current_app.registry_provider._get_category_folder(doc_type)
        ref_file.save(folder / ref_filename)

    if not record_id or not doc_number or not holder_name or not issuing_authority:
        flash('Record ID, Document Number, Holder Name, and Issuing Authority are mandatory.', 'danger')
        return redirect(url_for('registry.list_records'))

    data = {
        'record_id': record_id,
        'document_type': doc_type,
        'document_number': doc_number,
        'document_name': doc_name,
        'holder_name': holder_name,
        'issue_date': issue_date,
        'issuing_authority': issuing_authority,
        'status': 'VERIFIED'
    }

    try:
        current_app.registry_provider.add_or_update_record(data, reference_filename=ref_filename)
        current_app.audit_service.log('REGISTRY_RECORD_ADDED', user_id=current_user.id, target_type='REGISTRY_RECORD', target_id=record_id, details=data, ip_address=request.remote_addr)
        flash(f"Record '{record_id}' added to local registry and synchronized successfully!", 'success')
    except Exception as e:
        flash(f"Error adding record: {str(e)}", 'danger')

    return redirect(url_for('registry.list_records'))

@registry_bp.route('/edit/<record_id>', methods=['POST'])
def edit_record(record_id):
    doc_type = request.form.get('document_type', '').strip()
    doc_number = request.form.get('document_number', '').strip()
    doc_name = request.form.get('document_name', '').strip()
    holder_name = request.form.get('holder_name', '').strip()
    issue_date = request.form.get('issue_date', '').strip()
    issuing_authority = request.form.get('issuing_authority', '').strip()

    data = {
        'record_id': record_id,
        'document_type': doc_type,
        'document_number': doc_number,
        'document_name': doc_name,
        'holder_name': holder_name,
        'issue_date': issue_date,
        'issuing_authority': issuing_authority,
        'status': 'VERIFIED'
    }

    try:
        current_app.registry_provider.add_or_update_record(data)
        current_app.audit_service.log('REGISTRY_RECORD_EDITED', user_id=current_user.id, target_type='REGISTRY_RECORD', target_id=record_id, details=data, ip_address=request.remote_addr)
        flash(f"Record '{record_id}' updated successfully!", 'success')
    except Exception as e:
        flash(f"Error updating record: {str(e)}", 'danger')

    return redirect(url_for('registry.list_records'))

@registry_bp.route('/delete/<record_id>', methods=['POST'])
def delete_record(record_id):
    try:
        success = current_app.registry_provider.delete_record(record_id)
        if success:
            current_app.audit_service.log('REGISTRY_RECORD_DELETED', user_id=current_user.id, target_type='REGISTRY_RECORD', target_id=record_id, ip_address=request.remote_addr)
            flash(f"Record '{record_id}' deleted from folder and registry database.", 'info')
        else:
            flash(f"Record '{record_id}' not found.", 'warning')
    except Exception as e:
        flash(f"Error deleting record: {str(e)}", 'danger')

    return redirect(url_for('registry.list_records'))

@registry_bp.route('/sync', methods=['POST'])
def sync_folder():
    try:
        stats = current_app.registry_provider.sync_folder()
        current_app.audit_service.log('REGISTRY_FOLDER_SYNC', user_id=current_user.id, details=stats, ip_address=request.remote_addr)
        flash(f"Registry synchronized! Added: {stats['added']}, Updated: {stats['updated']}, Deactivated: {stats['deactivated']}. Total Active: {stats['total_active']}.", 'success')
    except Exception as e:
        flash(f"Registry synchronization error: {str(e)}", 'danger')

    return redirect(url_for('registry.list_records'))
