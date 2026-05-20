"""票价分布 API。"""

from fastapi import APIRouter

from app.services.data_loader import get_price_distribution

router = APIRouter(prefix="/api/price", tags=["price"])


@router.get("/distribution")
def api_price_distribution() -> dict[str, object]:
    """票价直方 / KDE 用密度、偏度、峰度等（来自 processed_data.parquet）。"""
    return get_price_distribution()
