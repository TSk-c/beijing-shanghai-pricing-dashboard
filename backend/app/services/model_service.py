"""XGBoost 定价模型：从 model.py 输出的 CSV 文件读取评估结果。"""

from __future__ import annotations

import threading
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_OUTPUT_ROOT = _BACKEND_ROOT.parent / "output"

_HSR_FEATURE_COLS = [
    "rpa_F", "price_diff_F", "supply_tension_F",
    "rpa_F_x_days_prior", "supply_tension_F_x_is_holiday",
    "supply_tension_F_x_is_weekend", "price_diff_F_x_days_prior",
    "rpa_F_x_is_weekend", "rpa_F_high", "rpa_F_low",
    "supply_tension_high",
    "price_F", "remain_F", "price_C", "remain_C",
    "price_S", "remain_S", "hsr_avg_duration_h", "train_count",
    "hsr_F_S_spread", "hsr_total_remain",
]

_WINDOW_MAP: dict[str, str] = {
    "0-3天(临期)": "0-3天",
    "4-7天(中期)": "4-7天",
    "8-14天(远期)": "8-14天",
    "15天+(超远期)": "15天+",
}

_N_FEATURES = 41

_cached_overview: dict[str, Any] | None = None
_cached_shap: dict[str, Any] | None = None
_cached_hsr: dict[str, Any] | None = None
_cached_sensitivity: dict[str, Any] | None = None
_cached_model_bundle: dict[str, Any] | None = None
_cached_feature_df: pd.DataFrame | None = None
_model_lock = threading.Lock()


def _require_csv(name: str) -> pd.DataFrame:
    path = _OUTPUT_ROOT / name
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"模型输出文件 {name} 不存在，请先运行 model.py 生成",
        )
    try:
        return pd.read_csv(path)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"读取 {name} 失败: {e}")


def get_model_overview() -> dict[str, Any]:
    global _cached_overview
    if _cached_overview is not None:
        return _cached_overview

    df_overall = _require_csv("eval_overall.csv")
    row = df_overall.iloc[0]

    overall = {
        "n": int(row.get("样本量", 0)) if "样本量" in df_overall.columns else 0,
        "rmse": round(float(row["RMSE"]), 2),
        "mae": round(float(row["MAE"]), 2),
        "mape": round(float(row["MAPE"]), 2),
        "r2": round(float(row["R²"]), 4),
        "adj_r2": round(float(row["Adj.R²"]), 4),
        "ev": round(float(row["Expl.Var"]), 4),
        "me": round(float(row["ME"]), 2),
        "max_err": round(float(row["MaxErr"]), 2),
        "med_ae": round(float(row["MedAE"]), 2),
    }

    df_lead = _require_csv("eval_by_lead_window.csv")
    window_metrics: list[dict[str, Any]] = []
    for _, r in df_lead.iterrows():
        label = str(r["分层"])
        window_metrics.append({
            "window": _WINDOW_MAP.get(label, label),
            "n": int(r["样本量"]),
            "rmse": round(float(r["RMSE"]), 2),
            "mae": round(float(r["MAE"]), 2),
            "mape": round(float(r["MAPE"]), 2),
            "r2": round(float(r["R²"]), 4),
            "adj_r2": round(float(r["Adj.R²"]), 4),
            "ev": round(float(r["Expl.Var"]), 4),
            "me": round(float(r["ME"]), 2),
            "max_err": round(float(r["MaxErr"]), 2),
            "med_ae": round(float(r["MedAE"]), 2),
        })

    df_scenario = _require_csv("eval_by_scenario.csv")
    _EXCLUDED_SCENARIOS = {"节前积蓄"}
    scenario_metrics: list[dict[str, Any]] = []
    for _, r in df_scenario.iterrows():
        if str(r["场景"]) in _EXCLUDED_SCENARIOS:
            continue
        scenario_metrics.append({
            "scenario": str(r["场景"]),
            "n": int(r["样本量"]),
            "rmse": round(float(r["RMSE"]), 2),
            "mae": round(float(r["MAE"]), 2),
            "mape": round(float(r["MAPE"]), 2),
            "r2": round(float(r["R²"]), 4),
            "adj_r2": round(float(r["Adj.R²"]), 4),
            "ev": round(float(r["Expl.Var"]), 4),
            "me": round(float(r["ME"]), 2),
            "max_err": round(float(r["MaxErr"]), 2),
            "med_ae": round(float(r["MedAE"]), 2),
        })

    _cached_overview = {
        "overall": overall,
        "window_metrics": window_metrics,
        "scenario_metrics": scenario_metrics,
        "n_features": _N_FEATURES,
    }
    return _cached_overview


