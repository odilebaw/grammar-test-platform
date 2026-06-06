from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from models import User, Admin, GrammarTopic, Question, TestResult

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

PER_PAGE = 20  # Sahifa boshiga savollar soni


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
    total_students    = User.query.filter_by(is_active=True).count()
    total_tests_taken = TestResult.query.count()
    total_topics      = GrammarTopic.query.filter_by(is_active=True).count()
    total_questions   = Question.query.filter_by(is_active=True).count()

    recent_results = TestResult.query\
        .order_by(TestResult.completed_at.desc())\
        .limit(10).all()

    topic_stats = []
    for topic in GrammarTopic.query.filter_by(is_active=True).all():
        t_results = TestResult.query.filter_by(topic_id=topic.id).all()
        if t_results:
            t_avg = sum(r.score_percentage for r in t_results) / len(t_results)
            topic_stats.append({
                'title':     topic.title,
                'avg_score': round(t_avg, 1),
                'attempts':  len(t_results),
            })
    topic_stats.sort(key=lambda x: x['attempts'], reverse=True)

    new_students = User.query.order_by(User.created_at.desc()).limit(5).all()

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


@admin_bp.route('/topics/add', methods=['POST'])
@login_required
@admin_required
def add_topic():
    """Yangi mavzu qo'shish."""
    title            = request.form.get('title', '').strip()
    difficulty_level = request.form.get('difficulty_level', 'boshlangich').strip()
    description      = request.form.get('description', '').strip() or None

    if not title:
        flash("Mavzu nomi bo'sh bo'lishi mumkin emas.", 'danger')
        return redirect(url_for('admin.topics'))

    if GrammarTopic.query.filter_by(title=title).first():
        flash(f"'{title}' mavzusi allaqachon mavjud.", 'warning')
        return redirect(url_for('admin.topics'))

    topic = GrammarTopic(
        title=title,
        difficulty_level=difficulty_level,
        description=description,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.session.add(topic)
    db.session.commit()
    flash(f"'{title}' mavzusi muvaffaqiyatli qo'shildi.", 'success')
    return redirect(url_for('admin.topics'))


@admin_bp.route('/topics/<int:topic_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_topic(topic_id):
    """Mavzuni faollashtirish/o'chirish."""
    topic = GrammarTopic.query.get_or_404(topic_id)
    topic.is_active = not topic.is_active
    db.session.commit()
    state = "faollashtirildi" if topic.is_active else "o'chirildi"
    flash(f"'{topic.title}' mavzusi {state}.", 'success')
    return redirect(url_for('admin.topics'))


@admin_bp.route('/topics/<int:topic_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_topic(topic_id):
    """Mavzuni o'chirish (faqat savolsiz)."""
    topic = GrammarTopic.query.get_or_404(topic_id)
    q_count = topic.questions.count()
    if q_count > 0:
        flash(f"Avval mavzu ichidagi {q_count} ta savolni o'chiring.", 'danger')
        return redirect(url_for('admin.topics'))
    db.session.delete(topic)
    db.session.commit()
    flash(f"'{topic.title}' mavzusi o'chirildi.", 'success')
    return redirect(url_for('admin.topics'))


# ── Savollar boshqaruvi ───────────────────────────────────────────────

@admin_bp.route('/questions')
@login_required
@admin_required
def questions():
    """Savollar banki — filtr, qidiruv va sahifalash bilan."""
    topic_id = request.args.get('topic_id', type=int)
    search   = request.args.get('q', '').strip()
    sort     = request.args.get('sort', 'newest')
    page     = request.args.get('page', 1, type=int)

    query = Question.query

    if topic_id:
        query = query.filter_by(topic_id=topic_id)

    if search:
        query = query.filter(Question.question_text.ilike(f'%{search}%'))

    if sort == 'oldest':
        query = query.order_by(Question.created_at.asc())
    elif sort == 'topic':
        query = query.join(GrammarTopic).order_by(GrammarTopic.title.asc())
    else:  # newest
        query = query.order_by(Question.created_at.desc())

    all_questions = query.all()
    total_questions_count = Question.query.count()

    # Pagination
    total_pages   = max(1, (len(all_questions) + PER_PAGE - 1) // PER_PAGE)
    current_page  = max(1, min(page, total_pages))
    start         = (current_page - 1) * PER_PAGE
    page_questions = all_questions[start:start + PER_PAGE]

    # Build filter querystring for pagination links
    filter_parts = []
    if topic_id:
        filter_parts.append(f'topic_id={topic_id}')
    if search:
        filter_parts.append(f'q={search}')
    if sort != 'newest':
        filter_parts.append(f'sort={sort}')
    filter_qs = ('&' + '&'.join(filter_parts)) if filter_parts else ''

    all_topics = GrammarTopic.query.filter_by(is_active=True).all()

    return render_template(
        'admin/questions.html',
        questions=all_questions,
        page_questions=page_questions,
        topics=all_topics,
        selected_topic=topic_id,
        search=search,
        sort=sort,
        current_page=current_page,
        total_pages=total_pages,
        per_page=PER_PAGE,
        filter_qs=filter_qs,
        total_questions=total_questions_count,
        now=datetime.utcnow(),
    )


@admin_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(question_id):
    """Savolni o'chirish."""
    question = Question.query.get_or_404(question_id)
    topic_id = question.topic_id
    db.session.delete(question)
    db.session.commit()
    flash("Savol muvaffaqiyatli o'chirildi.", 'success')
    # Return to same filtered page
    ref = request.referrer
    if ref:
        return redirect(ref)
    return redirect(url_for('admin.questions', topic_id=topic_id))


# ── O'quvchilar boshqaruvi ────────────────────────────────────────────

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    """O'quvchilar ro'yxati."""
    all_students = User.query.order_by(User.created_at.desc()).all()
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
    """Platforma statistikasi (qisqacha) — to'liq statistikaga yo'naltirish."""
    return redirect(url_for('stats.statistics'))


# ── Barcha natijalar ──────────────────────────────────────────────────

@admin_bp.route('/results')
@login_required
@admin_required
def all_results():
    """Barcha o'quvchilarning test natijalari."""
    topic_id = request.args.get('topic_id', type=int)
    sort     = request.args.get('sort', 'newest')

    query = TestResult.query
    if topic_id:
        query = query.filter_by(topic_id=topic_id)

    results = query.order_by(TestResult.completed_at.desc()).all()

    if sort == 'score_high':
        results.sort(key=lambda r: r.score_percentage, reverse=True)
    elif sort == 'score_low':
        results.sort(key=lambda r: r.score_percentage)

    all_topics = GrammarTopic.query.filter_by(is_active=True).all()

    return render_template(
        'admin/results.html',
        results=results,
        topics=all_topics,
        selected_topic=topic_id,
        sort=sort,
        now=datetime.utcnow(),
    )
