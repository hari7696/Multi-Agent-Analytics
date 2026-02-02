from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from routes import sessions, messages, download, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    yield

app = FastAPI(
    lifespan=lifespan,
    title="Financial Agent System", 
    version="1.0.0",
    description="""
    ## Financial Agent API
    
    This API provides financial analysis capabilities powered by AI agents.
    
    ### Features:
    - Multi-agent financial analysis
    - Invoice and contract processing
    - Revenue analysis
    - Interactive visualizations
    - Session management
    """,
    contact={
        "name": "Financial Agent API Support",
        "email": "support@financialagent.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions.router, prefix="/api", tags=["💬 Sessions"])
app.include_router(messages.router, prefix="/api", tags=["💬 Messages"])
app.include_router(download.router, prefix="/api", tags=["📥 Download"])
app.include_router(health.router, prefix="/api", tags=["🏥 Health"])

@app.get("/")
async def index():
    return RedirectResponse(url="/docs")