"""模型性能与解释 API。"""

from __future__ import annotations

from fastapi import APIRouter

from app.services.model_service import (
    get_model_hsr,
    get_model_overview,
    get_model_sensitivity,
    get_model_shap,
)

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/performance/overview")
def api_model_overview() -> dict[str, object]:
    """5.2 分窗口 + 5.3 分场景 + 整体指标。"""
    return get_model_overview()


@router.get("/performance/shap")
def api_model_shap() -> dict[str, object]:
    """5.4 SHAP 全局解释。"""
    return get_model_shap()


@router.get("/performance/hsr")
def api_model_hsr() -> dict[str, object]:
    """5.5 高铁竞争特征贡献度。"""
    return get_model_hsr()


@router.get("/performance/sensitivity")
def api_model_sensitivity() -> dict[str, object]:
    """5.6 超参数敏感性。"""
    return get_model_sensitivity()
