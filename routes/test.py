import random
from datetime import datetime, timezone

from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, session)
from flask_login import login_required, current_user

from app import db
from models import GrammarTopic, Question, TestResult

test_bp = Blueprint('test', __name__, url_prefix='/test')

# ── Sozlamalar ────────────────────────────────────────────────────────
QUESTIONS_PER_TEST = 20          # Har testda ko'rsatiladigan savollar soni
TIME_LIMIT_SECONDS = 20 * 60     # 20 daqiqa (soniyalarda)

OPTION_LETTERS = ['A', 'B', 'C', 'D']


# ── Yordamchi: faqat o'quvchilar ─────────────────────────────────────
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


# ── Yordamchi: savolni aralash variantlar bilan qaytarish ─────────────
def _shuffle_question(q):
    """
    Berilgan Question obyektini shablon uchun qulay dict-ga aylantiradi.
    Variantlar tartibi tasodifiy aralashtiriladi, lekin to'g'ri javob
    harfi yangi tartibga moslashtiriladi.
    """
    # Asl (harf → matn) juftliklar
    original = [
        ('A', q.option_a),
        ('B', q.option_b),
        ('C', q.option_c),
        ('D', q.option_d),
    ]
    random.shuffle(original)

    # Yangi tartibdagi variantlar: [(yangi_harf, matn), ...]
    options = []
    new_correct = 'A'
    for new_letter, (old_letter, text) in zip(OPTION_LETTERS, original):
        options.append((new_letter, text))
        if old_letter == q.correct_option:
            new_correct = new_letter

    return {
        'id':             q.id,
        'question_text':  q.question_text,
        'options':        options,          # [(harf, matn), ...]
        'correct_option': new_correct,      # Yangi tartibdagi to'g'ri harf
        'explanation':    q.explanation or '',
    }


# ── 1. Mavzular ro'yxati ──────────────────────────────────────────────
@test_bp.route('/topics')
@login_required
@student_required
def topics():
    """Barcha faol grammatika mavzulari."""
    all_topics = GrammarTopic.query.filter_by(is_active=True)\
                                   .order_by(GrammarTopic.title)\
                                   .all()

    # Har bir mavzu uchun foydalanuvchining natijalari
    user_results = {}
    for topic in all_topics:
        results = TestResult.query.filter_by(
            user_id=current_user.id,
            topic_id=topic.id
        ).order_by(TestResult.completed_at.desc()).all()
        user_results[topic.id] = results

    return render_template(
        'student/topics.html',
        topics=all_topics,
        user_results=user_results,
        now=datetime.utcnow(),
    )


# ── 2. Test boshlash ──────────────────────────────────────────────────
@test_bp.route('/start/<int:topic_id>')
@login_required
@student_required
def start_test(topic_id):
    """
    Tanlangan mavzu bo'yicha yangi test sessiyasini boshlaydi.
    Savollar va variantlar tasodifiy aralashtiriladi.
    """
    topic = GrammarTopic.query.get_or_404(topic_id)

    if not topic.is_active:
        flash("Bu mavzu hozirda mavjud emas.", 'warning')
        return redirect(url_for('test.topics'))

    # Faol savollarni olish
    all_questions = Question.query.filter_by(
        topic_id=topic_id, is_active=True
    ).all()

    if not all_questions:
        flash("Bu mavzuda hali savollar mavjud emas.", 'warning')
        return redirect(url_for('test.topics'))

    # Savollarni aralashtir va kerakli sonni ol
    random.shuffle(all_questions)
    selected = all_questions[:QUESTIONS_PER_TEST]

    # Har bir savol uchun variantlarni aralashtir
    shuffled = [_shuffle_question(q) for q in selected]

    # Sessiyaga test ma'lumotlarini saqlash
    # (server-side validation uchun to'g'ri javoblar saqlanadi)
    session['active_test'] = {
        'topic_id':   topic_id,
        'start_time': datetime.now(timezone.utc).isoformat(),
        'questions':  [
            {
                'id':             item['id'],
                'correct_option': item['correct_option'],
            }
            for item in shuffled
        ],
    }

    start_time_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    return render_template(
        'student/test.html',
        topic=topic,
        questions=shuffled,
        time_limit=TIME_LIMIT_SECONDS,
        start_time=start_time_str,
        now=datetime.utcnow(),
    )