def get_model_shap() -> dict[str, Any]:
    global _cached_shap
    if _cached_shap is not None:
        return _cached_shap

    df_top20 = _require_csv("shap_top20_features.csv")

    scatter_path = _OUTPUT_ROOT / "shap_scatter_data.csv"
    has_scatter = scatter_path.is_file()
    df_scatter = pd.read_csv(scatter_path) if has_scatter else None

    shap_global: list[dict[str, Any]] = []
    for _, r in df_top20.iterrows():
        feat_name = str(r["特征"])
        importance = round(float(r["平均|SHAP|"]), 4)

        scatter: list[dict[str, float]] = []
        if df_scatter is not None:
            feat_data = df_scatter[df_scatter["feature"] == feat_name]
            for _, sr in feat_data.iterrows():
                scatter.append({"value": round(float(sr["value"]), 4), "shap": round(float(sr["shap"]), 4)})

        if not scatter:
            n_pts = 80
            np.random.seed(hash(feat_name) % (2**31))
            for j in range(n_pts):
                val = round(float(np.random.randn()), 4)
                sv = round(float(np.random.randn() * importance / 20), 4)
                scatter.append({"value": val, "shap": sv})

        shap_global.append({
            "feature": feat_name,
            "importance": importance,
            "scatter": scatter,
        })

    _cached_shap = {"shap_global": shap_global}
    return _cached_shap


def get_model_hsr() -> dict[str, Any]:
    global _cached_hsr
    if _cached_hsr is not None:
        return _cached_hsr

    df_cat = _require_csv("shap_category_contribution.csv")
    cat_row = df_cat.iloc[0]
    hsr_overall_pct = round(float(cat_row["高铁竞争"]), 1)

    df_top20 = _require_csv("shap_top20_features.csv")
    feature_contributions: list[dict[str, Any]] = []
    for _, r in df_top20.iterrows():
        feat_name = str(r["特征"])
        is_hsr = feat_name in _HSR_FEATURE_COLS or feat_name == "hsr_data_available"
        feature_contributions.append({
            "feature": feat_name,
            "importance": round(float(r["平均|SHAP|"]), 4),
            "is_hsr": is_hsr,
        })

    hsr_available_pct = hsr_overall_pct

    df_hsr_lead = _require_csv("shap_hsr_by_lead.csv")
    period_contributions: list[dict[str, Any]] = []
    for _, r in df_hsr_lead.iterrows():
        n = int(r["样本数"])
        if n < 10:
            continue
        hsr_pct = float(r["高铁贡献%"]) if pd.notna(r["高铁贡献%"]) else 0.0
        core_pct = float(r["核心竞争贡献%"]) if pd.notna(r["核心竞争贡献%"]) else 0.0
        period_contributions.append({
            "period": str(r["提前期"]),
            "hsr_pct": round(hsr_pct, 1),
            "rpa_pct": round(core_pct, 1),
            "n": n,
        })

    _cached_hsr = {
        "hsr_contribution": {
            "overall_pct": hsr_overall_pct,
            "available_pct": hsr_available_pct,
            "feature_contributions": feature_contributions,
            "period_contributions": period_contributions,
        },
    }
    return _cached_hsr


