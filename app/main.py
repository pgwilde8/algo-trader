import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# Import logging config
from app.core.logging_config import setup_logging

# Initialize logging first
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="TraderMain Clean API", version="2.0.0")

# ——— Session middleware (for admin login) ———
app.add_middleware(
    SessionMiddleware, 
    secret_key="change-this-super-secret-session-key-in-production"
)

# ——— CORS middleware ———
origins = [
    "http://localhost:3000",
    "http://localhost:8888",
    "https://app.myalgoagent.com",
    "https://myalgoagent.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ——— Static files & templates ———
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ——— API routes ———
from app.api.routes import news_avoidance_router
app.include_router(news_avoidance_router, prefix="/api/news-avoidance", tags=["news-avoidance"])

# ——— Web (Jinja2) routes ———
from app.web.routes.pages import router as pages_router
app.include_router(pages_router)

# ——— Health check ———
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}

@app.on_event("startup")
async def startup_event():
    """Log application startup"""
    logger.info("🚀 Starting TraderMain Clean API on port 8888")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)

