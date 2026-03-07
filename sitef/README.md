# LMS Platform - Learning Management System

Полнофункциональная LMS-платформа на Python с использованием Flet и FastAPI.

## 📋 Содержание

- [Архитектура](#архитектура)
- [Установка](#установка)
- [Запуск](#запуск)
- [API Документация](#api-документация)
- [Структура проекта](#структура-проекта)
- [Схема базы данных](#схема-базы-данных)

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        LMS Platform                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │   Flet Web UI   │         │   FastAPI API   │           │
│  │   (Port 8550)   │◄───────►│   (Port 8000)   │           │
│  │                 │         │                 │           │
│  │  - Главная      │         │  - Webhook API  │           │
│  │  - Каталог      │         │  - REST API     │           │
│  │  - Курсы        │         │  - Payment API  │           │
│  │  - Админка      │         │                 │           │
│  └────────┬────────┘         └────────┬────────┘           │
│           │                           │                     │
│           └───────────┬───────────────┘                     │
│                       │                                     │
│              ┌────────▼────────┐                           │
│              │    SQLite DB    │                           │
│              │    (lms.db)     │                           │
│              └─────────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Установка

### 1. Клонирование и настройка

```bash
cd /home/z/my-project/lms_platform

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка конфигурации

```bash
cp config.py.example config.py
# Отредактируйте config.py с вашими настройками Prodamus
```

### 3. Инициализация базы данных

```bash
python database.py
```

---

## ▶️ Запуск

### Вариант 1: Разработка (раздельный запуск)

```bash
# Терминал 1: FastAPI сервер
python api.py

# Терминал 2: Flet приложение
python main.py
```

### Вариант 2: Комбинированный сервер

```bash
# Оба сервера в одном процессе
python run_server.py

# Только API
python run_server.py --api

# Только Flet
python run_server.py --flet
```

### Вариант 3: Production (uvicorn)

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

---

## 📖 API Документация

### Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `POST` | `/prodamus-webhook` | Webhook для уведомлений от Prodamus |
| `POST` | `/api/payment/create` | Создание ссылки на оплату |
| `GET` | `/api/courses` | Список курсов |
| `GET` | `/api/courses/{id}` | Детали курса |
| `GET` | `/health` | Проверка состояния |

### Примеры запросов

#### Создание платежной ссылки

```bash
curl -X POST http://localhost:8000/api/payment/create \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": 1,
    "email": "student@example.com"
  }'
```

#### Webhook от Prodamus

```bash
curl -X POST http://localhost:8000/prodamus-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "LMS-20240115-abc123-C1",
    "status": "success",
    "sign": "abc123...",
    "customer_email": "student@example.com",
    "total_price": 499000,
    "meta": {
      "course_id": "1"
    }
  }'
```

---

## 📁 Структура проекта

```
lms_platform/
├── main.py                 # Flet приложение (UI)
├── api.py                  # FastAPI сервер
├── database.py             # SQLite ORM и операции
├── prodamus_integration.py # Интеграция с Prodamus
├── run_server.py           # Комбинированный запуск
├── config.py.example       # Пример конфигурации
├── requirements.txt        # Зависимости
├── README.md               # Документация
└── lms.db                  # База данных (создаётся автоматически)
```

---

## 🗄️ Схема базы данных

### ER-диаграмма

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    users     │       │   courses    │       │   lessons    │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id           │       │ id           │       │ id           │
│ email        │       │ title        │       │ course_id    │──┐
│ password_hash│       │ description  │       │ title        │  │
│ role         │       │ image_url    │       │ description  │  │
│ created_at   │       │ price_rub    │       │ video_url    │  │
│ last_login   │       │ payment_link │       │ audio_url    │  │
│ is_active    │       │ is_published │       │ content_text │  │
└──────┬───────┘       └──────┬───────┘       │ sort_order   │  │
       │                      │               └──────────────┘  │
       │                      │                      ▲          │
       │               ┌──────▼───────┐              │          │
       │               │  purchases   │              │          │
       │               ├──────────────┤              │          │
       │               │ id           │              │          │
       └──────────────►│ user_id      │              │          │
                       │ course_id    │◄─────────────┘          │
                       │ payment_id   │                         │
                       │ amount_rub   │                         │
                       │ purchased_at │                         │
                       └──────────────┘                         │
                                                                │
                       ┌──────────────┐                         │
                       │  homeworks   │                         │
                       ├──────────────┤                         │
                       │ id           │                         │
                       │ lesson_id    │◄────────────────────────┘
                       │ content_text │
                       │ video_url    │
                       │ audio_url    │
                       │ options_json │
                       │ correct_ans  │
                       │ hint         │
                       └──────────────┘
```

### SQL Schema

```sql
-- Пользователи
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Курсы
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    price_rub INTEGER NOT NULL DEFAULT 0,
    payment_link TEXT,
    is_published BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sort_order INTEGER DEFAULT 0
);

-- Уроки
CREATE TABLE lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    video_url TEXT,
    audio_url TEXT,
    image_url TEXT,
    content_text TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- Домашние задания
CREATE TABLE homeworks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    content_text TEXT,
    video_url TEXT,
    audio_url TEXT,
    image_url TEXT,
    options_json TEXT,
    correct_answer TEXT,
    hint TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

-- Покупки (доступы)
CREATE TABLE purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_id TEXT,
    amount_rub INTEGER,
    payment_status TEXT DEFAULT 'completed',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE(user_id, course_id)
);
```

---

## 🔐 Авторизация

### Пользователь

1. После оплаты Prodamus автоматически создаёт аккаунт
2. Пароль генерируется и отправляется на email
3. Вход через `/login`

### Администратор

1. Перейдите на `/admin`
2. Введите пароль: `Kon!AdminFDRV`
3. Получите доступ к админ-панели

---

## 💳 Интеграция с Prodamus

### Генерация платёжной ссылки

```python
from prodamus_integration import generate_payment_link, generate_order_id

order_id = generate_order_id(course_id=1, user_email="user@example.com")

payment_url = generate_payment_link(
    order_id=order_id,
    product_name="Курс Python",
    price_rub=4990,
    customer_email="user@example.com",
    course_id=1,
    success_url="https://yoursite.com/success",
    fail_url="https://yoursite.com/fail",
    webhook_url="https://yoursite.com/prodamus-webhook"
)
```

### Обработка webhook

Webhook автоматически:
1. Проверяет подпись Prodamus
2. Создаёт пользователя (если новый)
3. Генерирует пароль
4. Выдаёт доступ к курсу

---

## 🎨 UI Компоненты

Дизайн следует принципам Tailwind CSS:
- Цветовая схема: Slate + Blue
- Закруглённые углы: 8-12px
- Тени: subtle shadows
- Адаптивность: responsive layout

---

## 📝 TODO / Roadmap

- [ ] Email уведомления (SMTP)
- [ ] Прогресс обучения
- [ ] Сертификаты
- [ ] Форум/комментарии
- [ ] Мобильное приложение
- [ ] Telegram-бот

---

## 📄 Лицензия

MIT License
