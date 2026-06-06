from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from models import User, Admin

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Foydalanuvchi va admin login sahifasi."""
    if current_user.is_authenticated:
        if session.get('user_type') == 'admin':
            return redirect('/admin')
        return redirect('/dashboard')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        if not username or not password:
            flash("Iltimos, barcha maydonlarni to'ldiring.", 'danger')
            return render_template('auth/login.html')

        # Avval admin jadvalidan tekshiramiz
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            if not admin.is_active:
                flash("Sizning hisobingiz faol emas.", 'warning')
                return render_template('auth/login.html')
            login_user(admin, remember=bool(remember))
            session['user_type'] = 'admin'
            flash("Tizimga muvaffaqiyatli kirdingiz!", 'success')
            return redirect('/admin')

        # Keyin oddiy foydalanuvchini tekshiramiz
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Sizning hisobingiz faol emas.", 'warning')
                return render_template('auth/login.html')
            login_user(user, remember=bool(remember))
            session['user_type'] = 'user'
            flash("Tizimga muvaffaqiyatli kirdingiz!", 'success')
            return redirect('/dashboard')

        flash("Foydalanuvchi nomi yoki parol noto'g'ri.", 'danger')
        return render_template('auth/login.html')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Yangi foydalanuvchi ro'yxatdan o'tish sahifasi."""
    if current_user.is_authenticated:
        return redirect('/dashboard')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if not username or not email or not password:
            flash("Iltimos, barcha majburiy maydonlarni to'ldiring.", 'danger')
            return render_template('auth/register.html')

        if password != password_confirm:
            flash("Parollar mos kelmadi.", 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash("Parol kamida 6 ta belgidan iborat bo'lishi kerak.", 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash("Bu foydalanuvchi nomi allaqachon mavjud.", 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash("Bu elektron pochta allaqachon ro'yxatdan o'tgan.", 'danger')
            return render_template('auth/register.html')

        user = User(
            username=username,
            email=email,
            first_name=first_name or None,
            last_name=last_name or None
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Ro'yxatdan muvaffaqiyatli o'tdingiz! Endi tizimga kirishingiz mumkin.", 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Foydalanuvchini tizimdan chiqarish."""
    session.pop('user_type', None)
    logout_user()
    flash("Tizimdan muvaffaqiyatli chiqdingiz.", 'info')
    return redirect(url_for('auth.login'))
