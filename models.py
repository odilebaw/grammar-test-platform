from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class User(UserMixin, db.Model):
    """Foydalanuvchi modeli."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    test_results = db.relationship('TestResult', backref='user', lazy='dynamic')

    def set_password(self, password):
        """Parolni xeshlash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Parolni tekshirish."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Admin(UserMixin, db.Model):
    """Administrator modeli."""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        """Parolni xeshlash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Parolni tekshirish."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'


class GrammarTopic(db.Model):
    """Grammatika mavzulari modeli."""
    __tablename__ = 'grammar_topics'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    difficulty_level = db.Column(db.String(20), nullable=False, default='boshlangich')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = db.relationship('Question', backref='topic', lazy='dynamic')

    def __repr__(self):
        return f'<GrammarTopic {self.title}>'


class Question(db.Model):
    """Savollar modeli."""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('grammar_topics.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:50]}>'


class TestResult(db.Model):
    """Test natijalari modeli."""
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('grammar_topics.id'), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    score_percentage = db.Column(db.Float, nullable=False)
    time_taken_seconds = db.Column(db.Integer, nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    topic = db.relationship('GrammarTopic', backref='test_results')

    def __repr__(self):
        return f'<TestResult User:{self.user_id} Topic:{self.topic_id} Score:{self.score_percentage}%>'
