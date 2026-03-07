"""
Test script for LMS Platform
Run this to verify database operations and create test data.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_database,
    create_user,
    create_course,
    create_lesson,
    create_homework,
    purchase_course,
    get_user_by_email,
    get_all_courses,
    get_course_with_lessons,
    get_dashboard_data,
    authenticate_user,
    hash_password,
    verify_password,
    generate_random_password,
)


def test_database():
    """Test database operations."""
    print("=" * 60)
    print("LMS Platform - Database Test")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_database()
    print("   ✅ Database initialized")
    
    # Create test user
    print("\n2. Creating test user...")
    try:
        test_user = create_user("test@example.com", "password123", "user")
        print(f"   ✅ User created: ID={test_user['id']}, email={test_user['email']}")
    except ValueError as e:
        print(f"   ⚠️  User already exists: {e}")
        test_user = get_user_by_email("test@example.com")
    
    # Create admin user
    print("\n3. Creating admin user...")
    try:
        admin_user = create_user("admin@lms.local", "admin123", "admin")
        print(f"   ✅ Admin created: ID={admin_user['id']}")
    except ValueError as e:
        print(f"   ⚠️  Admin already exists")
        admin_user = get_user_by_email("admin@lms.local")
    
    # Test authentication
    print("\n4. Testing authentication...")
    auth_user = authenticate_user("test@example.com", "password123")
    if auth_user:
        print(f"   ✅ Authentication successful: {auth_user['email']}")
    else:
        print("   ❌ Authentication failed")
    
    # Create test course
    print("\n5. Creating test course...")
    try:
        course = create_course(
            title="Python для начинающих",
            description="Изучите основы программирования на Python",
            price_rub=4990,
            is_published=True
        )
        print(f"   ✅ Course created: ID={course['id']}, title={course['title']}")
    except Exception as e:
        print(f"   ⚠️  Course creation error: {e}")
        courses = get_all_courses()
        course = courses[0] if courses else None
    
    # Create lessons
    if course:
        print("\n6. Creating lessons...")
        
        lessons_data = [
            {
                "title": "Введение в Python",
                "description": "Знакомство с языком программирования Python",
                "content_text": "# Введение в Python\n\nPython — высокоуровневый язык программирования...",
                "sort_order": 1
            },
            {
                "title": "Переменные и типы данных",
                "description": "Работа с переменными и основными типами данных",
                "content_text": "# Переменные\n\nПеременная — это именованная область памяти...",
                "sort_order": 2
            },
            {
                "title": "Условные операторы",
                "description": "Конструкции if, elif, else",
                "content_text": "# Условные операторы\n\nУсловные операторы позволяют...",
                "sort_order": 3
            },
        ]
        
        for lesson_data in lessons_data:
            try:
                lesson = create_lesson(
                    course_id=course['id'],
                    **lesson_data
                )
                print(f"   ✅ Lesson created: {lesson['title']}")
                
                # Create homework for first lesson
                if lesson_data["sort_order"] == 1:
                    try:
                        homework = create_homework(
                            lesson_id=lesson['id'],
                            content_text="Какой оператор используется для вывода текста в Python?",
                            options=["print()", "echo()", "console.log()", "printf()"],
                            correct_answer="print()",
                            hint="Вспомните первый пример из урока"
                        )
                        print(f"   ✅ Homework created for lesson: {lesson['title']}")
                    except Exception as e:
                        print(f"   ⚠️  Homework error: {e}")
                        
            except Exception as e:
                print(f"   ⚠️  Lesson error: {e}")
    
    # Purchase course
    print("\n7. Testing purchase...")
    if test_user and course:
        try:
            purchase = purchase_course(
                user_id=test_user['id'],
                course_id=course['id'],
                payment_id="TEST-PAYMENT-123",
                amount_rub=4990
            )
            print(f"   ✅ Purchase created: user={test_user['id']}, course={course['id']}")
        except ValueError as e:
            print(f"   ⚠️  Purchase already exists")
    
    # Get dashboard data
    print("\n8. Getting dashboard data...")
    if test_user:
        dashboard = get_dashboard_data(test_user['id'])
        print(f"   📚 Purchased courses: {len(dashboard['purchased_courses'])}")
        print(f"   📖 Available courses: {len(dashboard['available_courses'])}")
    
    # Get course with lessons
    print("\n9. Getting course details...")
    if course:
        full_course = get_course_with_lessons(course['id'])
        if full_course:
            print(f"   📚 Course: {full_course['title']}")
            print(f"   📝 Lessons: {len(full_course['lessons'])}")
            for lesson in full_course['lessons']:
                hw_status = "✅" if lesson.get('homework') else "❌"
                print(f"      - {lesson['title']} (HW: {hw_status})")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    # Print login info
    print("\n📋 Test Credentials:")
    print(f"   User:  test@example.com / password123")
    print(f"   Admin: admin@lms.local / admin123")
    print(f"   Admin Panel Password: Kon!AdminFDRV")


def test_password_functions():
    """Test password hashing functions."""
    print("\n" + "=" * 60)
    print("Testing Password Functions")
    print("=" * 60)
    
    # Generate random password
    password = generate_random_password(12)
    print(f"\nGenerated password: {password}")
    
    # Hash and verify
    hashed = hash_password(password)
    print(f"Hashed password: {hashed[:50]}...")
    
    is_valid = verify_password(password, hashed)
    print(f"Verification: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    wrong_check = verify_password("wrong_password", hashed)
    print(f"Wrong password check: {'❌ Invalid' if not wrong_check else '✅ Valid (ERROR!)'}")


if __name__ == "__main__":
    test_database()
    test_password_functions()
