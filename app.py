import os

from flask import Flask
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
    """Ilova fabrikasi - Flask ilovasini yaratish."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    @login_manager.user_loader
    def load_user(user_id):
        from flask import session
        from models import User, Admin
        user_type = session.get('user_type')
        if user_type == 'admin':
            return Admin.query.get(int(user_id))
        return User.query.get(int(user_id))

    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    with app.app_context():
        from models import User, Admin, GrammarTopic, Question, TestResult
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
