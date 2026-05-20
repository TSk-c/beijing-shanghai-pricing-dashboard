"""全库概览 API。"""

from fastapi import APIRouter

from app.services.data_loader import get_overview

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview")
def api_overview() -> dict[str, object]:
    """返回 parquet 聚合的真实概览统计。"""
    return get_overview()
