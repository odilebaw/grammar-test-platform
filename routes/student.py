from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user

from app import db
from models import GrammarTopic, TestResult

student_bp = Blueprint('student', __name__, url_prefix='/dashboard')


def student_required(f):
    """Faqat o'quvchilar uchun dekorator."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Iltimos, tizimga kiring.", 'info')
            return redirect(url_for('auth.login'))
        if session.get('user_type') == 'admin':
            flash("Bu sahifa faqat o'quvchilar uchun.", 'warning')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated


@student_bp.route('/')
@login_required
@student_required
def dashboard():
    """O'quvchi bosh paneli."""

    # ── Mavjud mavzular (faqat faollar) ──────────────────────────────
    topics = GrammarTopic.query.filter_by(is_active=True)\
                               .order_by(GrammarTopic.title)\
                               .all()

    # ── So'nggi 5 ta natija ───────────────────────────────────────────
    recent_results = TestResult.query\
        .filter_by(user_id=current_user.id)\
        .order_by(TestResult.completed_at.desc())\
        .limit(5)\
        .all()

    # ── Umumiy statistika ─────────────────────────────────────────────
    all_results = TestResult.query.filter_by(user_id=current_user.id).all()
    total_tests = len(all_results)

    avg_score  = None
    best_score = None
    if all_results:
        scores     = [r.score_percentage for r in all_results]
        avg_score  = sum(scores) / len(scores)
        best_score = max(scores)

    # ── Mavzu bo'yicha o'rtacha ball ──────────────────────────────────
    topic_stats = []
    for topic in topics:
        topic_results = TestResult.query.filter_by(
            user_id=current_user.id,
            topic_id=topic.id
        ).all()
        if topic_results:
            t_avg = sum(r.score_percentage for r in topic_results) / len(topic_results)
            topic_stats.append({
                'title':     topic.title,
                'avg_score': round(t_avg, 1),
            })
    # Eng past natijali mavzular yuqorida (zaif tomonlar birinchi)
    topic_stats.sort(key=lambda x: x['avg_score'])

    return render_template(
        'student/dashboard.html',
        topics=topics,
        recent_results=recent_results,
        total_tests=total_tests,
        avg_score=avg_score,
        best_score=best_score,
        topics_count=len(topics),
        topic_stats=topic_stats,
        now=datetime.utcnow(),
    )


@student_bp.route('/results')
@login_required
@student_required
def all_results():
    """O'quvchining barcha test natijalari — tarix sahifasiga yo'naltirish."""
    return redirect(url_for('stats.my_history'))


@student_bp.route('/test/<int:topic_id>')
@login_required
@student_required
def take_test(topic_id):
    """Test boshlash — test blueprint-ga yo'naltirish."""
    return redirect(url_for('test.start_test', topic_id=topic_id))


@student_bp.route('/topics')
@login_required
@student_required
def topics():
    """Mavzular sahifasiga yo'naltirish."""
    return redirect(url_for('test.topics'))
