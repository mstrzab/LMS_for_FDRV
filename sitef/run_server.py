"""
Combined Flet + FastAPI Server

This module provides a unified entry point that runs both:
1. Flet web application (UI)
2. FastAPI server (API + Webhooks)

This architecture allows:
- Flet to serve the web UI
- FastAPI to handle webhooks from Prodamus
- Both services to share the same database

Usage:
    python run_server.py

Or with uvicorn for production:
    uvicorn run_server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import logging
import threading
import os
from typing import Optional

import flet as ft
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import application modules
from database import init_database
from main import main as flet_main, COLORS, route_change
from prodamus_integration import (
    process_successful_payment,
    generate_payment_link,
    generate_order_id
)
from database import (
    get_course_by_id,
    get_user_by_id,
    get_all_courses,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==========================================
# FASTAPI APPLICATION
# ==========================================

# Create FastAPI app
api_app = FastAPI(
    title="LMS Platform API",
    description="API for LMS Platform",
    version="1.0.0"
)

# CORS
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api_app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    logger.info("🚀 Starting LMS Platform...")
    init_database()
    logger.info("✅ Database initialized")


@api_app.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "name": "LMS Platform",
        "version": "1.0.0",
        "flet_app": "/app",
        "api_docs": "/docs"
    }


@api_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "lms-platform"}


# ==========================================
# PRODAMUS WEBHOOK
# ==========================================

@api_app.post("/prodamus-webhook")
async def prodamus_webhook(request: Request):
    """
    Handle Prodamus payment webhook.
    
    This endpoint receives payment notifications from Prodamus
    and processes them to grant course access.
    """
    try:
        # Parse request
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)
        
        logger.info(f"📥 Webhook received: order={data.get('order_id')}, status={data.get('status')}")
        
        # Process payment
        result = await process_successful_payment(data)
        
        if result["success"]:
            logger.info(f"✅ Payment processed: {result}")
        else:
            logger.warning(f"⚠️ Payment not processed: {result['message']}")
        
        return {"success": result["success"], "message": result["message"]}
    
    except ValueError as e:
        logger.error(f"❌ Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# PAYMENT API
# ==========================================

@api_app.post("/api/payment/create")
async def create_payment(request: Request):
    """Create a payment link for a course."""
    data = await request.json()
    
    course_id = data.get("course_id")
    email = data.get("email")
    
    if not course_id or not email:
        raise HTTPException(400, "course_id and email required")
    
    course = get_course_by_id(course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    
    order_id = generate_order_id(course_id, email)
    base_url = str(request.base_url).rstrip("/")
    
    payment_url = generate_payment_link(
        order_id=order_id,
        product_name=course["title"],
        price_rub=course["price_rub"],
        customer_email=email,
        course_id=course_id,
        success_url=f"{base_url}/payment/success",
        fail_url=f"{base_url}/payment/fail",
        webhook_url=f"{base_url}/prodamus-webhook"
    )
    
    return {
        "order_id": order_id,
        "payment_url": payment_url
    }


# ==========================================
# COURSES API
# ==========================================

@api_app.get("/api/courses")
async def list_courses():
    """List all published courses."""
    courses = get_all_courses(published_only=True)
    # Remove sensitive data
    for c in courses:
        c.pop("payment_link", None)
    return {"courses": courses}


@api_app.get("/api/courses/{course_id}")
async def get_course(course_id: int):
    """Get course details."""
    from database import get_course_with_lessons
    course = get_course_with_lessons(course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    return course


# ==========================================
# COMBINED APPLICATION
# ==========================================

def run_flet_app():
    """Run Flet application in a separate thread."""
    logger.info("🎨 Starting Flet UI server...")
    ft.app(
        target=flet_main,
        view=ft.AppView.WEB_BROWSER,
        port=int(os.getenv("FLET_PORT", 8550)),
        host="0.0.0.0"
    )


def run_combined_server():
    """
    Run both Flet and FastAPI servers.
    
    Architecture:
    - FastAPI runs on port 8000 (main port)
    - Flet runs on port 8550 (internal)
    - Users access FastAPI which proxies to Flet
    """
    # Start Flet in background thread
    flet_thread = threading.Thread(target=run_flet_app, daemon=True)
    flet_thread.start()
    
    # Run FastAPI in main thread
    logger.info("🌐 Starting API server on port 8000...")
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


# ==========================================
# STANDALONE MODES
# ==========================================

def run_api_only():
    """Run only the FastAPI server."""
    logger.info("🌐 Starting API server (standalone)...")
    uvicorn.run(
        "run_server:api_app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


def run_flet_only():
    """Run only the Flet application."""
    logger.info("🎨 Starting Flet UI (standalone)...")
    ft.app(target=flet_main, view=ft.AppView.WEB_BROWSER)


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("LMS Platform - Flet + FastAPI")
    print("=" * 60)
    print("\nUsage:")
    print("  python run_server.py          - Run combined server")
    print("  python run_server.py --api    - Run API only")
    print("  python run_server.py --flet   - Run Flet only")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "--api":
            run_api_only()
        elif mode == "--flet":
            run_flet_only()
        else:
            print(f"Unknown mode: {mode}")
            sys.exit(1)
    else:
        run_combined_server()
