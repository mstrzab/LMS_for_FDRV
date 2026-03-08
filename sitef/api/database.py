"""
LMS Platform Database Module
SQLite database initialization and operations for the Learning Management System.
"""

import sqlite3
import json
import hashlib
import secrets
import string
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Database file path
DB_PATH = Path(__file__).parent / "lms.db"


def get_connection() -> sqlite3.Connection:
    """Create a database connection with Row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """
    Initialize the database with all required tables.
    
    Tables:
        - users: User accounts with email, password_hash, and role
        - courses: Course information including pricing
        - lessons: Lessons belonging to courses
        - homeworks: Homework assignments for lessons
        - purchases: User access to courses (purchase records)
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # ==========================================
        # USERS TABLE
        # ==========================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Index for faster email lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email 
            ON users(email)
        """)
        
        # ==========================================
        # COURSES TABLE
        # ==========================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
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
            )
        """)
        
        # ==========================================
        # LESSONS TABLE
        # ==========================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
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
            )
        """)
        
        # Index for faster course lessons lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lessons_course 
            ON lessons(course_id, sort_order)
        """)
        
        # ==========================================
        # HOMEWORKS TABLE
        # ==========================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS homeworks (
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
            )
        """)
        
        # Index for lesson homework lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_homeworks_lesson 
            ON homeworks(lesson_id)
        """)
        
        # ==========================================
        # PURCHASES TABLE (Access Control)
        # ==========================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
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
            )
        """)
        
        # Index for user purchases lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_purchases_user 
            ON purchases(user_id)
        """)
        
        # Index for course purchases lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_purchases_course 
            ON purchases(course_id)
        """)
        
        # ==========================================
        # HOMEWORK SUBMISSIONS TABLE
        # ==========================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS homework_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                homework_id INTEGER NOT NULL,
                answer TEXT,
                is_correct BOOLEAN,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (homework_id) REFERENCES homeworks(id) ON DELETE CASCADE
            )
        """)
        
        # Index for user submissions
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_submissions_user_hw 
            ON homework_submissions(user_id, homework_id)
        """)
        
        print("✅ Database initialized successfully!")


# ==========================================
# USER OPERATIONS
# ==========================================

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    return f"{salt}:{hashlib.sha256((salt + password).encode()).hexdigest()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        salt, hash_value = stored_hash.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == hash_value
    except ValueError:
        return False


def generate_random_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    # Ensure at least one of each character type
    if not any(c.islower() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_lowercase)
    if not any(c.isupper() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_uppercase)
    if not any(c.isdigit() for c in password):
        password = password[:-1] + secrets.choice(string.digits)
    return password


def create_user(email: str, password: str = None, role: str = "user") -> Dict[str, Any]:
    """
    Create a new user in the database.
    
    Args:
        email: User's email address
        password: User's password (if None, generates random password)
        role: User's role ('user' or 'admin')
    
    Returns:
        Dict with user data including the generated password
    """
    if password is None:
        password = generate_random_password()
    
    password_hash = hash_password(password)
    
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (email, password_hash, role)
                VALUES (?, ?, ?)
            """, (email, password_hash, role))
            
            user_id = cursor.lastrowid
            
            return {
                "id": user_id,
                "email": email,
                "password": password,  # Return plain password for one-time display
                "role": role,
                "created_at": datetime.now().isoformat()
            }
        except sqlite3.IntegrityError:
            raise ValueError(f"User with email {email} already exists")


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email address."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user with email and password."""
    user = get_user_by_email(email)
    if user and verify_password(password, user['password_hash']):
        # Update last login
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user['id'])
            )
        return user
    return None


# ==========================================
# COURSE OPERATIONS
# ==========================================