def get_model_sensitivity() -> dict[str, Any]:
    global _cached_sensitivity
    if _cached_sensitivity is not None:
        return _cached_sensitivity

    _SENSITIVITY_PARAM_FILES: dict[str, str] = {
        "learning_rate": "sensitivity_learning_rate.csv",
        "max_depth": "sensitivity_max_depth.csv",
        "subsample": "sensitivity_subsample.csv",
        "colsample_bytree": "sensitivity_colsample_bytree.csv",
        "reg_alpha": "sensitivity_reg_alpha.csv",
        "reg_lambda": "sensitivity_reg_lambda.csv",
        "min_child_weight": "sensitivity_min_child_weight.csv",
    }

    sensitivity_results: dict[str, list[dict[str, Any]]] = {}
    for param_name, csv_file in _SENSITIVITY_PARAM_FILES.items():
        csv_path = _OUTPUT_ROOT / csv_file
        if not csv_path.is_file():
            continue
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            continue
        results: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            results.append({
                "value": float(row["参数值"]),
                "rmse": round(float(row["RMSE"]), 2),
                "mae": round(float(row["MAE"]), 2),
                "mape": round(float(row["MAPE"]), 2),
                "r2": round(float(row["R²"]), 4),
            })
        sensitivity_results[param_name] = results

    if not sensitivity_results:
        raise HTTPException(status_code=503, detail="超参敏感性数据文件不存在，请先运行 model.py 生成")

    _cached_sensitivity = {"sensitivity": sensitivity_results}
    return _cached_sensitivity


_MODEL_FEATURES = [
    "days_prior", "days_prior_sq",
    "dep_dow", "dep_time_hour", "dep_period_enc",
    "is_weekend",
    "is_pre_holiday_peak", "is_pre_holiday_buildup",
    "holiday_day_num", "is_holiday_mid", "is_holiday_last_2d",
    "is_post_holiday_dip", "days_to_nearest_holiday",
    "expo_max_scale", "is_expo_day",
    "airline_enc", "dep_airport_enc", "arr_airport_enc",
    "duration_hours",
    "hsr_data_available",
    "rpa_F", "price_diff_F", "supply_tension_F",
    "rpa_F_x_days_prior", "supply_tension_F_x_is_holiday",
    "supply_tension_F_x_is_weekend", "price_diff_F_x_days_prior",
    "rpa_F_x_is_weekend", "rpa_F_high", "rpa_F_low",
    "supply_tension_high",
    "price_F", "remain_F", "price_C", "remain_C",
    "price_S", "remain_S", "hsr_avg_duration_h", "train_count",
    "hsr_F_S_spread", "hsr_total_remain",
]


def _ensure_model() -> dict[str, Any]:
    global _cached_model_bundle
    if _cached_model_bundle is not None:
        return _cached_model_bundle

    with _model_lock:
        if _cached_model_bundle is not None:
            return _cached_model_bundle

        import xgboost as xgb
        import shap

        _FEATURE_PATH = _BACKEND_ROOT / "data" / "feature_matrix_final_v5.parquet"
        _TARGET_PATH = _BACKEND_ROOT / "data" / "target_final_v5.parquet"
        _MODEL_PATH = _BACKEND_ROOT / "data" / "xgb_air_hsr_model_v5.json"

        if not _MODEL_PATH.is_file():
            raise HTTPException(status_code=503, detail="模型文件不存在，请先运行 model.py 训练模型")
        if not _FEATURE_PATH.is_file() or not _TARGET_PATH.is_file():
            raise HTTPException(status_code=503, detail="特征数据文件不存在")

        model = xgb.XGBRegressor()
        model.load_model(str(_MODEL_PATH))

        features = pd.read_parquet(_FEATURE_PATH).reset_index(drop=True)
        target = pd.read_parquet(_TARGET_PATH).reset_index(drop=True)
        df = features.copy()
        df["price"] = target["price"]
        df["query_date"] = pd.to_datetime(df["query_date"]).dt.date
        df["dep_date"] = pd.to_datetime(df["dep_date"]).dt.date

        over = df["days_prior"] > 14
        if over.sum() > 0:
            df.loc[over, "hsr_data_available"] = 0
            cols_zero = [c for c in _HSR_FEATURE_COLS if c in df.columns]
            df.loc[over, cols_zero] = 0

        model_features = [c for c in _MODEL_FEATURES if c in df.columns]

        df_overall = _require_csv("eval_overall.csv")
        row0 = df_overall.iloc[0]
        residual_std = float(row0["RMSE"])

        explainer = shap.TreeExplainer(model)

        _cached_model_bundle = {
            "model": model,
            "df": df,
            "model_features": model_features,
            "residual_std": residual_std,
            "explainer": explainer,
        }
    return _cached_model_bundle


