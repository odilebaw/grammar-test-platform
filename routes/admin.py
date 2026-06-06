from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from models import User, Admin, GrammarTopic, Question, TestResult

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Faqat adminlar uchun dekorator."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Iltimos, tizimga kiring.", 'info')
            return redirect(url_for('auth.login'))
        if session.get('user_type') != 'admin':
            flash("Bu sahifaga kirish huquqingiz yo'q.", 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── Asosiy panel ──────────────────────────────────────────────────────

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin bosh paneli."""

    # ── Umumiy hisoblagichlar ─────────────────────────────────────────
    total_students    = User.query.filter_by(is_active=True).count()
    total_tests_taken = TestResult.query.count()
    total_topics      = GrammarTopic.query.filter_by(is_active=True).count()
    total_questions   = Question.query.filter_by(is_active=True).count()

    # ── So'nggi 10 ta natija ──────────────────────────────────────────
    recent_results = TestResult.query\
        .order_by(TestResult.completed_at.desc())\
        .limit(10)\
        .all()

    # ── Mavzu bo'yicha statistika ─────────────────────────────────────
    topic_stats = []
    topics = GrammarTopic.query.filter_by(is_active=True).all()
    for topic in topics:
        t_results = TestResult.query.filter_by(topic_id=topic.id).all()
        if t_results:
            t_avg = sum(r.score_percentage for r in t_results) / len(t_results)
            topic_stats.append({
                'title':     topic.title,
                'avg_score': round(t_avg, 1),
                'attempts':  len(t_results),
            })
    topic_stats.sort(key=lambda x: x['attempts'], reverse=True)

    # ── Eng yangi o'quvchilar (oxirgi 5 ta) ──────────────────────────
    new_students = User.query\
        .order_by(User.created_at.desc())\
        .limit(5)\
        .all()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_tests_taken=total_tests_taken,
        total_topics=total_topics,
        total_questions=total_questions,
        recent_results=recent_results,
        topic_stats=topic_stats,
        new_students=new_students,
        now=datetime.utcnow(),
    )


# ── Mavzular boshqaruvi ───────────────────────────────────────────────

@admin_bp.route('/topics')
@login_required
@admin_required
def topics():
    """Grammatika mavzulari ro'yxati."""
    all_topics = GrammarTopic.query.order_by(GrammarTopic.created_at.desc()).all()
    return render_template(
        'admin/topics.html',
        topics=all_topics,
        now=datetime.utcnow(),
    )


# ── Savollar boshqaruvi ───────────────────────────────────────────────

@admin_bp.route('/questions')
@login_required
@admin_required
def questions():
    """Savollar banki ro'yxati."""
    topic_id = request.args.get('topic_id', type=int)
    query = Question.query

    if topic_id:
        query = query.filter_by(topic_id=topic_id)

    all_questions = query.order_by(Question.created_at.desc()).all()
    all_topics    = GrammarTopic.query.filter_by(is_active=True).all()

    return render_template(
        'admin/questions.html',
        questions=all_questions,
        topics=all_topics,
        selected_topic=topic_id,
        now=datetime.utcnow(),
    )


# ── O'quvchilar boshqaruvi ────────────────────────────────────────────

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    """O'quvchilar ro'yxati."""
    all_students = User.query.order_by(User.created_at.desc()).all()

    # Har bir o'quvchi uchun test soni va o'rtacha ball
    student_data = []
    for student in all_students:
        results = TestResult.query.filter_by(user_id=student.id).all()
        avg = round(sum(r.score_percentage for r in results) / len(results), 1) \
              if results else None
        student_data.append({
            'user':       student,
            'test_count': len(results),
            'avg_score':  avg,
        })

    return render_template(
        'admin/students.html',
        student_data=student_data,
        now=datetime.utcnow(),
    )


# ── Statistika ────────────────────────────────────────────────────────

@admin_bp.route('/statistics')
@login_required
@admin_required
def statistics():
    """Platforma statistikasi."""
    total_students    = User.query.count()
    total_tests_taken = TestResult.query.count()
    total_topics      = GrammarTopic.query.count()
    total_questions   = Question.query.count()

    all_results = TestResult.query.all()
    overall_avg = None
    if all_results:
        overall_avg = round(
            sum(r.score_percentage for r in all_results) / len(all_results), 1
        )

    # Mavzu bo'yicha to'liq statistika
    topic_stats = []
    for topic in GrammarTopic.query.all():
        t_results = TestResult.query.filter_by(topic_id=topic.id).all()
        if t_results:
            scores = [r.score_percentage for r in t_results]
            topic_stats.append({
                'title':     topic.title,
                'attempts':  len(t_results),
                'avg_score': round(sum(scores) / len(scores), 1),
                'best':      round(max(scores), 1),
                'worst':     round(min(scores), 1),
            })
    topic_stats.sort(key=lambda x: x['attempts'], reverse=True)

    return render_template(
        'admin/statistics.html',
        total_students=total_students,
        total_tests_taken=total_tests_taken,
        total_topics=total_topics,
        total_questions=total_questions,
        overall_avg=overall_avg,
        topic_stats=topic_stats,
        now=datetime.utcnow(),
    )


# ── Barcha natijalar ──────────────────────────────────────────────────

@admin_bp.route('/results')
@login_required
@admin_required
def all_results():
    """Barcha o'quvchilarning test natijalari."""
    topic_id = request.args.get('topic_id', type=int)
    query = TestResult.query

    if topic_id:
        query = query.filter_by(topic_id=topic_id)

    results    = query.order_by(TestResult.completed_at.desc()).all()
    all_topics = GrammarTopic.query.filter_by(is_active=True).all()

    return render_template(
        'admin/results.html',
        results=results,
        topics=all_topics,
        selected_topic=topic_id,
        now=datetime.utcnow(),
    )
