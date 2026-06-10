from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.api.endpoints import router as core_router
from app.api.uploads import router as uploads_router
from app.api.agent_endpoints import router as agent_router

import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.main")

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    await connect_to_mongo()
    yield
    # Shutdown: Close MongoDB Connection
    await close_mongo_connection()

app = FastAPI(
    title="Return Portal Backend API",
    description="Python FastAPI backend serving Shopify returns, file storage with GridFS and Gemini AI Agent.",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"API request received: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"API response status: {response.status_code} for {request.method} {request.url.path}")
        return response
    except Exception as e:
        # Structured logging of full backend exception stack trace
        logger.error(f"Validation failure or Unhandled Exception at {request.method} {request.url.path}: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": "An unexpected server error occurred."}
        )

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers under /api
app.include_router(core_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(agent_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Welcome to Return Portal API",
        "docs_url": "/docs",
        "status": "running",
        "env": settings.ENV
    }

@app.get("/api/health")
async def health_check():
    from app.database.mongodb import db
    db_status = "disconnected"
    if db.db is not None:
        try:
            await db.db.command("ping")
            db_status = "connected"
        except Exception:
            db_status = "unreachable"
            
    return {
        "status": "healthy",
        "database": db_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
