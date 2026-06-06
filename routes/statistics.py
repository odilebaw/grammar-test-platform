from datetime import datetime, timedelta
from collections import defaultdict

from flask import (Blueprint, render_template, redirect,
                   url_for, flash, session, request, jsonify)
from flask_login import login_required, current_user

from app import db
from models import User, GrammarTopic, Question, TestResult

stats_bp = Blueprint('stats', __name__, url_prefix='/admin/stats')


# ── Dekorator ─────────────────────────────────────────────────────────
def admin_required(f):
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


def student_required(f):
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


# ══════════════════════════════════════════════════════════════════════
# ADMIN — TO'LIQ STATISTIKA
# ══════════════════════════════════════════════════════════════════════
@stats_bp.route('/')
@login_required
@admin_required
def statistics():
    """Platforma bo'yicha to'liq statistika sahifasi."""

    # ── 1. Umumiy hisoblagichlar ──────────────────────────────────────
    total_students    = User.query.count()
    total_tests_taken = TestResult.query.count()
    total_topics      = GrammarTopic.query.count()
    total_questions   = Question.query.count()

    all_results = TestResult.query.all()
    overall_avg = None
    pass_count  = 0
    fail_count  = 0
    if all_results:
        scores      = [r.score_percentage for r in all_results]
        overall_avg = round(sum(scores) / len(scores), 1)
        pass_count  = sum(1 for s in scores if s >= 60)
        fail_count  = len(scores) - pass_count

    # ── 2. Mavzu bo'yicha statistika ──────────────────────────────────
    topic_stats = []
    for topic in GrammarTopic.query.order_by(GrammarTopic.title).all():
        t_results = TestResult.query.filter_by(topic_id=topic.id).all()
        q_count   = topic.questions.filter_by(is_active=True).count()
        if t_results:
            scores = [r.score_percentage for r in t_results]
            topic_stats.append({
                'id':        topic.id,
                'title':     topic.title,
                'level':     topic.difficulty_level,
                'attempts':  len(t_results),
                'avg_score': round(sum(scores) / len(scores), 1),
                'best':      round(max(scores), 1),
                'worst':     round(min(scores), 1),
                'pass_rate': round(sum(1 for s in scores if s >= 60) / len(scores) * 100, 1),
                'q_count':   q_count,
            })
    topic_stats.sort(key=lambda x: x['attempts'], reverse=True)

    # ── 3. Top-10 o'quvchilar (o'rtacha ball bo'yicha) ────────────────
    student_leaderboard = []
    for user in User.query.all():
        u_results = TestResult.query.filter_by(user_id=user.id).all()
        if u_results:
            scores = [r.score_percentage for r in u_results]
            student_leaderboard.append({
                'user':       user,
                'test_count': len(u_results),
                'avg_score':  round(sum(scores) / len(scores), 1),
                'best_score': round(max(scores), 1),
                'total_correct': sum(r.correct_answers for r in u_results),
                'total_questions': sum(r.total_questions for r in u_results),
            })
    student_leaderboard.sort(key=lambda x: x['avg_score'], reverse=True)
    top_students = student_leaderboard[:10]

    # ── 4. Eng faol o'quvchilar (test soni bo'yicha) ──────────────────
    most_active = sorted(student_leaderboard,
                         key=lambda x: x['test_count'], reverse=True)[:10]

    # ── 5. So'nggi 30 kun — kunlik testlar soni (Chart.js uchun) ──────
    today      = datetime.utcnow().date()
    date_range = [today - timedelta(days=i) for i in range(29, -1, -1)]
    daily_counts = defaultdict(int)
    for r in TestResult.query.filter(
            TestResult.completed_at >= datetime.utcnow() - timedelta(days=30)
    ).all():
        daily_counts[r.completed_at.date()] += 1

    chart_labels      = [d.strftime('%d.%m') for d in date_range]
    chart_daily_tests = [daily_counts.get(d, 0) for d in date_range]

    # ── 6. Mavzu bo'yicha o'rtacha ball (bar chart) ───────────────────
    chart_topic_labels = [t['title'][:20] for t in topic_stats]
    chart_topic_avgs   = [t['avg_score'] for t in topic_stats]

    # ── 7. Ball taqsimoti (donut chart): A'lo / Yaxshi / Qoniqarli / Qoniqarsiz
    grade_dist = {'excellent': 0, 'good': 0, 'average': 0, 'poor': 0}
    for r in all_results:
        s = r.score_percentage
        if   s >= 90: grade_dist['excellent'] += 1
        elif s >= 70: grade_dist['good']      += 1
        elif s >= 50: grade_dist['average']   += 1
        else:         grade_dist['poor']      += 1

    # ── 8. So'nggi 10 ta natija ───────────────────────────────────────
    recent_results = TestResult.query\
        .order_by(TestResult.completed_at.desc())\
        .limit(10).all()

    return render_template(
        'admin/statistics.html',
        total_students=total_students,
        total_tests_taken=total_tests_taken,
        total_topics=total_topics,
        total_questions=total_questions,
        overall_avg=overall_avg,
        pass_count=pass_count,
        fail_count=fail_count,
        topic_stats=topic_stats,
        top_students=top_students,
        most_active=most_active,
        recent_results=recent_results,
        # Chart data
        chart_labels=chart_labels,
        chart_daily_tests=chart_daily_tests,
        chart_topic_labels=chart_topic_labels,
        chart_topic_avgs=chart_topic_avgs,
        grade_dist=grade_dist,
        now=datetime.utcnow(),
    )


