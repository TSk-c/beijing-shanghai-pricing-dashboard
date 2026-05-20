"""数据全景 API。"""

from fastapi import APIRouter

from app.services.data_loader import get_data_panorama

router = APIRouter(prefix="/api", tags=["panorama"])


@router.get("/data-panorama")
def api_data_panorama() -> dict[str, object]:
    return get_data_panorama()
