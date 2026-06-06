import json
import re
import time
import os
from datetime import datetime

import google.generativeai as genai
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, session, jsonify)
from flask_login import login_required, current_user

from app import db
from models import GrammarTopic, Question

ai_bp = Blueprint('ai', __name__, url_prefix='/admin/ai')

# ── Sozlamalar ────────────────────────────────────────────────────────
# Gemini Free: max 15 req/min, 1M tokens/day (gemini-1.5-flash)
GEMINI_MODEL     = 'gemini-1.5-flash'
MAX_PER_BATCH    = 20      # Har bir Gemini so'rovida nechta savol so'raladi
RETRY_ATTEMPTS   = 3       # Xatolikda urinishlar soni
RETRY_DELAY_SEC  = 4       # Urinishlar orasidagi kutish


# ── Admin dekorator ───────────────────────────────────────────────────
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


# ── Gemini klientini sozlash ──────────────────────────────────────────
def _get_gemini_client():
    """Gemini API kalitini muhitdan oladi va klientni qaytaradi."""
    api_key = os.environ.get('GEMINI_API_KEY') or \
              os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY muhit o'zgaruvchisi topilmadi. "
            "PythonAnywhere → Web → Environment variables bo'limida sozlang."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


# ── Prompt quruvchi ───────────────────────────────────────────────────
def _build_prompt(topic_name: str, q_type: str, count: int) -> str:
    """
    Har bir savol turi uchun aniq strukturali JSON prompt yaratadi.
    Gemini javobini JSON array sifatida qaytarishi shart.
    """

    base = f"""
Sen ingliz tili grammatikasi bo'yicha professional test yaratuvchisan.
Mavzu: "{topic_name}"
Savol soni: {count}
MUHIM: Faqat sof JSON array qaytargin — boshqa hech qanday matn, izoh, markdown yo'q.
Izohlar (explanation) O'ZBEK tilida bo'lsin.
Savol matni INGLIZ tilida bo'lsin.
"""

    if q_type == 'multiple_choice':
        return base + """
Quyidagi formatda JSON array qaytargin:
[
  {
    "question_text": "She ___ to school every day.",
    "option_a": "go",
    "option_b": "goes",
    "option_c": "gone",
    "option_d": "going",
    "correct_option": "B",
    "explanation": "Uchinchi shaxs birlikda (she/he/it) hozirgi zamon fe'liga '-s' qo'shiladi."
  }
]
"""
    elif q_type == 'fill_blank':
        return base + """
To'ldirish uchun bo'sh joy ('___') bo'lgan savollar yarat.
To'g'ri javob option_a bo'lsin, qolgan 3 ta variant chalg'ituvchi bo'lsin.
correct_option har doim "A" bo'lsin.
[
  {
    "question_text": "She ___ to school every day. (go)",
    "option_a": "goes",
    "option_b": "go",
    "option_c": "went",
    "option_d": "going",
    "correct_option": "A",
    "explanation": "Uchinchi shaxs birlikda hozirgi zamon fe'liga '-s' qo'shiladi: 'goes'."
  }
]
"""
    else:  # true_false
        return base + """
True/False savollar yarat.
option_a = "True", option_b = "False", option_c = "True", option_d = "False" qo'y.
correct_option "A" (True) yoki "B" (False) bo'lsin.
[
  {
    "question_text": "The sentence 'She go to school' is grammatically correct.",
    "option_a": "True",
    "option_b": "False",
    "option_c": "True",
    "option_d": "False",
    "correct_option": "B",
    "explanation": "Bu gap noto'g'ri. To'g'ri variant: 'She goes to school' — uchinchi shaxs birlikda '-s' qo'shiladi."
  }
]
"""


# ── JSON parser ───────────────────────────────────────────────────────
def _parse_gemini_response(raw: str) -> list[dict]:
    """
    Gemini javobidan sof JSON array ajratib oladi.
    Markdown kod bloklari (```json ... ```) ni tozalaydi.
    """
    # Markdown bloklarini olib tashlash
    text = re.sub(r'```(?:json)?', '', raw).replace('```', '').strip()

    # Birinchi '[' dan oxirgi ']' gacha olish
    start = text.find('[')
    end   = text.rfind(']')
    if start == -1 or end == -1:
        raise ValueError("Javobda JSON array topilmadi.")

    json_str = text[start:end + 1]
    return json.loads(json_str)


# ── Savol validatori ──────────────────────────────────────────────────
def _validate_question(q: dict) -> bool:
    """Savolning majburiy maydonlarini tekshiradi."""
    required = ['question_text', 'option_a', 'option_b',
                'option_c', 'option_d', 'correct_option']
    if not all(k in q and str(q[k]).strip() for k in required):
        return False
    if q['correct_option'].upper() not in ('A', 'B', 'C', 'D'):
        return False
    return True


# ── Gemini dan savollar olish (batch + retry) ─────────────────────────
def _generate_questions_from_gemini(
        model, topic_name: str, q_type: str, count: int
) -> tuple[list[dict], list[str]]:
    """
    count ta savol hosil qiladi.
    MAX_PER_BATCH oshsa, so'rovlarni bo'lib yuboradi.
    (result_list, error_list) qaytaradi.
    """
    results: list[dict] = []
    errors:  list[str]  = []
    remaining = count

    while remaining > 0:
        batch = min(remaining, MAX_PER_BATCH)
        prompt = _build_prompt(topic_name, q_type, batch)

        success = False
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = model.generate_content(prompt)
                parsed   = _parse_gemini_response(response.text)
                valid    = [q for q in parsed if _validate_question(q)]
                results.extend(valid)
                if len(valid) < batch:
                    errors.append(
                        f"{q_type}: {batch} ta so'raldi, "
                        f"{len(valid)} ta yaroqli savol olindi."
                    )
                success = True
                break
            except Exception as e:
                if attempt < RETRY_ATTEMPTS:
                    time.sleep(RETRY_DELAY_SEC)
                else:
                    errors.append(f"{q_type} ({batch} ta) xatosi: {str(e)}")

        remaining -= batch
        # Free tier rate limit uchun qisqa pauza
        if remaining > 0:
            time.sleep(2)

    return results, errors