# ── 3. Testni topshirish ──────────────────────────────────────────────
@test_bp.route('/submit/<int:topic_id>', methods=['POST'])
@login_required
@student_required
def submit_test(topic_id):
    """
    Foydalanuvchi javoblarini qabul qiladi, baholaydi va natijani
    ma'lumotlar bazasiga saqlaydi.
    """
    topic = GrammarTopic.query.get_or_404(topic_id)

    # ── Sessiya tekshiruvi ────────────────────────────────────────────
    active = session.get('active_test')
    if not active or active.get('topic_id') != topic_id:
        flash("Faol test topilmadi. Iltimos, qaytadan boshlang.", 'warning')
        return redirect(url_for('test.topics'))

    session_questions = active['questions']   # [{id, correct_option}, ...]
    start_iso         = active['start_time']

    # ── Vaqtni hisoblash (server-side) ───────────────────────────────
    try:
        start_dt = datetime.fromisoformat(start_iso)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        elapsed = int((datetime.now(timezone.utc) - start_dt).total_seconds())
    except Exception:
        elapsed = TIME_LIMIT_SECONDS

    # Server vaqtini cheklash: limitdan oshmasin
    elapsed = min(elapsed, TIME_LIMIT_SECONDS)

    # ── Baholash ──────────────────────────────────────────────────────
    correct_count = 0
    review_items  = []

    for sq in session_questions:
        qid            = sq['id']
        correct_option = sq['correct_option']          # Aralashtirilgan tartibdagi to'g'ri harf
        student_answer = request.form.get(f'answer_{qid}', '').strip().upper()
        is_correct     = (student_answer == correct_option) and bool(student_answer)
        answered       = bool(student_answer)

        if is_correct:
            correct_count += 1

        # Sharh uchun savol ma'lumotlarini qayta tiklash
        q_obj = Question.query.get(qid)
        if q_obj:
            # Aralashtirilgan variantlarni qayta yasash
            # (shablon uchun: student nima tanladi va to'g'risi qaysi)
            shuffled_q = _rebuild_options_for_review(q_obj, correct_option, student_answer)
            review_items.append({
                'question_text':  q_obj.question_text,
                'options':        shuffled_q['options'],
                'correct_option': correct_option,
                'student_answer': student_answer,
                'is_correct':     is_correct,
                'answered':       answered,
                'explanation':    q_obj.explanation or '',
            })

    total      = len(session_questions)
    score_pct  = round((correct_count / total * 100), 2) if total > 0 else 0.0

    # ── Natijani bazaga yozish ────────────────────────────────────────
    result = TestResult(
        user_id            = current_user.id,
        topic_id           = topic_id,
        total_questions    = total,
        correct_answers    = correct_count,
        score_percentage   = score_pct,
        time_taken_seconds = elapsed,
        completed_at       = datetime.utcnow(),
    )
    db.session.add(result)
    db.session.commit()

    # ── Sessiyadan testni o'chirish ───────────────────────────────────
    session.pop('active_test', None)

    return render_template(
        'student/results.html',
        topic=topic,
        result=result,
        review_items=review_items,
        now=datetime.utcnow(),
    )


# ── 4. Barcha natijalar ───────────────────────────────────────────────
@test_bp.route('/results')
@login_required
@student_required
def all_results():
    """Foydalanuvchining barcha test natijalari tarixi."""
    results = TestResult.query\
        .filter_by(user_id=current_user.id)\
        .order_by(TestResult.completed_at.desc())\
        .all()

    # Statistika
    total       = len(results)
    avg_score   = round(sum(r.score_percentage for r in results) / total, 1) if total else None
    best_score  = round(max(r.score_percentage for r in results), 1)         if total else None

    return render_template(
        'student/all_results.html',
        results=results,
        total=total,
        avg_score=avg_score,
        best_score=best_score,
        now=datetime.utcnow(),
    )


# ── Yordamchi: sharh uchun variantlarni qayta tiklash ─────────────────
def _rebuild_options_for_review(q_obj, correct_option_letter, student_answer):
    """
    Submit vaqtida sessiyadan olingan to'g'ri harf (aralashtirilgan tartibdagi)
    va o'quvchi javobi asosida options listini qayta tiklaydi.

    Muhim: biz submit paytida aralashtirilgan tartibni saqlamaganmiz,
    shuning uchun sharh uchun asl (A/B/C/D) tartibda ko'rsatamiz,
    lekin correct_option va student_answer ni asl harflarga moslaymiz.

    Yechim: sharh sahifasida faqat qaysi variant to'g'ri va qaysi
    variant tanlangani ko'rsatiladi — asl tartibda.
    """
    # Asl variantlar (A→option_a, ...)
    original = [
        ('A', q_obj.option_a),
        ('B', q_obj.option_b),
        ('C', q_obj.option_c),
        ('D', q_obj.option_d),
    ]

    # correct_option_letter — aralashtirilgan tartibdagi harf
    # Biz uni asl harfga moslashtira olmaymiz (tartib saqlanmagan)
    # Shuning uchun sharh sahifasi uchun qayta shuffle qilamiz,
    # ammo bu safar deterministik qilish uchun q.id asosida seed ishlatamiz
    rng = random.Random(q_obj.id)  # deterministik: har safar bir xil tartib
    shuffled_list = original[:]
    rng.shuffle(shuffled_list)

    # To'g'ri javob harfini deterministik tartibdan topamiz
    true_correct_letter = q_obj.correct_option   # Asl: A/B/C/D
    new_correct = 'A'
    for new_letter, (old_letter, _) in zip(OPTION_LETTERS, shuffled_list):
        if old_letter == true_correct_letter:
            new_correct = new_letter
            break

    options = [(nl, txt) for nl, (ol, txt) in zip(OPTION_LETTERS, shuffled_list)]

    return {
        'options':        options,
        'correct_option': new_correct,
    }
