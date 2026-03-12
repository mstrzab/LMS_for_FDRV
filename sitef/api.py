"""
LMS Platform - FastAPI Application  
Minimalist design with Bebas Neue / Inter fonts
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import Response, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from database import (
    init_database, get_all_courses, get_course_by_id,
    create_course, create_lesson, create_homework, create_user,
    authenticate_user, get_purchased_course_ids, user_has_course_access,
    purchase_course, update_course, delete_course,
    get_lessons_by_course, get_homework_by_lesson, delete_lesson
)
from prodamus_integration import generate_payment_link, generate_order_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Kon!AdminFDRV")
BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield

app = FastAPI(title="LMS Platform", lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)

@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    if "/static/" in str(request.url):
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif "text/html" in response.headers.get("content-type", ""):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Helper function to get course with lessons
def get_course_with_lessons(course_id: int):
    course = get_course_by_id(course_id)
    if not course:
        return None
    lessons = get_lessons_by_course(course_id)
    course['lessons'] = []
    for lesson in lessons:
        lesson_data = dict(lesson)
        lesson_data['homework'] = get_homework_by_lesson(lesson['id'])
        course['lessons'].append(lesson_data)
    return course


# Models
class LoginRequest(BaseModel):
    email: str
    password: str

class AdminVerifyRequest(BaseModel):
    password: str

class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    price_rub: Optional[int] = 0
    payment_link: Optional[str] = ""
    is_published: Optional[bool] = False

class PaymentCreate(BaseModel):
    course_id: int
    email: str


# ==========================================
# CSS STYLES
# ==========================================

CSS = '''
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&family=Oswald:wght@400;500;600;700&display=swap');

:root {
  --color-black: #000000;
  --color-white: #FFFFFF;
  --color-red: #D00000;
  --color-red-hover: #A30000;
  --color-off-white: #F2F1ED;
  --color-dark-grey: #1A1A1A;
  --color-border-dark: #333333;
  --color-text-muted: #999999;
  --font-heading: 'Bebas Neue', 'Oswald', sans-serif;
  --font-body: 'Inter', sans-serif;
  --text-hero: clamp(4rem, 12vw, 15rem);
  --text-h1: clamp(3rem, 8vw, 7rem);
  --text-h2: clamp(2rem, 4vw, 3.5rem);
  --text-h3: clamp(1.2rem, 2vw, 1.5rem);
  --text-body: 1rem;
  --text-small: 0.875rem;
  --text-huge-numbers: clamp(5rem, 10vw, 8rem);
  --space-xs: 0.5rem;
  --space-sm: 1rem;
  --space-md: 2rem;
  --space-lg: 4rem;
  --space-xl: clamp(4rem, 10vw, 8rem);
  --container-width: 1440px;
  --radius-none: 0px;
  --border-thin: 1px solid var(--color-border-dark);
  --transition-fast: 0.2s ease-in-out;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }

body {
  font-family: var(--font-body);
  font-size: var(--text-body);
  line-height: 1.6;
  color: var(--color-black);
  background: var(--color-off-white);
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-heading);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
}

h1 { font-size: var(--text-h1); }
h2 { font-size: var(--text-h2); }
h3 { font-size: var(--text-h3); }

a { color: inherit; text-decoration: none; }

.container {
  max-width: var(--container-width);
  margin: 0 auto;
  padding: 0 var(--space-md);
}

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--color-black);
  color: var(--color-white);
  padding: var(--space-sm) 0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-family: var(--font-heading);
  font-size: var(--text-h3);
  color: var(--color-white);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.logo svg { width: 32px; height: 32px; }

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-md);
  font-family: var(--font-heading);
  font-size: var(--text-body);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  cursor: pointer;
  border: none;
  border-radius: var(--radius-none);
  transition: var(--transition-fast);
}

.btn-primary {
  background: var(--color-red);
  color: var(--color-white);
}

.btn-primary:hover {
  background: var(--color-red-hover);
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--color-white);
  color: var(--color-white);
}

.btn-outline:hover {
  background: var(--color-white);
  color: var(--color-black);
}

.btn-outline-dark {
  background: transparent;
  border: 1px solid var(--color-black);
  color: var(--color-black);
}

.btn-outline-dark:hover {
  background: var(--color-black);
  color: var(--color-white);
}

.btn-sm {
  padding: var(--space-xs) var(--space-sm);
  font-size: var(--text-small);
}

.hero {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-black);
  color: var(--color-white);
  text-align: center;
  padding: var(--space-xl) var(--space-md);
  position: relative;
  overflow: hidden;
}

.hero-content {
  position: relative;
  z-index: 1;
}

.hero h1 {
  font-size: var(--text-hero);
  margin-bottom: var(--space-md);
}

.hero p {
  font-size: var(--text-h3);
  color: var(--color-text-muted);
  max-width: 600px;
  margin: 0 auto var(--space-lg);
}

.hero-number {
  position: absolute;
  right: -5%;
  bottom: 10%;
  font-size: var(--text-huge-numbers);
  font-family: var(--font-heading);
  color: rgba(255, 255, 255, 0.03);
  line-height: 1;
}

.section {
  padding: var(--space-xl) 0;
}

.section-light {
  background: var(--color-off-white);
  color: var(--color-black);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: var(--space-lg);
}

.courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--space-md);
}

.card {
  position: relative;
  background: var(--color-black);
  color: var(--color-white);
  border: var(--border-thin);
  padding: var(--space-md);
  transition: var(--transition-fast);
  overflow: hidden;
}

.card:hover {
  border-color: var(--color-red);
}

.card-number {
  position: absolute;
  right: var(--space-sm);
  bottom: -0.2em;
  font-size: var(--text-huge-numbers);
  font-family: var(--font-heading);
  color: rgba(255, 255, 255, 0.05);
  line-height: 1;
  pointer-events: none;
}

.card-content {
  position: relative;
  z-index: 1;
}

.card-title {
  font-size: var(--text-h3);
  margin-bottom: var(--space-xs);
}

.card-desc {
  color: var(--color-text-muted);
  font-size: var(--text-small);
  margin-bottom: var(--space-md);
  min-height: 3em;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--space-sm);
  border-top: 1px solid var(--color-border-dark);
}

.card-price {
  font-family: var(--font-heading);
  font-size: var(--text-h3);
}

.card-price span {
  font-family: var(--font-body);
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

.form-group {
  margin-bottom: var(--space-sm);
}

.form-label {
  display: block;
  font-size: var(--text-small);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: var(--space-xs);
  color: var(--color-text-muted);
}

.form-input {
  width: 100%;
  padding: var(--space-sm);
  font-family: var(--font-body);
  font-size: var(--text-body);
  color: var(--color-black);
  background: var(--color-white);
  border: none;
  border-radius: var(--radius-none);
}

.form-input:focus {
  outline: 2px solid var(--color-black);
}

.auth-error {
  color: var(--color-red);
  font-size: var(--text-small);
  margin-bottom: var(--space-sm);
}

.course-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
  padding-top: 60px;
}

.course-sidebar {
  background: var(--color-black);
  color: var(--color-white);
  padding: var(--space-md);
  border-right: 1px solid var(--color-border-dark);
  position: sticky;
  top: 60px;
  height: calc(100vh - 60px);
  overflow-y: auto;
}

.course-sidebar h3 {
  font-size: var(--text-body);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-muted);
  margin-bottom: var(--space-sm);
}

.course-content {
  padding: var(--space-lg);
  max-width: 900px;
}

.lesson-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  border-left: 2px solid transparent;
}

.lesson-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.lesson-item.active {
  background: rgba(255, 255, 255, 0.1);
  border-left-color: var(--color-red);
}

.lesson-num {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-heading);
  font-size: var(--text-small);
  border: 1px solid var(--color-border-dark);
}

.lesson-item.active .lesson-num {
  background: var(--color-red);
  border-color: var(--color-red);
}

.lesson-title {
  font-size: var(--text-small);
}

.hw-section {
  margin-top: var(--space-lg);
  padding: var(--space-md);
  background: var(--color-black);
  color: var(--color-white);
  border: var(--border-thin);
}

.hw-title {
  font-size: var(--text-h3);
  margin-bottom: var(--space-md);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.hw-option {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm);
  cursor: pointer;
  border: 1px solid var(--color-border-dark);
  margin-bottom: var(--space-xs);
  transition: var(--transition-fast);
}

.hw-option:hover {
  border-color: var(--color-white);
}

.hw-option.selected {
  border-color: var(--color-red);
  background: rgba(208, 0, 0, 0.1);
}

.hw-option input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-red);
}

.hw-result {
  margin-top: var(--space-sm);
  padding: var(--space-sm);
  font-size: var(--text-small);
}

.hw-result.correct {
  background: rgba(34, 197, 94, 0.1);
  color: #22C55E;
}

.hw-result.incorrect {
  background: rgba(208, 0, 0, 0.1);
  color: var(--color-red);
}

.content-box {
  font-size: var(--text-body);
  line-height: 1.8;
}

.content-box h1,
.content-box h2 {
  margin: var(--space-md) 0 var(--space-sm);
}

.content-box pre {
  background: var(--color-black);
  color: var(--color-white);
  padding: var(--space-md);
  margin: var(--space-md) 0;
  overflow-x: auto;
  font-family: monospace;
  font-size: var(--text-small);
}

.admin-layout {
  display: grid;
  grid-template-columns: 250px 1fr;
  min-height: 100vh;
  padding-top: 60px;
}

.admin-sidebar {
  background: var(--color-black);
  color: var(--color-white);
  padding: var(--space-md);
  border-right: 1px solid var(--color-border-dark);
}

.admin-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.admin-nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm);
  color: var(--color-text-muted);
  font-size: var(--text-small);
  cursor: pointer;
  transition: var(--transition-fast);
  border-left: 2px solid transparent;
}

.admin-nav-item:hover {
  color: var(--color-white);
}

.admin-nav-item.active {
  color: var(--color-white);
  border-left-color: var(--color-red);
}

.admin-content {
  padding: var(--space-lg);
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-small);
}

.table th,
.table td {
  padding: var(--space-sm) var(--space-md);
  text-align: left;
  border-bottom: 1px solid rgba(0,0,0,0.1);
}

.table th {
  font-family: var(--font-heading);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 400;
  color: var(--color-text-muted);
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: var(--text-small);
  text-transform: uppercase;
}

.badge-success {
  background: rgba(34, 197, 94, 0.1);
  color: #22C55E;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.1);
  color: #F59E0B;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 2px solid var(--color-border-dark);
  border-top-color: var(--color-red);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .course-layout,
  .admin-layout {
    grid-template-columns: 1fr;
  }
  .course-sidebar,
  .admin-sidebar {
    display: none;
  }
  .courses-grid {
    grid-template-columns: 1fr;
  }
}

.hidden { display: none !important; }
'''

# ==========================================
# HTML PAGES
# ==========================================

def get_main_html():
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LMS Platform</title>
<style>{CSS}</style>
</head>
<body>
<header class="header">
  <div class="container header-content">
    <a href="/" class="logo">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3z"/></svg>
      LMS
    </a>
    <div id="header-actions"></div>
  </div>
</header>

<section class="hero">
  <div class="hero-content">
    <h1>LEARN</h1>
    <p>Образовательная платформа для профессионального роста</p>
    <div id="hero-actions"></div>
  </div>
  <div class="hero-number">01</div>
</section>

<main class="section section-light">
  <div class="container">
    <div id="purchased-section"></div>
    
    <div class="section-header">
      <div>
        <h2>КАТАЛОГ КУРСОВ</h2>
        <p id="courses-count"></p>
      </div>
      <div id="admin-link"></div>
    </div>
    
    <div id="courses-grid" class="courses-grid">
      <div style="text-align: center; padding: 4rem;">
        <div class="spinner" style="margin: 0 auto;"></div>
      </div>
    </div>
    
    <div id="auth-section"></div>
  </div>
</main>

<script>
const API = window.location.origin;
let user = null;
let courses = [];
let purchasedIds = [];

function init() {{
  const saved = localStorage.getItem('lms_user');
  if (saved) {{
    user = JSON.parse(saved);
    purchasedIds = JSON.parse(localStorage.getItem('lms_purchased') || '[]');
  }}
  loadCourses();
}}

async function loadCourses() {{
  try {{
    const res = await fetch(API + '/api/courses');
    const data = await res.json();
    courses = data.courses || [];
    console.log('Loaded courses:', courses.length, courses);
    render();
  }} catch (e) {{
    document.getElementById('courses-grid').innerHTML = '<p>Ошибка загрузки</p>';
  }}
}}

function render() {{
  const headerActions = document.getElementById('header-actions');
  if (user) {{
    headerActions.innerHTML = '<span style="color: var(--color-text-muted); font-size: var(--text-small); margin-right: 1rem;">'+user.email+'</span><button class="btn btn-outline btn-sm" onclick="logout()">ВЫЙТИ</button>';
  }} else {{
    headerActions.innerHTML = '<button class="btn btn-outline btn-sm" onclick="showAuth()">ВОЙТИ</button>';
  }}
  
  document.getElementById('hero-actions').innerHTML = user 
    ? '<button class="btn btn-primary" onclick="scrollToCourses()">ПРОДОЛЖИТЬ ОБУЧЕНИЕ</button>'
    : '<button class="btn btn-primary" onclick="showAuth()">НАЧАТЬ ОБУЧЕНИЕ</button>';
  
  document.getElementById('admin-link').innerHTML = localStorage.getItem('lms_admin')
    ? '<a href="/admin" class="btn btn-outline-dark btn-sm">АДМИНКА</a>' : '';
  
  const purchased = courses.filter(c => purchasedIds.includes(c.id));
  document.getElementById('purchased-section').innerHTML = purchased.length > 0
    ? '<div class="section-header"><h2>МОИ КУРСЫ</h2></div><div class="courses-grid">'+purchased.map((c,i)=>renderCard(c,i,true)).join('')+'</div><div style="margin-bottom: var(--space-xl);"></div>'
    : '';
  
  const available = courses.filter(c => !purchasedIds.includes(c.id));
  document.getElementById('courses-count').textContent = available.length + ' курсов';
  document.getElementById('courses-grid').innerHTML = available.length > 0
    ? available.map((c,i) => renderCard(c, i + purchased.length, false)).join('')
    : '<p style="color: var(--color-text-muted);">Нет доступных курсов</p>';
  
  document.getElementById('auth-section').innerHTML = !user ? 
    '<div style="margin-top: var(--space-xl); padding: var(--space-lg); border: var(--border-thin); text-align: center;"><h3>Уже купили курс?</h3><p style="color: var(--color-text-muted); margin: var(--space-sm) 0 var(--space-md);">Войдите для доступа к материалам</p><button class="btn btn-outline-dark" onclick="showAuth()">ВОЙТИ</button></div>' : '';
}}

function renderCard(course, index, isPurchased) {{
  const price = course.price_rub > 0 ? new Intl.NumberFormat('ru-RU').format(course.price_rub)+' <span>₽</span>' : 'БЕСПЛАТНО';
  return '<div class="card" onclick="'+(isPurchased?'openCourse('+course.id+')':'buyCourse('+course.id+')')+'" style="cursor:pointer"><div class="card-number">'+String(index+1).padStart(2,'0')+'</div><div class="card-content"><h3 class="card-title">'+course.title+'</h3><p class="card-desc">'+(course.description||'')+'</p><div class="card-footer"><div class="card-price">'+price+'</div><button class="btn '+(isPurchased?'btn-primary':'btn-outline')+' btn-sm" onclick="event.stopPropagation();'+(isPurchased?'openCourse('+course.id+')':'buyCourse('+course.id+')')+'">'+(isPurchased?'ОТКРЫТЬ':'КУПИТЬ')+'</button></div></div></div>';
}}

function showAuth() {{
  document.getElementById('auth-section').innerHTML = '<div style="margin-top: var(--space-xl); padding: var(--space-lg); border: var(--border-thin); max-width: 400px; margin-left: auto; margin-right: auto;"><h3 style="margin-bottom: var(--space-sm);">ВХОД</h3><div id="auth-error" class="auth-error hidden"></div><div class="form-group"><label class="form-label">Email</label><input type="email" class="form-input" id="auth-email" placeholder="user@example.com"></div><div class="form-group"><label class="form-label">Пароль</label><input type="password" class="form-input" id="auth-password" placeholder="••••••••"></div><button class="btn btn-primary" style="width: 100%;" onclick="login()">ВОЙТИ</button><p style="margin-top: var(--space-md); text-align: center; color: var(--color-text-muted); font-size: var(--text-small);"><a href="#" onclick="showAdminLogin()" style="color: var(--color-text-muted);">Вход для администратора</a></p></div>';
}}

async function login() {{
  const email = document.getElementById('auth-email').value;
  const password = document.getElementById('auth-password').value;
  const errorEl = document.getElementById('auth-error');
  try {{
    const res = await fetch(API+'/api/auth/login', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{email,password}})}});
    const data = await res.json();
    if (res.ok) {{ user = data.user; purchasedIds = data.purchased_ids || []; localStorage.setItem('lms_user', JSON.stringify(user)); localStorage.setItem('lms_purchased', JSON.stringify(purchasedIds)); render(); }}
    else {{ errorEl.textContent = data.detail || 'Ошибка входа'; errorEl.classList.remove('hidden'); }}
  }} catch(e) {{ errorEl.textContent = 'Ошибка соединения'; errorEl.classList.remove('hidden'); }}
}}

function logout() {{ user = null; purchasedIds = []; localStorage.removeItem('lms_user'); localStorage.removeItem('lms_purchased'); localStorage.removeItem('lms_admin'); render(); }}

async function showAdminLogin() {{
  const password = prompt('Пароль администратора:');
  if (!password) return;
  const res = await fetch(API+'/api/admin/verify', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{password}})}});
  if (res.ok) {{ localStorage.setItem('lms_admin', 'true'); window.location.href = '/admin'; }}
  else alert('Неверный пароль');
}}

function buyCourse(id) {{
  const course = courses.find(c => c.id === id);
  if (!course) return;
  if (course.price_rub === 0) {{ purchasedIds.push(id); localStorage.setItem('lms_purchased', JSON.stringify(purchasedIds)); render(); return; }}
  const email = prompt('Введите email для получения доступа:');
  if (!email) return;
  fetch(API+'/api/payment/create', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{course_id:id, email}})}}).then(r=>r.json()).then(d=>{{ if(d.payment_url) {{ alert('Перенаправление на оплату'); window.open(d.payment_url, '_blank'); }} }});
}}

function openCourse(id) {{ window.location.href = '/course/'+id; }}

async function editCourse(id) {{
  const res = await fetch(API+'/api/courses/'+id);
  const course = await res.json();
  if (!course) return;
  const content = document.getElementById('admin-content');
  content.innerHTML = '<h2>РЕДАКТИРОВАТЬ КУРС</h2><div style="max-width:500px;margin-top:var(--space-md);"><div id="course-error" class="auth-error hidden"></div><div class="form-group"><label class="form-label">Название</label><input type="text" class="form-input" id="course-title" value="'+course.title+'"></div><div class="form-group"><label class="form-label">Описание</label><textarea class="form-input" id="course-desc" rows="3">'+(course.description||'')+'</textarea></div><div class="form-group"><label class="form-label">Цена (руб.)</label><input type="number" class="form-input" id="course-price" value="'+course.price_rub+'"></div><div class="form-group"><label class="form-label">Ссылка на оплату</label><input type="text" class="form-input" id="course-payment-link" value="'+(course.payment_link||'')+'"></div><div class="form-group"><label class="form-label"><input type="checkbox" id="course-published" '+(course.is_published?'checked':'')+'> Опубликован</label></div><button class="btn btn-primary" onclick="updateCourse('+id+')">СОХРАНИТЬ</button> <button class="btn btn-outline" onclick="showSection(\'courses\')">ОТМЕНА</button></div>';
}}

async function updateCourse(id) {{
  const title = document.getElementById('course-title').value;
  const description = document.getElementById('course-desc').value;
  const price_rub = parseInt(document.getElementById('course-price').value) || 0;
  const payment_link = document.getElementById('course-payment-link').value;
  const is_published = document.getElementById('course-published').checked;
  
  const res = await fetch(API+'/api/admin/courses/'+id, {{
    method: 'PUT',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{title, description, price_rub, payment_link, is_published}})
  }});
  
  if (res.ok) {{
    showSection('courses');
  }} else {{
    const data = await res.json();
    document.getElementById('course-error').textContent = data.detail || 'Ошибка';
    document.getElementById('course-error').classList.remove('hidden');
  }}
}}

async function deleteCourse(id) {{
  if (!confirm('Удалить курс?')) return;
  const res = await fetch(API+'/api/admin/courses/'+id, {{method: 'DELETE'}});
  if (res.ok) showSection('courses');
}}
function scrollToCourses() {{ document.querySelector('.section-light').scrollIntoView({{behavior:'smooth'}}); }}
init();
</script>

<!-- Payment Modal -->
<div id="payment-modal" class="modal hidden">
  <div class="modal-overlay" onclick="closePaymentModal()"></div>
  <div class="modal-content">
    <button class="modal-close" onclick="closePaymentModal()">X</button>
    <h2 id="payment-modal-title" class="modal-title">Course</h2>
    <div class="modal-price" id="payment-modal-price">0 RUB</div>
    <p class="modal-desc">You will be redirected to payment page</p>
    <button id="payment-btn" class="btn btn-primary" style="width:100%">PAY NOW</button>
  </div>
</div>
</body>
</html>'''


def get_course_html(course):
    lessons_json = json.dumps(course.get('lessons', []), ensure_ascii=False)
    return f'''<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{course['title']} - LMS</title><style>{CSS}</style></head>
<body>
<header class="header"><div class="container header-content"><a href="/" class="logo"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3z"/></svg>LMS</a><button class="btn btn-outline btn-sm" onclick="window.location.href='/'">НАЗАД</button></div></header>
<div class="course-layout"><aside class="course-sidebar" id="sidebar"></aside><main class="course-content" id="content"></main></div>
<script>
const course={json.dumps({'id':course['id'],'title':course['title'],'lessons':course.get('lessons',[])}, ensure_ascii=False)};
let currentLesson=0;
function init(){{renderSidebar();if(course.lessons.length>0)showLesson(0);else document.getElementById('content').innerHTML='<h1>Нет уроков</h1>';}}
function renderSidebar(){{document.getElementById('sidebar').innerHTML='<h3>УРОКИ</h3>'+course.lessons.map((l,i)=>'<div class="lesson-item '+(i===0?'active':'')+'" onclick="showLesson('+i+')"><div class="lesson-num">'+(i+1)+'</div><div class="lesson-title">'+l.title+'</div></div>').join('');}}
function showLesson(i){{currentLesson=i;document.querySelectorAll('.lesson-item').forEach((el,idx)=>el.classList.toggle('active',idx===i));const l=course.lessons[i];const hw=l.homework;let html='<h1>'+l.title+'</h1><p style="color:var(--color-text-muted);margin-bottom:var(--space-md);">'+(l.description||'')+'</p>';if(l.content_text)html+='<div class="content-box">'+l.content_text.replace(/```\\w*\\n([\\s\\S]*?)```/g,'<pre><code>$1</code></pre>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\\n/g,'<br>')+'</div>';if(hw){{const opts=hw.options||[];html+='<div class="hw-section"><h3 class="hw-title"><svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1z"/></svg>ДОМАШНЕЕ ЗАДАНИЕ</h3><p style="margin-bottom:var(--space-md);">'+(hw.content_text||'')+'</p>'+(opts.length?'<div class="hw-options">'+opts.map(o=>'<label class="hw-option"><input type="radio" name="hw-answer" value="'+o+'" onchange="checkAnswer(this)">'+o+'</label>').join('')+'</div><div id="hw-result"></div>':'')+'</div>';}}document.getElementById('content').innerHTML=html;let nav='<div style="display:flex;gap:1rem;margin-top:var(--space-lg);">';if(currentLesson>0)nav+='<button class="btn btn-outline" onclick="showLesson('+(currentLesson-1)+')">← ПРЕДЫДУЩИЙ</button>';if(currentLesson<course.lessons.length-1)nav+='<button class="btn btn-primary" onclick="showLesson('+(currentLesson+1)+')">СЛЕДУЮЩИЙ →</button>';nav+='</div>';document.getElementById('content').innerHTML+=nav;}}
function checkAnswer(inp){{const hw=course.lessons[currentLesson].homework;document.querySelectorAll('.hw-option').forEach(el=>el.classList.remove('selected'));inp.closest('.hw-option').classList.add('selected');document.getElementById('hw-result').innerHTML=inp.value===hw.correct_answer?'<div class="hw-result correct">✅ ПРАВИЛЬНО</div>':'<div class="hw-result incorrect">❌ НЕПРАВИЛЬНО</div>';}}
init();
</script>

<!-- Payment Modal -->
<div id="payment-modal" class="modal hidden">
  <div class="modal-overlay" onclick="closePaymentModal()"></div>
  <div class="modal-content">
    <button class="modal-close" onclick="closePaymentModal()">X</button>
    <h2 id="payment-modal-title" class="modal-title">Course</h2>
    <div class="modal-price" id="payment-modal-price">0 RUB</div>
    <p class="modal-desc">You will be redirected to payment page</p>
    <button id="payment-btn" class="btn btn-primary" style="width:100%">PAY NOW</button>
  </div>
</div>
</body>
</html>'''


def get_admin_html():
    return f'''<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Админка - LMS</title><style>{CSS}</style></head>
<body>
<header class="header"><div class="container header-content"><a href="/" class="logo"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3z"/></svg>LMS ADMIN</a><div><a href="/" class="btn btn-outline btn-sm">НА САЙТ</a> <button class="btn btn-outline btn-sm" onclick="logout()">ВЫЙТИ</button></div></div></header>
<div class="admin-layout"><aside class="admin-sidebar"><nav class="admin-nav"><div class="admin-nav-item active" onclick="showSection('courses')">КУРСЫ</div><div class="admin-nav-item" onclick="showSection('new-course')">+ НОВЫЙ КУРС</div></nav></aside><main class="admin-content" id="admin-content"><div style="text-align:center;padding:4rem;"><div class="spinner" style="margin:0 auto;"></div></div></main></div>
<script>
const API=window.location.origin;
function init(){{if(!localStorage.getItem('lms_admin')){{window.location.href='/';return;}}showSection('courses');}}
function logout(){{localStorage.clear();window.location.href='/';}}
async function showSection(section){{document.querySelectorAll('.admin-nav-item').forEach((el,i)=>el.classList.toggle('active',i===(section==='courses'?0:1)));const content=document.getElementById('admin-content');if(section==='courses'){{const res=await fetch(API+'/api/courses');const data=await res.json();const courses=data.courses||[];content.innerHTML='<div class="section-header"><h2>ВСЕ КУРСЫ</h2><button class="btn btn-primary btn-sm" onclick="showSection(\\'new-course\\')">+ ДОБАВИТЬ</button></div><table class="table"><thead><tr><th>ID</th><th>Название</th><th>Цена</th><th>Статус</th><th>Действия</th></tr></thead><tbody>'+courses.map(c=>'<tr><td>'+c.id+'</td><td>'+c.title+'</td><td>'+c.price_rub+' RUB</td><td><span class="badge '+(c.is_published?'badge-success':'badge-warning')+'">'+(c.is_published?'Published':'Draft')+'</span></td><td><button class="btn btn-sm" onclick="editCourse('+c.id+')">EDIT</button></td></tr>').join('')+'</tbody></table>';}}else if(section==='new-course'){{content.innerHTML='<h2>НОВЫЙ КУРС</h2><div style="max-width:500px;margin-top:var(--space-md);"><div id="course-error" class="auth-error hidden"></div><div class="form-group"><label class="form-label">Название</label><input type="text" class="form-input" id="course-title" placeholder="Название курса"></div><div class="form-group"><label class="form-label">Описание</label><textarea class="form-input" id="course-desc" rows="3" placeholder="Описание курса"></textarea></div><div class="form-group"><label class="form-label">Цена (руб.)</label><input type="number" class="form-input" id="course-payment-link" placeholder="https://payform.ru/..."></div><div class="form-group"><label class="form-label"><input type="checkbox" id="course-published"> Опубликован</label></div><button class="btn btn-primary" onclick="createCourse()">СОЗДАТЬ</button></div>';}}}}
async function createCourse(){{const title=document.getElementById('course-title').value;const description=document.getElementById('course-desc').value;const price_rub=parseInt(document.getElementById('course-price').value)||0;const payment_link=document.getElementById('course-payment-link').value;const is_published=document.getElementById('course-published').checked;if(!title){{document.getElementById('course-error').textContent='Введите название';document.getElementById('course-error').classList.remove('hidden');return;}}const res=await fetch(API+'/api/admin/courses',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title,description,price_rub,payment_link,is_published}})}});if(res.ok)showSection('courses');else{{const data=await res.json();document.getElementById('course-error').textContent=data.detail||'Ошибка';document.getElementById('course-error').classList.remove('hidden');}}}}
init();
</script>

<!-- Payment Modal -->
<div id="payment-modal" class="modal hidden">
  <div class="modal-overlay" onclick="closePaymentModal()"></div>
  <div class="modal-content">
    <button class="modal-close" onclick="closePaymentModal()">X</button>
    <h2 id="payment-modal-title" class="modal-title">Course</h2>
    <div class="modal-price" id="payment-modal-price">0 RUB</div>
    <p class="modal-desc">You will be redirected to payment page</p>
    <button id="payment-btn" class="btn btn-primary" style="width:100%">PAY NOW</button>
  </div>
</div>
</body>
</html>'''


# Routes

class LessonCreate(BaseModel):
    course_id: int
    title: str
    description: Optional[str] = ""
    video_url: Optional[str] = ""
    content_text: Optional[str] = ""
    sort_order: Optional[int] = 0

class HomeworkCreateModel(BaseModel):
    lesson_id: int
    content_text: str
    options: Optional[list] = []
    correct_answer: str




# Lesson Management API
@app.post("/api/admin/lessons")
async def admin_create_lesson(lesson: LessonCreate):
    lid = create_lesson(
        course_id=lesson.course_id,
        title=lesson.title,
        description=lesson.description,
        video_url=lesson.video_url,
        content_text=lesson.content_text,
        sort_order=lesson.sort_order
    )
    return {"id": lid, "success": True}

@app.get("/api/admin/lessons/{course_id}")
async def admin_get_lessons(course_id: int):
    lessons = get_lessons_by_course(course_id)
    for l in lessons:
        l['homework'] = get_homework_by_lesson(l['id'])
    return {"lessons": lessons}

@app.delete("/api/admin/lessons/{lesson_id}")
async def admin_delete_lesson(lesson_id: int):
    delete_lesson(lesson_id)
    return {"success": True}

@app.post("/api/admin/homework")
async def admin_create_homework(hw: HomeworkCreateModel):
    hid = create_homework(
        lesson_id=hw.lesson_id,
        content_text=hw.content_text,
        options=hw.options,
        correct_answer=hw.correct_answer
    )
    return {"id": hid, "success": True}



# Lesson API Endpoints
@app.post("/api/admin/lessons")
async def admin_create_lesson(request: Request):
    data = await request.json()
    lid = create_lesson(
        course_id=data.get("course_id"),
        title=data.get("title"),
        description=data.get("description", ""),
        video_url=data.get("video_url"),
        content_text=data.get("content_text"),
        sort_order=data.get("sort_order", 0)
    )
    return {"id": lid, "success": True}

@app.get("/api/admin/lessons/{course_id}")
async def admin_get_lessons(course_id: int):
    lessons = get_lessons_by_course(course_id)
    return {"lessons": lessons}

@app.delete("/api/admin/lessons/{lesson_id}")
async def admin_delete_lesson(lesson_id: int):
    delete_lesson(lesson_id)
    return {"success": True}



# HEAD endpoints for browser compatibility


@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request):
    if request.method == "HEAD":
        return Response(content=b"", media_type="text/html")
    return HTMLResponse(content=get_main_html())


@app.api_route("/api/courses", methods=["GET", "HEAD"])
async def api_courses():
    courses = get_all_courses(published_only=True)
    return {"courses": courses}


@app.get("/api/courses/{course_id}")
async def api_course(course_id: int):
    course = get_course_with_lessons(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Not found")
    return course


@app.get("/course/{course_id}")
async def course_page(course_id: int):
    course = get_course_with_lessons(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Not found")
    return HTMLResponse(content=get_course_html(course))


@app.post("/api/auth/login")
async def api_login(data: LoginRequest):
    user = authenticate_user(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    purchased_ids = get_purchased_course_ids(user['id'])
    return {"user": {"id": user['id'], "email": user['email'], "role": user['role']}, "purchased_ids": purchased_ids}


@app.post("/api/admin/verify")
async def api_admin_verify(data: AdminVerifyRequest):
    if data.password == ADMIN_PASSWORD:
        return {"success": True}
    raise HTTPException(status_code=401, detail="Неверный пароль")


@app.post("/api/admin/courses")
async def api_create_course(data: CourseCreate):
    return create_course(title=data.title, description=data.description, price_rub=data.price_rub, payment_link=data.payment_link, is_published=data.is_published)


@app.post("/api/payment/create")
async def api_payment(request: Request, data: PaymentCreate):
    course = get_course_by_id(data.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    order_id = generate_order_id(data.course_id, data.email)
    base_url = str(request.url).split('/api')[0]
    payment_url = generate_payment_link(order_id=order_id, product_name=course["title"], price_rub=course["price_rub"], customer_email=data.email, course_id=data.course_id, success_url=f"{base_url}/?payment=success", webhook_url=f"{base_url}/prodamus-webhook")
    return {"order_id": order_id, "payment_url": payment_url}


@app.get("/admin")
async def admin_page():
    return HTMLResponse(content=get_admin_html())


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/prodamus-webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Webhook: {data}")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)










