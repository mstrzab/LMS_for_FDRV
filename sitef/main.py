"""
LMS Platform - Main Application
Learning Management System built with Flet framework.

Routes:
    /               - Home page (dashboard with courses)
    /login          - User login page
    /admin          - Admin panel (password protected)
    /course/{id}    - Course page with lessons
    /logout         - Logout and redirect to home
"""

import flet as ft
from typing import Optional, Callable
from database import (
    init_database,
    authenticate_user,
    get_user_by_id,
    get_dashboard_data,
    get_course_with_lessons,
    get_all_courses,
    user_has_course_access,
    # Course CRUD
    create_course,
    update_course,
    delete_course,
    # Lesson CRUD
    create_lesson,
    update_lesson,
    delete_lesson,
    # Homework CRUD
    create_homework,
    update_homework,
    delete_homework,
    get_homework_by_lesson,
    # Purchase
    get_purchased_course_ids,
    submit_homework_answer,
)

# ==========================================
# CONSTANTS & CONFIGURATION
# ==========================================

ADMIN_PASSWORD = "Kon!AdminFDRV"

# Color scheme (Tailwind-inspired)
COLORS = {
    "primary": "#3B82F6",        # Blue-500
    "primary_dark": "#2563EB",   # Blue-600
    "secondary": "#6366F1",      # Indigo-500
    "success": "#22C55E",        # Green-500
    "warning": "#F59E0B",        # Amber-500
    "error": "#EF4444",          # Red-500
    "background": "#F8FAFC",     # Slate-50
    "surface": "#FFFFFF",        # White
    "text_primary": "#0F172A",   # Slate-900
    "text_secondary": "#64748B", # Slate-500
    "border": "#E2E8F0",         # Slate-200
}

# ==========================================
# APP STATE MANAGEMENT
# ==========================================

