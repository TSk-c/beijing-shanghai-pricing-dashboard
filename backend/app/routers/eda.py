"""EDA 可视化 API。"""

from fastapi import APIRouter

from app.services.data_loader import get_eda_charts

router = APIRouter(prefix="/api/eda", tags=["eda"])


@router.get("/charts")
def api_eda_charts() -> dict[str, object]:
    return get_eda_charts()
