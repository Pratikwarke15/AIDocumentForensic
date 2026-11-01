import os
from pathlib import Path
from flask import Flask, render_template, send_from_directory, abort
from flask_login import LoginManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.config import Config
from app.models import Base, User
from app.verification.local_registry import LocalRegistryProvider
from app.ml.model_manager import ModelManager
from app.reports.pdf_generator import PDFReportGenerator
from app.services.verification_service import VerificationService
from app.services.audit_service import AuditService

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Database Setup
    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
        connect_args={'check_same_thread': False} if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI'] else {}
    )
    session_factory = scoped_session(sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine
    ))
    app.session_factory = session_factory
    app.db_engine = engine

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        session = session_factory()
        return session.query(User).get(int(user_id))

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        session_factory.remove()

    # Initialize Core Services
    registry_provider = LocalRegistryProvider(
        records_dir=app.config['VERIFICATION_RECORDS_DIR'],
        session_factory=session_factory
    )
    model_manager = ModelManager(models_dir=app.config['MODELS_DIR'])
    pdf_report_generator = PDFReportGenerator()
    audit_service = AuditService(session_factory=session_factory)
    
    verification_service = VerificationService(
        storage_dir=app.config['STORAGE_DIR'],
        session_factory=session_factory,
        registry_provider=registry_provider,
        model_manager=model_manager,
        pdf_report_generator=pdf_report_generator
    )

    app.registry_provider = registry_provider
    app.model_manager = model_manager
    app.pdf_report_generator = pdf_report_generator
    app.audit_service = audit_service
    app.verification_service = verification_service

    # Seed Default Admin and Demo Users
    session = session_factory()
    try:
        if not session.query(User).filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@forensics.gov.local', role='admin')
            admin_user.set_password('Admin@12345')
            session.add(admin_user)
            
        if not session.query(User).filter_by(username='demo').first():
            demo_user = User(username='demo', email='demo@forensics.local', role='user')
            demo_user.set_password('Demo@12345')
            session.add(demo_user)
            
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[Init] User seed notice: {e}")
    finally:
        session_factory.remove()

    # Sync local registry folder on startup
    try:
        registry_provider.sync_folder()
    except Exception as e:
        print(f"[Init] Initial registry sync notice: {e}")

    # Secure storage file serving route
    @app.route('/storage/<path:subpath>')
    def serve_storage_file(subpath):
        storage_root = Path(app.config['STORAGE_DIR']).resolve()
        target_path = (storage_root / subpath).resolve()
        
        # Path traversal protection
        if not str(target_path).startswith(str(storage_root)):
            abort(403)
        if not target_path.exists():
            abort(404)
            
        return send_from_directory(str(target_path.parent), target_path.name)

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.verify_routes import verify_bp
    from app.routes.search_routes import search_bp
    from app.routes.history_routes import history_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.registry_routes import registry_bp
    from app.routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(verify_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(registry_bp, url_prefix='/admin/registry')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Error Handlers
    @app.errorhandler(400)
    def bad_request_error(error):
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html', error=error), 500

    return app