def create_course(
    title: str,
    description: str = "",
    image_url: str = None,
    price_rub: int = 0,
    payment_link: str = None,
    is_published: bool = False
) -> Dict[str, Any]:
    """Create a new course."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO courses (title, description, image_url, price_rub, payment_link, is_published)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, description, image_url, price_rub, payment_link, is_published))
        
        return {
            "id": cursor.lastrowid,
            "title": title,
            "description": description,
            "image_url": image_url,
            "price_rub": price_rub,
            "payment_link": payment_link,
            "is_published": is_published
        }


def get_course_by_id(course_id: int) -> Optional[Dict[str, Any]]:
    """Get course by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_courses(published_only: bool = False) -> List[Dict[str, Any]]:
    """Get all courses."""
    with get_db() as conn:
        cursor = conn.cursor()
        if published_only:
            cursor.execute(
                "SELECT * FROM courses WHERE is_published = 1 ORDER BY sort_order, created_at DESC"
            )
        else:
            cursor.execute("SELECT * FROM courses ORDER BY sort_order, created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def update_course(course_id: int, **kwargs) -> bool:
    """Update course fields."""
    allowed_fields = ['title', 'description', 'image_url', 'price_rub', 'payment_link', 'is_published', 'sort_order']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    updates['updated_at'] = datetime.now().isoformat()
    set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE courses SET {set_clause} WHERE id = ?",
            list(updates.values()) + [course_id]
        )
        return cursor.rowcount > 0


def delete_course(course_id: int) -> bool:
    """Delete a course and all its lessons."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        return cursor.rowcount > 0


# ==========================================
# LESSON OPERATIONS
# ==========================================

def create_lesson(
    course_id: int,
    title: str,
    description: str = "",
    video_url: str = None,
    audio_url: str = None,
    image_url: str = None,
    content_text: str = None,
    sort_order: int = 0
) -> Dict[str, Any]:
    """Create a new lesson."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lessons (course_id, title, description, video_url, audio_url, image_url, content_text, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (course_id, title, description, video_url, audio_url, image_url, content_text, sort_order))
        
        return {
            "id": cursor.lastrowid,
            "course_id": course_id,
            "title": title,
            "description": description,
            "video_url": video_url,
            "audio_url": audio_url,
            "image_url": image_url,
            "content_text": content_text,
            "sort_order": sort_order
        }


def get_lesson_by_id(lesson_id: int) -> Optional[Dict[str, Any]]:
    """Get lesson by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_lessons_by_course(course_id: int) -> List[Dict[str, Any]]:
    """Get all lessons for a course."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM lessons WHERE course_id = ? ORDER BY sort_order, id",
            (course_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def update_lesson(lesson_id: int, **kwargs) -> bool:
    """Update lesson fields."""
    allowed_fields = ['title', 'description', 'video_url', 'audio_url', 'image_url', 'content_text', 'sort_order']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE lessons SET {set_clause} WHERE id = ?",
            list(updates.values()) + [lesson_id]
        )
        return cursor.rowcount > 0


def delete_lesson(lesson_id: int) -> bool:
    """Delete a lesson."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
        return cursor.rowcount > 0


# ==========================================
# HOMEWORK OPERATIONS
# ==========================================

def create_homework(
    lesson_id: int,
    content_text: str = "",
    video_url: str = None,
    audio_url: str = None,
    image_url: str = None,
    options: List[str] = None,
    correct_answer: str = None,
    hint: str = None
) -> Dict[str, Any]:
    """Create a new homework assignment."""
    options_json = json.dumps(options, ensure_ascii=False) if options else None
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO homeworks (lesson_id, content_text, video_url, audio_url, image_url, options_json, correct_answer, hint)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (lesson_id, content_text, video_url, audio_url, image_url, options_json, correct_answer, hint))
        
        return {
            "id": cursor.lastrowid,
            "lesson_id": lesson_id,
            "content_text": content_text,
            "video_url": video_url,
            "audio_url": audio_url,
            "image_url": image_url,
            "options": options,
            "correct_answer": correct_answer,
            "hint": hint
        }


def get_homework_by_lesson(lesson_id: int) -> Optional[Dict[str, Any]]:
    """Get homework for a lesson."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM homeworks WHERE lesson_id = ?", (lesson_id,))
        row = cursor.fetchone()
        if row:
            hw = dict(row)
            if hw['options_json']:
                hw['options'] = json.loads(hw['options_json'])
            return hw
        return None