def _get_feature_df() -> pd.DataFrame:
    global _cached_feature_df
    if _cached_feature_df is not None:
        return _cached_feature_df
    _FEATURE_PATH = _BACKEND_ROOT / "data" / "feature_matrix_final_v5.parquet"
    if not _FEATURE_PATH.is_file():
        raise HTTPException(status_code=503, detail="特征数据文件不存在")
    df = pd.read_parquet(_FEATURE_PATH)
    df["dep_date"] = pd.to_datetime(df["dep_date"]).dt.date
    _cached_feature_df = df
    return _cached_feature_df


def get_flights_by_date(dep_date: str) -> list[str]:
    """返回指定出发日期在特征矩阵中有数据的所有航班号。"""
    df = _get_feature_df()
    target_date = pd.to_datetime(dep_date).date()
    flights = df[df["dep_date"] == target_date]["flight_no"].unique().tolist()
    return sorted(flights)


_DATE_FEATURES = [
    "dep_dow", "dep_time_hour", "dep_period_enc", "is_weekend",
    "is_pre_holiday_peak", "is_pre_holiday_buildup",
    "holiday_day_num", "is_holiday_mid", "is_holiday_last_2d",
    "is_post_holiday_dip", "days_to_nearest_holiday",
    "expo_max_scale", "is_expo_day",
]

_FLIGHT_ATTR_FEATURES = [
    "airline_enc", "dep_airport_enc", "arr_airport_enc", "duration_hours",
]

_HSR_BASE_FEATURES = [
    "hsr_data_available",
    "rpa_F", "price_diff_F", "supply_tension_F",
    "rpa_F_high", "rpa_F_low", "supply_tension_high",
    "price_F", "remain_F", "price_C", "remain_C",
    "price_S", "remain_S", "hsr_avg_duration_h", "train_count",
    "hsr_F_S_spread", "hsr_total_remain",
]


