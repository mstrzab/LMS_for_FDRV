// LMS Platform - Frontend JavaScript

const API_URL = window.location.origin;

// State
let currentUser = null;
let purchasedCourses = [];
let allCourses = [];

// ============ API Functions ============

async function api(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    if (options.body && typeof options.body === 'object') {
        options.body = JSON.stringify(options.body);
    }
    
    const response = await fetch(API_URL + endpoint, { ...defaultOptions, ...options });
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
        throw new Error(data.detail || 'Ошибка сервера');
    }
    
    return data;
}

// ============ Auth Functions ============

function getToken() {
    return localStorage.getItem('lms_token');
}

function setToken(token) {
    localStorage.setItem('lms_token', token);
}

function getUser() {
    const user = localStorage.getItem('lms_user');
    return user ? JSON.parse(user) : null;
}

function setUser(user) {
    localStorage.setItem('lms_user', JSON.stringify(user));
    currentUser = user;
}

function isLoggedIn() {
    return !!getToken();
}

function logout() {
    localStorage.removeItem('lms_token');
    localStorage.removeItem('lms_user');
    currentUser = null;
    showHomePage();
}

// ============ Navigation ============

function navigate(path) {
    history.pushState({}, '', path);
    handleRoute();
}

function handleRoute() {
    const path = window.location.pathname;
    const token = getToken();
    
    // Public routes
    if (path === '/login') {
        if (token) {
            navigate('/');
            return;
        }
        showLoginPage();
        return;
    }
    
    if (path === '/admin') {
        showAdminLoginPage();
        return;
    }
    
    if (path.startsWith('/admin/')) {
        if (!localStorage.getItem('lms_admin')) {
            navigate('/admin');
            return;
        }
        showAdminPanel();
        return;
    }
    
    if (path.startsWith('/course/')) {
        const courseId = path.split('/')[2];
        showCoursePage(courseId);
        return;
    }
    
    // Home - require auth
    if (!token) {
        navigate('/login');
        return;
    }
    
    showHomePage();
}

// ============ Page Rendering ============

function renderApp(content) {
    document.getElementById('app').innerHTML = content;
    attachEventListeners();
}

function renderHeader(showLogout = false) {
    const user = getUser();
    const isAdmin = localStorage.getItem('lms_admin');
    
    return `
        <header class="header">
            <div class="container header-content">
                <a href="/" class="logo" onclick="event.preventDefault(); navigate('/')">
                    <svg class="logo-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z"/>
                    </svg>
                    LMS Platform
                </a>
                <div class="flex gap-2">
                    ${isAdmin ? '<a href="/admin/dashboard" class="btn btn-secondary btn-sm" onclick="event.preventDefault(); navigate(\'/admin/dashboard\')">Админ</a>' : ''}
                    ${showLogout ? `
                        ${user ? `<span style="color: var(--text-secondary); font-size: 14px;">${user.email}</span>` : ''}
                        <button class="btn btn-secondary btn-sm" onclick="logout()">Выйти</button>
                    ` : ''}
                </div>
            </div>
        </header>
    `;
}

// ============ Login Page ============

function showLoginPage() {
    const content = `
        <div class="auth-container">
            <div class="auth-card">
                <div class="auth-logo">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z"/>
                    </svg>
                </div>
                <h1 class="auth-title">Вход в платформу</h1>
                <p class="auth-subtitle">Используйте email и пароль для входа</p>
                
                <div id="login-error" class="alert alert-error hidden"></div>
                
                <form id="login-form">
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-input" id="login-email" placeholder="user@example.com" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Пароль</label>
                        <input type="password" class="form-input" id="login-password" placeholder="••••••••" required>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: 100%">
                        Войти
                    </button>
                </form>
                
                <div class="text-center mt-8">
                    <a href="/admin" class="btn btn-secondary" onclick="event.preventDefault(); navigate('/admin')">
                        Вход для администратора
                    </a>
                </div>
            </div>
        </div>
    `;
    
    renderApp(content);
}