def get_homework_by_id(homework_id: int) -> Optional[Dict[str, Any]]:
    """Get homework by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM homeworks WHERE id = ?", (homework_id,))
        row = cursor.fetchone()
        if row:
            hw = dict(row)
            if hw['options_json']:
                hw['options'] = json.loads(hw['options_json'])
            return hw
        return None


def update_homework(homework_id: int, **kwargs) -> bool:
    """Update homework fields."""
    allowed_fields = ['content_text', 'video_url', 'audio_url', 'image_url', 'correct_answer', 'hint']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    # Handle options separately (JSON serialization)
    if 'options' in kwargs:
        updates['options_json'] = json.dumps(kwargs['options'], ensure_ascii=False)
    
    if not updates:
        return False
    
    set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE homeworks SET {set_clause} WHERE id = ?",
            list(updates.values()) + [homework_id]
        )
        return cursor.rowcount > 0


def delete_homework(homework_id: int) -> bool:
    """Delete a homework assignment."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM homeworks WHERE id = ?", (homework_id,))
        return cursor.rowcount > 0


def submit_homework_answer(user_id: int, homework_id: int, answer: str) -> Dict[str, Any]:
    """Submit an answer to a homework and check if correct."""
    homework = get_homework_by_id(homework_id)
    is_correct = homework and homework['correct_answer'] == answer
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO homework_submissions (user_id, homework_id, answer, is_correct)
            VALUES (?, ?, ?, ?)
        """, (user_id, homework_id, answer, is_correct))
        
        return {
            "id": cursor.lastrowid,
            "is_correct": is_correct,
            "correct_answer": homework['correct_answer'] if homework else None
        }


# ==========================================
# PURCHASE OPERATIONS
# ==========================================

def purchase_course(
    user_id: int,
    course_id: int,
    payment_id: str = None,
    amount_rub: int = None,
    payment_status: str = "completed"
) -> Dict[str, Any]:
    """
    Grant user access to a course (record a purchase).
    
    This is called after successful payment verification.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO purchases (user_id, course_id, payment_id, amount_rub, payment_status)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, course_id, payment_id, amount_rub, payment_status))
            
            return {
                "id": cursor.lastrowid,
                "user_id": user_id,
                "course_id": course_id,
                "payment_id": payment_id,
                "amount_rub": amount_rub,
                "payment_status": payment_status,
                "purchased_at": datetime.now().isoformat()
            }
        except sqlite3.IntegrityError:
            raise ValueError(f"User {user_id} already has access to course {course_id}")


def user_has_course_access(user_id: int, course_id: int) -> bool:
    """Check if user has access to a course."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM purchases 
            WHERE user_id = ? AND course_id = ? AND payment_status = 'completed'
        """, (user_id, course_id))
        return cursor.fetchone() is not None


def get_user_purchases(user_id: int) -> List[Dict[str, Any]]:
    """Get all courses a user has purchased."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, c.title, c.description, c.image_url
            FROM purchases p
            JOIN courses c ON p.course_id = c.id
            WHERE p.user_id = ? AND p.payment_status = 'completed'
            ORDER BY p.purchased_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_purchased_course_ids(user_id: int) -> List[int]:
    """Get list of course IDs user has access to."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT course_id FROM purchases 
            WHERE user_id = ? AND payment_status = 'completed'
        """, (user_id,))
        return [row['course_id'] for row in cursor.fetchall()]


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_course_with_lessons(course_id: int) -> Optional[Dict[str, Any]]:
    """Get course with all its lessons."""
    course = get_course_by_id(course_id)
    if not course:
        return None
    
    course['lessons'] = get_lessons_by_course(course_id)
    
    # Add homework info for each lesson
    for lesson in course['lessons']:
        lesson['homework'] = get_homework_by_lesson(lesson['id'])
    
    return course


def get_dashboard_data(user_id: int) -> Dict[str, Any]:
    """Get all data needed for the user dashboard."""
    purchased_ids = get_purchased_course_ids(user_id)
    all_courses = get_all_courses(published_only=True)
    
    purchased_courses = [c for c in all_courses if c['id'] in purchased_ids]
    available_courses = [c for c in all_courses if c['id'] not in purchased_ids]
    
    return {
        "purchased_courses": purchased_courses,
        "available_courses": available_courses
    }


# Initialize database when module is imported
if __name__ == "__main__":
    init_database()
    print("Database schema created successfully!")
    
    # Create a test admin user (optional)
    try:
        admin = create_user("admin@lms.local", "admin123", "admin")
        print(f"Test admin created: {admin['email']} / {admin['password']}")
    except ValueError as e:
        print(f"Admin user already exists: {e}")