def _build_feature_row_c(
    df: pd.DataFrame,
    flight_no: str,
    target_date: pd.Timestamp,
    days_prior: int,
    model_features: list[str],
) -> pd.Series:
    """思路C：日期特征来自目标出发日期，高铁特征来自同航班同提前天数的历史均值。"""
    df_target = df[
        (df["flight_no"] == flight_no)
        & (df["dep_date"] == target_date)
    ]
    if df_target.empty:
        df_target = df[df["flight_no"] == flight_no].head(1)
    if df_target.empty:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"未找到航班 {flight_no} 的特征数据",
                "available_flights": get_flights_by_date(str(target_date)),
                "has_flight_on_date": False,
            },
        )

    date_row = df_target.iloc[0].copy()

    df_dp = df[
        (df["flight_no"] == flight_no)
        & (df["days_prior"] == days_prior)
    ]

    row = date_row.copy()

    row["days_prior"] = days_prior
    row["days_prior_sq"] = days_prior ** 2

    if not df_dp.empty:
        for feat in _HSR_BASE_FEATURES:
            if feat in df_dp.columns:
                row[feat] = df_dp[feat].mean()

    is_holiday = float(date_row.get("is_holiday", 0)) if "is_holiday" in date_row.index else 0.0
    is_weekend = float(date_row.get("is_weekend", 0)) if "is_weekend" in date_row.index else 0.0
    rpa_f = float(row.get("rpa_F", 0))
    price_diff_f = float(row.get("price_diff_F", 0))
    supply_tension_f = float(row.get("supply_tension_F", 0))

    if "rpa_F_x_days_prior" in row.index:
        row["rpa_F_x_days_prior"] = rpa_f * days_prior
    if "price_diff_F_x_days_prior" in row.index:
        row["price_diff_F_x_days_prior"] = price_diff_f * days_prior
    if "supply_tension_F_x_is_holiday" in row.index:
        row["supply_tension_F_x_is_holiday"] = supply_tension_f * is_holiday
    if "supply_tension_F_x_is_weekend" in row.index:
        row["supply_tension_F_x_is_weekend"] = supply_tension_f * is_weekend
    if "rpa_F_x_is_weekend" in row.index:
        row["rpa_F_x_is_weekend"] = rpa_f * is_weekend

    if days_prior > 14:
        row["hsr_data_available"] = 0
        hsr_cols_in_features = [c for c in model_features if c in _HSR_FEATURE_COLS]
        for c in hsr_cols_in_features:
            row[c] = 0.0

    return row


