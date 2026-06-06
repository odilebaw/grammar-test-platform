# 🚀 PythonAnywhere — To'liq Joylashtirish Qo'llanmasi

**Grammatika Test Platform** — bosqichma-bosqich o'rnatish yo'riqnomasi  
Daraja: Yangi boshlovchilar uchun | Platforma: PythonAnywhere Free Tarif

---

## 📋 MUNDARIJA

1. [PythonAnywhere hisobi yaratish](#1-pythonanywhere-hisobi-yaratish)
2. [Fayllarni yuklash](#2-fayllarni-yuklash)
3. [Virtual muhit va paketlarni o'rnatish](#3-virtual-muhit-va-paketlarni-ornatish)
4. [WSGI faylini sozlash](#4-wsgi-faylini-sozlash)
5. [Muhit o'zgaruvchilarini sozlash](#5-muhit-ozgaruvchilarini-sozlash)
6. [Ma'lumotlar bazasini ishga tushirish](#6-malumotlar-bazasini-ishga-tushirish)
7. [Web ilovasini ishga tushirish](#7-web-ilovasini-ishga-tushirish)
8. [Saytni tekshirish](#8-saytni-tekshirish)
9. [Gemini API kalitini ulash](#9-gemini-api-kalitini-ulash)
10. [Muammolarni hal qilish](#10-muammolarni-hal-qilish)
11. [Muhim eslatmalar](#11-muhim-eslatmalar)

---

## 1. PythonAnywhere Hisobi Yaratish

### 1.1 Ro'yxatdan o'tish

1. Brauzeringizda **[www.pythonanywhere.com](https://www.pythonanywhere.com)** saytini oching
2. Yuqori o'ng burchakdagi **"Pricing & signup"** tugmasini bosing
3. **"Create a Beginner account"** (Bepul tarif) ni tanlang
4. Quyidagi ma'lumotlarni to'ldiring:
   - **Username** — foydalanuvchi nomingiz _(muhim: bu sayt manzilingiz bo'ladi)_
   - **Email** — elektron pochta manzilingiz
   - **Password** — kuchli parol
5. **"Register"** tugmasini bosing
6. Elektron pochtangizga kelgan tasdiqlash xatini tasdiqlang

> ⚠️ **Diqqat:** Tanlagan username saytingiz manziliga kiradi:  
> `https://USERNAME.pythonanywhere.com`  
> Masalan: `https://alibek.pythonanywhere.com`

---

## 2. Fayllarni Yuklash

### 2.1 Loyiha fayllarini zip arxivga soling (lokal kompyuterda)

Loyiha papkangizni `.zip` formatga siqing. Papka tarkibi:

```
grammar-test-platform.zip
├── app.py
├── config.py
├── models.py
├── wsgi.py
├── init_db.py
├── requirements.txt
├── .env.example
├── .gitignore
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── admin.py
│   ├── student.py
│   ├── test.py
│   ├── ai_generator.py
│   └── statistics.py
└── templates/
    ├── base.html
    ├── index.html
    ├── admin/
    ├── auth/
    ├── errors/
    └── student/
```

### 2.2 PythonAnywhere Files sahifasiga o'ting

1. Dashboard (bosh sahifa) da **"Files"** tugmasini bosing
2. Siz hozir `/home/USERNAME/` papkadasiz

### 2.3 Loyiha papkasini yarating

1. **"New directory"** maydoniga `grammar-test-platform` yozing
2. **"New directory"** tugmasini bosing
3. Yangi papkaga kiring: `grammar-test-platform` ni bosing

### 2.4 Zip faylni yuklash

1. **"Upload a file"** tugmasini bosing
2. `grammar-test-platform.zip` faylini tanlang
3. Yuklash tugaguncha kuting

### 2.5 Zip faylni ochish

1. Dashboard da **"Consoles"** bo'limiga o'ting
2. **"Bash"** ni bosib yangi konsol oching
3. Quyidagi buyruqlarni kiriting:

```bash
cd ~/grammar-test-platform
unzip grammar-test-platform.zip
ls -la
```

> Agar fayllar ichki papkada bo'lsa (`grammar-test-platform/grammar-test-platform/`):
> ```bash
> mv grammar-test-platform/* .
> rm -rf grammar-test-platform
> ```

---

## 3. Virtual Muhit va Paketlarni O'rnatish

### 3.1 Virtual muhit yaratish

Bash konsolida quyidagi buyruqni bajaring:

```bash
cd ~
python3.10 -m venv grammar_venv
```

> 💡 **Eslatma:** PythonAnywhere da Python 3.10 tavsiya etiladi.  
> Mavjud versiyalarni tekshirish: `python3.10 --version`

### 3.2 Virtual muhitni faollashtirish

```bash
source ~/grammar_venv/bin/activate
```

Buyruq satrining boshi `(grammar_venv)` ga o'zgarishi kerak:
```
(grammar_venv) 12:34 ~ $
```

### 3.3 Paketlarni o'rnatish

```bash
cd ~/grammar-test-platform
pip install --upgrade pip
pip install -r requirements.txt
```

O'rnatish bir necha daqiqa davom etadi. Barcha paketlar muvaffaqiyatli o'rnatilganini tekshirish:

```bash
pip list
```

Quyidagi paketlar ro'yxatda bo'lishi kerak:
- `Flask`
- `Flask-SQLAlchemy`
- `Flask-Login`
- `Flask-WTF`
- `Flask-Migrate`
- `google-generativeai`

---

## 4. WSGI Faylini Sozlash

### 4.1 Web ilovasini yaratish

1. Dashboard da **"Web"** tugmasini bosing
2. **"Add a new web app"** tugmasini bosing
3. **"Next"** ni bosing (domen nomi tasdiqlash)
4. **"Manual configuration"** ni tanlang _(Flask emas!)_
5. **"Python 3.10"** ni tanlang
6. **"Next"** ni bosing

### 4.2 WSGI faylini tahrirlash

1. "Web" sahifasida **"WSGI configuration file"** qatorini toping
2. Ko'k havolani bosing (masalan: `/var/www/USERNAME_pythonanywhere_com_wsgi.py`)
3. Fayl ochiladi — **barcha mavjud kodni o'chirib** quyidagini yozing:

```python
import sys
import os

# Loyiha yo'lini qo'shish — USERNAME ni o'zingiznikiga almashtiring
project_home = '/home/USERNAME/grammar-test-platform'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Ishlab chiqarish rejimi
os.environ['FLASK_CONFIG'] = 'production'

# Flask ilovasini yuklash
from app import create_app
application = create_app('production')
```

> ⚠️ **`USERNAME`** ni o'zingizning PythonAnywhere foydalanuvchi nomingizga almashtiring!

4. **"Save"** tugmasini bosing

### 4.3 Virtualenv yo'lini sozlash

"Web" sahifasida **"Virtualenv"** bo'limiga o'ting:

1. **"Enter path to a virtualenv"** maydoniga kiriting:
   ```
   /home/USERNAME/grammar_venv
   ```
2. Belgini bosib tasdiqlang (✓)

### 4.4 Static fayllar yo'lini sozlash

"Web" sahifasida **"Static files"** bo'limiga o'ting:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/USERNAME/grammar-test-platform/static/` |

_(Agar `static/` papkangiz bo'lmasa, keyinchalik qo'shiladi)_

---

## 5. Muhit O'zgaruvchilarini Sozlash

### 5.1 Maxfiy kalitlarni yaratish

Bash konsolida:

```bash
# SECRET_KEY yaratish
python3 -c "import secrets; print('SECRET_KEY:', secrets.token_hex(32))"

# WTF_CSRF_SECRET_KEY yaratish
python3 -c "import secrets; print('WTF_CSRF_SECRET_KEY:', secrets.token_hex(24))"
```

Natijalarni nusxalab saqlang!

### 5.2 Gemini API kalitini olish

1. **[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)** saytiga o'ting
2. Google hisobingiz bilan kiring
3. **"Create API key"** tugmasini bosing
4. **"Create API key in new project"** ni tanlang
5. Yaratilgan kalitni nusxalab oling: `AIza...`

> 💡 Bepul tarif: 15 so'rov/daqiqa, 1 million token/kun — loyiha uchun yetarli.

### 5.3 Muhit o'zgaruvchilarini WSGI faylga qo'shish

WSGI faylini qayta oching va `os.environ['FLASK_CONFIG']` qatoridan keyin qo'shing:

```python
import sys
import os

project_home = '/home/USERNAME/grammar-test-platform'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── Muhit o'zgaruvchilari ──────────────────────────────────────────────
os.environ['FLASK_CONFIG']       = 'production'
os.environ['SECRET_KEY']         = 'BU_YERGA_YARATGAN_SECRET_KEY_INGIZNI_KIRITING'
os.environ['WTF_CSRF_SECRET_KEY']= 'BU_YERGA_YARATGAN_CSRF_KEY_INGIZNI_KIRITING'
os.environ['GEMINI_API_KEY']     = 'BU_YERGA_GEMINI_API_KALIT_INGIZNI_KIRITING'

# Ma'lumotlar bazasi — to'liq yo'l
os.environ['DATABASE_URL'] = 'sqlite:////home/USERNAME/grammar-test-platform/grammar_test.db'

from app import create_app
application = create_app('production')
```

**Saqlang.**

> 🔒 **Xavfsizlik:** Hech qachon haqiqiy kalitlarni GitHub yoki ochiq joylarga yuklamang!

---

## 6. Ma'lumotlar Bazasini Ishga Tushirish

### 6.1 init_db.py skriptini ishga tushirish

Bash konsolida:

```bash
# Virtual muhitni faollashtirish
source ~/grammar_venv/bin/activate

# Loyiha papkasiga o'tish
cd ~/grammar-test-platform

# Muhit o'zgaruvchilarini o'rnatish
export FLASK_CONFIG=production
export SECRET_KEY="yaratgan_secret_key_ingiz"
export DATABASE_URL="sqlite:////home/USERNAME/grammar-test-platform/grammar_test.db"

# Ma'lumotlar bazasini ishga tushirish
python init_db.py
```

### 6.2 Skript so'ragan ma'lumotlarni kiriting

```
==================================================
  Grammatika Test Platform — DB Initsializatsiya
==================================================

⚙️  Konfiguratsiya: production

📦 Ma'lumotlar bazasi jadvallar yaratilmoqda...
✅ Barcha jadvallar muvaffaqiyatli yaratildi.

👤 Birinchi admin hisobini yaratish
────────────────────────────────────────
Admin foydalanuvchi nomi: admin
Admin elektron pochta: admin@example.com
Admin to'liq ismi: Sarvar Karimov
Parol (kamida 8 belgi): ••••••••
Parolni tasdiqlang: ••••••••

✅ Admin muvaffaqiyatli yaratildi!

Namuna mavzularini qo'shish? (ha/yo'q): ha
✅ 8 ta mavzu qo'shildi.

🎉 Initsializatsiya yakunlandi!
```

### 6.3 Ma'lumotlar bazasi faylini tekshirish

```bash
ls -lh ~/grammar-test-platform/grammar_test.db
```

Fayl ko'rinishi kerak, masalan: `grammar_test.db  48K`

---

## 7. Web Ilovasini Ishga Tushirish

### 7.1 Web ilovasini qayta yuklash

1. PythonAnywhere **"Web"** sahifasiga qayting
2. Yashil **"Reload USERNAME.pythonanywhere.com"** tugmasini bosing
3. Tugma aylanib to'xtashi va yashil bo'lishi kutiladi

### 7.2 Xato jurnalini tekshirish (agar kerak bo'lsa)

"Web" sahifasida **"Log files"** bo'limida:
- **Error log** — xatolarni ko'rish
- **Access log** — kirish jurnali
- **Server log** — server xatolari

---

## 8. Saytni Tekshirish

### 8.1 Saytni brauzerda oching

```
https://USERNAME.pythonanywhere.com
```

Quyidagi sahifalar ishlashi kerak:

| URL | Tavsif |
|-----|--------|
| `/` | Bosh sahifa (Kirish / Ro'yxatdan o'tish tugmalari) |
| `/auth/login` | Tizimga kirish |
| `/auth/register` | Yangi hisob yaratish |
| `/admin/` | Admin paneli (admin kirishi kerak) |
| `/dashboard/` | O'quvchi paneli |
| `/test/topics` | Mavzular ro'yxati |

### 8.2 Admin sifatida kirish

1. `https://USERNAME.pythonanywhere.com/auth/login` ga o'ting
2. `init_db.py` da yaratgan **admin username** va **parolni** kiriting
3. Avtomatik `/admin/` sahifasiga yo'naltirilasiz

### 8.3 O'quvchi hisob yaratish va test

1. Boshqa brauzer yoki inkognito rejimda `https://USERNAME.pythonanywhere.com/auth/register` ga o'ting
2. Yangi o'quvchi hisobi yarating
3. Tizimga kiring — `/dashboard/` ko'rinishi kerak
4. Mavzu tanlang va test boshlang

---

## 9. Gemini API Kalitini Ulash

### 9.1 API kalitini WSGI faylida tekshirish

WSGI faylida `GEMINI_API_KEY` to'g'ri o'rnatilganini tekshiring.

### 9.2 AI generatorni sinash

1. Admin sifatida kiring
2. **"Admin paneli" → "AI Savol Generatori"** (`/admin/ai/`) ga o'ting
3. Mavzu tanlang: masalan "Present Simple"
4. Savol turi: **Ko'p tanlov**
5. Son: **10**
6. **"AI bilan savollar yaratish"** tugmasini bosing
7. Yashil muvaffaqiyat xabari ko'rinishi kerak

> ⏳ **Kutish vaqti:** 10 ta savol ~15-30 soniya, 100 ta savol ~3-5 daqiqa.

---

## 10. Muammolarni Hal Qilish

### ❌ "500 Internal Server Error"

**Sabab:** Odatda import xatosi yoki noto'g'ri yo'l.

**Yechim:**
```bash
# Error log ni tekshirish
tail -50 /var/log/USERNAME.pythonanywhere.com.error.log
```

Eng ko'p uchraydigan xatolar:

| Xato | Yechim |
|------|--------|
| `ModuleNotFoundError: No module named 'flask'` | Virtual muhit to'g'ri sozlanmagan. Virtualenv yo'lini tekshiring |
| `ModuleNotFoundError: No module named 'routes'` | `project_home` yo'li noto'g'ri. USERNAME ni tekshiring |
| `OperationalError: no such table` | `python init_db.py` qayta ishga tushiring |
| `SECRET_KEY` xatosi | WSGI faylida `SECRET_KEY` o'rnatilganini tekshiring |

### ❌ "No such file or directory: grammar_test.db"

```bash
# To'liq yo'l bilan ishga tushirish
cd ~/grammar-test-platform
export DATABASE_URL="sqlite:////home/USERNAME/grammar-test-platform/grammar_test.db"
python init_db.py
```

### ❌ "CSRF token missing or incorrect"

**Sabab:** `WTF_CSRF_SECRET_KEY` o'rnatilmagan.

**Yechim:** WSGI faylida `WTF_CSRF_SECRET_KEY` qatorini tekshiring va Web ilovasini qayta yuklang.

### ❌ Gemini API ishlamayapti

```bash
# API kalitini tekshirish
source ~/grammar_venv/bin/activate
python3 -c "
import os
os.environ['GEMINI_API_KEY'] = 'KALIT_INGIZNI_BU_YERGA_QOYINGIZ'
import google.generativeai as genai
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')
r = model.generate_content('Say hello in one word')
print('OK:', r.text)
"
```

### ❌ Sayt juda sekin yuklanyapti

PythonAnywhere Free tarif cheklovlari:
- CPU sekundlari cheklangan (har kuni yangilanadi)
- Tashqi so'rovlar (Gemini API) faqat **"allowed sites"** orqali ishlaydi

**Yechim:** PythonAnywhere → "Network" — `generativelanguage.googleapis.com` qo'shilganligini tekshiring.

### ❌ Static fayllar (CSS/JS) yuklanmayapti

"Web" sahifasida "Static files" bo'limini tekshiring:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/USERNAME/grammar-test-platform/static/` |

Web ilovasini qayta yuklang.

---

## 11. Muhim Eslatmalar

### 🆓 PythonAnywhere Free Tarif Cheklovlari

| Resurs | Limit |
|--------|-------|
| Disk hajmi | 512 MB |
| CPU vaqti | 100 CPU soniya/kun |
| Tashqi so'rovlar | Faqat ruxsat etilgan domenlar |
| Ma'lumotlar bazasi | SQLite (MySQL ham bepul tarif bilan mavjud) |
| Domen nomi | `USERNAME.pythonanywhere.com` |
| Web app soni | 1 ta |

### 🔒 Xavfsizlik Tavsiyalari

1. **`SECRET_KEY`** — har doim tasodifiy, kamida 32 belgi
2. **`.env` fayli** — hech qachon GitHub ga yuklamang (`.gitignore` ga qo'shilgan)
3. **Admin paroli** — kamida 12 ta belgi, harf+raqam+belgi
4. **`DEBUG = False`** — ishlab chiqarishda albatta o'chirilgan bo'lishi kerak
5. **Ma'lumotlar bazasi** — muntazam zaxira nusxa oling

### 💾 Ma'lumotlar Bazasini Zaxiralash

```bash
# Har kuni zaxira nusxasi (PythonAnywhere "Tasks" orqali sozlang)
cp ~/grammar-test-platform/grammar_test.db \
   ~/grammar-test-platform/backups/grammar_test_$(date +%Y%m%d).db
```

### 🔄 Saytni Yangilash

Fayllarni o'zgartirganingizdan so'ng:

```bash
# Fayllarni yangilash
cd ~/grammar-test-platform
# ... fayllarni o'zgartiring ...

# Web ilovasini qayta yuklash (buyruq satridan)
touch /var/www/USERNAME_pythonanywhere_com_wsgi.py
```

Yoki PythonAnywhere "Web" sahifasida **"Reload"** tugmasini bosing.

### 📧 Yordam va Resurslar

| Resurs | Havola |
|--------|--------|
| PythonAnywhere rasmiy hujjatlar | [help.pythonanywhere.com](https://help.pythonanywhere.com) |
| Flask hujjatlar | [flask.palletsprojects.com](https://flask.palletsprojects.com) |
| Gemini API | [ai.google.dev](https://ai.google.dev) |
| PythonAnywhere Forum | [www.pythonanywhere.com/forums](https://www.pythonanywhere.com/forums) |

---

## ✅ Yakuniy Tekshiruv Ro'yxati

Saytni ochishdan oldin quyidagilarni tekshiring:

- [ ] `grammar_test.db` fayli yaratilgan
- [ ] Kamida 1 ta admin hisobi mavjud
- [ ] WSGI faylida `SECRET_KEY` o'rnatilgan
- [ ] WSGI faylida `DATABASE_URL` to'liq yo'l bilan ko'rsatilgan
- [ ] Virtual muhit to'g'ri yo'lda
- [ ] Web ilovasi "Reload" qilingan
- [ ] `https://USERNAME.pythonanywhere.com` ochiladi
- [ ] Admin tizimga kira oladi
- [ ] O'quvchi ro'yxatdan o'tib test topa oladi
- [ ] _(Ixtiyoriy)_ `GEMINI_API_KEY` o'rnatilgan va AI generator ishlaydi

---

```
🎓 Grammatika Test Platform muvaffaqiyatli joylashtirildi!
   Saytingiz: https://USERNAME.pythonanywhere.com
```
