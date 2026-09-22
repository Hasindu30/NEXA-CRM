from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import setup_exception_handlers
from app.api.v1.health import router as health_router
from app.modules.auth.router import router as auth_router
from app.modules.workspaces.router import router as workspaces_router
from app.modules.companies.router import router as companies_router
from app.modules.people.router import router as people_router
from app.db.session import engine

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: setup resources (e.g., DB pool) if needed
    yield
    # Shutdown: teardown resources (e.g., close DB engine)
    await engine.dispose()

app = FastAPI(
    title=settings.project_name,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    lifespan=lifespan
)

# Set up CORS middleware
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

setup_exception_handlers(app)

app.include_router(health_router, prefix=settings.api_v1_str)
app.include_router(auth_router, prefix=settings.api_v1_str)
app.include_router(workspaces_router, prefix=settings.api_v1_str)
app.include_router(companies_router, prefix=settings.api_v1_str)
app.include_router(people_router, prefix=settings.api_v1_str)