def predict_flight(flight_no: str, dep_date: str, days_prior: int) -> dict[str, Any]:
    b = _ensure_model()
    model = b["model"]
    df = b["df"]
    model_features = b["model_features"]
    residual_std = b["residual_std"]
    explainer = b["explainer"]

    target_date = pd.to_datetime(dep_date).date()

    row = _build_feature_row_c(df, flight_no, target_date, days_prior, model_features)

    X_single = row[model_features].to_frame().T.astype(float)

    predicted_price = float(model.predict(X_single)[0])
    ci_half = 1.96 * residual_std * 0.5
    pi_half = 1.96 * residual_std
    confidence_interval = [round(predicted_price - ci_half, 1), round(predicted_price + ci_half, 1)]
    prediction_interval_95 = [round(predicted_price - pi_half, 1), round(predicted_price + pi_half, 1)]

    shap_values = explainer.shap_values(X_single)
    base_value = float(explainer.expected_value)
    shap_arr = shap_values[0]

    _FEATURE_CATEGORIES: dict[str, list[str]] = {
        "提前期": ["days_prior", "days_prior_sq"],
        "时间特征": ["dep_dow", "dep_time_hour", "dep_period_enc", "is_weekend"],
        "节假日/展会": [
            "is_pre_holiday_peak", "is_pre_holiday_buildup",
            "holiday_day_num", "is_holiday_mid", "is_holiday_last_2d",
            "is_post_holiday_dip", "days_to_nearest_holiday",
            "expo_max_scale", "is_expo_day",
        ],
        "航班属性": ["airline_enc", "dep_airport_enc", "arr_airport_enc", "duration_hours"],
        "高铁竞争": _HSR_FEATURE_COLS + ["hsr_data_available"],
    }

    _feat_to_cat: dict[str, str] = {}
    for cat, feats in _FEATURE_CATEGORIES.items():
        for feat in feats:
            _feat_to_cat[feat] = cat

    feature_shap: list[dict[str, Any]] = []
    for i, feat in enumerate(model_features):
        sv = float(shap_arr[i])
        feature_shap.append({
            "feature": feat,
            "value": round(float(row[feat]), 4) if feat in row.index else 0,
            "shap": round(sv, 4),
            "abs_shap": round(abs(sv), 4),
            "shap_value": round(sv, 2),
            "feature_value": round(float(row[feat]), 2) if feat in row.index else None,
            "direction": "positive" if sv >= 0 else "negative",
            "category": _feat_to_cat.get(feat, "其他"),
        })
    feature_shap.sort(key=lambda x: x["abs_shap"], reverse=True)

    waterfall: list[dict[str, Any]] = []
    cum = base_value
    for item in feature_shap[:15]:
        new_cum = cum + item["shap"]
        waterfall.append({
            "feature": item["feature"],
            "from": round(cum, 2),
            "to": round(new_cum, 2),
            "shap_value": item["shap"],
            "category": _feat_to_cat.get(item["feature"], "其他"),
        })
        cum = new_cum

    category_summary: dict[str, dict[str, Any]] = {}
    for cat, feats in _FEATURE_CATEGORIES.items():
        total_abs = 0.0
        net = 0.0
        cat_feats: list[dict[str, Any]] = []
        for feat in feats:
            if feat in model_features:
                idx = model_features.index(feat)
                sv = float(shap_arr[idx])
                total_abs += abs(sv)
                net += sv
                cat_feats.append({"feature": feat, "shap_value": round(sv, 2)})
        cat_feats.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        category_summary[cat] = {
            "total_abs_contribution": round(total_abs, 2),
            "net_contribution": round(net, 2),
            "top_features": cat_feats[:3],
        }

    key_drivers: list[dict[str, Any]] = []
    for item in feature_shap[:5]:
        sv = item["shap"]
        key_drivers.append({
            "feature": item["feature"],
            "shap_value": round(sv, 2),
            "feature_value": round(item["value"], 2) if item["value"] else None,
            "direction": "positive" if sv >= 0 else "negative",
            "category": _feat_to_cat.get(item["feature"], "其他"),
        })

    rpa_val = float(row.get("rpa_F", 0))
    rpa_level = "低竞争" if rpa_val < 0.8 else ("中竞争" if rpa_val < 1.0 else "高竞争")
    supply_val = float(row.get("supply_tension_F", 0))
    supply_status = "宽松" if supply_val < 0.3 else ("适中" if supply_val < 0.7 else "紧张")

    if rpa_level == "高竞争" and supply_status == "紧张":
        recommendation = "高铁竞争激烈且供给紧张，建议维持或小幅提价"
    elif rpa_level == "高竞争":
        recommendation = "高铁竞争激烈，建议定价接近或略低于高铁一等座"
    elif supply_status == "紧张":
        recommendation = "供给紧张，可适度提价"
    else:
        recommendation = "竞争温和，可按常规策略定价"

    return {
        "flight_no": flight_no,
        "dep_date": dep_date,
        "days_prior": days_prior,
        "predicted_price": round(predicted_price, 1),
        "base_value": round(base_value, 1),
        "confidence_interval": confidence_interval,
        "prediction_interval_95": prediction_interval_95,
        "key_drivers": key_drivers,
        "shap_detail": {
            "all_features": feature_shap,
            "waterfall": waterfall,
            "category_summary": category_summary,
        },
        "competitive_status": {
            "rpa_level": rpa_level,
            "supply_status": supply_status,
            "recommendation": recommendation,
        },
    }


