import os
from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

from config import config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

login_manager.login_view = 'auth.login'
login_manager.login_message = "Iltimos, tizimga kiring."
login_manager.login_message_category = 'info'


def create_app(config_name=None):
    """Ilova fabrikasi — Flask ilovasini yaratish."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ── Kengaytmalarni bog'lash ───────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # ── Foydalanuvchi yuklash (Admin + User) ─────────────────────────
    @login_manager.user_loader
    def load_user(user_id):
        from flask import session
        from models import User, Admin
        user_type = session.get('user_type')
        if user_type == 'admin':
            return Admin.query.get(int(user_id))
        return User.query.get(int(user_id))

    # ── Barcha blueprintlarni ro'yxatga olish ────────────────────────
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.admin import admin_bp
    from routes.test import test_bp
    from routes.ai_generator import ai_bp
    from routes.statistics import stats_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(stats_bp)

    # ── Asosiy yo'nalish ─────────────────────────────────────────────
    @app.route('/')
    def index():
        """Bosh sahifa: kirgan foydalanuvchini yo'naltirish."""
        from flask_login import current_user
        from flask import session
        if current_user.is_authenticated:
            if session.get('user_type') == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))
        return render_template('index.html')

    # ── Xato sahifalari ──────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # ── Barcha jadvallarni yaratish ──────────────────────────────────
    with app.app_context():
        from models import User, Admin, GrammarTopic, Question, TestResult
        db.create_all()

    return app


# ── Lokal ishga tushirish ─────────────────────────────────────────────
if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5000)