// ============ Admin Login Page ============

function showAdminLoginPage() {
    if (localStorage.getItem('lms_admin')) {
        navigate('/admin/dashboard');
        return;
    }
    
    const content = `
        <div class="auth-container">
            <div class="auth-card">
                <div class="auth-logo">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/>
                    </svg>
                </div>
                <h1 class="auth-title">Панель администратора</h1>
                <p class="auth-subtitle">Введите пароль для доступа</p>
                
                <div id="admin-error" class="alert alert-error hidden"></div>
                
                <form id="admin-form">
                    <div class="form-group">
                        <label class="form-label">Пароль администратора</label>
                        <input type="password" class="form-input" id="admin-password" placeholder="••••••••" required>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: 100%">
                        Войти
                    </button>
                </form>
                
                <div class="text-center mt-8">
                    <a href="/" class="btn btn-secondary" onclick="event.preventDefault(); navigate('/')">
                        ← На главную
                    </a>
                </div>
            </div>
        </div>
    `;
    
    renderApp(content);
}

// ============ Home Page ============

async function showHomePage() {
    renderApp(`
        ${renderHeader(true)}
        <div class="container section">
            <div class="loading"><div class="spinner"></div></div>
        </div>
    `);
    
    try {
        // Load courses
        const data = await api('/api/courses');
        allCourses = data.courses || [];
        
        // TODO: Load user purchases from API
        purchasedCourses = [];
        
        renderDashboard();
    } catch (error) {
        console.error('Error loading courses:', error);
        renderApp(`
            ${renderHeader(true)}
            <div class="container section">
                <div class="alert alert-error">Ошибка загрузки курсов: ${error.message}</div>
            </div>
        `);
    }
}

function renderDashboard() {
    const purchasedIds = purchasedCourses.map(c => c.id);
    const purchased = allCourses.filter(c => purchasedIds.includes(c.id));
    const available = allCourses.filter(c => !purchasedIds.includes(c.id));
    
    const content = `
        ${renderHeader(true)}
        <div class="container">
            ${purchased.length > 0 ? `
                <section class="section">
                    <div class="section-header">
                        <div>
                            <h2 class="section-title">Продолжить обучение</h2>
                            <p class="section-subtitle">${purchased.length} курсов</p>
                        </div>
                    </div>
                    <div class="courses-grid">
                        ${purchased.map(course => renderCourseCard(course, true)).join('')}
                    </div>
                </section>
            ` : ''}
            
            <section class="section">
                <div class="section-header">
                    <div>
                        <h2 class="section-title">Каталог курсов</h2>
                        <p class="section-subtitle">${available.length} курсов</p>
                    </div>
                </div>
                <div class="courses-grid">
                    ${available.length > 0 
                        ? available.map(course => renderCourseCard(course, false)).join('')
                        : '<p style="color: var(--text-secondary);">Нет доступных курсов</p>'
                    }
                </div>
            </section>
        </div>
    `;
    
    renderApp(content);
}

