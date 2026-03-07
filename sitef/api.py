"""
FastAPI Application for Prodamus Webhook Handling

This module provides:
1. Webhook endpoint for Prodamus payment notifications
2. Parallel execution with Flet application
3. CORS configuration for web deployment

The FastAPI server runs alongside Flet and handles:
- POST /prodamus-webhook: Payment notifications from Prodamus
- GET /health: Health check endpoint
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

# Import our modules
from prodamus_integration import process_successful_payment, verify_webhook_signature
from database import (
    init_database,
    get_user_by_email,
    create_user,
    get_course_by_id,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==========================================
# APPLICATION LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events handler."""
    # Startup
    logger.info("🚀 Starting LMS API Server...")
    init_database()
    logger.info("✅ Database initialized")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down LMS API Server...")


# ==========================================
# FASTAPI APP
# ==========================================

app = FastAPI(
    title="LMS Platform API",
    description="API for LMS Platform with Prodamus payment integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# PYDANTIC MODELS
# ==========================================

class WebhookResponse(BaseModel):
    """Response for webhook endpoint."""
    success: bool
    message: str
    data: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str


class PaymentNotification(BaseModel):
    """Prodamus payment notification model."""
    order_id: str
    status: str
    sign: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    total_price: Optional[int] = None
    date: Optional[str] = None


# ==========================================
# WEBHOOK ENDPOINT
# ==========================================

@app.post("/prodamus-webhook", response_model=WebhookResponse)
async def prodamus_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Prodamus payment webhook notifications.
    
    This endpoint receives POST requests from Prodamus when a payment
    is completed. It verifies the signature and processes the payment.
    
    The webhook expects form-data or JSON with the following fields:
        - order_id: Unique order identifier
        - status: Payment status (success, fail, etc.)
        - sign: Signature for verification
        - customer_email: Customer's email address
        - total_price: Total amount in kopecks
        - meta[course_id]: Course ID (if provided during payment creation)
    
    Returns:
        WebhookResponse with success status and message
    """
    try:
        # Get content type
        content_type = request.headers.get("content-type", "")
        
        # Parse request body based on content type
        if "application/json" in content_type:
            data = await request.json()
        elif "application/x-www-form-urlencoded" in content_type:
            form_data = await request.form()
            data = dict(form_data)
        else:
            # Try JSON first, then form data
            try:
                data = await request.json()
            except:
                form_data = await request.form()
                data = dict(form_data)
        
        logger.info(f"📥 Received webhook: order_id={data.get('order_id')}, status={data.get('status')}")
        
        # Log full webhook data for debugging (remove in production)
        logger.debug(f"Webhook data: {json.dumps(data, indent=2, default=str)}")
        
        # Process the payment
        result = await process_successful_payment(data)
        
        if result["success"]:
            logger.info(f"✅ Payment processed: user_id={result.get('user_id')}, course_id={result.get('course_id')}")
            return WebhookResponse(
                success=True,
                message=result["message"],
                data=result
            )
        else:
            logger.warning(f"⚠️ Payment not processed: {result['message']}")
            return WebhookResponse(
                success=False,
                message=result["message"],
                data=result
            )
    
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/prodamus-webhook/test")
async def test_webhook(request: Request):
    """
    Test endpoint for webhook debugging.
    Returns the received data without processing.
    """
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        data = await request.json()
    else:
        form_data = await request.form()
        data = dict(form_data)
    
    return {
        "received": True,
        "content_type": content_type,
        "data": data
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database="connected"
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "LMS Platform API",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/prodamus-webhook",
            "health": "/health",
            "docs": "/docs",
        }
    }


# ==========================================
# USER ENDPOINTS (FOR TESTING)
# ==========================================

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID (for testing)."""
    from database import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Remove sensitive data
    user.pop("password_hash", None)
    return user


@app.get("/courses")
async def list_courses():
    """List all published courses."""
    from database import get_all_courses
    courses = get_all_courses(published_only=True)
    return {"courses": courses}


@app.get("/courses/{course_id}")
async def get_course(course_id: int):
    """Get course details."""
    course = get_course_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# ==========================================
# PAYMENT LINK GENERATION ENDPOINT
# ==========================================

@app.post("/generate-payment-link")
async def generate_link(request: Request):
    """
    Generate a Prodamus payment link.
    
    Request body:
        {
            "course_id": 1,
            "email": "user@example.com",
            "success_url": "https://...",
            "fail_url": "https://..."
        }
    """
    from prodamus_integration import generate_payment_link, generate_order_id
    
    data = await request.json()
    
    course_id = data.get("course_id")
    email = data.get("email")
    success_url = data.get("success_url")
    fail_url = data.get("fail_url")
    
    if not course_id or not email:
        raise HTTPException(status_code=400, detail="course_id and email are required")
    
    # Get course
    course = get_course_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Generate order ID
    order_id = generate_order_id(course_id, email)
    
    # Generate payment link
    payment_url = generate_payment_link(
        order_id=order_id,
        product_name=course["title"],
        price_rub=course["price_rub"],
        customer_email=email,
        course_id=course_id,
        success_url=success_url,
        fail_url=fail_url,
        webhook_url=str(request.base_url) + "prodamus-webhook"
    )
    
    return {
        "order_id": order_id,
        "payment_url": payment_url,
        "course": {
            "id": course["id"],
            "title": course["title"],
            "price_rub": course["price_rub"]
        }
    }


# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Starting LMS API Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  - http://localhost:8000/              : API Root")
    print("  - http://localhost:8000/docs          : API Documentation")
    print("  - http://localhost:8000/prodamus-webhook : Webhook endpoint")
    print("  - http://localhost:8000/health        : Health check")
    print("\n" + "=" * 60)
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
