"""
PythonAnywhere WSGI konfiguratsiya fayli.

PythonAnywhere Web sahifasida WSGI configuration file
qatoriga ushbu faylning to'liq yo'lini ko'rsating:
  /home/YOUR_USERNAME/grammar-test-platform/wsgi.py
"""

import sys
import os

# ── Loyiha papkasini Python yo'liga qo'shish ──────────────────────────
# YOUR_USERNAME ni o'zingizning PythonAnywhere foydalanuvchi nomiga almashtiring
project_home = '/home/YOUR_USERNAME/grammar-test-platform'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── Muhit o'zgaruvchilarini .env faylidan yuklash (ixtiyoriy) ─────────
# python-dotenv o'rnatilgan bo'lsa ishlatiladi
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(project_home, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
except ImportError:
    pass  # python-dotenv yo'q — muhit o'zgaruvchilari PythonAnywhere panelidan sozlangan

# ── Muhit turini ishlab chiqarish rejimiga o'rnatish ──────────────────
os.environ.setdefault('FLASK_CONFIG', 'production')

# ── Flask ilovasini yaratish ──────────────────────────────────────────
from app import create_app

application = create_app('production')
