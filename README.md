# 🔥 سیستم مدیریت تعمیرات سها (SAHAB-SERVICE V2.0)

> **سیستم جامع مدیریت تعمیرات تجهیزات اعلام و اطفا حریق**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-24+-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 فهرست مطالب

- [معرفی پروژه](#-معرفی-پروژه)
- [ویژگی‌ها](#-ویژگی‌ها)
- [تکنولوژی‌های استفاده شده](#-تکنولوژی‌های-استفاده-شده)
- [نصب و راه‌اندازی](#-نصب-و-راه‌اندازی)
- [ساختار پروژه](#-ساختار-پروژه)
- [راهنمای استفاده](#-راهنمای-استفاده)
- [API Documentation](#-api-documentation)
- [مشارکت در پروژه](#-مشارکت-در-پروژه)
- [توسعه‌دهندگان](#-توسعه‌دهندگان)
- [لایسنس](#-لایسنس)

---

## 🎯 معرفی پروژه

**سیستم مدیریت تعمیرات سها** یک راه‌حل جامع و پیشرفته برای مدیریت فرآیند تعمیرات تجهیزات اعلام و اطفا حریق است. این سیستم با هدف افزایش بهره‌وری، شفافیت و سرعت در فرآیند ثبت، پیگیری و تحویل پرونده‌های تعمیرات طراحی شده است.

### 📌 اهداف اصلی
- **مدیریت یکپارچه** مشتریان، پنل‌ها و پرونده‌های تعمیرات
- **پیگیری لحظه‌ای** وضعیت پرونده‌ها
- **گزارش‌گیری پیشرفته** و خروجی‌های متنوع
- **امنیت بالا** با احراز هویت JWT
- **رابط کاربری** زیبا، واکنش‌گرا و کاربرپسند

---

## ✨ ویژگی‌ها

### 🏗️ بخش‌های اصلی

| بخش | توضیح |
|------|--------|
| **ثبت پرونده** | فرم ۱۰ مرحله‌ای با قابلیت ثبت مشتری، محل نصب، پنل و بردها |
| **مدیریت مشتریان** | جستجو، ثبت و مدیریت اطلاعات مشتریان (حقیقی/حقوقی) |
| **مدیریت پنل‌ها** | ثبت و جستجوی پنل‌ها با مشخصات کامل |
| **مدیریت بردها** | ثبت داینامیک بردها با انواع مختلف |
| **تغییر وضعیت** | مدیریت چرخه حیات پرونده با ۱۰ وضعیت مختلف |
| **برگه پذیرش** | خروجی قابل چاپ با تمام اطلاعات پرونده |
| **داشبورد** | نمایش آمار و آخرین پرونده‌ها |
| **مدیریت کاربران** | مدیریت کاربران با نقش‌های مختلف |

### 🔄 چرخه وضعیت‌های پرونده
ثبت شده
↓
در انتظار بررسی فنی
↓
در حال عیب‌یابی
↓
در انتظار تایید مشتری
↓
در حال تعمیر
↓
در حال تست
↓
کنترل نهایی
↓
آماده تحویل
↓
تحویل شده / مختومه بدون تعمیر

### 👥 نقش‌های کاربری

| نقش | دسترسی‌ها |
|------|-----------|
| **ADMIN** | دسترسی کامل به همه بخش‌ها |
| **TECHNICAL** | تغییر وضعیت پرونده‌ها |
| **RECEPTION** | ثبت و مدیریت پرونده‌ها |
| **CUSTOMER_RELATIONS** | مدیریت مشتریان |
| **VIEWER** | مشاهده اطلاعات |

---

## 🛠️ تکنولوژی‌های استفاده شده

### بک‌اند (Backend)

| تکنولوژی | نسخه | کاربرد |
|-----------|-------|--------|
| **Python** | 3.11+ | زبان اصلی |
| **FastAPI** | 0.100+ | چارچوب وب |
| **SQLAlchemy** | 2.0+ | ORM و مدیریت دیتابیس |
| **PostgreSQL** | 15+ | دیتابیس اصلی |
| **JWT** | - | احراز هویت |
| **Pydantic** | 2.0+ | اعتبارسنجی داده‌ها |
| **Uvicorn** | - | سرور ASGI |
| **Docker** | 24+ | کانتینریزیشن |

### فرانت‌اند (Frontend)

| تکنولوژی | نسخه | کاربرد |
|-----------|-------|--------|
| **HTML5** | - | ساختار صفحات |
| **CSS3** | - | استایل‌دهی |
| **Bootstrap** | 5.3 | فریم‌ورک CSS |
| **JavaScript** | ES6 | منطق تعاملات |
| **jQuery** | 3.7 | کتابخانه جاوااسکریپت |
| **SweetAlert2** | 11 | نمایش پیام‌ها و مودال‌ها |
| **Font Awesome** | 6.4 | آیکون‌ها |

### ابزارهای توسعه

| ابزار | کاربرد |
|--------|--------|
| **Git** | کنترل نسخه |
| **GitHub** | مخزن کد |
| **VS Code** | ویرایشگر کد |
| **pgAdmin** | مدیریت دیتابیس |
| **Postman** | تست API |

---

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها
- Python 3.11 یا بالاتر
- PostgreSQL 15 یا بالاتر
- Docker (اختیاری)
- Git

---
📁 ساختار پروژه
text
SAHAB-SERVICEV2.0/
├── app/
│   ├── __init__.py
│   ├── main.py                 # نقطه ورود برنامه
│   ├── config.py               # تنظیمات
│   ├── auth.py                 # احراز هویت
│   ├── database.py             # اتصال به دیتابیس
│   ├── models/                 # مدل‌های دیتابیس
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── customer.py
│   │   ├── device.py
│   │   ├── repair_order.py
│   │   ├── status_history.py
│   │   ├── attachment.py
│   │   ├── site.py
│   │   ├── panel.py
│   │   └── board.py
│   ├── routes/                 # مسیرهای API
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── reception.py
│   └── schemas/                # مدل‌های Pydantic
│       └── __init__.py
├── frontend/
│   ├── templates/              # صفحات HTML
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── orders.html
│   │   ├── new_order.html
│   │   ├── order_detail.html
│   │   ├── users.html
│   │   └── receipt.html
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           ├── app.js
│           └── pages/
│               ├── dashboard.js
│               ├── orders.js
│               ├── new_order.js
│               ├── new_order_v2.js
│               ├── order_detail.js
│               └── users.js
├── uploads/                    # فایل‌های آپلودی
│   ├── photos/
│   └── attachments/
├── .env                        # متغیرهای محیطی
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── create_admin.py
└── README.md

مسیرهای اصلی
مسیر	توضیح
/	صفحه اصلی
/login	صفحه ورود
/dashboard	داشبورد
/orders	لیست پرونده‌ها
/new-order	ثبت پرونده جدید
/order/{id}	جزئیات پرونده
/users	مدیریت کاربران
/api/docs	مستندات API
📚 API Documentation
پس از اجرای برنامه، مستندات کامل API در آدرس‌های زیر قابل دسترس است:

Swagger UI: http://localhost:8000/api/docs

ReDoc: http://localhost:8000/api/redoc

مهم‌ترین مسیرهای API
متد	مسیر	توضیح
POST	/auth/login	ورود به سیستم
POST	/auth/register	ثبت کاربر جدید
GET	/auth/me	اطلاعات کاربر جاری
GET	/reception/repair-orders	لیست پرونده‌ها
POST	/reception/repair-orders-v2	ثبت پرونده جدید
GET	/reception/repair-orders/{id}	جزئیات پرونده
PUT	/reception/repair-orders/{id}/status	تغییر وضعیت
GET	/reception/repair-orders/{id}/receipt	برگه پذیرش
GET	/reception/stats	آمار پرونده‌ها
GET	/reception/customers/search-v2	جستجوی مشتری
🤝 مشارکت در پروژه
چگونه مشارکت کنیم؟
Fork کردن مخزن

ایجاد Branch جدید:

bash
git checkout -b feature/your-feature
Commit تغییرات:

bash
git commit -m "Add your feature"
Push به Branch:

bash
git push origin feature/your-feature
ایجاد Pull Request

استانداردهای کدنویسی
Python: PEP 8

JavaScript: ES6

Commit Messages:

✨ feat: توضیح

🐛 fix: توضیح

📝 docs: توضیح

🔧 chore: توضیح

🎨 style: توضیح

🚀 perf: توضیح

👨‍💻 توسعه‌دهندگان
نام	نقش	ایمیل
سینا فاتح	توسعه‌دهنده اصلی	Cnofateh@gmail.com

📞 ارتباط با من
ایمیل: Cnofateh@gmail.com

گیت‌هاب: github.com/sinafateh

⭐ اگر پروژه رو دوست داشتی
اگر از این پروژه خوشت اومد، لطفاً یک ⭐ بهش بدید! 😊

ساخته شده با ❤️ توسط سینا فاتح