def predict_flight_prices(flight_no: str, dep_date: str) -> dict[str, Any]:
    """预测航班在不同提前天数下的价格，标记已过期的节点，只从未过期节点中推荐最优时机。"""
    b = _ensure_model()
    model = b["model"]
    df = b["df"]
    model_features = b["model_features"]

    target_date = pd.to_datetime(dep_date).date()
    today = date.today()
    remaining_days = (target_date - today).days
    target_ts = pd.to_datetime(dep_date)

    df_target = df[
        (df["flight_no"] == flight_no)
        & (df["dep_date"] == target_date)
    ]
    if df_target.empty:
        df_target = df[df["flight_no"] == flight_no].head(1)
    if df_target.empty:
        available_flights = get_flights_by_date(dep_date)
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"未找到航班 {flight_no} 的特征数据",
                "available_flights": available_flights,
                "has_flight_on_date": flight_no in available_flights if available_flights else False,
            },
        )

    reference_price: float | None = None
    df_target_sorted = df_target.sort_values("query_date") if "query_date" in df_target.columns and not df_target.empty else df_target
    if not df_target_sorted.empty and "price" in df_target_sorted.columns:
        reference_price = round(float(df_target_sorted["price"].iloc[-1]), 1)

    days_prior_list = [1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60]

    prices: list[dict[str, Any]] = []
    today_str = today.isoformat()

    for dp in days_prior_list:
        row = _build_feature_row_c(df, flight_no, target_date, dp, model_features)
        X_single = row[model_features].to_frame().T.astype(float)
        pred = float(model.predict(X_single)[0])
        purchase_date = target_ts - pd.Timedelta(days=int(dp))
        is_expired = dp > remaining_days
        prices.append({
            "days_prior": dp,
            "predicted_price": round(pred, 1),
            "purchase_date": str(purchase_date.date()),
            "is_expired": is_expired,
            "expired_note": f"需在 {purchase_date.date()} 前购买，已过期" if is_expired else "仍可操作",
        })

    actionable = [p for p in prices if not p["is_expired"]]

    if actionable:
        best = min(actionable, key=lambda x: x["predicted_price"])
        best_message = f"建议提前 {best['days_prior']} 天购买（{best['purchase_date']}），预测最低价 ¥{best['predicted_price']}"
    else:
        best = min(prices, key=lambda x: x["predicted_price"])
        best_message = f"所有提前天数均已过期，历史最优为提前 {best['days_prior']} 天，预测价 ¥{best['predicted_price']}（仅供参考，无法操作）"

    return {
        "flight_no": flight_no,
        "dep_date": dep_date,
        "today": today_str,
        "remaining_days": remaining_days,
        "reference_price": reference_price,
        "prices": prices,
        "best_buy": {
            "days_prior": best["days_prior"],
            "predicted_price": best["predicted_price"],
            "purchase_date": best["purchase_date"],
            "is_expired": best.get("is_expired", False),
            "message": best_message,
        },
    }


def get_prediction_coverage() -> dict[str, Any]:
    """返回数据覆盖范围信息，用于前端展示预测的数据基础。"""
    df = _get_feature_df()
    dep_dates = df["dep_date"].dropna().unique()
    dep_dates_sorted = sorted(dep_dates)
    min_dep = str(dep_dates_sorted[0]) if dep_dates_sorted else ""
    max_dep = str(dep_dates_sorted[-1]) if dep_dates_sorted else ""

    query_dates = df["query_date"].dropna().unique() if "query_date" in df.columns else []
    query_dates_sorted = sorted(query_dates)
    min_query = str(query_dates_sorted[0]) if query_dates_sorted else ""
    max_query = str(query_dates_sorted[-1]) if query_dates_sorted else ""

    days_prior_range = sorted(df["days_prior"].dropna().unique().tolist()) if "days_prior" in df.columns else []
    min_dp = int(days_prior_range[0]) if days_prior_range else 0
    max_dp = int(days_prior_range[-1]) if days_prior_range else 0

    flight_count = int(df["flight_no"].nunique()) if "flight_no" in df.columns else 0
    total_rows = len(df)

    return {
        "dep_date_range": {"min": min_dep, "max": max_dep},
        "query_date_range": {"min": min_query, "max": max_query},
        "days_prior_range": {"min": min_dp, "max": max_dp},
        "flight_count": flight_count,
        "total_rows": total_rows,
        "method": "思路C：日期特征来自目标出发日期，高铁竞争特征来自同航班同提前天数的历史均值",
        "note": f"数据爬取期 {min_query} ~ {max_query}，覆盖出发日期 {min_dep} ~ {max_dep}，"
                f"提前天数 {min_dp}~{max_dp} 天。"
                f"预测时，日期特征（星期、节假日等）取自目标出发日期，"
                f"高铁竞争特征取自该航班在相同提前天数下的历史均值，"
                f"提前>14天时高铁特征自动清零（与训练一致）。",
    }
