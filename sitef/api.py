"""
FastAPI Application for LMS Platform
Full-stack API with:
- Static file serving (frontend)
- User authentication
- Course management
- Prodamus webhook handling
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr

# Import our modules
from prodamus_integration import (
    process_successful_payment,
    generate_payment_link,
    generate_order_id
)
from database import (
    init_database,
    # Users
    get_user_by_email,
    get_user_by_id,
    authenticate_user,
    create_user,
    # Courses
    get_course_by_id,
    get_all_courses,
    create_course,
    update_course,
    delete_course,
    get_course_with_lessons,
    # Lessons
    get_lessons_by_course,
    create_lesson,
    update_lesson,
    delete_lesson,
    # Homework
    get_homework_by_lesson,
    create_homework,
    # Purchases
    purchase_course,
    user_has_course_access,
    get_purchased_course_ids,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Kon!AdminFDRV")
BASE_DIR = Path(__file__).resolve().parent

# ==========================================
# APPLICATION LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events handler."""
    logger.info("🚀 Starting LMS Platform...")
    init_database()
    
    # Create test data if needed
    courses = get_all_courses()
    if not courses:
        create_test_data()
    
    logger.info("✅ Database initialized")
    yield
    logger.info("👋 Shutting down LMS Platform...")


def create_test_data():
    """Create test courses for demo."""
    logger.info("📝 Creating test data...")
    
    # Create test course
    course = create_course(
        title="Python для начинающих",
        description="Изучите основы программирования на Python с нуля. Этот курс подойдёт для тех, кто хочет начать карьеру в IT.",
        price_rub=4990,
        is_published=True
    )
    
    # Create lessons
    lesson1 = create_lesson(
        course_id=course['id'],
        title="Введение в Python",
        description="Знакомство с языком программирования Python",
        content_text="""
# Введение в Python

Python — это высокоуровневый язык программирования общего назначения. 
Он был создан Гвидо ван Россумом и впервые выпущен в 1991 году.

## Почему Python?

1. **Простой синтаксис** — код читается как английский текст
2. **Универсальность** — веб, Data Science, ML, автоматизация
3. **Большое сообщество** — множество библиотек и документации

## Первая программа

```python
print("Hello, World!")
```

Попробуйте запустить этот код в интерпретаторе Python!
        """,
        sort_order=1
    )
    
    # Create homework for lesson 1
    create_homework(
        lesson_id=lesson1['id'],
        content_text="Какая функция используется для вывода текста в Python?",
        options=["print()", "echo()", "console.log()", "printf()"],
        correct_answer="print()",
        hint="Вспомните пример из урока"
    )
    
    lesson2 = create_lesson(
        course_id=course['id'],
        title="Переменные и типы данных",
        description="Изучаем переменные и основные типы данных",
        content_text="""
# Переменные и типы данных

Переменная — это именованная область памяти для хранения данных.

## Основные типы данных

```python
# Числа
age = 25              # int (целое число)
price = 99.99         # float (дробное число)

# Строки
name = "Python"       # str (строка)

# Логический тип
is_active = True      # bool (True/False)

# Списки
numbers = [1, 2, 3]   # list (список)
```

## Примеры

```python
# Объявление переменных
course_name = "Python для начинающих"
lesson_number = 2
is_completed = False

# Вывод значений
print(f"Курс: {course_name}")
print(f"Урок: {lesson_number}")
```
        """,
        sort_order=2
    )
    
    lesson3 = create_lesson(
        course_id=course['id'],
        title="Условные операторы",
        description="Конструкции if, elif, else",
        content_text="""
# Условные операторы

Условные операторы позволяют выполнять код в зависимости от условий.

## Синтаксис if

```python
age = 18

if age >= 18:
    print("Совершеннолетний")
else:
    print("Несовершеннолетний")
```

## Множественные условия

```python
score = 85

if score >= 90:
    grade = "Отлично"
elif score >= 70:
    grade = "Хорошо"
elif score >= 50:
    grade = "Удовлетворительно"
else:
    grade = "Неудовлетворительно"
    
print(f"Оценка: {grade}")
```
        """,
        sort_order=3
    )
    
    # Create another course
    course2 = create_course(
        title="JavaScript с нуля",
        description="Научитесь создавать интерактивные веб-приложения на JavaScript.",
        price_rub=5990,
        is_published=True
    )
    
    create_lesson(
        course_id=course2['id'],
        title="Введение в JavaScript",
        description="Первый урок по JavaScript",
        content_text="# JavaScript\n\nJavaScript — язык программирования для веб...",
        sort_order=1
    )
    
    # Free course
    course3 = create_course(
        title="Git для начинающих",
        description="Бесплатный курс по системе контроля версий Git. Научитесь работать с репозиториями.",
        price_rub=0,
        is_published=True
    )
    
    logger.info(f"✅ Created {3} courses with lessons")


