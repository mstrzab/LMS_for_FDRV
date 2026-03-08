"""
Vercel Serverless Handler for LMS Platform
"""
import os
import sys
import json
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Local imports (same directory)
from database import (
    init_database, get_all_courses, get_course_by_id, get_course_with_lessons,
    create_course, authenticate_user, get_purchased_course_ids
)
from prodamus_integration import generate_payment_link, generate_order_id

# Initialize database
init_database()

# Constants
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Kon!AdminFDRV")

# Create FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
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


# HTML content
MAIN_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LMS Platform</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--primary:#3B82F6;--bg:#F8FAFC;--surface:#FFF;--text:#0F172A;--border:#E2E8F0;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
.header{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;position:sticky;top:0;z-index:100;}
.header-content{max-width:1280px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;}
.logo{display:flex;align-items:center;gap:12px;font-size:20px;font-weight:700;text-decoration:none;color:var(--text);}
.logo svg{color:var(--primary);}
.container{max-width:1280px;margin:0 auto;padding:24px;}
.courses-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px;margin-top:24px;}
.card{background:var(--surface);border-radius:12px;border:1px solid var(--border);overflow:hidden;transition:transform 0.2s;}
.card:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,0.1);}
.card-image{height:160px;background:linear-gradient(135deg,var(--primary),#6366F1);display:flex;align-items:center;justify-content:center;color:white;font-size:48px;}
.card-body{padding:20px;}
.card-title{font-size:18px;font-weight:600;margin-bottom:8px;}
.card-desc{font-size:14px;color:#64748B;margin-bottom:16px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.card-footer{display:flex;justify-content:space-between;align-items:center;padding-top:16px;border-top:1px solid var(--border);}
.price{font-size:20px;font-weight:700;color:var(--primary);}
.btn{padding:10px 20px;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;border:none;text-decoration:none;display:inline-flex;align-items:center;gap:8px;}
.btn-primary{background:var(--primary);color:white;}
.btn-sm{padding:6px 12px;font-size:12px;}
.section-title{font-size:24px;font-weight:600;}
.section-subtitle{color:#64748B;margin-top:4px;}
.login-prompt{text-align:center;padding:60px 20px;background:var(--surface);border-radius:16px;margin-top:40px;}
.form-group{margin-bottom:16px;text-align:left;}
.form-label{display:block;font-size:14px;font-weight:500;margin-bottom:8px;}
.form-input{width:100%;padding:12px 16px;border:1px solid var(--border);border-radius:8px;font-size:14px;}
#login-form{max-width:400px;margin:0 auto;}
.error{color:#EF4444;font-size:14px;margin-top:8px;}
.spinner{width:40px;height:40px;border:3px solid var(--border);border-top-color:var(--primary);border-radius:50%;animation:spin 1s linear infinite;margin:0 auto;}
@keyframes spin{to{transform:rotate(360deg);}}
.hidden{display:none;}
</style>
</head>
<body>
<header class="header">
<div class="header-content">
<a href="/" class="logo"><svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3z"/></svg>LMS Platform</a>
<div id="user-info"></div>
</div>
</header>
<main class="container" id="main-content">
<div style="text-align:center;padding:60px;"><div class="spinner"></div><p style="margin-top:16px;color:#64748B;">Загрузка...</p></div>
</main>
<script>
const API=window.location.origin;let currentUser=null,courses=[],purchasedIds=[];
async function checkAuth(){const s=localStorage.getItem('lms_user');if(s){currentUser=JSON.parse(s);purchasedIds=JSON.parse(localStorage.getItem('lms_purchased')||'[]');}}
async function loadCourses(){const r=await fetch(API+'/api/courses'),d=await r.json();courses=d.courses||[];}
function render(){const u=document.getElementById('user-info'),c=document.getElementById('main-content');if(currentUser){u.innerHTML='<span style="color:#64748B;margin-right:12px">'+currentUser.email+'</span><button class="btn btn-sm" style="background:transparent;color:var(--primary)" onclick="logout()">Выйти</button>';const p=courses.filter(x=>purchasedIds.includes(x.id)),a=courses.filter(x=>!purchasedIds.includes(x.id));c.innerHTML=(p.length?'<section style="margin-bottom:40px"><h2 class="section-title">Продолжить обучение</h2><div class="courses-grid">'+p.map(x=>card(x,1)).join('')+'</div></section>':'')+'<section><h2 class="section-title">Каталог курсов</h2><p class="section-subtitle">'+a.length+' курсов</p><div class="courses-grid">'+(a.length?a.map(x=>card(x,0)).join(''):'<p style="color:#64748B">Нет доступных курсов</p>')+'</div></section>';}else{u.innerHTML='';c.innerHTML='<section><h2 class="section-title">Каталог курсов</h2><p class="section-subtitle">'+courses.length+' курсов</p><div class="courses-grid">'+courses.map(x=>card(x,0)).join('')+'</div></section><div class="login-prompt"><h2>Войдите для доступа к курсам</h2><p>После покупки курса вы получите данные для входа</p><div id="login-error" class="error hidden"></div><form id="login-form" onsubmit="handleLogin(event)"><div class="form-group"><label class="form-label">Email</label><input type="email" class="form-input" id="email" placeholder="user@example.com" required></div><div class="form-group"><label class="form-label">Пароль</label><input type="password" class="form-input" id="password" required></div><button type="submit" class="btn btn-primary" style="width:100%">Войти</button></form><p style="margin-top:20px;color:#64748B"><a href="#" onclick="showAdminLogin()" style="color:var(--primary)">Вход для администратора</a></p></div>';}}
function card(c,b){const p=c.price_rub>0?new Intl.NumberFormat('ru-RU').format(c.price_rub)+' ₽':'Бесплатно';return'<div class="card"><div class="card-image">📚</div><div class="card-body"><h3 class="card-title">'+c.title+'</h3><p class="card-desc">'+(c.description||'')+'</p><div class="card-footer"><span class="price">'+p+'</span>'+(b?'<button class="btn btn-primary btn-sm" onclick="openCourse('+c.id+')">Открыть</button>':'<button class="btn btn-primary btn-sm" onclick="buyCourse('+c.id+')">Купить</button>')+'</div></div></div>';}
async function handleLogin(e){e.preventDefault();try{const r=await fetch(API+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('email').value,password:document.getElementById('password').value})}),d=await r.json();if(r.ok){currentUser=d.user;purchasedIds=d.purchased_ids||[];localStorage.setItem('lms_user',JSON.stringify(currentUser));localStorage.setItem('lms_purchased',JSON.stringify(purchasedIds));render();}else{document.getElementById('login-error').textContent=d.detail||'Ошибка';document.getElementById('login-error').classList.remove('hidden');}}catch(err){document.getElementById('login-error').textContent='Ошибка соединения';document.getElementById('login-error').classList.remove('hidden');}}
function logout(){currentUser=null;purchasedIds=[];localStorage.clear();render();}
function showAdminLogin(){const p=prompt('Пароль администратора:');if(p)fetch(API+'/api/admin/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})}).then(r=>r.json()).then(d=>{if(d.success){localStorage.setItem('lms_admin','true');window.location.href='/admin';}else alert('Неверный пароль');});}
function buyCourse(id){const c=courses.find(x=>x.id===id);if(c.price_rub===0){purchasedIds.push(id);localStorage.setItem('lms_purchased',JSON.stringify(purchasedIds));render();return;}const e=prompt('Email:');if(e)fetch(API+'/api/payment/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({course_id:id,email:e})}).then(r=>r.json()).then(d=>{if(d.payment_url){alert('Перенаправление на оплату');window.open(d.payment_url,'_blank');}});}
function openCourse(id){window.location.href='/course/'+id;}
async function init(){await checkAuth();await loadCourses();render();}
init();
</script>
</body>
</html>'''


# Routes
@app.get("/")
async def root():
    return HTMLResponse(content=MAIN_HTML)


@app.get("/api/courses")
async def api_courses():
    courses = get_all_courses(published_only=True)
    for c in courses:
        c.pop("payment_link", None)
    return {"courses": courses}


@app.get("/api/courses/{course_id}")
async def api_course(course_id: int):
    course = get_course_with_lessons(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Not found")
    return course


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
    return create_course(title=data.title, description=data.description, image_url=data.image_url, price_rub=data.price_rub, is_published=data.is_published)


@app.post("/api/payment/create")
async def api_payment(request: Request, data: PaymentCreate):
    course = get_course_by_id(data.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    order_id = generate_order_id(data.course_id, data.email)
    base_url = str(request.url).split('/api')[0]
    payment_url = generate_payment_link(order_id=order_id, product_name=course["title"], price_rub=course["price_rub"], customer_email=data.email, course_id=data.course_id, success_url=f"{base_url}/?payment=success", webhook_url=f"{base_url}/api/webhook")
    return {"order_id": order_id, "payment_url": payment_url}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/course/{course_id}")
async def course_page(course_id: int):
    course = get_course_with_lessons(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Not found")
    
    lessons_json = json.dumps(course['lessons'], ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{course['title']} - LMS</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>:root{{--primary:#3B82F6;--bg:#F8FAFC;--surface:#FFF;--text:#0F172A;--border:#E2E8F0;--secondary:#6366F1;--success:#22C55E;--error:#EF4444;}}*{{margin:0;padding:0;box-sizing:border-box;}}body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);}}.header{{background:var(--surface);border-bottom:1px solid var(--border);padding:12px 24px;position:sticky;top:0;z-index:100;}}.header-content{{display:flex;align-items:center;gap:16px;}}.back-btn{{background:none;border:none;cursor:pointer;display:flex;align-items:center;gap:8px;}}.layout{{display:grid;grid-template-columns:280px 1fr;min-height:calc(100vh - 56px);}}.sidebar{{background:var(--surface);border-right:1px solid var(--border);padding:20px;overflow-y:auto;}}.content{{padding:32px;overflow-y:auto;max-width:900px;}}.lesson-item{{padding:12px 16px;border-radius:8px;cursor:pointer;display:flex;align-items:center;gap:12px;margin-bottom:4px;}}.lesson-item:hover{{background:var(--bg);}}.lesson-item.active{{background:var(--primary);color:white;}}.lesson-num{{width:28px;height:28px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;}}.lesson-item.active .lesson-num{{background:white;color:var(--primary);}}h1{{font-size:28px;margin-bottom:8px;}}.desc{{color:#64748B;margin-bottom:24px;}}.content-box{{background:var(--surface);padding:24px;border-radius:12px;border:1px solid var(--border);line-height:1.8;}}.content-box pre{{background:var(--bg);padding:16px;border-radius:8px;overflow-x:auto;}}.content-box code{{background:var(--bg);padding:2px 6px;border-radius:4px;font-family:monospace;}}.hw-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;margin-top:24px;}}.hw-title{{display:flex;align-items:center;gap:12px;font-size:18px;font-weight:600;margin-bottom:16px;}}.radio-group{{display:flex;flex-direction:column;gap:12px;margin:16px 0;}}.radio-opt{{display:flex;align-items:center;gap:12px;padding:14px 16px;border:1px solid var(--border);border-radius:8px;cursor:pointer;}}.radio-opt:hover{{border-color:var(--primary);}}.radio-opt.selected{{border-color:var(--primary);background:rgba(59,130,246,0.05);}}.btn{{padding:10px 20px;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;border:none;}}.btn-primary{{background:var(--primary);color:white;}}.result{{margin-top:16px;padding:12px;border-radius:8px;}}.result.success{{background:rgba(34,197,94,0.1);color:var(--success);}}.result.error{{background:rgba(239,68,68,0.1);color:var(--error);}}@media(max-width:768px){{.layout{{grid-template-columns:1fr;}}.sidebar{{display:none;}}}}</style>
</head>
<body>
<header class="header"><div class="header-content"><button class="back-btn" onclick="window.location.href='/'"><svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg></button><span style="font-size:18px;font-weight:600;">{course['title']}</span></div></header>
<div class="layout"><aside class="sidebar" id="sidebar"></aside><main class="content" id="content"></main></div>
<script>
const course={json.dumps({'id':course['id'],'title':course['title'],'lessons':course['lessons']}, ensure_ascii=False)};
let currentLesson=0;
function renderSidebar(){{document.getElementById('sidebar').innerHTML=course.lessons.map((l,i)=>'<div class="lesson-item '+(i===0?'active':'')+'" onclick="showLesson('+i+')"><div class="lesson-num">'+(i+1)+'</div><div><div style="font-weight:500;">'+l.title+'</div>'+(l.homework?'📋 Есть ДЗ':'')+'</div></div>').join('');}}
function showLesson(i){{currentLesson=i;document.querySelectorAll('.lesson-item').forEach((el,idx)=>el.classList.toggle('active',idx===i));const l=course.lessons[i];const hw=l.homework;let html='<h1>'+l.title+'</h1><p class="desc">'+(l.description||'')+'</p>';if(l.content_text){{html+='<div class="content-box">'+fmt(l.content_text)+'</div>';}}if(hw){{const opts=hw.options||[];html+='<div class="hw-card"><div class="hw-title">📋 Домашнее задание</div><p>'+(hw.content_text||'')+'</p>'+(opts.length?'<div class="radio-group">'+opts.map(o=>'<label class="radio-opt"><input type="radio" name="ans" value="'+o+'" onchange="checkAns(this)">'+o+'</label>').join('')+'</div><div id="res"></div>':'')+'</div>';}}document.getElementById('content').innerHTML=html;}}
function fmt(t){{return t.replace(/```\\w*\\n([\\s\\S]*?)```/g,'<pre><code>$1</code></pre>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/## (.*)/g,'<h2>$1</h2>').replace(/# (.*)/g,'<h1>$1</h1>').replace(/\\n/g,'<br>');}}
function checkAns(inp){{const hw=course.lessons[currentLesson].homework;document.querySelectorAll('.radio-opt').forEach(el=>el.classList.remove('selected'));inp.closest('.radio-opt').classList.add('selected');document.getElementById('res').innerHTML=inp.value===hw.correct_answer?'<div class="result success">✅ Правильно!</div>':'<div class="result error">❌ Неправильно</div>';}}
renderSidebar();showLesson(0);
</script>
</body>
</html>'''
    return HTMLResponse(content=html)


@app.get("/admin")
async def admin_page():
    return HTMLResponse(content='''<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Admin - LMS</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>:root{--primary:#3B82F6;--bg:#F8FAFC;--surface:#FFF;--text:#0F172A;--border:#E2E8F0;}*{margin:0;padding:0;box-sizing:border-box;}body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);}.header{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;}.header-content{max-width:1280px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;}.logo{display:flex;align-items:center;gap:12px;font-size:20px;font-weight:700;text-decoration:none;color:var(--text);}.container{max-width:1280px;margin:0 auto;padding:24px;}.table{width:100%;border-collapse:collapse;background:var(--surface);border-radius:12px;overflow:hidden;margin-top:24px;}.table th,.table td{padding:14px 16px;text-align:left;border-bottom:1px solid var(--border);}.table th{background:var(--bg);font-weight:600;font-size:14px;color:#64748B;}.btn{padding:8px 16px;border-radius:6px;font-size:14px;cursor:pointer;border:none;text-decoration:none;}.btn-primary{background:var(--primary);color:white;}.form{background:var(--surface);padding:24px;border-radius:12px;border:1px solid var(--border);max-width:600px;margin-top:24px;}.form-group{margin-bottom:16px;}.form-label{display:block;font-size:14px;font-weight:500;margin-bottom:8px;}.form-input{width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:8px;font-size:14px;}.badge{display:inline-block;padding:4px 8px;border-radius:4px;font-size:12px;}.badge-success{background:rgba(34,197,94,0.1);color:#22C55E;}.badge-warning{background:rgba(245,158,11,0.1);color:#F59E0B;}.section-header{display:flex;justify-content:space-between;align-items:center;}h1{font-size:24px;}</style>
</head>
<body>
<header class="header"><div class="header-content"><a href="/" class="logo"><svg width="32" height="32" viewBox="0 0 24 24" fill="var(--primary)"><path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3z"/></svg>LMS Admin</a><div><a href="/" class="btn btn-primary" style="padding:6px 12px;font-size:12px;">На сайт</a> <button class="btn" style="padding:6px 12px;font-size:12px;" onclick="localStorage.clear();window.location.href='/'">Выйти</button></div></div></header>
<main class="container">
<div class="section-header"><h1>Управление курсами</h1><button class="btn btn-primary" onclick="document.getElementById('form-container').style.display='block'">+ Новый курс</button></div>
<div id="form-container" style="display:none;"><div class="form"><h2 style="margin-bottom:20px;">Новый курс</h2><div class="form-group"><label class="form-label">Название</label><input type="text" class="form-input" id="title"></div><div class="form-group"><label class="form-label">Описание</label><textarea class="form-input" id="description" rows="3"></textarea></div><div class="form-group"><label class="form-label">Цена (руб.)</label><input type="number" class="form-input" id="price" value="0"></div><div class="form-group"><label class="form-label"><input type="checkbox" id="published"> Опубликован</label></div><button class="btn btn-primary" onclick="createCourse()">Создать</button> <button class="btn" style="background:transparent;margin-left:8px;" onclick="document.getElementById('form-container').style.display='none'">Отмена</button></div></div>
<table class="table" id="tbl"><thead><tr><th>ID</th><th>Название</th><th>Цена</th><th>Статус</th></tr></thead><tbody></tbody></table>
</main>
<script>
const API=window.location.origin;
async function load(){const r=await fetch(API+'/api/courses'),d=await r.json();document.querySelector('#tbl tbody').innerHTML=(d.courses||[]).map(c=>'<tr><td>'+c.id+'</td><td>'+c.title+'</td><td>'+c.price_rub+' ₽</td><td><span class="badge '+(c.is_published?'badge-success':'badge-warning')+'">'+(c.is_published?'Опубликован':'Черновик')+'</span></td></tr>').join('');}
async function createCourse(){const d={title:document.getElementById('title').value,description:document.getElementById('description').value,price_rub:parseInt(document.getElementById('price').value)||0,is_published:document.getElementById('published').checked};if(!d.title){alert('Введите название');return;}const r=await fetch(API+'/api/admin/courses',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});if(r.ok){document.getElementById('form-container').style.display='none';load();}}
load();
</script>
</body>
</html>''')


@app.post("/api/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Webhook: {data}")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Vercel handler - this is what Vercel looks for
def handler(request, context):
    return app(request, context)
