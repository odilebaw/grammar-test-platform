"""
Ma'lumotlar bazasini ishga tushirish va birinchi admin yaratish skripti.

Ishlatish tartibi:
  python init_db.py

PythonAnywhere Bash konsolida:
  cd ~/grammar-test-platform
  python init_db.py
"""

import os
import sys
from datetime import datetime
from getpass import getpass

# Loyiha papkasini yo'lga qo'shish
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Admin, GrammarTopic, Question, TestResult


def init_database():
    """Barcha jadvallarni yaratish."""
    print("\n📦 Ma'lumotlar bazasi jadvallar yaratilmoqda...")
    db.create_all()
    print("✅ Barcha jadvallar muvaffaqiyatli yaratildi.")
    print(f"   - users          (foydalanuvchilar)")
    print(f"   - admins         (administratorlar)")
    print(f"   - grammar_topics (grammatika mavzulari)")
    print(f"   - questions      (savollar)")
    print(f"   - test_results   (test natijalari)")


def create_first_admin():
    """Birinchi admin hisobini yaratish."""
    print("\n👤 Birinchi admin hisobini yaratish")
    print("─" * 40)

    # Mavjud adminni tekshirish
    existing_count = Admin.query.count()
    if existing_count > 0:
        print(f"ℹ️  Tizimda allaqachon {existing_count} ta admin mavjud.")
        choice = input("Yangi admin qo'shishni xohlaysizmi? (ha/yo'q): ").strip().lower()
        if choice not in ('ha', 'h', 'yes', 'y'):
            print("ℹ️  Admin yaratish o'tkazib yuborildi.")
            return

    # Admin ma'lumotlarini kiritish
    while True:
        username = input("Admin foydalanuvchi nomi: ").strip()
        if not username:
            print("❌ Foydalanuvchi nomi bo'sh bo'lishi mumkin emas.")
            continue
        if Admin.query.filter_by(username=username).first():
            print(f"❌ '{username}' allaqachon mavjud. Boshqa nom tanlang.")
            continue
        break

    while True:
        email = input("Admin elektron pochta: ").strip()
        if not email or '@' not in email:
            print("❌ To'g'ri elektron pochta manzilini kiriting.")
            continue
        if Admin.query.filter_by(email=email).first():
            print(f"❌ '{email}' allaqachon ro'yxatdan o'tgan.")
            continue
        break

    full_name = input("Admin to'liq ismi (ixtiyoriy, Enter — o'tkazib yuborish): ").strip()

    while True:
        password = getpass("Parol (kamida 8 belgi): ")
        if len(password) < 8:
            print("❌ Parol kamida 8 ta belgidan iborat bo'lishi kerak.")
            continue
        confirm = getpass("Parolni tasdiqlang: ")
        if password != confirm:
            print("❌ Parollar mos kelmadi. Qayta urinib ko'ring.")
            continue
        break

    # Admin yaratish
    admin = Admin(
        username   = username,
        email      = email,
        full_name  = full_name or None,
        is_active  = True,
        created_at = datetime.utcnow(),
    )
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    print(f"\n✅ Admin muvaffaqiyatli yaratildi!")
    print(f"   Foydalanuvchi nomi : {username}")
    print(f"   Elektron pochta    : {email}")
    if full_name:
        print(f"   To'liq ismi        : {full_name}")
    print(f"   Tizimga kirish URL : /auth/login")


def create_sample_topics():
    """Namuna grammatika mavzulari qo'shish (ixtiyoriy)."""
    print("\n📚 Namuna mavzulari qo'shilsinmi?")
    choice = input("Namuna mavzularini qo'shish? (ha/yo'q): ").strip().lower()
    if choice not in ('ha', 'h', 'yes', 'y'):
        print("ℹ️  Namuna mavzular o'tkazib yuborildi.")
        return

    sample_topics = [
        {
            'title':           'Present Simple',
            'description':     'Hozirgi oddiy zamon — odatiy harakatlar va umumiy haqiqatlar.',
            'difficulty_level':'boshlangich',
        },
        {
            'title':           'Present Continuous',
            'description':     'Hozirgi davom etayotgan zamon — hozir sodir bo\'layotgan harakatlar.',
            'difficulty_level':'boshlangich',
        },
        {
            'title':           'Past Simple',
            'description':     'O\'tgan oddiy zamon — tugallangan harakatlar.',
            'difficulty_level':'boshlangich',
        },
        {
            'title':           'Present Perfect',
            'description':     'Hozirgi tugallangan zamon — tajriba va natijalarga urg\'u.',
            'difficulty_level':'orta',
        },
        {
            'title':           'Future Simple',
            'description':     'Kelasi oddiy zamon — will bilan kelajak harakatlar.',
            'difficulty_level':'boshlangich',
        },
        {
            'title':           'Passive Voice',
            'description':     'Noaniq nisbat — harakat bajaruvchi emas, natijaga urg\'u.',
            'difficulty_level':'orta',
        },
        {
            'title':           'Conditional Sentences',
            'description':     'Shart gaplari — 0, 1, 2, 3-tur shartlar.',
            'difficulty_level':'yuqori',
        },
        {
            'title':           'Modal Verbs',
            'description':     'Modal fe\'llar — can, could, must, should, may, might.',
            'difficulty_level':'orta',
        },
    ]

    added = 0
    skipped = 0
    for t in sample_topics:
        if GrammarTopic.query.filter_by(title=t['title']).first():
            skipped += 1
            continue
        topic = GrammarTopic(
            title            = t['title'],
            description      = t['description'],
            difficulty_level = t['difficulty_level'],
            is_active        = True,
            created_at       = datetime.utcnow(),
        )
        db.session.add(topic)
        added += 1

    db.session.commit()
    print(f"✅ {added} ta mavzu qo'shildi. {skipped} ta allaqachon mavjud bo'lgani o'tkazib yuborildi.")


def show_summary():
    """Ma'lumotlar bazasi holatini ko'rsatish."""
    print("\n📊 Ma'lumotlar bazasi holati:")
    print("─" * 40)
    print(f"   Administratorlar : {Admin.query.count()} ta")
    print(f"   O'quvchilar      : {User.query.count()} ta")
    print(f"   Mavzular         : {GrammarTopic.query.count()} ta")
    print(f"   Savollar         : {Question.query.count()} ta")
    print(f"   Test natijalari  : {TestResult.query.count()} ta")
    print("─" * 40)


def main():
    print("=" * 50)
    print("  Grammatika Test Platform — DB Initsializatsiya")
    print("=" * 50)

    config_name = os.environ.get('FLASK_CONFIG', 'production')
    print(f"\n⚙️  Konfiguratsiya: {config_name}")

    app = create_app(config_name)

    with app.app_context():
        # 1. Jadvallarni yaratish
        init_database()

        # 2. Birinchi admin yaratish
        create_first_admin()

        # 3. Namuna mavzular (ixtiyoriy)
        create_sample_topics()

        # 4. Yakuniy holat
        show_summary()

    print("\n🎉 Initsializatsiya yakunlandi!")
    print("   Saytingiz ishga tayyor. Tizimga kiring: /auth/login")
    print()


if __name__ == '__main__':
    main()
