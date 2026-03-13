"""DataPilot - FastAPI Application Entry Point"""
import logging
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.routes import ask, connect, health
from app.agent_router import router as agent_router
from app.api.routes.admin import router as admin_router
from app.api.routes.feedback import router as feedback_router
from app.config import settings

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.INFO)

# Rate limiter — keyed by client IP
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])

app = FastAPI(
    title="DataPilot API",
    description="AI-powered BI Agent — ask questions about any PostgreSQL database in plain English",
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(connect.router, prefix="/connect", tags=["Connection"])
app.include_router(ask.router, prefix="/ask", tags=["Query"])
app.include_router(agent_router)
app.include_router(feedback_router)
app.include_router(admin_router)

@app.on_event("startup")
async def startup():
    structlog.get_logger().info("DataPilot API started", env=settings.app_env)
