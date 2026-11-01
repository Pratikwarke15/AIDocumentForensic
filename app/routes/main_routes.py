from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from app.models import Document, VerificationHistory, VerificationRecord

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def landing():
    return render_template('landing.html')

@main_bp.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    session = current_app.session_factory()
    try:
        # User statistics
        q_user = session.query(VerificationHistory)
        if not current_user.is_admin:
            q_user = q_user.filter_by(user_id=current_user.id)

        total_verifications = q_user.count()
        verified_records = q_user.filter_by(record_status='VERIFIED').count()
        manipulated_count = q_user.filter_by(forensic_status='POTENTIALLY MANIPULATED').count()
        authentic_count = q_user.filter_by(forensic_status='AUTHENTIC').count()

        recent_verifications = q_user.order_by(VerificationHistory.timestamp.desc()).limit(8).all()
        
        # Total local registry active records
        total_registry_records = session.query(VerificationRecord).filter_by(is_active=True).count()

        return render_template(
            'dashboard.html',
            total_verifications=total_verifications,
            verified_records=verified_records,
            manipulated_count=manipulated_count,
            authentic_count=authentic_count,
            total_registry_records=total_registry_records,
            recent_verifications=recent_verifications
        )
    finally:
        session.close()
