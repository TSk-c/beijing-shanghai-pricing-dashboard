"""空铁竞争相关 API。"""

from fastapi import APIRouter

from app.services.data_loader import get_rpa_trend

router = APIRouter(prefix="/api/rail-air", tags=["rail-air"])


@router.get("/rpa-trend")
def api_rpa_trend() -> dict[str, object]:
    """RPA 时序聚合结果（按 query_date）。"""
    return get_rpa_trend()
