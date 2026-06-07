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
GEMINI_MODEL  = 'gemini-1.5-flash'
MAX_PER_BATCH = 20   # Har bir so'rovda so'raladigan max savol soni
BATCH_PAUSE   = 2    # Batch'lar orasida kutish (soniya), rate limit uchun


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


# ══════════════════════════════════════════════════════════════════════
# API KALIT ROTATSIYA TIZIMI
# ══════════════════════════════════════════════════════════════════════

def _load_api_keys() -> list[str]:
    """
    Muhit o'zgaruvchilaridan barcha mavjud Gemini API kalitlarini yuklaydi.

    Qidiruv tartibi:
      1. GEMINI_API_KEY_1 … GEMINI_API_KEY_4  (asosiy 4 ta kalit)
      2. GEMINI_API_KEY                         (yagona kalit, orqaga muvofiqlik)
      3. GOOGLE_API_KEY                         (muqobil nom)

    Faqat bo'sh bo'lmagan kalitlar ro'yxatga kiritiladi.
    Kamida 1 ta kalit bo'lishi shart — aks holda deploy bosqichida
    foydalanuvchi ogohlantirish oladi.
    """
    keys: list[str] = []

    # 4 ta raqamlangan kalit
    for i in range(1, 5):
        val = os.environ.get(f'GEMINI_API_KEY_{i}', '').strip()
        if val:
            keys.append(val)

    # Zahira: yagona eski kalit (agar raqamlangan kalitlar yo'q bo'lsa)
    if not keys:
        for name in ('GEMINI_API_KEY', 'GOOGLE_API_KEY'):
            val = os.environ.get(name, '').strip()
            if val:
                keys.append(val)
                break

    return keys


def _is_rate_limit_error(exc: Exception) -> bool:
    """
    Xato 429 (ResourceExhausted / rate limit) ekanligini aniqlaydi.
    google-generativeai kutubxonasi turli exception turlari ishlatadi —
    barcha holatlarni qamrab oluvchi keng tekshiruv amalga oshiriladi.
    """
    msg = str(exc).lower()
    return (
        '429'               in msg or
        'resource_exhausted' in msg or
        'resourceexhausted'  in msg or
        'rate limit'         in msg or
        'quota'              in msg or
        'too many requests'  in msg
    )


def _build_model_with_key(api_key: str) -> genai.GenerativeModel:
    """Berilgan kalit bilan yangi Gemini model obyektini yaratadi."""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


def _call_gemini_with_rotation(prompt: str) -> str:
    """
    Kalit rotatsiyasi bilan Gemini API ga so'rov yuboradi.

    Algoritm:
      for key_index in 0..N-1:
          model = build_model(keys[key_index])
          try:
              return model.generate_content(prompt).text
          except 429 → log, switch to next key, continue
          except other → raise immediately (dastur xatosi, retry foyda keltirmaydi)
      raise AllKeysExhaustedError

    Qaytaradi: str — Gemini javobining xom matni
    Chiqaradi:
        ValueError  — hech qanday kalit topilmadi
        RuntimeError — barcha kalitlar 429 qaytardi
        Exception   — boshqa turdagi xato (Gemini ichki xatosi va h.k.)
    """
    keys = _load_api_keys()

    if not keys:
        raise ValueError(
            "Gemini API kaliti topilmadi. "
            "PythonAnywhere → Web → Environment variables bo'limida "
            "GEMINI_API_KEY_1 (yoki GEMINI_API_KEY) ni sozlang."
        )

    exhausted_keys: list[int] = []   # 429 qaytargan kalit raqamlari (1-based)

    for idx, key in enumerate(keys):
        key_num = idx + 1
        try:
            model    = _build_model_with_key(key)
            response = model.generate_content(prompt)
            # Muvaffaqiyatli javob — qaysi kalit ishlashini log ga yozamiz
            if len(keys) > 1 and exhausted_keys:
                # Rotatsiya amalga oshdi — bu foydaliy ma'lumot
                pass  # (logging ixtiyoriy)
            return response.text

        except Exception as exc:
            if _is_rate_limit_error(exc):
                exhausted_keys.append(key_num)
                next_key_num = key_num + 1 if key_num < len(keys) else None
                # Keyingi kalit mavjud bo'lsa kutmasdan davom etamiz
                # (keyingi kalit allaqachon yangi quota bilan keladi)
                continue
            else:
                # 429 bo'lmagan xato — darhol chiqaramiz
                raise

    # Barcha kalitlar 429 qaytardi
    tried = ', '.join(f'#{n}' for n in exhausted_keys)
    raise RuntimeError(
        f"Barcha {len(keys)} ta Gemini API kaliti so'rovlar limitini (429) qaytardi "
        f"(tekshirilgan kalitlar: {tried}). "
        f"Bir necha daqiqadan so'ng qayta urinib ko'ring yoki "
        f"yangi API kalit qo'shing."
    )