function renderCourseCard(course, isPurchased) {
    const priceFormatted = new Intl.NumberFormat('ru-RU').format(course.price_rub);
    
    return `
        <div class="card">
            <div class="card-image">
                ${course.image_url 
                    ? `<img src="${course.image_url}" alt="${course.title}" style="width:100%;height:100%;object-fit:cover;">`
                    : `<svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3z"/></svg>`
                }
            </div>
            <div class="card-body">
                <h3 class="card-title">${course.title}</h3>
                <p class="card-description">${course.description || 'Описание отсутствует'}</p>
                <div class="card-footer">
                    <span class="card-price">${course.price_rub > 0 ? priceFormatted + ' ₽' : 'Бесплатно'}</span>
                    ${isPurchased 
                        ? `<button class="btn btn-primary btn-sm" onclick="navigate('/course/${course.id}')">Открыть</button>`
                        : `<button class="btn btn-primary btn-sm" onclick="showPaymentModal(${course.id})">Купить</button>`
                    }
                </div>
            </div>
        </div>
    `;
}

// ============ Course Page ============

async function showCoursePage(courseId) {
    if (!getToken()) {
        navigate('/login');
        return;
    }
    
    renderApp(`
        ${renderHeader(true)}
        <div class="container section">
            <div class="loading"><div class="spinner"></div></div>
        </div>
    `);
    
    try {
        const course = await api(`/api/courses/${courseId}`);
        
        // Check if user has access
        if (!purchasedCourses.find(c => c.id === parseInt(courseId))) {
            renderApp(`
                ${renderHeader(true)}
                <div class="container section">
                    <div class="auth-card" style="max-width: 500px; margin: 0 auto;">
                        <div class="text-center">
                            <svg width="60" height="60" viewBox="0 0 24 24" fill="var(--error)">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-7h2v4h-2zm0-6h2v4h-2z"/>
                            </svg>
                            <h2 class="mt-4" style="font-size: 24px;">Доступ запрещён</h2>
                            <p class="section-subtitle mt-4">Купите курс для доступа к материалам</p>
                            <button class="btn btn-primary mt-8" onclick="showPaymentModal(${courseId})">Купить курс</button>
                        </div>
                    </div>
                </div>
            `);
            return;
        }
        
        renderCourseContent(course);
    } catch (error) {
        renderApp(`
            ${renderHeader(true)}
            <div class="container section">
                <div class="alert alert-error">Ошибка: ${error.message}</div>
                <button class="btn btn-secondary mt-4" onclick="navigate('/')">← На главную</button>
            </div>
        `);
    }
}

function renderCourseContent(course) {
    const lessons = course.lessons || [];
    const firstLesson = lessons[0];
    
    const content = `
        ${renderHeader(true)}
        <div class="course-layout">
            <aside class="course-sidebar">
                <h3 style="font-weight: 600; margin-bottom: 8px;">${course.title}</h3>
                <p style="font-size: 14px; color: var(--text-secondary); margin-bottom: 16px;">
                    ${lessons.length} уроков
                </p>
                <div class="lessons-list">
                    ${lessons.map((lesson, index) => `
                        <div class="lesson-item ${index === 0 ? 'active' : ''}" 
                             data-lesson-id="${lesson.id}"
                             onclick="selectLesson(${course.id}, ${lesson.id}, this)">
                            <div class="lesson-number">${index + 1}</div>
                            <div>
                                <div style="font-weight: 500;">${lesson.title}</div>
                                ${lesson.homework ? '<span style="font-size: 12px; color: var(--text-secondary);">📋 Есть ДЗ</span>' : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </aside>
            <main class="course-content" id="lesson-content">
                ${firstLesson ? renderLessonView(firstLesson) : '<p>Нет уроков</p>'}
            </main>
        </div>
    `;
    
    renderApp(content);
}

function renderLessonView(lesson) {
    let videoHtml = '';
    if (lesson.video_url) {
        if (lesson.video_url.includes('youtube.com') || lesson.video_url.includes('youtu.be')) {
            videoHtml = `<div class="video-container"><iframe src="${lesson.video_url}" frameborder="0" allowfullscreen></iframe></div>`;
        } else {
            videoHtml = `<div class="video-container"><video controls src="${lesson.video_url}"></video></div>`;
        }
    }
    
    let homeworkHtml = '';
    if (lesson.homework) {
        const hw = lesson.homework;
        const options = hw.options || [];
        
        homeworkHtml = `
            <div class="homework-card">
                <div class="homework-title">
                    <svg class="homework-icon" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                    </svg>
                    Домашнее задание
                </div>
                <p>${hw.content_text || ''}</p>
                ${options.length > 0 ? `
                    <div class="radio-group">
                        ${options.map((opt, i) => `
                            <label class="radio-option">
                                <input type="radio" name="hw-answer" value="${opt}">
                                ${opt}
                            </label>
                        `).join('')}
                    </div>
                    <button class="btn btn-primary" onclick="checkHomework(${hw.id})">Проверить ответ</button>
                    <div id="hw-result" class="mt-4"></div>
                ` : ''}
            </div>
        `;
    }
    
    return `
        <div>
            <h1 style="font-size: 24px; font-weight: 700; margin-bottom: 8px;">${lesson.title}</h1>
            <p style="color: var(--text-secondary); margin-bottom: 24px;">${lesson.description || ''}</p>
            
            ${videoHtml}
            
            ${lesson.content_text ? `
                <div style="background: var(--surface); padding: 24px; border-radius: 12px; border: 1px solid var(--border);">
                    ${lesson.content_text}
                </div>
            ` : ''}
            
            ${homeworkHtml}
        </div>
    `;
}

function selectLesson(courseId, lessonId, element) {
    // Update active state
    document.querySelectorAll('.lesson-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    
    // Find lesson from course data
    api(`/api/courses/${courseId}`).then(course => {
        const lesson = course.lessons.find(l => l.id === lessonId);
        if (lesson) {
            document.getElementById('lesson-content').innerHTML = renderLessonView(lesson);
        }
    });
}

// ============ Admin Panel ============

function showAdminPanel() {
    const content = `
        ${renderHeader(true)}
        <div class="admin-layout">
            <aside class="admin-sidebar">
                <nav>
                    <a href="#" class="admin-nav-item active" onclick="event.preventDefault(); showAdminSection('courses')">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"/></svg>
                        Курсы
                    </a>
                    <a href="#" class="admin-nav-item" onclick="event.preventDefault(); showAdminSection('new-course')">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                        Новый курс
                    </a>
                </nav>
            </aside>
            <main class="admin-content" id="admin-content">
                <div class="loading"><div class="spinner"></div></div>
            </main>
        </div>
    `;
    
    renderApp(content);
    showAdminSection('courses');
}

async function showAdminSection(section) {
    const container = document.getElementById('admin-content');
    
    // Update nav
    document.querySelectorAll('.admin-nav-item').forEach(el => el.classList.remove('active'));
    event?.target?.closest('.admin-nav-item')?.classList.add('active');
    
    if (section === 'courses') {
        container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        
        try {
            const data = await api('/api/courses');
            const courses = data.courses || [];
            
            container.innerHTML = `
                <div class="section-header">
                    <h2 class="section-title">Все курсы</h2>
                    <button class="btn btn-primary" onclick="showAdminSection('new-course')">+ Новый курс</button>
                </div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Название</th>
                            <th>Цена</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${courses.map(c => `
                            <tr>
                                <td>${c.id}</td>
                                <td>${c.title}</td>
                                <td>${c.price_rub} ₽</td>
                                <td>
                                    <span class="badge ${c.is_published ? 'badge-success' : 'badge-warning'}">
                                        ${c.is_published ? 'Опубликован' : 'Черновик'}
                                    </span>
                                </td>
                                <td>
                                    <button class="btn btn-secondary btn-sm" onclick="editCourse(${c.id})">✏️</button>
                                    <button class="btn btn-error btn-sm" onclick="deleteCourse(${c.id})">🗑️</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            container.innerHTML = `<div class="alert alert-error">Ошибка: ${error.message}</div>`;
        }
    } else if (section === 'new-course') {
        container.innerHTML = `
            <h2 class="section-title">Новый курс</h2>
            <form id="course-form" style="max-width: 600px; margin-top: 24px;">
                <div id="course-error" class="alert alert-error hidden"></div>
                
                <div class="form-group">
                    <label class="form-label">Название курса</label>
                    <input type="text" class="form-input" id="course-title" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Описание</label>
                    <textarea class="form-input form-textarea" id="course-description"></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">URL изображения</label>
                    <input type="url" class="form-input" id="course-image">
                </div>
                <div class="form-group">
                    <label class="form-label">Цена (руб.)</label>
                    <input type="number" class="form-input" id="course-price" value="0" min="0">
                </div>
                <div class="form-group">
                    <label class="form-label">
                        <input type="checkbox" id="course-published"> Опубликован
                    </label>
                </div>
                <button type="submit" class="btn btn-primary">Создать курс</button>
            </form>
        `;
    }
}

// ============ Payment Modal ============

function showPaymentModal(courseId) {
    const course = allCourses.find(c => c.id === courseId);
    if (!course) return;
    
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.id = 'payment-modal';
    modal.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title">Покупка курса</h3>
                <button class="modal-close" onclick="closePaymentModal()">&times;</button>
            </div>
            <div>
                <p style="margin-bottom: 16px;"><strong>${course.title}</strong></p>
                <p style="font-size: 24px; font-weight: 700; color: var(--primary); margin-bottom: 24px;">
                    ${new Intl.NumberFormat('ru-RU').format(course.price_rub)} ₽
                </p>
                <div class="form-group">
                    <label class="form-label">Email для получения доступа</label>
                    <input type="email" class="form-input" id="payment-email" placeholder="your@email.com" required>
                </div>
                <button class="btn btn-primary" style="width: 100%;" onclick="processPayment(${course.id})">
                    Перейти к оплате
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function closePaymentModal() {
    const modal = document.getElementById('payment-modal');
    if (modal) modal.remove();
}

async function processPayment(courseId) {
    const email = document.getElementById('payment-email').value;
    if (!email) {
        alert('Введите email');
        return;
    }
    
    try {
        const result = await api('/api/payment/create', {
            method: 'POST',
            body: { course_id: courseId, email }
        });
        
        if (result.payment_url) {
            window.open(result.payment_url, '_blank');
            closePaymentModal();
            alert('После оплаты проверьте почту — туда придут данные для входа');
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

// ============ Event Listeners ============

function attachEventListeners() {
    // Login form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            
            try {
                const result = await api('/api/auth/login', {
                    method: 'POST',
                    body: { email, password }
                });
                
                if (result.token) {
                    setToken(result.token);
                    setUser(result.user);
                    navigate('/');
                }
            } catch (error) {
                const errorDiv = document.getElementById('login-error');
                errorDiv.textContent = error.message;
                errorDiv.classList.remove('hidden');
            }
        });
    }
    
    // Admin form
    const adminForm = document.getElementById('admin-form');
    if (adminForm) {
        adminForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const password = document.getElementById('admin-password').value;
            
            try {
                const result = await api('/api/admin/verify', {
                    method: 'POST',
                    body: { password }
                });
                
                if (result.success) {
                    localStorage.setItem('lms_admin', 'true');
                    navigate('/admin/dashboard');
                }
            } catch (error) {
                const errorDiv = document.getElementById('admin-error');
                errorDiv.textContent = 'Неверный пароль';
                errorDiv.classList.remove('hidden');
            }
        });
    }
    
    // Course form
    const courseForm = document.getElementById('course-form');
    if (courseForm) {
        courseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            try {
                const result = await api('/api/admin/courses', {
                    method: 'POST',
                    body: {
                        title: document.getElementById('course-title').value,
                        description: document.getElementById('course-description').value,
                        image_url: document.getElementById('course-image').value,
                        price_rub: parseInt(document.getElementById('course-price').value) || 0,
                        is_published: document.getElementById('course-published').checked
                    }
                });
                
                if (result.id) {
                    alert('Курс создан!');
                    showAdminSection('courses');
                }
            } catch (error) {
                const errorDiv = document.getElementById('course-error');
                errorDiv.textContent = error.message;
                errorDiv.classList.remove('hidden');
            }
        });
    }
}

// ============ Init ============

window.addEventListener('popstate', handleRoute);
document.addEventListener('DOMContentLoaded', handleRoute);
