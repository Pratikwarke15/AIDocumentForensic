from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        session = current_app.session_factory()
        user = session.query(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Account has been deactivated. Please contact an administrator.', 'danger')
                return render_template('login.html')

            login_user(user)
            current_app.audit_service.log('USER_LOGIN', user_id=user.id, ip_address=request.remote_addr)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        session = current_app.session_factory()
        if session.query(User).filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'danger')
            return render_template('register.html')

        try:
            user = User(username=username, email=email, role='user')
            user.set_password(password)
            session.add(user)
            session.commit()

            current_app.audit_service.log('USER_REGISTERED', user_id=user.id, details={'username': username, 'email': email}, ip_address=request.remote_addr)
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            session.rollback()
            flash(f'Registration error: {str(e)}', 'danger')

    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    uid = current_user.id
    logout_user()
    current_app.audit_service.log('USER_LOGOUT', user_id=uid, ip_address=request.remote_addr)
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('main.landing'))