class AppState:
    """Global application state management."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self._user_id: Optional[int] = None
        self._is_admin: bool = False
    
    @property
    def user_id(self) -> Optional[int]:
        return self._user_id
    
    @user_id.setter
    def user_id(self, value: Optional[int]):
        self._user_id = value
        if value:
            self.page.session.set("user_id", value)
        else:
            self.page.session.remove("user_id")
    
    @property
    def is_admin(self) -> bool:
        return self._is_admin
    
    @is_admin.setter
    def is_admin(self, value: bool):
        self._is_admin = value
        self.page.session.set("is_admin", value)
    
    def restore_session(self):
        """Restore session from storage."""
        user_id = self.page.session.get("user_id")
        is_admin = self.page.session.get("is_admin")
        
        if user_id:
            self._user_id = user_id
        if is_admin:
            self._is_admin = is_admin
    
    def logout(self):
        """Clear all session data."""
        self._user_id = None
        self._is_admin = False
        self.page.session.clear()


# ==========================================
# UI COMPONENTS (Tailwind-inspired)
# ==========================================

def card_container(
    content: ft.Control,
    padding: int = 16,
    on_click: Callable = None,
    on_hover: Callable = None,
) -> ft.Container:
    """
    Create a card container with Tailwind-inspired styling.
    
    Mimics: bg-white rounded-xl shadow-sm border border-slate-200
    """
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=COLORS["surface"],
        border_radius=12,
        border=ft.border.all(1, COLORS["border"]),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=4,
            color="#00000008",
            offset=ft.Offset(0, 1),
        ),
        on_click=on_click,
        on_hover=on_hover,
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT) if on_click else None,
    )


def primary_button(text: str, on_click: Callable = None, icon: str = None) -> ft.ElevatedButton:
    """Create a primary action button."""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        bgcolor=COLORS["primary"],
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
        ),
    )


def secondary_button(text: str, on_click: Callable = None, icon: str = None) -> ft.OutlinedButton:
    """Create a secondary action button."""
    return ft.OutlinedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            side=ft.BorderSide(1, COLORS["primary"]),
            color=COLORS["primary"],
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
        ),
    )


def text_field(
    label: str,
    password: bool = False,
    value: str = "",
    on_change: Callable = None,
    on_submit: Callable = None,
    width: int = None,
) -> ft.TextField:
    """Create a styled text input field."""
    return ft.TextField(
        label=label,
        password=password,
        can_reveal_password=password,
        value=value,
        on_change=on_change,
        on_submit=on_submit,
        width=width,
        border_color=COLORS["border"],
        focused_border_color=COLORS["primary"],
        cursor_color=COLORS["primary"],
        border_radius=8,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )


def section_title(text: str) -> ft.Text:
    """Create a section title heading."""
    return ft.Text(
        text,
        size=20,
        weight=ft.FontWeight.W600,
        color=COLORS["text_primary"],
    )


def breadcrumb(items: list[tuple[str, str]]) -> ft.Row:
    """Create a breadcrumb navigation."""
    controls = []
    for i, (text, route) in enumerate(items):
        if i > 0:
            controls.append(ft.Text(" / ", color=COLORS["text_secondary"], size=14))
        controls.append(
            ft.TextButton(
                text,
                on_click=lambda e, r=route: e.page.go(r),
                style=ft.ButtonStyle(color=COLORS["text_secondary"]),
            )
        )
    return ft.Row(controls, spacing=0)


# ==========================================
# PAGE: LOGIN
# ==========================================

def login_page(page: ft.Page, state: AppState) -> ft.View:
    """Login page with email and password authentication."""
    
    email_field = text_field("Email", width=400)
    password_field = text_field("Пароль", password=True, width=400)
    error_text = ft.Text("", color=COLORS["error"], size=14)
    
    def handle_login(e):
        email = email_field.value.strip()
        password = password_field.value
        
        if not email or not password:
            error_text.value = "Введите email и пароль"
            page.update()
            return
        
        user = authenticate_user(email, password)
        if user:
            state.user_id = user['id']
            state.is_admin = (user['role'] == 'admin')
            page.go("/")
        else:
            error_text.value = "Неверный email или пароль"
            page.update()
    
    def go_to_admin(e):
        page.go("/admin")
    
    return ft.View(
        "/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        # Logo / Title
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Icon(ft.Icons.SCHOOL_ROUNDED, size=60, color=COLORS["primary"]),
                                    ft.Text(
                                        "LMS Platform",
                                        size=32,
                                        weight=ft.FontWeight.BOLD,
                                        color=COLORS["text_primary"],
                                    ),
                                    ft.Text(
                                        "Войдите для доступа к курсам",
                                        size=16,
                                        color=COLORS["text_secondary"],
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=12,
                            ),
                            padding=ft.padding.only(bottom=40),
                        ),
                        # Login Form
                        card_container(
                            ft.Column(
                                [
                                    ft.Text("Вход в аккаунт", size=18, weight=ft.FontWeight.W600),
                                    ft.Divider(height=1, color=COLORS["border"]),
                                    email_field,
                                    password_field,
                                    error_text,
                                    ft.Container(
                                        content=primary_button("Войти", on_click=handle_login),
                                        alignment=ft.alignment.center,
                                        padding=ft.padding.only(top=16),
                                    ),
                                ],
                                spacing=16,
                                width=400,
                            ),
                            padding=32,
                        ),
                        # Admin link
                        ft.Container(
                            content=ft.TextButton(
                                "Вход для администратора",
                                on_click=go_to_admin,
                                style=ft.ButtonStyle(color=COLORS["text_secondary"]),
                            ),
                            padding=ft.padding.only(top=24),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
            ),
        ],
        bgcolor=COLORS["background"],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ==========================================
# PAGE: ADMIN AUTH
# ==========================================

def admin_auth_page(page: ft.Page, state: AppState) -> ft.View:
    """Admin authentication page with password input."""
    
    password_field = text_field("Пароль администратора", password=True, width=400)
    error_text = ft.Text("", color=COLORS["error"], size=14)
    
    def handle_admin_auth(e):
        if password_field.value == ADMIN_PASSWORD:
            state.is_admin = True
            page.go("/admin")
        else:
            error_text.value = "Неверный пароль"
            page.update()
    
    def go_back(e):
        page.go("/")
    
    return ft.View(
        "/admin",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED, size=60, color=COLORS["primary"]),
                        ft.Text(
                            "Панель администратора",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["text_primary"],
                        ),
                        ft.Text(
                            "Введите пароль для доступа",
                            size=14,
                            color=COLORS["text_secondary"],
                        ),
                        ft.Container(height=24),
                        password_field,
                        error_text,
                        ft.Row(
                            [
                                secondary_button("Назад", on_click=go_back, icon=ft.Icons.ARROW_BACK),
                                primary_button("Войти", on_click=handle_admin_auth, icon=ft.Icons.LOGIN),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=16,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
            ),
        ],
        bgcolor=COLORS["background"],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ==========================================
# PAGE: HOME (DASHBOARD)
# ==========================================

def home_page(page: ft.Page, state: AppState) -> ft.View:
    """Home page with purchased courses and course catalog."""
    
    # Header
    def logout(e):
        state.logout()
        page.go("/login")
    
    header = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SCHOOL_ROUNDED, color=COLORS["primary"], size=28),
                        ft.Text("LMS Platform", size=20, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=12,
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            "Админ-панель",
                            on_click=lambda e: page.go("/admin"),
                            visible=state.is_admin,
                            icon=ft.Icons.SETTINGS,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT,
                            on_click=logout,
                            tooltip="Выйти",
                        ),
                    ],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
        bgcolor=COLORS["surface"],
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
    )
    
    # Course card component
    def course_card(course: dict, is_purchased: bool = False):
        def on_card_click(e):
            if is_purchased:
                page.go(f"/course/{course['id']}")
        
        def on_buy_click(e):
            # TODO: Integrate with Prodamus payment
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Переход к оплате курса: {course['title']}"),
                bgcolor=COLORS["success"],
            )
            page.snack_bar.open = True
            page.update()
        
        return ft.Container(
            content=ft.Column(
                [
                    # Course image
                    ft.Container(
                        content=ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED, size=48, color=ft.Colors.WHITE),
                        bgcolor=COLORS["primary"] if not course.get('image_url') else None,
                        image_src=course.get('image_url'),
                        image_fit=ft.ImageFit.COVER,
                        border_radius=ft.border_radius.all(8),
                        height=120,
                        alignment=ft.alignment.center,
                    ),
                    # Course info
                    ft.Column(
                        [
                            ft.Text(
                                course['title'],
                                size=16,
                                weight=ft.FontWeight.W600,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                course.get('description', 'Описание отсутствует'),
                                size=12,
                                color=COLORS["text_secondary"],
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=8,
                        expand=True,
                    ),
                    # Price / Action
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(
                                    f"{course['price_rub']:,} ₽".replace(",", " "),
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLORS["primary"],
                                ) if not is_purchased else ft.Container(),
                                primary_button(
                                    "Открыть" if is_purchased else "Купить",
                                    on_click=on_card_click if is_purchased else on_buy_click,
                                    icon=ft.Icons.OPEN_IN_NEW if is_purchased else ft.Icons.SHOPPING_CART,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=ft.padding.only(top=8),
                    ),
                ],
                spacing=12,
            ),
            width=280,
            padding=16,
            bgcolor=COLORS["surface"],
            border_radius=12,
            border=ft.border.all(1, COLORS["border"]),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color="#00000008",
                offset=ft.Offset(0, 2),
            ),
            on_click=on_card_click if is_purchased else None,
        )
    
    # Load dashboard data
    if state.user_id:
        dashboard = get_dashboard_data(state.user_id)
        purchased_courses = dashboard['purchased_courses']
        available_courses = dashboard['available_courses']
    else:
        purchased_courses = []
        available_courses = get_all_courses(published_only=True)
    
    # Purchased courses section
    purchased_section = ft.Column(
        [
            ft.Row(
                [
                    section_title("Продолжить обучение"),
                    ft.Text(f"{len(purchased_courses)} курсов", color=COLORS["text_secondary"]),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=ft.Row(
                    [course_card(c, is_purchased=True) for c in purchased_courses] or [
                        ft.Text("У вас пока нет купленных курсов", color=COLORS["text_secondary"])
                    ],
                    spacing=16,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=ft.padding.symmetric(vertical=16),
            ),
        ],
        visible=len(purchased_courses) > 0,
        spacing=8,
    )
    
    # Available courses section
    available_section = ft.Column(
        [
            ft.Row(
                [
                    section_title("Каталог курсов"),
                    ft.Text(f"{len(available_courses)} курсов", color=COLORS["text_secondary"]),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=ft.Row(
                    [course_card(c, is_purchased=False) for c in available_courses] or [
                        ft.Text("Нет доступных курсов", color=COLORS["text_secondary"])
                    ],
                    spacing=16,
                    scroll=ft.ScrollMode.AUTO,
                    wrap=True,
                ),
                padding=ft.padding.symmetric(vertical=16),
            ),
        ],
        spacing=8,
    )
    
    # Main content
    content = ft.Container(
        content=ft.Column(
            [
                purchased_section,
                ft.Divider(height=1, color=COLORS["border"]) if purchased_courses else ft.Container(),
                available_section,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        padding=24,
        expand=True,
    )
    
    return ft.View(
        "/",
        controls=[
            ft.Column(
                [
                    header,
                    content,
                ],
                expand=True,
            ),
        ],
        bgcolor=COLORS["background"],
        scroll=ft.ScrollMode.AUTO,
    )


# ==========================================
# PAGE: COURSE VIEW
# ==========================================

def course_page(page: ft.Page, state: AppState, course_id: int) -> ft.View:
    """Course page with lessons list and content viewer."""
    
    # Check access
    if not state.user_id or not user_has_course_access(state.user_id, course_id):
        return ft.View(
            f"/course/{course_id}",
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.LOCK_ROUNDED, size=60, color=COLORS["error"]),
                            ft.Text("Доступ запрещён", size=24, weight=ft.FontWeight.BOLD),
                            ft.Text("Купите курс для доступа к материалам", color=COLORS["text_secondary"]),
                            primary_button("На главную", on_click=lambda e: page.go("/")),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=16,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                ),
            ],
            bgcolor=COLORS["background"],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    
    # Load course data
    course = get_course_with_lessons(course_id)
    if not course:
        return ft.View(
            f"/course/{course_id}",
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Курс не найден", size=24),
                            primary_button("На главную", on_click=lambda e: page.go("/")),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                ),
            ],
            bgcolor=COLORS["background"],
        )
    
    # State for selected lesson
    selected_lesson = ft.Ref[ft.Container]()
    
    # Lesson content area
    lesson_content = ft.Column(
        [
            ft.Text("Выберите урок из списка слева", color=COLORS["text_secondary"], size=16),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    
    def load_lesson(lesson: dict):
        """Load lesson content into the content area."""
        homework = get_homework_by_lesson(lesson['id'])
        
        # Build lesson content
        controls = [
            ft.Text(lesson['title'], size=24, weight=ft.FontWeight.BOLD),
            ft.Text(lesson.get('description', ''), color=COLORS["text_secondary"]),
        ]
        
        # Video
        if lesson.get('video_url'):
            controls.append(
                ft.Container(
                    content=ft.Video(
                        playlist=[ft.VideoMedia(lesson['video_url'])],
                        expand=True,
                        fill_color=COLORS["background"],
                    ),
                    height=400,
                    border_radius=12,
                    bgcolor=ft.Colors.BLACK,
                )
            )
        
        # Audio
        if lesson.get('audio_url'):
            controls.append(
                card_container(
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.AUDIOTRACK_ROUNDED, color=COLORS["primary"]),
                            ft.Text("Аудиоматериал", weight=ft.FontWeight.W600),
                        ]),
                        ft.Audio(src=lesson['audio_url'], autoplay=False),
                    ]),
                )
            )
        
        # Content text
        if lesson.get('content_text'):
            controls.append(
                card_container(
                    ft.Markdown(
                        lesson['content_text'],
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    ),
                )
            )
        
        # Homework section
        if homework:
            hw_controls = [
                ft.Row([
                    ft.Icon(ft.Icons.ASSIGNMENT_ROUNDED, color=COLORS["secondary"]),
                    ft.Text("Домашнее задание", size=18, weight=ft.FontWeight.W600),
                ]),
            ]
            
            if homework.get('content_text'):
                hw_controls.append(ft.Text(homework['content_text']))
            
            # Options (radio buttons)
            if homework.get('options'):
                answer_result = ft.Ref[ft.Text]()
                
                def check_answer(e):
                    selected = radio_group.value
                    result = submit_homework_answer(state.user_id, homework['id'], selected)
                    if result['is_correct']:
                        answer_result.current.value = "✅ Правильно!"
                        answer_result.current.color = COLORS["success"]
                    else:
                        answer_result.current.value = f"❌ Неправильно. Правильный ответ: {result['correct_answer']}"
                        answer_result.current.color = COLORS["error"]
                    page.update()
                
                radio_group = ft.RadioGroup(
                    content=ft.Column([
                        ft.Radio(value=opt, label=opt) for opt in homework['options']
                    ]),
                )
                
                hw_controls.extend([
                    radio_group,
                    primary_button("Проверить", on_click=check_answer, icon=ft.Icons.CHECK),
                    ft.Text(ref=answer_result, size=14),
                ])
            
            controls.append(
                card_container(
                    ft.Column(hw_controls, spacing=12),
                    padding=16,
                )
            )
        
        lesson_content.controls = controls
        page.update()
    
    # Lessons list
    lessons_list = ft.Column(
        [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, color=COLORS["primary"]),
                        ft.Text("Уроки", weight=ft.FontWeight.W600),
                    ],
                ),
                padding=ft.padding.only(bottom=8),
            ),
            ft.Divider(height=1, color=COLORS["border"]),
        ],
        spacing=0,
    )
    
    for i, lesson in enumerate(course['lessons']):
        lesson_btn = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(str(i + 1), color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.BOLD),
                        bgcolor=COLORS["primary"],
                        border_radius=ft.border_radius.all(12),
                        width=24,
                        height=24,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(lesson['title'], size=14, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, size=16, color=COLORS["text_secondary"]),
                ],
                spacing=12,
            ),
            padding=12,
            border_radius=8,
            on_click=lambda e, l=lesson: load_lesson(l),
            on_hover=lambda e, c=e.control: setattr(c, 'bgcolor', COLORS["background"] if e.data == "true" else None),
        )
        lessons_list.controls.append(lesson_btn)
    
    # Header
    header = ft.Container(
        content=ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: page.go("/"),
                ),
                ft.Text(course['title'], size=20, weight=ft.FontWeight.BOLD, expand=True),
            ],
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        bgcolor=COLORS["surface"],
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
    )
    
    # Layout
    layout = ft.Row(
        [
            # Left sidebar - lessons list
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=lessons_list,
                            padding=16,
                        ),
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=280,
                bgcolor=COLORS["surface"],
                border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])),
                expand=True,
            ),
            # Main content
            ft.Container(
                content=lesson_content,
                padding=24,
                expand=True,
            ),
        ],
        expand=True,
    )
    
    # Auto-load first lesson if exists
    if course['lessons']:
        load_lesson(course['lessons'][0])
    
    return ft.View(
        f"/course/{course_id}",
        controls=[
            ft.Column(
                [
                    header,
                    layout,
                ],
                expand=True,
            ),
        ],
        bgcolor=COLORS["background"],
    )


# ==========================================
# PAGE: ADMIN PANEL
# ==========================================

def admin_panel_page(page: ft.Page, state: AppState) -> ft.View:
    """Admin panel for managing courses, lessons, and homeworks."""
    
    # Check admin access
    if not state.is_admin:
        page.go("/admin")
        return ft.View("/admin/dashboard", controls=[ft.Text("Redirecting...")])
    
    # Current editing state
    current_course_id = ft.Ref[int]()
    current_lesson_id = ft.Ref[int]()
    
    # Content area (right side)
    content_area = ft.Column(
        [
            ft.Text("Выберите действие из меню слева", size=16, color=COLORS["text_secondary"]),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    
    # ===== Course Management =====
    def show_course_form(course: dict = None):
        """Show form for creating/editing a course."""
        title_field = text_field("Название курса", value=course['title'] if course else "", width=500)
        desc_field = text_field("Описание", value=course.get('description', '') if course else "", width=500)
        image_field = text_field("URL изображения", value=course.get('image_url', '') if course else "", width=500)
        price_field = text_field("Цена (руб.)", value=str(course['price_rub']) if course else "0", width=200)
        published_switch = ft.Switch(label="Опубликован", value=course.get('is_published', False) if course else False)
        
        result_text = ft.Text("", color=COLORS["success"])
        
        def save_course(e):
            try:
                price = int(price_field.value) if price_field.value.isdigit() else 0
                if course:  # Update
                    update_course(course['id'],
                        title=title_field.value,
                        description=desc_field.value,
                        image_url=image_field.value,
                        price_rub=price,
                        is_published=published_switch.value
                    )
                    result_text.value = "Курс обновлён!"
                else:  # Create
                    new_course = create_course(
                        title=title_field.value,
                        description=desc_field.value,
                        image_url=image_field.value,
                        price_rub=price,
                        is_published=published_switch.value
                    )
                    result_text.value = f"Курс создан! ID: {new_course['id']}"
                
                result_text.color = COLORS["success"]
                page.update()
            except Exception as ex:
                result_text.value = f"Ошибка: {str(ex)}"
                result_text.color = COLORS["error"]
                page.update()
        
        content_area.controls = [
            ft.Text("Создать курс" if not course else f"Редактировать курс: {course['title']}", 
                   size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1, color=COLORS["border"]),
            title_field,
            desc_field,
            image_field,
            ft.Row([price_field, published_switch], spacing=24),
            ft.Row([
                primary_button("Сохранить", on_click=save_course, icon=ft.Icons.SAVE),
                secondary_button("Отмена", on_click=lambda e: show_courses_list()),
            ], spacing=16),
            result_text,
        ]
        page.update()
    
    def show_courses_list():
        """Show list of all courses with edit/delete options."""
        courses = get_all_courses()
        
        def edit_course(e, course_id):
            course = next((c for c in courses if c['id'] == course_id), None)
            if course:
                show_course_form(course)
        
        def delete_course_handler(e, course_id):
            delete_course(course_id)
            show_courses_list()
        
        rows = []
        for c in courses:
            rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(str(c['id']), width=50),
                            ft.Text(c['title'], expand=True),
                            ft.Text(f"{c['price_rub']:,} ₽".replace(",", " "), width=100),
                            ft.Icon(ft.Icons.CHECK_CIRCLE if c['is_published'] else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                   color=COLORS["success"] if c['is_published'] else COLORS["text_secondary"]),
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.EDIT, on_click=lambda e, cid=c['id']: edit_course(e, cid)),
                                ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, cid=c['id']: delete_course_handler(e, cid),
                                            icon_color=COLORS["error"]),
                            ]),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=12,
                    border_radius=8,
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["border"]),
                )
            )
        
        content_area.controls = [
            ft.Row([
                ft.Text("Все курсы", size=20, weight=ft.FontWeight.BOLD),
                primary_button("Новый курс", on_click=lambda e: show_course_form(), icon=ft.Icons.ADD),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1, color=COLORS["border"]),
            ft.Column(rows, spacing=8, scroll=ft.ScrollMode.AUTO),
        ]
        page.update()
    
    # ===== Lesson Management =====
    def show_lesson_form(course_id: int, lesson: dict = None):
        """Show form for creating/editing a lesson."""
        course = get_course_by_id(course_id) if course_id else None
        
        title_field = text_field("Название урока", value=lesson['title'] if lesson else "", width=500)
        desc_field = text_field("Описание", value=lesson.get('description', '') if lesson else "", width=500)
        video_field = text_field("URL видео", value=lesson.get('video_url', '') if lesson else "", width=500)
        audio_field = text_field("URL аудио", value=lesson.get('audio_url', '') if lesson else "", width=500)
        content_field = text_field("Текст урока (Markdown)", value=lesson.get('content_text', '') if lesson else "", width=500, multiline=True)
        
        result_text = ft.Text("", color=COLORS["success"])
        
        def save_lesson(e):
            try:
                if lesson:  # Update
                    update_lesson(lesson['id'],
                        title=title_field.value,
                        description=desc_field.value,
                        video_url=video_field.value,
                        audio_url=audio_field.value,
                        content_text=content_field.value
                    )
                    result_text.value = "Урок обновлён!"
                else:  # Create
                    new_lesson = create_lesson(
                        course_id=course_id,
                        title=title_field.value,
                        description=desc_field.value,
                        video_url=video_field.value,
                        audio_url=audio_field.value,
                        content_text=content_field.value
                    )
                    result_text.value = f"Урок создан! ID: {new_lesson['id']}"
                
                result_text.color = COLORS["success"]
                page.update()
            except Exception as ex:
                result_text.value = f"Ошибка: {str(ex)}"
                result_text.color = COLORS["error"]
                page.update()
        
        content_area.controls = [
            ft.Text(f"Урок для курса: {course['title']}" if course else "Выберите курс", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1, color=COLORS["border"]),
            title_field,
            desc_field,
            video_field,
            audio_field,
            content_field,
            ft.Row([
                primary_button("Сохранить", on_click=save_lesson, icon=ft.Icons.SAVE),
                secondary_button("Назад", on_click=lambda e: show_courses_list()),
            ], spacing=16),
            result_text,
        ]
        page.update()
    
    # ===== Homework Management =====
    def show_homework_form(lesson_id: int, homework: dict = None):
        """Show form for creating/editing homework."""
        lesson = get_lesson_by_id(lesson_id) if lesson_id else None
        
        content_field = text_field("Текст задания", value=homework.get('content_text', '') if homework else "", width=500, multiline=True)
        video_field = text_field("URL видео", value=homework.get('video_url', '') if homework else "", width=500)
        audio_field = text_field("URL аудио", value=homework.get('audio_url', '') if homework else "", width=500)
        
        options_field = text_field("Варианты ответов (через ;)", 
                                   value="; ".join(homework.get('options', [])) if homework and homework.get('options') else "",
                                   width=500)
        correct_field = text_field("Правильный ответ", value=homework.get('correct_answer', '') if homework else "", width=300)
        hint_field = text_field("Подсказка", value=homework.get('hint', '') if homework else "", width=500)
        
        result_text = ft.Text("", color=COLORS["success"])
        
        def save_homework(e):
            try:
                options = [o.strip() for o in options_field.value.split(';') if o.strip()]
                
                if homework:  # Update
                    update_homework(homework['id'],
                        content_text=content_field.value,
                        video_url=video_field.value,
                        audio_url=audio_field.value,
                        options=options,
                        correct_answer=correct_field.value,
                        hint=hint_field.value
                    )
                    result_text.value = "Домашнее задание обновлено!"
                else:  # Create
                    new_hw = create_homework(
                        lesson_id=lesson_id,
                        content_text=content_field.value,
                        video_url=video_field.value,
                        audio_url=audio_field.value,
                        options=options,
                        correct_answer=correct_field.value,
                        hint=hint_field.value
                    )
                    result_text.value = f"Домашнее задание создано! ID: {new_hw['id']}"
                
                result_text.color = COLORS["success"]
                page.update()
            except Exception as ex:
                result_text.value = f"Ошибка: {str(ex)}"
                result_text.color = COLORS["error"]
                page.update()
        
        content_area.controls = [
            ft.Text(f"Домашнее задание для урока: {lesson['title']}" if lesson else "Выберите урок", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1, color=COLORS["border"]),
            content_field,
            video_field,
            audio_field,
            options_field,
            correct_field,
            hint_field,
            ft.Row([
                primary_button("Сохранить", on_click=save_homework, icon=ft.Icons.SAVE),
                secondary_button("Назад", on_click=lambda e: show_courses_list()),
            ], spacing=16),
            result_text,
        ]
        page.update()
    
    # ===== Navigation Menu =====
    nav_menu = ft.Column(
        [
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED, color=COLORS["primary"]),
                    ft.Text("Админ-панель", weight=ft.FontWeight.BOLD),
                ]),
                padding=16,
            ),
            ft.Divider(height=1, color=COLORS["border"]),
            ft.Container(
                content=ft.Column([
                    ft.TextButton(
                        "📚 Курсы",
                        on_click=lambda e: show_courses_list(),
                        style=ft.ButtonStyle(alignment=ft.alignment.center_left),
                    ),
                    ft.TextButton(
                        "➕ Новый курс",
                        on_click=lambda e: show_course_form(),
                        style=ft.ButtonStyle(alignment=ft.alignment.center_left),
                    ),
                ]),
                padding=8,
            ),
        ],
        spacing=0,
    )
    
    # Header
    header = ft.Container(
        content=ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.HOME,
                    on_click=lambda e: page.go("/"),
                ),
                ft.Text("Админ-панель", size=20, weight=ft.FontWeight.BOLD, expand=True),
                ft.TextButton("Выйти", on_click=lambda e: [setattr(state, 'is_admin', False), page.go("/")]),
            ],
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        bgcolor=COLORS["surface"],
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
    )
    
    # Initialize with courses list
    show_courses_list()
    
    return ft.View(
        "/admin/dashboard",
        controls=[
            ft.Column(
                [
                    header,
                    ft.Row(
                        [
                            # Left sidebar - navigation
                            ft.Container(
                                content=nav_menu,
                                width=250,
                                bgcolor=COLORS["surface"],
                                border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])),
                            ),
                            # Main content
                            ft.Container(
                                content=content_area,
                                padding=24,
                                expand=True,
                            ),
                        ],
                        expand=True,
                    ),
                ],
                expand=True,
            ),
        ],
        bgcolor=COLORS["background"],
    )


# ==========================================
# ROUTER
# ==========================================

def route_change(route: str, page: ft.Page, state: AppState):
    """Handle route changes and render appropriate views."""
    
    # Parse route
    route_path = route.split("?")[0]
    
    # Restore session
    state.restore_session()
    
    # Route matching
    if route_path == "/login":
        page.views.clear()
        page.views.append(login_page(page, state))
    
    elif route_path == "/admin":
        # If already admin, show dashboard
        if state.is_admin:
            page.views.clear()
            page.views.append(admin_panel_page(page, state))
        else:
            # Show auth form
            page.views.clear()
            page.views.append(admin_auth_page(page, state))
    
    elif route_path.startswith("/course/"):
        try:
            course_id = int(route_path.split("/")[2])
            page.views.clear()
            page.views.append(course_page(page, state, course_id))
        except (ValueError, IndexError):
            page.go("/")
    
    elif route_path == "/logout":
        state.logout()
        page.go("/login")
    
    else:  # Default: home
        # If not logged in, redirect to login
        if not state.user_id:
            page.go("/login")
            return
        page.views.clear()
        page.views.append(home_page(page, state))
    
    page.update()


def view_pop(view: ft.View, page: ft.Page):
    """Handle back navigation."""
    page.views.pop()
    top_view = page.views[-1] if page.views else None
    if top_view:
        page.go(top_view.route)
    else:
        page.go("/")


# ==========================================
# MAIN ENTRY POINT
# ==========================================

def main(page: ft.Page):
    """Main application entry point."""
    
    # Page configuration
    page.title = "LMS Platform"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.fonts = {
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    }
    page.theme = ft.Theme(
        font_family="Inter",
        color_scheme=ft.ColorScheme(
            primary=COLORS["primary"],
            secondary=COLORS["secondary"],
        ),
    )
    
    # Initialize database
    init_database()
    
    # Create app state
    state = AppState(page)
    
    # Setup routing
    def on_route_change(e):
        route_change(page.route, page, state)
    
    def on_view_pop(e):
        view_pop(e.control, page)
    
    page.on_route_change = on_route_change
    page.on_view_pop = on_view_pop
    
    # Navigate to initial route
    page.go(page.route or "/")


# Run the app
if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