# ══════════════════════════════════════════════════════════════════════
# ADMIN — O'QUVCHILAR RO'YXATI
# ══════════════════════════════════════════════════════════════════════
@stats_bp.route('/students')
@login_required
@admin_required
def students():
    """Barcha ro'yxatdan o'tgan o'quvchilar."""
    search = request.args.get('q', '').strip()
    sort   = request.args.get('sort', 'newest')   # newest | tests | score

    query = User.query
    if search:
        like = f'%{search}%'
        query = query.filter(
            (User.username.ilike(like)) |
            (User.email.ilike(like))    |
            (User.first_name.ilike(like)) |
            (User.last_name.ilike(like))
        )

    all_users = query.all()

    student_data = []
    for user in all_users:
        u_results = TestResult.query.filter_by(user_id=user.id).all()
        scores    = [r.score_percentage for r in u_results]
        avg       = round(sum(scores) / len(scores), 1) if scores else None
        best      = round(max(scores), 1)               if scores else None
        last_test = max(r.completed_at for r in u_results) if u_results else None
        student_data.append({
            'user':       user,
            'test_count': len(u_results),
            'avg_score':  avg,
            'best_score': best,
            'last_test':  last_test,
        })

    # Saralash
    if sort == 'tests':
        student_data.sort(key=lambda x: x['test_count'], reverse=True)
    elif sort == 'score':
        student_data.sort(key=lambda x: (x['avg_score'] or 0), reverse=True)
    else:  # newest
        student_data.sort(key=lambda x: x['user'].created_at, reverse=True)

    total_users = len(student_data)
    active_users = sum(1 for s in student_data if s['test_count'] > 0)

    return render_template(
        'admin/students.html',
        student_data=student_data,
        search=search,
        sort=sort,
        total_users=total_users,
        active_users=active_users,
        now=datetime.utcnow(),
    )


# ══════════════════════════════════════════════════════════════════════
# ADMIN — BITTA O'QUVCHI TARIXI
# ══════════════════════════════════════════════════════════════════════
@stats_bp.route('/students/<int:user_id>')
@login_required
@admin_required
def student_detail(user_id):
    """Admin ko'zi bilan bitta o'quvchining to'liq tarixi."""
    user = User.query.get_or_404(user_id)
    return _render_history(user, admin_view=True)


# ══════════════════════════════════════════════════════════════════════
# STUDENT — O'Z TARIXI
# ══════════════════════════════════════════════════════════════════════
@stats_bp.route('/my-history')
@login_required
@student_required
def my_history():
    """O'quvchining o'z test tarixi."""
    return _render_history(current_user, admin_view=False)


# ── Umumiy render yordamchisi ─────────────────────────────────────────
def _render_history(user, admin_view: bool):
    topic_filter = request.args.get('topic_id', type=int)
    sort         = request.args.get('sort', 'newest')

    q = TestResult.query.filter_by(user_id=user.id)
    if topic_filter:
        q = q.filter_by(topic_id=topic_filter)

    results = q.order_by(TestResult.completed_at.desc()).all()

    # Client-side sort
    if sort == 'score_high':
        results.sort(key=lambda r: r.score_percentage, reverse=True)
    elif sort == 'score_low':
        results.sort(key=lambda r: r.score_percentage)
    # else: newest (already ordered by DB)

    # ── Statistika ────────────────────────────────────────────────────
    total      = len(results)
    scores     = [r.score_percentage for r in results]
    avg_score  = round(sum(scores) / total, 1) if total else None
    best_score = round(max(scores), 1)         if total else None
    worst_score= round(min(scores), 1)         if total else None
    pass_count = sum(1 for s in scores if s >= 60)
    fail_count = total - pass_count

    # Mavzu bo'yicha o'rtacha
    topic_breakdown = {}
    for r in TestResult.query.filter_by(user_id=user.id).all():
        tid = r.topic_id
        topic_breakdown.setdefault(tid, []).append(r.score_percentage)

    topic_summary = []
    for tid, sc in topic_breakdown.items():
        t = GrammarTopic.query.get(tid)
        if t:
            topic_summary.append({
                'title':     t.title,
                'attempts':  len(sc),
                'avg_score': round(sum(sc) / len(sc), 1),
                'best':      round(max(sc), 1),
            })
    topic_summary.sort(key=lambda x: x['avg_score'], reverse=True)

    # Mavzular filtr uchun
    all_topics = GrammarTopic.query.order_by(GrammarTopic.title).all()

    # Chart — kunlik natijalar (so'nggi 30 kun)
    today      = datetime.utcnow().date()
    date_range = [today - timedelta(days=i) for i in range(29, -1, -1)]
    daily_scores = defaultdict(list)
    for r in TestResult.query.filter_by(user_id=user.id).filter(
            TestResult.completed_at >= datetime.utcnow() - timedelta(days=30)
    ).all():
        daily_scores[r.completed_at.date()].append(r.score_percentage)

    chart_labels = [d.strftime('%d.%m') for d in date_range]
    chart_scores = [
        round(sum(daily_scores[d]) / len(daily_scores[d]), 1)
        if daily_scores[d] else None
        for d in date_range
    ]

    return render_template(
        'student/history.html',
        target_user=user,
        results=results,
        total=total,
        avg_score=avg_score,
        best_score=best_score,
        worst_score=worst_score,
        pass_count=pass_count,
        fail_count=fail_count,
        topic_summary=topic_summary,
        all_topics=all_topics,
        topic_filter=topic_filter,
        sort=sort,
        admin_view=admin_view,
        chart_labels=chart_labels,
        chart_scores=chart_scores,
        now=datetime.utcnow(),
    )
