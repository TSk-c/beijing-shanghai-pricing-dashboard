"""模型对比与预测 API。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, field_validator

from app.services.data_loader import (
    get_model_comparison_static,
    mock_predict_response,
    verify_model_file_loaded,
    get_flights,
)
from app.services.model_service import predict_flight, predict_flight_prices, get_flights_by_date, get_prediction_coverage

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/comparison")
def api_model_comparison() -> dict[str, object]:
    """离线模型指标对比（静态评估表）。"""
    return get_model_comparison_static()


class PredictRequest(BaseModel):
    """41 维特征向量（与训练特征顺序一致，当前仅校验长度）。"""

    features: list[float] = Field(..., description="41 维浮点特征")

    @field_validator("features")
    @classmethod
    def must_be_41_dim(cls, v: list[float]) -> list[float]:
        if len(v) != 41:
            raise ValueError("features 必须为长度 41 的数组")
        return v


@router.post("/predict")
def api_model_predict(body: PredictRequest) -> dict[str, object]:
    """
    单样本预测占位：校验模型文件存在后返回固定 mock；
    后续可在此接入 xgboost.Booster 与特征对齐推理。
    """
    verify_model_file_loaded()
    return mock_predict_response()


class PredictFlightRequest(BaseModel):
    flight_no: str = Field(..., description="航班号，如 CA1507")
    dep_date: str = Field(..., description="出发日期，如 2026-04-15")
    days_prior: int = Field(..., ge=0, le=120, description="提前天数")


@router.post("/predict-flight")
def api_model_predict_flight(body: PredictFlightRequest) -> dict[str, object]:
    """根据航班号、出发日期、提前天数，从特征矩阵查找匹配行并用 xgboost 推理。"""
    return predict_flight(body.flight_no, body.dep_date, body.days_prior)


class PredictFlightPricesRequest(BaseModel):
    flight_no: str = Field(..., description="航班号，如 CA1507")
    dep_date: str = Field(..., description="出发日期，如 2026-04-15")


@router.post("/predict-flight-prices")
def api_model_predict_flight_prices(body: PredictFlightPricesRequest) -> dict[str, object]:
    """预测航班在不同提前天数下的价格曲线，返回最优购买时机。"""
    return predict_flight_prices(body.flight_no, body.dep_date)


@router.get("/flights")
def api_flights() -> list[dict[str, object]]:
    """获取真实航班列表（从 flights 表读取）。"""
    return get_flights()


@router.get("/flights-by-date")
def api_flights_by_date(dep_date: str = Query(..., description="出发日期，如 2026-04-15")) -> dict[str, object]:
    """获取指定出发日期在特征矩阵中有数据的所有航班号。"""
    flights = get_flights_by_date(dep_date)
    return {"dep_date": dep_date, "flights": flights}


@router.get("/prediction-coverage")
def api_prediction_coverage() -> dict[str, object]:
    """返回数据覆盖范围信息。"""
    return get_prediction_coverage()