# ── Savollarni bazaga saqlash ─────────────────────────────────────────
def _save_to_db(topic_id: int, questions: list[dict]) -> int:
    """
    Validatsiyadan o'tgan savollarni Question jadvaliga saqlaydi.
    Saqlangan savollar sonini qaytaradi.
    """
    saved = 0
    for q in questions:
        try:
            obj = Question(
                topic_id      = topic_id,
                question_text = q['question_text'].strip(),
                option_a      = q['option_a'].strip(),
                option_b      = q['option_b'].strip(),
                option_c      = q['option_c'].strip(),
                option_d      = q['option_d'].strip(),
                correct_option= q['correct_option'].strip().upper(),
                explanation   = q.get('explanation', '').strip() or None,
                is_active     = True,
                created_at    = datetime.utcnow(),
            )
            db.session.add(obj)
            saved += 1
        except Exception:
            db.session.rollback()
            continue
    if saved:
        db.session.commit()
    return saved


# ══════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════

@ai_bp.route('/', methods=['GET'])
@login_required
@admin_required
def generator_page():
    """AI savol generatori sahifasi (GET)."""
    topics = GrammarTopic.query.filter_by(is_active=True)\
                               .order_by(GrammarTopic.title)\
                               .all()
    return render_template(
        'admin/ai_generator.html',
        topics=topics,
        now=datetime.utcnow(),
    )


@ai_bp.route('/generate', methods=['POST'])
@login_required
@admin_required
def generate():
    """
    AJAX endpoint — Gemini dan savollar generatsiya qiladi va
    ma'lumotlar bazasiga saqlaydi.
    JSON javob qaytaradi: { success, saved, errors, message }
    """
    # ── Form ma'lumotlarini olish ─────────────────────────────────────
    topic_id        = request.form.get('topic_id', type=int)
    topic_name_raw  = request.form.get('topic_name', '').strip()
    total_count     = request.form.get('question_count', type=int, default=10)
    q_types_raw     = request.form.getlist('question_types')   # ['multiple_choice', ...]

    # ── Validatsiya ───────────────────────────────────────────────────
    errors: list[str] = []

    if not q_types_raw:
        return jsonify(success=False,
                       message="Kamida bitta savol turini tanlang.",
                       errors=[], saved=0), 400

    if total_count < 1 or total_count > 200:
        return jsonify(success=False,
                       message="Savollar soni 1 dan 200 gacha bo'lishi kerak.",
                       errors=[], saved=0), 400

    # Mavzu nomi: mavjud mavzudan yoki qo'lda kiritilgan
    topic = None
    if topic_id:
        topic = GrammarTopic.query.get(topic_id)

    if topic:
        topic_name = topic.title
    elif topic_name_raw:
        # Yangi mavzu avtomatik yaratiladi
        existing = GrammarTopic.query.filter_by(title=topic_name_raw).first()
        if existing:
            topic = existing
        else:
            topic = GrammarTopic(
                title            = topic_name_raw,
                description      = f"AI tomonidan yaratilgan: {topic_name_raw}",
                difficulty_level = 'boshlangich',
                is_active        = True,
            )
            db.session.add(topic)
            db.session.commit()
        topic_name = topic.title
    else:
        return jsonify(success=False,
                       message="Mavzuni tanlang yoki yangi mavzu nomini kiriting.",
                       errors=[], saved=0), 400

    # ── Savollarni turlarga bo'lish ───────────────────────────────────
    # Agar bir nechta tur tanlangan bo'lsa, umumiy sonni teng bo'lish
    per_type   = total_count // len(q_types_raw)
    remainder  = total_count  % len(q_types_raw)
    counts     = {qt: per_type for qt in q_types_raw}
    # Qolgan savollarni birinchi turga qo'shish
    if remainder:
        counts[q_types_raw[0]] += remainder

    # ── Gemini klientini yaratish ─────────────────────────────────────
    try:
        model = _get_gemini_client()
    except ValueError as e:
        return jsonify(success=False, message=str(e), errors=[], saved=0), 500

    # ── Generatsiya ───────────────────────────────────────────────────
    all_questions: list[dict] = []
    for q_type, count in counts.items():
        if count < 1:
            continue
        q_list, q_errors = _generate_questions_from_gemini(
            model, topic_name, q_type, count
        )
        all_questions.extend(q_list)
        errors.extend(q_errors)

    if not all_questions:
        return jsonify(
            success=False,
            message="Gemini hech qanday savol yarata olmadi. "
                    "API kalitini va mavzu nomini tekshiring.",
            errors=errors,
            saved=0
        ), 500

    # ── Bazaga saqlash ────────────────────────────────────────────────
    saved = _save_to_db(topic.id, all_questions)

    return jsonify(
        success=True,
        saved=saved,
        topic=topic_name,
        errors=errors,
        message=f"✅ {saved} ta savol muvaffaqiyatli yaratildi va saqlandi!"
    )


@ai_bp.route('/topics-list', methods=['GET'])
@login_required
@admin_required
def topics_json():
    """Mavzular ro'yxatini JSON formatda qaytaradi (AJAX uchun)."""
    topics = GrammarTopic.query.filter_by(is_active=True)\
                               .order_by(GrammarTopic.title)\
                               .all()
    return jsonify([{'id': t.id, 'title': t.title} for t in topics])