# ══════════════════════════════════════════════════════════════════════
# PROMPT QURUVCHI
# ══════════════════════════════════════════════════════════════════════

def _build_prompt(topic_name: str, q_type: str, count: int) -> str:
    """Har bir savol turi uchun strukturali JSON prompt yaratadi."""
    base = (
        f'Sen ingliz tili grammatikasi bo\'yicha professional test yaratuvchisan.\n'
        f'Mavzu: "{topic_name}"\n'
        f'Savol soni: {count}\n'
        f'MUHIM: Faqat sof JSON array qaytargin — boshqa hech qanday matn, '
        f'izoh, markdown yo\'q.\n'
        f'Izohlar (explanation) O\'ZBEK tilida bo\'lsin.\n'
        f'Savol matni INGLIZ tilida bo\'lsin.\n'
    )

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


# ══════════════════════════════════════════════════════════════════════
# JSON PARSER + VALIDATSIYA
# ══════════════════════════════════════════════════════════════════════

def _parse_gemini_response(raw: str) -> list[dict]:
    """Gemini javobidan sof JSON array ajratib oladi."""
    text  = re.sub(r'```(?:json)?', '', raw).replace('```', '').strip()
    start = text.find('[')
    end   = text.rfind(']')
    if start == -1 or end == -1:
        raise ValueError("Javobda JSON array topilmadi.")
    return json.loads(text[start:end + 1])


def _validate_question(q: dict) -> bool:
    """Savolning majburiy maydonlarini tekshiradi."""
    required = ['question_text', 'option_a', 'option_b',
                'option_c', 'option_d', 'correct_option']
    if not all(k in q and str(q[k]).strip() for k in required):
        return False
    return q['correct_option'].upper() in ('A', 'B', 'C', 'D')


# ══════════════════════════════════════════════════════════════════════
# ASOSIY GENERATSIYA FUNKSIYASI
# ══════════════════════════════════════════════════════════════════════

def _generate_questions_from_gemini(
        topic_name: str, q_type: str, count: int
) -> tuple[list[dict], list[str]]:
    """
    count ta savol hosil qiladi.
    MAX_PER_BATCH dan oshsa, so'rovlarni bo'lib yuboradi.
    Har bir so'rovda kalit rotatsiyasi avtomatik ishlaydi.

    Qaytaradi: (savollar_ro'yxati, xatolar_ro'yxati)
    """
    results: list[dict] = []
    errors:  list[str]  = []
    remaining = count

    while remaining > 0:
        batch  = min(remaining, MAX_PER_BATCH)
        prompt = _build_prompt(topic_name, q_type, batch)

        try:
            raw_text = _call_gemini_with_rotation(prompt)
            parsed   = _parse_gemini_response(raw_text)
            valid    = [q for q in parsed if _validate_question(q)]
            results.extend(valid)

            if len(valid) < batch:
                errors.append(
                    f"{q_type}: {batch} ta so'raldi, "
                    f"{len(valid)} ta yaroqli savol olindi."
                )

        except (ValueError, RuntimeError) as exc:
            # Kalit yo'q yoki barcha kalitlar 429 — foydalanuvchiga Uzbek xabar
            errors.append(str(exc))
            break  # Davom etishdan ma'no yo'q

        except Exception as exc:
            errors.append(
                f"{q_type} ({batch} ta) generatsiyasida xatolik: {str(exc)}"
            )
            # Boshqa batch'larni sinab ko'rish uchun break qilmaymiz

        remaining -= batch
        if remaining > 0:
            time.sleep(BATCH_PAUSE)

    return results, errors


