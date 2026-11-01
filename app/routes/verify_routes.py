from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, abort
from flask_login import login_required, current_user
from app.models import Document, VerificationHistory, ForensicResult
from app.services.file_service import FileValidationError

verify_bp = Blueprint('verify', __name__)

DOCUMENT_TYPES = [
    'Aadhaar',
    'PAN',
    'Marksheet',
    'Certificate',
    'Caste Certificate',
    'Income Certificate',
    'Domicile Certificate',
    'Driving Licence',
    'Other'
]

@verify_bp.route('/verify', methods=['GET', 'POST'])
@login_required
def upload_and_verify():
    if request.method == 'POST':
        doc_type = request.form.get('document_type')
        doc_number = request.form.get('document_number', '').strip()
        doc_name = request.form.get('document_name', '').strip()
        holder_name = request.form.get('holder_name', '').strip()
        issue_date_str = request.form.get('issue_date', '').strip() or None
        file_obj = request.files.get('document_file')

        if not doc_type or not doc_number or not holder_name or not file_obj or not file_obj.filename:
            flash('Document Type, Document Number, Holder Name, and Document File are required.', 'danger')
            return render_template('verify.html', document_types=DOCUMENT_TYPES)

        try:
            res = current_app.verification_service.process_and_verify_document(
                file_storage=file_obj,
                doc_type=doc_type,
                doc_number=doc_number,
                doc_name=doc_name or f"{doc_type} - {doc_number}",
                holder_name=holder_name,
                issue_date_str=issue_date_str,
                user_id=current_user.id
            )

            current_app.audit_service.log(
                'DOCUMENT_VERIFIED',
                user_id=current_user.id,
                target_type='DOCUMENT',
                target_id=res['document_id'],
                details={
                    'document_number': doc_number,
                    'record_status': res['record_status'],
                    'forensic_status': res['forensic_status'],
                    'confidence': res['confidence']
                },
                ip_address=request.remote_addr
            )

            flash('Document analyzed and verified successfully!', 'success')
            return redirect(url_for('verify.view_result', v_id=res['verification_id']))

        except FileValidationError as e:
            flash(f"File Validation Error: {str(e)}", 'danger')
        except Exception as e:
            flash(f"Verification Pipeline Error: {str(e)}", 'danger')

    return render_template('verify.html', document_types=DOCUMENT_TYPES)

@verify_bp.route('/verifications/<int:v_id>')
@login_required
def view_result(v_id):
    session = current_app.session_factory()
    try:
        verification = session.query(VerificationHistory).get(v_id)
        if not verification:
            abort(404)

        if not current_user.is_admin and verification.user_id != current_user.id:
            abort(403)

        document = verification.document
        forensic_res = verification.forensic_result

        features = forensic_res.get_features() if forensic_res else {}
        metadata = forensic_res.get_metadata() if forensic_res else {}
        ocr_data = forensic_res.get_ocr() if forensic_res else {}
        signals = forensic_res.get_signals() if forensic_res else {}

        # Query previous verifications for this document number
        history_count = session.query(VerificationHistory).join(Document).filter(
            Document.document_number == document.document_number
        ).count()

        # Check local registry record details
        reg_record = current_app.registry_provider.verify_document(
            document_type=document.document_type,
            document_number=document.document_number,
            holder_name=document.holder_name,
            issue_date=document.issue_date.strftime('%Y-%m-%d') if document.issue_date else None
        )

        return render_template(
            'result.html',
            verification=verification,
            document=document,
            forensic_res=forensic_res,
            features=features,
            metadata=metadata,
            ocr_data=ocr_data,
            signals=signals,
            reg_record=reg_record,
            history_count=history_count
        )
    finally:
        session.close()

@verify_bp.route('/verifications/<int:v_id>/report')
@login_required
def download_report(v_id):
    session = current_app.session_factory()
    try:
        verification = session.query(VerificationHistory).get(v_id)
        if not verification:
            abort(404)

        if not current_user.is_admin and verification.user_id != current_user.id:
            abort(403)

        report_path = Path(verification.report_path) if verification.report_path else None
        if not report_path or not report_path.exists():
            if report_path:
                rel_path = current_app.config['STORAGE_DIR'] / 'reports' / report_path.name
                if rel_path.exists():
                    report_path = rel_path
        if not report_path or not report_path.exists():
            flash('PDF report is currently unavailable.', 'warning')
            return redirect(url_for('verify.view_result', v_id=v_id))

        return send_file(
            str(report_path),
            as_attachment=True,
            download_name=f"Forensic_Report_{verification.document.document_number}.pdf",
            mimetype='application/pdf'
        )
    finally:
        session.close()