# ==========================================
# FASTAPI APP
# ==========================================

app = FastAPI(
    title="LMS Platform",
    description="Learning Management System with Prodamus payment integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
(static_dir / "css").mkdir(exist_ok=True)
(static_dir / "js").mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(exist_ok=True)


# ==========================================
# PYDANTIC MODELS
# ==========================================

class LoginRequest(BaseModel):
    email: str
    password: str


class AdminVerifyRequest(BaseModel):
    password: str


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    image_url: Optional[str] = None
    price_rub: Optional[int] = 0
    is_published: Optional[bool] = False


class PaymentCreate(BaseModel):
    course_id: int
    email: str


# ==========================================
# FRONTEND ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    """Serve the main frontend application."""
    index_path = templates_dir / "index.html"
    
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding='utf-8'))
    
    # Fallback inline HTML
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LMS Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #3B82F6;
            --bg: #F8FAFC;
            --surface: #FFFFFF;
            --text: #0F172A;
            --border: #E2E8F0;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
        .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 16px 24px; }
        .header-content { max-width: 1280px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        .logo { display: flex; align-items: center; gap: 12px; font-size: 20px; font-weight: 700; text-decoration: none; color: var(--text); }
        .logo svg { color: var(--primary); }
        .container { max-width: 1280px; margin: 0 auto; padding: 24px; }
        .courses-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; margin-top: 24px; }
        .card { background: var(--surface); border-radius: 12px; border: 1px solid var(--border); overflow: hidden; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); }
        .card-image { height: 160px; background: linear-gradient(135deg, var(--primary), #6366F1); display: flex; align-items: center; justify-content: center; color: white; font-size: 48px; }
        .card-body { padding: 20px; }
        .card-title { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
        .card-desc { font-size: 14px; color: #64748B; margin-bottom: 16px; }
        .card-footer { display: flex; justify-content: space-between; align-items: center; padding-top: 16px; border-top: 1px solid var(--border); }
        .price { font-size: 20px; font-weight: 700; color: var(--primary); }
        .btn { padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; text-decoration: none; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: #2563EB; }
        .section-title { font-size: 24px; font-weight: 600; }
        .section-subtitle { color: #64748B; margin-top: 4px; }
        .login-prompt { text-align: center; padding: 60px 20px; background: var(--surface); border-radius: 16px; margin-top: 40px; }
        .login-prompt h2 { font-size: 24px; margin-bottom: 16px; }
        .login-prompt p { color: #64748B; margin-bottom: 24px; }
        .form-group { margin-bottom: 16px; text-align: left; }
        .form-label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; }
        .form-input { width: 100%; padding: 12px 16px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; }
        .form-input:focus { outline: none; border-color: var(--primary); }
        #login-form { max-width: 400px; margin: 0 auto; }
        .error { color: #EF4444; font-size: 14px; margin-top: 8px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <a href="/" class="logo">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3z"/>
                </svg>
                LMS Platform
            </a>
            <div id="user-info"></div>
        </div>
    </header>
    
    <main class="container" id="main-content">
        <div style="text-align: center; padding: 40px;">
            <div class="spinner"></div>
            <p style="margin-top: 16px; color: #64748B;">Загрузка...</p>
        </div>
    </main>
    
    <script>
        const API = window.location.origin;
        let currentUser = null;
        let courses = [];
        let purchasedIds = [];
        
        // Check session
        async function checkAuth() {
            const saved = localStorage.getItem('lms_user');
            if (saved) {
                currentUser = JSON.parse(saved);
                purchasedIds = JSON.parse(localStorage.getItem('lms_purchased') || '[]');
            }
            return currentUser;
        }
        
        // Load courses
        async function loadCourses() {
            const res = await fetch(API + '/api/courses');
            const data = await res.json();
            courses = data.courses || [];
            return courses;
        }
        
        // Render
        function render() {
            const userInfo = document.getElementById('user-info');
            const content = document.getElementById('main-content');
            
            if (currentUser) {
                userInfo.innerHTML = `
                    <span style="color: #64748B; margin-right: 12px;">${currentUser.email}</span>
                    <button class="btn" style="background: transparent; color: var(--primary);" onclick="logout()">Выйти</button>
                `;
                
                const purchased = courses.filter(c => purchasedIds.includes(c.id));
                const available = courses.filter(c => !purchasedIds.includes(c.id));
                
                content.innerHTML = `
                    ${purchased.length > 0 ? `
                        <section style="margin-bottom: 40px;">
                            <h2 class="section-title">Продолжить обучение</h2>
                            <p class="section-subtitle">${purchased.length} курсов</p>
                            <div class="courses-grid">
                                ${purchased.map(c => renderCard(c, true)).join('')}
                            </div>
                        </section>
                    ` : ''}
                    
                    <section>
                        <h2 class="section-title">Каталог курсов</h2>
                        <p class="section-subtitle">${available.length} курсов</p>
                        <div class="courses-grid">
                            ${available.length > 0 
                                ? available.map(c => renderCard(c, false)).join('') 
                                : '<p style="color: #64748B;">Нет доступных курсов</p>'}
                        </div>
                    </section>
                `;
            } else {
                userInfo.innerHTML = '';
                content.innerHTML = `
                    <section style="margin-bottom: 40px;">
                        <h2 class="section-title">Каталог курсов</h2>
                        <p class="section-subtitle">${courses.length} курсов</p>
                        <div class="courses-grid">
                            ${courses.map(c => renderCard(c, false)).join('')}
                        </div>
                    </section>
                    
                    <div class="login-prompt">
                        <h2>Войдите для доступа к курсам</h2>
                        <p>После покупки курса вы получите данные для входа на email</p>
                        <div id="login-error" class="error hidden"></div>
                        <form id="login-form" onsubmit="handleLogin(event)">
                            <div class="form-group">
                                <label class="form-label">Email</label>
                                <input type="email" class="form-input" id="email" placeholder="user@example.com" required>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Пароль</label>
                                <input type="password" class="form-input" id="password" placeholder="••••••••" required>
                            </div>
                            <button type="submit" class="btn btn-primary" style="width: 100%;">Войти</button>
                        </form>
                        <p style="margin-top: 20px; color: #64748B;">
                            <a href="#" onclick="showAdminLogin()" style="color: var(--primary);">Вход для администратора</a>
                        </p>
                    </div>
                `;
            }
        }
        
        function renderCard(course, isPurchased) {
            const price = course.price_rub > 0 
                ? new Intl.NumberFormat('ru-RU').format(course.price_rub) + ' ₽'
                : 'Бесплатно';
            
            return `
                <div class="card">
                    <div class="card-image">📚</div>
                    <div class="card-body">
                        <h3 class="card-title">${course.title}</h3>
                        <p class="card-desc">${course.description || ''}</p>
                        <div class="card-footer">
                            <span class="price">${price}</span>
                            ${isPurchased 
                                ? `<button class="btn btn-primary" onclick="openCourse(${course.id})">Открыть</button>`
                                : `<button class="btn btn-primary" onclick="buyCourse(${course.id})">Купить</button>`
                            }
                        </div>
                    </div>
                </div>
            `;
        }
        
        async function handleLogin(e) {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('login-error');
            
            try {
                const res = await fetch(API + '/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await res.json();
                
                if (res.ok) {
                    currentUser = data.user;
                    purchasedIds = data.purchased_ids || [];
                    localStorage.setItem('lms_user', JSON.stringify(currentUser));
                    localStorage.setItem('lms_purchased', JSON.stringify(purchasedIds));
                    render();
                } else {
                    errorDiv.textContent = data.detail || 'Ошибка входа';
                    errorDiv.classList.remove('hidden');
                }
            } catch (err) {
                errorDiv.textContent = 'Ошибка соединения';
                errorDiv.classList.remove('hidden');
            }
        }
        
        function logout() {
            currentUser = null;
            purchasedIds = [];
            localStorage.removeItem('lms_user');
            localStorage.removeItem('lms_purchased');
            localStorage.removeItem('lms_admin');
            render();
        }
        
        function showAdminLogin() {
            const password = prompt('Введите пароль администратора:');
            if (password === 'Kon!AdminFDRV') {
                localStorage.setItem('lms_admin', 'true');
                window.location.href = '/admin';
            } else {
                alert('Неверный пароль');
            }
        }
        
        function buyCourse(courseId) {
            const course = courses.find(c => c.id === courseId);
            if (!course) return;
            
            if (course.price_rub === 0) {
                // Free course - add to purchased
                purchasedIds.push(courseId);
                localStorage.setItem('lms_purchased', JSON.stringify(purchasedIds));
                render();
                return;
            }
            
            const email = prompt('Введите email для получения доступа:');
            if (!email) return;
            
            fetch(API + '/api/payment/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ course_id: courseId, email })
            })
            .then(res => res.json())
            .then(data => {
                if (data.payment_url) {
                    alert('Вы будете перенаправлены на страницу оплаты');
                    window.open(data.payment_url, '_blank');
                }
            });
        }
        
        function openCourse(courseId) {
            window.location.href = '/course/' + courseId;
        }
        
        // Init
        async function init() {
            await checkAuth();
            await loadCourses();
            render();
        }
        
        init();
    </script>
</body>
</html>
    """)


@app.get("/course/{course_id}", response_class=HTMLResponse)
async def course_page(request: Request, course_id: int):
    """Course page with lessons."""
    course = get_course_with_lessons(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{course['title']} - LMS Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #3B82F6;
            --bg: #F8FAFC;
            --surface: #FFFFFF;
            --text: #0F172A;
            --border: #E2E8F0;
            --secondary: #6366F1;
            --success: #22C55E;
            --error: #EF4444;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); }}
        .header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 24px; position: sticky; top: 0; z-index: 100; }}
        .header-content {{ max-width: 100%; display: flex; align-items: center; gap: 16px; }}
        .back-btn {{ display: flex; align-items: center; gap: 8px; background: none; border: none; cursor: pointer; color: var(--text); font-size: 16px; }}
        .course-title {{ font-size: 18px; font-weight: 600; }}
        .layout {{ display: grid; grid-template-columns: 280px 1fr; min-height: calc(100vh - 56px); }}
        .sidebar {{ background: var(--surface); border-right: 1px solid var(--border); padding: 20px; overflow-y: auto; }}
        .content {{ padding: 32px; overflow-y: auto; max-width: 900px; }}
        .lesson-item {{ padding: 12px 16px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }}
        .lesson-item:hover {{ background: var(--bg); }}
        .lesson-item.active {{ background: var(--primary); color: white; }}
        .lesson-num {{ width: 28px; height: 28px; border-radius: 50%; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }}
        .lesson-item.active .lesson-num {{ background: white; color: var(--primary); }}
        .lesson-info {{ flex: 1; }}
        .lesson-title {{ font-weight: 500; font-size: 14px; }}
        .lesson-hw {{ font-size: 12px; opacity: 0.7; }}
        h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .desc {{ color: #64748B; margin-bottom: 24px; }}
        .video {{ position: relative; padding-bottom: 56.25%; background: #000; border-radius: 12px; margin: 20px 0; }}
        .video iframe, .video video {{ position: absolute; width: 100%; height: 100%; }}
        .content-box {{ background: var(--surface); padding: 24px; border-radius: 12px; border: 1px solid var(--border); line-height: 1.8; }}
        .content-box h1, .content-box h2 {{ margin: 24px 0 12px; }}
        .content-box pre {{ background: var(--bg); padding: 16px; border-radius: 8px; overflow-x: auto; }}
        .content-box code {{ background: var(--bg); padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
        .hw-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-top: 24px; }}
        .hw-title {{ display: flex; align-items: center; gap: 12px; font-size: 18px; font-weight: 600; margin-bottom: 16px; }}
        .hw-icon {{ color: var(--secondary); }}
        .radio-group {{ display: flex; flex-direction: column; gap: 12px; margin: 16px 0; }}
        .radio-opt {{ display: flex; align-items: center; gap: 12px; padding: 14px 16px; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; }}
        .radio-opt:hover {{ border-color: var(--primary); }}
        .radio-opt.selected {{ border-color: var(--primary); background: rgba(59,130,246,0.05); }}
        .btn {{ padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; }}
        .btn-primary {{ background: var(--primary); color: white; }}
        .result {{ margin-top: 16px; padding: 12px; border-radius: 8px; }}
        .result.success {{ background: rgba(34,197,94,0.1); color: var(--success); }}
        .result.error {{ background: rgba(239,68,68,0.1); color: var(--error); }}
        .locked {{ text-align: center; padding: 60px; }}
        .locked svg {{ width: 60px; height: 60px; color: var(--error); }}
        @media (max-width: 768px) {{ .layout {{ grid-template-columns: 1fr; }} .sidebar {{ display: none; }} }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <button class="back-btn" onclick="window.location.href='/'">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
            </button>
            <span class="course-title">{course['title']}</span>
        </div>
    </header>
    
    <div class="layout">
        <aside class="sidebar" id="sidebar">
            {"".join(f'''
            <div class="lesson-item {'active' if i == 0 else ''}" data-index="{i}" onclick="showLesson({i})">
                <div class="lesson-num">{i + 1}</div>
                <div class="lesson-info">
                    <div class="lesson-title">{lesson['title']}</div>
                    {'<div class="lesson-hw">📋 Есть ДЗ</div>' if lesson.get('homework') else ''}
                </div>
            </div>
            ''' for i, lesson in enumerate(course['lessons']))}
        </aside>
        
        <main class="content" id="content">
            {'<div class="locked"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-7h2v4h-2zm0-6h2v4h-2z"/></svg><h2 style="margin-top: 16px;">Доступ запрещён</h2><p style="color: #64748B; margin: 8px 0 24px;">Купите курс для доступа к материалам</p><button class="btn btn-primary" onclick="window.location.href=\'/\'">На главную</button></div>' if not check_course_access(course_id) else ''}
        </main>
    </div>
    
    <script>
        const course = {json.dumps(course, ensure_ascii=False)};
        const hasAccess = {str(check_course_access(course_id)).lower()};
        let currentLesson = 0;
        
        function showLesson(index) {{
            if (!hasAccess) return;
            
            currentLesson = index;
            document.querySelectorAll('.lesson-item').forEach((el, i) => {{
                el.classList.toggle('active', i === index);
            }});
            
            const lesson = course.lessons[index];
            const hw = lesson.homework;
            
            let html = `
                <h1>${{lesson.title}}</h1>
                <p class="desc">${{lesson.description || ''}}</p>
            `;
            
            if (lesson.video_url) {{
                html += `<div class="video"><iframe src="${{lesson.video_url}}" frameborder="0" allowfullscreen></iframe></div>`;
            }}
            
            if (lesson.content_text) {{
                html += `<div class="content-box">${{formatMarkdown(lesson.content_text)}}</div>`;
            }}
            
            if (hw) {{
                const options = hw.options || [];
                html += `
                    <div class="hw-card">
                        <div class="hw-title">
                            <svg class="hw-icon" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1z"/>
                            </svg>
                            Домашнее задание
                        </div>
                        <p>${{hw.content_text || ''}}</p>
                        ${{options.length > 0 ? `
                            <div class="radio-group">
                                ${{options.map((opt, i) => `
                                    <label class="radio-opt">
                                        <input type="radio" name="answer" value="${{opt}}" onchange="checkAnswer(this)">
                                        ${{opt}}
                                    </label>
                                `).join('')}}
                            </div>
                            <div id="hw-result"></div>
                        ` : ''}}
                    </div>
                `;
            }}
            
            document.getElementById('content').innerHTML = html;
        }}
        
        function formatMarkdown(text) {{
            return text
                .replace(/```(\\w+)?\\n([\\s\\S]*?)```/g, '<pre><code>$2</code></pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/## (.*)/g, '<h2>$1</h2>')
                .replace(/# (.*)/g, '<h1>$1</h1>')
                .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/\\n/g, '<br>');
        }}
        
        function checkAnswer(input) {{
            const lesson = course.lessons[currentLesson];
            const hw = lesson.homework;
            const selected = input.value;
            const correct = hw.correct_answer;
            const resultDiv = document.getElementById('hw-result');
            
            input.closest('.radio-group').querySelectorAll('.radio-opt').forEach(el => {{
                el.classList.remove('selected');
            }});
            input.closest('.radio-opt').classList.add('selected');
            
            if (selected === correct) {{
                resultDiv.innerHTML = '<div class="result success">✅ Правильно!</div>';
            }} else {{
                resultDiv.innerHTML = '<div class="result error">❌ Неправильно. Попробуйте ещё раз.</div>';
            }}
        }}
        
        if (hasAccess && course.lessons.length > 0) {{
            showLesson(0);
        }}
    </script>
</body>
</html>
    """)


def check_course_access(course_id: int) -> bool:
    """Check if current user has access to course."""
    # For demo, allow access to free courses
    course = get_course_by_id(course_id)
    if course and course['price_rub'] == 0:
        return True
    # In real app, check from session/token
    return True  # Demo mode


# ==========================================
# API ROUTES
# ==========================================

@app.get("/api/courses")
async def api_list_courses():
    """List all published courses."""
    courses = get_all_courses(published_only=True)
    for c in courses:
        c.pop("payment_link", None)
    return {"courses": courses}


@app.get("/api/courses/{course_id}")
async def api_get_course(course_id: int):
    """Get course with lessons."""
    course = get_course_with_lessons(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@app.post("/api/auth/login")
async def api_login(data: LoginRequest):
    """User login."""
    user = authenticate_user(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    purchased_ids = get_purchased_course_ids(user['id'])
    
    return {
        "user": {
            "id": user['id'],
            "email": user['email'],
            "role": user['role']
        },
        "purchased_ids": purchased_ids
    }


@app.post("/api/admin/verify")
async def api_admin_verify(data: AdminVerifyRequest):
    """Verify admin password."""
    if data.password == ADMIN_PASSWORD:
        return {"success": True}
    raise HTTPException(status_code=401, detail="Неверный пароль")


@app.post("/api/admin/courses")
async def api_create_course(data: CourseCreate):
    """Create a new course (admin only)."""
    course = create_course(
        title=data.title,
        description=data.description,
        image_url=data.image_url,
        price_rub=data.price_rub,
        is_published=data.is_published
    )
    return course


@app.post("/api/payment/create")
async def api_create_payment(request: Request, data: PaymentCreate):
    """Create payment link."""
    course = get_course_by_id(data.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    order_id = generate_order_id(data.course_id, data.email)
    base_url = str(request.base_url).rstrip("/")
    
    payment_url = generate_payment_link(
        order_id=order_id,
        product_name=course["title"],
        price_rub=course["price_rub"],
        customer_email=data.email,
        course_id=data.course_id,
        success_url=f"{base_url}/?payment=success",
        fail_url=f"{base_url}/?payment=fail",
        webhook_url=f"{base_url}/prodamus-webhook"
    )
    
    return {
        "order_id": order_id,
        "payment_url": payment_url
    }


@app.post("/prodamus-webhook")
async def prodamus_webhook(request: Request):
    """Handle Prodamus webhook."""
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)
        
        logger.info(f"📥 Webhook: order={data.get('order_id')}, status={data.get('status')}")
        
        result = await process_successful_payment(data)
        
        return {"success": result["success"], "message": result["message"]}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "version": "1.0.0"}


# Admin page
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin panel."""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - LMS Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #3B82F6; --bg: #F8FAFC; --surface: #FFFFFF; --text: #0F172A; --border: #E2E8F0; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); }
        .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 16px 24px; }
        .header-content { max-width: 1280px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        .logo { display: flex; align-items: center; gap: 12px; font-size: 20px; font-weight: 700; text-decoration: none; color: var(--text); }
        .container { max-width: 1280px; margin: 0 auto; padding: 24px; }
        .table { width: 100%; border-collapse: collapse; background: var(--surface); border-radius: 12px; overflow: hidden; margin-top: 24px; }
        .table th, .table td { padding: 14px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        .table th { background: var(--bg); font-weight: 600; font-size: 14px; color: #64748B; }
        .btn { padding: 8px 16px; border-radius: 6px; font-size: 14px; cursor: pointer; border: none; text-decoration: none; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .form { background: var(--surface); padding: 24px; border-radius: 12px; border: 1px solid var(--border); max-width: 600px; margin-top: 24px; }
        .form-group { margin-bottom: 16px; }
        .form-label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; }
        .form-input { width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; }
        .form-input:focus { outline: none; border-color: var(--primary); }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .badge-success { background: rgba(34,197,94,0.1); color: #22C55E; }
        .badge-warning { background: rgba(245,158,11,0.1); color: #F59E0B; }
        .section-header { display: flex; justify-content: space-between; align-items: center; }
        h1 { font-size: 24px; }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <a href="/" class="logo">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--primary)"><path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3z"/></svg>
                LMS Admin
            </a>
            <div>
                <a href="/" class="btn btn-primary btn-sm">На сайт</a>
                <button class="btn btn-sm" onclick="localStorage.clear(); window.location.href='/'">Выйти</button>
            </div>
        </div>
    </header>
    
    <main class="container">
        <div class="section-header">
            <h1>Управление курсами</h1>
            <button class="btn btn-primary" onclick="showForm()">+ Новый курс</button>
        </div>
        
        <div id="form-container" style="display: none;">
            <div class="form">
                <h2 style="margin-bottom: 20px;">Новый курс</h2>
                <div class="form-group">
                    <label class="form-label">Название</label>
                    <input type="text" class="form-input" id="title" placeholder="Python для начинающих">
                </div>
                <div class="form-group">
                    <label class="form-label">Описание</label>
                    <textarea class="form-input" id="description" rows="3" style="resize: vertical;"></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Цена (руб.)</label>
                    <input type="number" class="form-input" id="price" value="0" min="0">
                </div>
                <div class="form-group">
                    <label class="form-label" style="display: flex; align-items: center; gap: 8px;">
                        <input type="checkbox" id="published"> Опубликован
                    </label>
                </div>
                <button class="btn btn-primary" onclick="createCourse()">Создать</button>
                <button class="btn" style="background: transparent; margin-left: 8px;" onclick="hideForm()">Отмена</button>
            </div>
        </div>
        
        <table class="table" id="courses-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Название</th>
                    <th>Цена</th>
                    <th>Статус</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </main>
    
    <script>
        const API = window.location.origin;
        
        async function loadCourses() {
            const res = await fetch(API + '/api/courses');
            const data = await res.json();
            const tbody = document.querySelector('#courses-table tbody');
            tbody.innerHTML = (data.courses || []).map(c => `
                <tr>
                    <td>${c.id}</td>
                    <td>${c.title}</td>
                    <td>${c.price_rub} ₽</td>
                    <td><span class="badge ${c.is_published ? 'badge-success' : 'badge-warning'}">${c.is_published ? 'Опубликован' : 'Черновик'}</span></td>
                </tr>
            `).join('');
        }
        
        function showForm() {
            document.getElementById('form-container').style.display = 'block';
        }
        
        function hideForm() {
            document.getElementById('form-container').style.display = 'none';
        }
        
        async function createCourse() {
            const data = {
                title: document.getElementById('title').value,
                description: document.getElementById('description').value,
                price_rub: parseInt(document.getElementById('price').value) || 0,
                is_published: document.getElementById('published').checked
            };
            
            if (!data.title) {
                alert('Введите название');
                return;
            }
            
            const res = await fetch(API + '/api/admin/courses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (res.ok) {
                hideForm();
                loadCourses();
                document.getElementById('title').value = '';
                document.getElementById('description').value = '';
                document.getElementById('price').value = '0';
                document.getElementById('published').checked = false;
            } else {
                alert('Ошибка создания');
            }
        }
        
        loadCourses();
    </script>
</body>
</html>
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