# ══════════════════════════════════════════════════════════════════════
# BAZAGA SAQLASH
# ══════════════════════════════════════════════════════════════════════

def _save_to_db(topic_id: int, questions: list[dict]) -> int:
    """Validatsiyadan o'tgan savollarni Question jadvaliga saqlaydi."""
    saved = 0
    for q in questions:
        try:
            obj = Question(
                topic_id       = topic_id,
                question_text  = q['question_text'].strip(),
                option_a       = q['option_a'].strip(),
                option_b       = q['option_b'].strip(),
                option_c       = q['option_c'].strip(),
                option_d       = q['option_d'].strip(),
                correct_option = q['correct_option'].strip().upper(),
                explanation    = q.get('explanation', '').strip() or None,
                is_active      = True,
                created_at     = datetime.utcnow(),
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
    topics = (GrammarTopic.query
              .filter_by(is_active=True)
              .order_by(GrammarTopic.title)
              .all())

    # Nechta kalit sozlanganligi haqida ma'lumot (shablon uchun)
    active_key_count = len(_load_api_keys())

    return render_template(
        'admin/ai_generator.html',
        topics=topics,
        active_key_count=active_key_count,
        now=datetime.utcnow(),
    )


@ai_bp.route('/generate', methods=['POST'])
@login_required
@admin_required
def generate():
    """
    AJAX endpoint — Gemini dan savollar generatsiya qiladi va bazaga saqlaydi.
    Qaytaradi: JSON { success, saved, errors, message }
    """
    topic_id       = request.form.get('topic_id', type=int)
    topic_name_raw = request.form.get('topic_name', '').strip()
    total_count    = request.form.get('question_count', type=int, default=10)
    q_types_raw    = request.form.getlist('question_types')

    # ── Validatsiya ───────────────────────────────────────────────────
    if not q_types_raw:
        return jsonify(success=False,
                       message="Kamida bitta savol turini tanlang.",
                       errors=[], saved=0), 400

    if not (1 <= total_count <= 200):
        return jsonify(success=False,
                       message="Savollar soni 1 dan 200 gacha bo'lishi kerak.",
                       errors=[], saved=0), 400

    # ── Mavzu ─────────────────────────────────────────────────────────
    topic = None
    if topic_id:
        topic = GrammarTopic.query.get(topic_id)

    if topic:
        topic_name = topic.title
    elif topic_name_raw:
        topic = GrammarTopic.query.filter_by(title=topic_name_raw).first()
        if not topic:
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

    # ── Savollarni turlarga taqsimlash ────────────────────────────────
    per_type  = total_count // len(q_types_raw)
    remainder = total_count  % len(q_types_raw)
    counts    = {qt: per_type for qt in q_types_raw}
    if remainder:
        counts[q_types_raw[0]] += remainder

    # ── Generatsiya (kalit rotatsiyasi avtomatik) ─────────────────────
    all_questions: list[dict] = []
    all_errors:    list[str]  = []

    for q_type, count in counts.items():
        if count < 1:
            continue
        q_list, q_errors = _generate_questions_from_gemini(
            topic_name, q_type, count
        )
        all_questions.extend(q_list)
        all_errors.extend(q_errors)

    if not all_questions:
        # Barcha xatolar allaqachon Uzbek tilida
        main_error = all_errors[0] if all_errors else (
            "Gemini hech qanday savol yarata olmadi. "
            "API kalitini va mavzu nomini tekshiring."
        )
        return jsonify(
            success=False,
            message=main_error,
            errors=all_errors,
            saved=0
        ), 500

    # ── Bazaga saqlash ────────────────────────────────────────────────
    saved = _save_to_db(topic.id, all_questions)

    return jsonify(
        success=True,
        saved=saved,
        topic=topic_name,
        errors=all_errors,
        message=f"✅ {saved} ta savol muvaffaqiyatli yaratildi va saqlandi!"
    )


@ai_bp.route('/topics-list', methods=['GET'])
@login_required
@admin_required
def topics_json():
    """Mavzular ro'yxatini JSON formatda qaytaradi (AJAX uchun)."""
    topics = (GrammarTopic.query
              .filter_by(is_active=True)
              .order_by(GrammarTopic.title)
              .all())
    return jsonify([{'id': t.id, 'title': t.title} for t in topics])
