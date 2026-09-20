import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness_check(session: AsyncSession = Depends(get_db_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except (SQLAlchemyError, OSError) as e:
        logger.exception("Database readiness check failed", exc_info=e)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Service unavailable"}
        )
