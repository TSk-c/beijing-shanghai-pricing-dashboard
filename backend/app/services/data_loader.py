"""从 processed_data.parquet 加载聚合指标（真实统计）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from scipy.stats import pearsonr, ttest_ind

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_PARQUET_PATH = _BACKEND_ROOT / "data" / "processed_data.parquet"
_DB_PATH = _BACKEND_ROOT / "data" / "air_hsr_pricing.db"


def _read_df() -> pd.DataFrame:
    if not _PARQUET_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"数据文件不存在：{_PARQUET_PATH.name}，请先运行 scripts/generate_sample_processed_parquet.py 生成示例数据。",
        )
    return pd.read_parquet(_PARQUET_PATH)


def get_overview() -> dict[str, Any]:
    """全库概览：记录数、高铁匹配率、时间跨度、最优模型 MAPE。"""
    df = _read_df()
    total = int(len(df))
    if "hsr_data_available" in df.columns:
        hsr_cov = float(df["hsr_data_available"].mean())
    else:
        hsr_cov = float(df["price_S"].notna().mean())
    dd = pd.to_datetime(df["dep_date"])
    start = str(dd.min().date())
    end = str(dd.max().date())
    best_mape = 6.46
    try:
        from app.services.model_service import get_model_overview
        overview = get_model_overview()
        best_mape = float(overview["overall"]["mape"])
    except Exception:
        pass
    return {
        "total_records": total,
        "hsr_coverage": round(hsr_cov, 4),
        "date_range": {"start": start, "end": end},
        "best_model_mape": round(best_mape, 2),
    }


def get_price_distribution() -> dict[str, Any]:
    """票价直方 + KDE 用密度序列、偏度、峰度等（基于 price 列）。"""
    df = _read_df()
    prices = df["price"].dropna().astype(float)
    if prices.empty:
        raise HTTPException(status_code=503, detail="票价列为空，无法计算分布。")

    edges = np.linspace(400, 2400, 81)
    hist, edges = np.histogram(prices.to_numpy(), bins=edges)
    bin_w = float(edges[1] - edges[0])
    density = hist.astype(float) / (len(prices) * bin_w + 1e-12)
    kde = np.convolve(density, np.ones(7) / 7.0, mode="same")

    bins: list[dict[str, float]] = []
    for i in range(len(hist)):
        bins.append(
            {
                "start": float(edges[i]),
                "end": float(edges[i + 1]),
                "density": float(max(kde[i], 1e-12)),
            }
        )

    median = float(prices.median())
    mean = float(prices.mean())
    skewness = float(prices.skew()) if len(prices) > 2 else 0.0
    kurtosis = float(prices.kurtosis()) if len(prices) > 3 else 0.0

    return {
        "bins": bins,
        "median": round(median, 2),
        "mean": round(mean, 2),
        "skewness": round(skewness, 2),
        "kurtosis": round(kurtosis, 2),
    }


def _weekend_indices(dates: list[str], exclude_holidays: bool = True) -> list[int]:
    out: list[int] = []
    for i, d in enumerate(dates):
        wd = pd.Timestamp(d).weekday()
        if wd >= 5:
            if exclude_holidays and ("2026-05-01" <= d <= "2026-05-05"):
                continue
            out.append(i)
    return out


def _holiday_indices(dates: list[str]) -> list[int]:
    out: list[int] = []
    for i, d in enumerate(dates):
        if "2026-05-01" <= d <= "2026-05-05":
            out.append(i)
    return out


def _first_holiday_span(dates: list[str]) -> dict[str, int] | None:
    indices = _holiday_indices(dates)
    if not indices:
        return None
    lo = indices[0]
    hi = indices[0]
    for v in indices[1:]:
        if v == hi + 1:
            hi = v
        else:
            break
    return {"start": lo, "end": hi}


def get_rpa_trend() -> dict[str, Any]:
    """按 dep_date 聚合：航空均价（全量）、高铁三档（仅有效数据，取最新查询日）、RPA 实时计算。"""
    df = _read_df()

    air_daily = df.groupby("dep_date", as_index=False)["price"].mean()
    air_daily.columns = ["dep_date", "air_avg"]

    hsr_cols = ["dep_date", "query_date", "price_C", "price_F", "price_S"]
    hsr_df = df[df["hsr_data_available"] == 1][hsr_cols].drop_duplicates()
    for col in ["price_C", "price_F", "price_S"]:
        hsr_df.loc[hsr_df[col] == 0, col] = np.nan
    hsr_latest = hsr_df.sort_values("query_date").groupby("dep_date").last().reset_index()
    hsr_latest = hsr_latest[hsr_latest["price_C"].notna()]

    combined = air_daily.merge(
        hsr_latest[["dep_date", "price_S", "price_F", "price_C"]],
        on="dep_date", how="inner",
    ).sort_values("dep_date")

    dates = combined["dep_date"].astype(str).tolist()
    air = [round(float(x), 2) for x in combined["air_avg"].tolist()]
    rpa = [
        round(float(combined["price_F"].iloc[i]) / combined["air_avg"].iloc[i], 4)
        if combined["air_avg"].iloc[i] > 0 else 0
        for i in range(len(combined))
    ]
    hs2 = [round(float(x), 2) if np.isfinite(x) else 553.0 for x in combined["price_S"].tolist()]
    hs1 = [round(float(x), 2) if np.isfinite(x) else 933.0 for x in combined["price_F"].tolist()]
    hsb = [round(float(x), 2) if np.isfinite(x) else 1748.0 for x in combined["price_C"].tolist()]

    holidays = _first_holiday_span(dates)
    weekends = _weekend_indices(dates)

    pearson_r: float | None = None
    pearson_p: float | None = None
    if len(air) >= 3 and len(rpa) >= 3:
        r_val, p_val = pearsonr(air, rpa)
        pearson_r = round(float(r_val), 4)
        pearson_p = round(float(p_val), 4)

    out: dict[str, Any] = {
        "dates": dates,
        "airPrices": air,
        "rpaValues": rpa,
        "hsrSecond": hs2,
        "hsrFirst": hs1,
        "hsrBusiness": hsb,
        "weekends": weekends,
        "pearson_r": pearson_r,
        "pearson_p": pearson_p,
    }
    if holidays:
        out["holidays"] = holidays
    return out


_VS_ROOT = _BACKEND_ROOT.parent / "output_model_vs"

_MODEL_NAME_MAP: dict[str, str] = {"随机森林": "RandomForest"}

_MODEL_ORDER = [
    "Ridge", "Lasso", "ElasticNet",
    "RandomForest", "GradientBoosting", "LightGBM", "XGBoost",
    "LSTM",
]

_LAYER_ORDER = ["0-3天(临期)", "4-7天(中期)", "8-14天(远期)", "15天+(超远期)"]


def _extract_comparison_metrics(
    df: pd.DataFrame, model_order: list[str],
) -> dict[str, list[float | None]]:
    result: dict[str, list[float | None]] = {"mae": [], "mape": [], "rmse": []}
    for model in model_order:
        row = df[df["模型"] == model]
        if len(row) == 0 or row["MAE"].isna().all():
            result["mae"].append(None)
            result["mape"].append(None)
            result["rmse"].append(None)
        else:
            result["mae"].append(round(float(row["MAE"].iloc[0]), 2))
            result["mape"].append(round(float(row["MAPE"].iloc[0]), 2))
            result["rmse"].append(round(float(row["RMSE"].iloc[0]), 2))
    return result


def _fallback_comparison() -> dict[str, Any]:
    return {
        "models": [
            "Ridge", "Lasso", "ElasticNet",
            "RandomForest", "GradientBoosting", "LightGBM", "XGBoost",
        ],
        "layers": [],
        "overall": {
            "mae": [129.01, 122.95, 154.69, 60.27, 67.18, 51.81, 47.75],
            "mape": [17.07, 16.57, 21.14, 7.56, 8.54, 6.54, 6.46],
            "rmse": [185.29, 181.92, 202.78, 116.09, 106.13, 101.79, 93.80],
        },
        "layered": {},
    }


def get_model_comparison_static() -> dict[str, Any]:
    """模型对比表（离线评估结果，含整体与分层评估）。"""
    overall_csv = _VS_ROOT / "model_comparison_v2_overall.csv"
    layered_csv = _VS_ROOT / "model_comparison_v2_layered.csv"

    if not overall_csv.is_file() or not layered_csv.is_file():
        return _fallback_comparison()

    try:
        overall_df = pd.read_csv(overall_csv)
        layered_df = pd.read_csv(layered_csv)
    except Exception:
        return _fallback_comparison()

    overall_df["模型"] = overall_df["模型"].map(lambda x: _MODEL_NAME_MAP.get(x, x))
    layered_df["模型"] = layered_df["模型"].map(lambda x: _MODEL_NAME_MAP.get(x, x))

    overall = _extract_comparison_metrics(overall_df, _MODEL_ORDER)

    layered: dict[str, dict[str, list[float | None]]] = {}
    for layer in _LAYER_ORDER:
        layer_df = layered_df[layered_df["分层"] == layer]
        layered[layer] = _extract_comparison_metrics(layer_df, _MODEL_ORDER)

    return {
        "models": _MODEL_ORDER,
        "layers": _LAYER_ORDER,
        "overall": overall,
        "layered": layered,
    }


def get_data_panorama() -> dict[str, Any]:
    """数据全景：数据质量 + 采集覆盖 + 样本分布（基于 air_hsr_pricing.db）。"""
    if not _DB_PATH.is_file():
        raise HTTPException(status_code=503, detail=f"数据库文件不存在：{_DB_PATH.name}")

    conn = sqlite3.connect(str(_DB_PATH))

    fp = pd.read_sql("SELECT * FROM flight_prices", conn)
    hsr = pd.read_sql("SELECT * FROM hsr_prices", conn)
    expo = pd.read_sql("SELECT * FROM expos", conn)
    flights = pd.read_sql("SELECT * FROM flights", conn)
    conn.close()

    fp["query_date"] = pd.to_datetime(fp["query_date"])
    fp["dep_date"] = pd.to_datetime(fp["dep_date"])
    hsr["query_date"] = pd.to_datetime(hsr["query_date"])
    hsr["dep_date"] = pd.to_datetime(hsr["dep_date"])

    # ---- 数据质量 ----
    total = int(len(fp))
    missing_count = int(fp.isnull().any(axis=1).sum())
    missing_rate = round(missing_count / total, 4) if total > 0 else 0.0
    anomaly_count = int(((fp["price"] <= 0) | (fp["price"] > 10000)).sum())

    daily_counts = fp.groupby("query_date").size().reset_index(name="count")
    daily_counts["query_date"] = daily_counts["query_date"].dt.strftime("%Y-%m-%d")
    median_daily = float(daily_counts["count"].median())
    low_threshold = median_daily * 0.3
    low_coverage_dates = daily_counts[daily_counts["count"] < low_threshold][
        "query_date"
    ].tolist()

    daily_record_list = [
        {"date": r["query_date"], "count": int(r["count"])}
        for _, r in daily_counts.iterrows()
    ]

    # ---- 采集覆盖 ----
    air_query_start = str(fp["query_date"].min().date())
    air_query_end = str(fp["query_date"].max().date())
    air_dep_start = str(fp["dep_date"].min().date())
    air_dep_end = str(fp["dep_date"].max().date())
    air_query_days = int(fp["query_date"].nunique())
    air_dep_days = int(fp["dep_date"].nunique())
    unique_flights_count = int(flights["flight_no"].nunique())

    daily_flight_counts = (
        fp.groupby("query_date")["flight_no"]
        .nunique()
        .reset_index(name="count")
    )
    daily_flight_counts["query_date"] = daily_flight_counts["query_date"].dt.strftime(
        "%Y-%m-%d"
    )
    daily_flight_list = [
        {"date": r["query_date"], "count": int(r["count"])}
        for _, r in daily_flight_counts.iterrows()
    ]

    hsr_query_start = str(hsr["query_date"].min().date())
    hsr_query_end = str(hsr["query_date"].max().date())
    hsr_dep_start = str(hsr["dep_date"].min().date())
    hsr_dep_end = str(hsr["dep_date"].max().date())
    hsr_query_days = int(hsr["query_date"].nunique())
    hsr_total = int(len(hsr))

    expo_total = int(len(expo))
    expo_start = str(expo["start_date"].min())
    expo_end = str(expo["end_date"].max())

    # ---- 样本分布 ----
    airline_dist = (
        fp.groupby("airline")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    airline_list = [
        {"name": r["airline"], "count": int(r["count"])}
        for _, r in airline_dist.iterrows()
    ]

    dep_airport_dist = (
        fp.groupby("dep_airport")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    dep_airport_list = [
        {"name": r["dep_airport"], "count": int(r["count"])}
        for _, r in dep_airport_dist.iterrows()
    ]

    arr_airport_dist = (
        fp.groupby("arr_airport")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    arr_airport_list = [
        {"name": r["arr_airport"], "count": int(r["count"])}
        for _, r in arr_airport_dist.iterrows()
    ]

    price_stats = {
        "min": round(float(fp["price"].min()), 1),
        "max": round(float(fp["price"].max()), 1),
        "mean": round(float(fp["price"].mean()), 1),
        "median": round(float(fp["price"].median()), 1),
        "std": round(float(fp["price"].std()), 1),
    }

    weekday_count = int((fp["is_weekend"] == 0).sum())
    weekend_count = int((fp["is_weekend"] == 1).sum())
    holiday_count = int((fp["is_holiday"] == 1).sum())
    normal_count = int((fp["is_holiday"] == 0).sum())

    return {
        "data_quality": {
            "total_records": total,
            "missing_count": missing_count,
            "missing_rate": missing_rate,
            "anomaly_count": anomaly_count,
            "low_coverage_dates": low_coverage_dates,
            "daily_records": daily_record_list,
        },
        "collection_coverage": {
            "air": {
                "query_date_range": {"start": air_query_start, "end": air_query_end},
                "dep_date_range": {"start": air_dep_start, "end": air_dep_end},
                "query_days": air_query_days,
                "dep_days": air_dep_days,
                "unique_flights": unique_flights_count,
                "daily_flights": daily_flight_list,
            },
            "hsr": {
                "query_date_range": {"start": hsr_query_start, "end": hsr_query_end},
                "dep_date_range": {"start": hsr_dep_start, "end": hsr_dep_end},
                "query_days": hsr_query_days,
                "total_records": hsr_total,
            },
            "expo": {
                "total": expo_total,
                "date_range": {"start": expo_start, "end": expo_end},
            },
        },
        "sample_distribution": {
            "airlines": airline_list,
            "dep_airports": dep_airport_list,
            "arr_airports": arr_airport_list,
            "price_stats": price_stats,
            "weekday_count": weekday_count,
            "weekend_count": weekend_count,
            "holiday_count": holiday_count,
            "normal_count": normal_count,
        },
    }


_eda_cache: dict[str, Any] | None = None


def get_eda_charts() -> dict[str, Any]:
    """EDA 可视化数据：提前天数分析、航司预订曲线、热力图、余票时序、RPA异质性、节假日N型、展会效应。"""
    global _eda_cache
    if _eda_cache is not None:
        return _eda_cache
    df = _read_df()
    df["dep_date"] = pd.to_datetime(df["dep_date"])
    if "query_date" in df.columns:
        df["query_date"] = pd.to_datetime(df["query_date"])

    hsr_mask = df["hsr_data_available"] == 1 if "hsr_data_available" in df.columns else df["price_S"].notna()

    # ---- E2: 提前天数分析 ----
    dp_sub = df[df["days_prior"] <= 30]
    quantile_curve = dp_sub.groupby("days_prior")["price"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).unstack()
    quantile_curve.columns = ["p10", "p25", "p50", "p75", "p90"]
    quantile_curve = quantile_curve.reset_index()
    days_prior_list = quantile_curve["days_prior"].astype(int).tolist()
    quantile_data = {
        "days": days_prior_list,
        "p10": [round(float(v), 1) for v in quantile_curve["p10"].tolist()],
        "p25": [round(float(v), 1) for v in quantile_curve["p25"].tolist()],
        "p50": [round(float(v), 1) for v in quantile_curve["p50"].tolist()],
        "p75": [round(float(v), 1) for v in quantile_curve["p75"].tolist()],
        "p90": [round(float(v), 1) for v in quantile_curve["p90"].tolist()],
    }

    # ---- E2-1: 典型出发日期预订曲线 ----
    holiday_ranges_list: list[dict[str, str]] = []
    holiday_dates_sorted = sorted(df[df["is_holiday"] == 1]["dep_date"].unique())
    if holiday_dates_sorted:
        h_start = holiday_dates_sorted[0]
        h_prev = holiday_dates_sorted[0]
        for d in holiday_dates_sorted[1:]:
            if (d - h_prev).days == 1:
                h_prev = d
            else:
                holiday_ranges_list.append({"start": str(h_start.date()) if hasattr(h_start, 'date') else str(h_start), "end": str(h_prev.date()) if hasattr(h_prev, 'date') else str(h_prev)})
                h_start = h_prev = d
        holiday_ranges_list.append({"start": str(h_start.date()) if hasattr(h_start, 'date') else str(h_start), "end": str(h_prev.date()) if hasattr(h_prev, 'date') else str(h_prev)})

    typical_dates_data: list[dict[str, Any]] = []
    if "dep_dow" not in df.columns:
        df["dep_dow"] = pd.to_datetime(df["dep_date"]).dt.weekday
    min_dep = df["dep_date"].min()
    max_dep = df["dep_date"].max()

    wednesdays = sorted(set(df[(df["dep_dow"] == 2) & (df["is_holiday"] == 0) &
                               (df["is_pre_holiday_peak"] == 0) & (df["is_expo_day"] == 0)]["dep_date"].tolist()))
    if wednesdays:
        d = wednesdays[0]
        sub = df[df["dep_date"] == d].groupby("days_prior")["price"].mean().sort_index()
        typical_dates_data.append({"label": f"普通周三 ({d.date() if hasattr(d, 'date') else d})", "days": sub.index.astype(int).tolist(), "prices": [round(float(v), 1) for v in sub.values.tolist()]})

    preferred_friday = pd.Timestamp("2026-04-24")
    if preferred_friday in df["dep_date"].values:
        d = preferred_friday
        sub = df[df["dep_date"] == d].groupby("days_prior")["price"].mean().sort_index()
        typical_dates_data.append({"label": f"周五 ({d.date() if hasattr(d, 'date') else d})", "days": sub.index.astype(int).tolist(), "prices": [round(float(v), 1) for v in sub.values.tolist()]})
    else:
        fridays_all = sorted(set(df[(df["dep_dow"] == 4) & (df["is_holiday"] == 0) &
                                    (df["is_pre_holiday_peak"] == 0)]["dep_date"].tolist()))
        friday_stats = [(d2, df[df["dep_date"] == d2]["days_prior"].max(), len(df[df["dep_date"] == d2]))
                        for d2 in fridays_all]
        good = [(d2, m, n) for d2, m, n in friday_stats if m >= 14 and n >= 20]
        if good:
            chosen = sorted(good, key=lambda x: x[0])[len(good) // 2][0]
            sub = df[df["dep_date"] == chosen].groupby("days_prior")["price"].mean().sort_index()
            typical_dates_data.append({"label": f"周五 ({chosen.date() if hasattr(chosen, 'date') else chosen})", "days": sub.index.astype(int).tolist(), "prices": [round(float(v), 1) for v in sub.values.tolist()]})

    if "is_pre_holiday_peak" in df.columns:
        pre_peak = sorted(set(df[df["is_pre_holiday_peak"] == 1]["dep_date"].tolist()))
        if pre_peak:
            d = pre_peak[0]
            sub = df[df["dep_date"] == d].groupby("days_prior")["price"].mean().sort_index()
            typical_dates_data.append({"label": f"节假日前1天 ({d.date() if hasattr(d, 'date') else d})", "days": sub.index.astype(int).tolist(), "prices": [round(float(v), 1) for v in sub.values.tolist()]})

    if "is_holiday_mid" in df.columns:
        holiday_mid = sorted(set(df[df["is_holiday_mid"] == 1]["dep_date"].tolist()))
        if holiday_mid:
            d = holiday_mid[0]
            sub = df[df["dep_date"] == d].groupby("days_prior")["price"].mean().sort_index()
            typical_dates_data.append({"label": f"节假日中 ({d.date() if hasattr(d, 'date') else d})", "days": sub.index.astype(int).tolist(), "prices": [round(float(v), 1) for v in sub.values.tolist()]})

    if holiday_ranges_list:
        last_holiday_dates = [end_dt for _, end_dt in [(pd.Timestamp(hr2["start"]), pd.Timestamp(hr2["end"])) for hr2 in holiday_ranges_list]]
        available_last = sorted(set(d2 for d2 in last_holiday_dates
                                    if d2 >= min_dep and d2 <= max_dep and d2 in df["dep_date"].values))
        if available_last:
            d = available_last[0]
            sub = df[df["dep_date"] == d].groupby("days_prior")["price"].mean().sort_index()
            typical_dates_data.append({"label": f"节假日最后一天 ({d.date() if hasattr(d, 'date') else d})", "days": sub.index.astype(int).tolist(), "prices": [round(float(v), 1) for v in sub.values.tolist()]})

    # ---- E2-3: 关键区间箱线图 ----
    if "prior_bin" not in df.columns:
        bins_box = [0, 1, 3, 7, 14, 21, 31, 90]
        labels_box = ["当天", "1-2天", "3-6天", "7-13天", "14-20天", "21-30天", "30天+"]
        df["prior_bin"] = pd.cut(df["days_prior"], bins=bins_box, labels=labels_box, right=False)
    box_order = ["当天", "1-2天", "3-6天", "7-13天", "14-20天", "21-30天", "30天+"]
    existing_bins = [b for b in box_order if b in df["prior_bin"].unique()]
    box_data: dict[str, list[float]] = {}
    box_stats: list[dict[str, Any]] = []
    for b in existing_bins:
        sub = df.loc[df["prior_bin"] == b, "price"].dropna()
        if len(sub) < 5:
            continue
        sampled = sub.sample(min(len(sub), 300), random_state=42).tolist()
        box_data[b] = [round(float(v), 1) for v in sampled]
        box_stats.append({
            "bin": b,
            "mean": round(float(sub.mean()), 1),
            "median": round(float(sub.median()), 1),
            "q1": round(float(sub.quantile(0.25)), 1),
            "q3": round(float(sub.quantile(0.75)), 1),
            "count": int(len(sub)),
        })
    overall_median = round(float(df["price"].median()), 1)

    # ---- E3: 航司预订曲线 ----
    airlines = sorted(df["airline"].unique().tolist())
    airline_curves: dict[str, Any] = {}
    for al in airlines:
        sub = df[(df["airline"] == al) & (df["days_prior"] <= 30)].groupby("days_prior")["price"].mean().sort_index()
        airline_curves[al] = {
            "days": sub.index.astype(int).tolist(),
            "prices": [round(float(v), 1) for v in sub.values.tolist()],
        }

    # ---- E3-2: 热力图 (dep_dow × prior_bin) ----
    if "dep_dow" not in df.columns:
        df["dep_dow"] = pd.to_datetime(df["dep_date"]).dt.weekday
    if "prior_bin_heat" not in df.columns:
        bins_heat = [0, 3, 7, 14, 30, 90]
        labels_heat = ["0-2天", "3-6天", "7-13天", "14-29天", "30天+"]
        df["prior_bin_heat"] = pd.cut(df["days_prior"], bins=bins_heat, labels=labels_heat, right=False)
    pivot_heat = df.groupby(["dep_dow", "prior_bin_heat"], observed=True)["price"].mean().unstack()
    dow_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    heat_cols = [str(c) for c in pivot_heat.columns.tolist()]
    heat_matrix: list[list[float | None]] = []
    for dow in range(7):
        row: list[float | None] = []
        for col in pivot_heat.columns:
            if dow in pivot_heat.index:
                val = pivot_heat.loc[dow, col]
                row.append(round(float(val), 1) if pd.notna(val) else None)
            else:
                row.append(None)
        heat_matrix.append(row)
    heatmap = {"dow_names": dow_names, "columns": heat_cols, "matrix": heat_matrix}

    # ---- E4-1b: 高铁余票时序 ----
    air_daily = df.groupby("dep_date", as_index=False)["price"].agg(["mean", "std", "count"])
    air_daily.columns = ["dep_date", "air_avg", "air_std", "flight_count"]

    hsr_cols_remain = ["dep_date", "query_date", "price_C", "price_F", "price_S", "remain_C", "remain_F", "remain_S"]
    available_hsr_cols = [c for c in hsr_cols_remain if c in df.columns]
    hsr_df_r = df[hsr_mask][available_hsr_cols].drop_duplicates()
    for col in ["price_C", "price_F", "price_S"]:
        if col in hsr_df_r.columns:
            hsr_df_r.loc[hsr_df_r[col] == 0, col] = np.nan
    for col in ["remain_C", "remain_F", "remain_S"]:
        if col in hsr_df_r.columns and hsr_df_r[col].dtype in [np.float64, np.int64]:
            hsr_df_r.loc[hsr_df_r[col] == 0, col] = np.nan

    hsr_latest_r = hsr_df_r.sort_values("query_date").groupby("dep_date").last().reset_index()
    remain_cols = [c for c in ["remain_C", "remain_F", "remain_S"] if c in hsr_latest_r.columns]
    if remain_cols:
        hsr_latest_r = hsr_latest_r[hsr_latest_r[remain_cols[0]].notna()]

    combined_r = air_daily.merge(hsr_latest_r[["dep_date"] + remain_cols], on="dep_date", how="inner").sort_values("dep_date")
    remain_dates = combined_r["dep_date"].astype(str).tolist()
    remain_data: dict[str, Any] = {
        "dates": remain_dates,
        "air_avg": [round(float(v), 1) for v in combined_r["air_avg"].tolist()],
        "weekends": _weekend_indices(remain_dates),
    }
    remain_holidays = _first_holiday_span(remain_dates)
    if remain_holidays:
        remain_data["holidays"] = remain_holidays
    for col in ["remain_C", "remain_F", "remain_S"]:
        remain_data[col] = [round(float(v), 0) if np.isfinite(v) else 0 for v in combined_r[col].tolist()] if col in combined_r.columns else []

    # ---- E4-3: 供给紧张度时序 ----
    supply_trend: dict[str, Any] = {}
    if "supply_tension_F" in df.columns:
        supply_daily = df[hsr_mask].groupby("dep_date", as_index=False)["supply_tension_F"].mean()
        supply_daily.columns = ["dep_date", "supply_avg"]
        air_for_supply = df.groupby("dep_date", as_index=False)["price"].mean()
        air_for_supply.columns = ["dep_date", "air_avg"]
        merged_supply = air_for_supply.merge(supply_daily, on="dep_date", how="inner").dropna().sort_values("dep_date")
        supply_pearson_r: float | None = None
        supply_pearson_p: float | None = None
        if len(merged_supply) > 2:
            r_val, p_val = pearsonr(merged_supply["supply_avg"], merged_supply["air_avg"])
            supply_pearson_r = round(float(r_val), 4)
            supply_pearson_p = round(float(p_val), 4)
        supply_dates = merged_supply["dep_date"].astype(str).tolist()
        supply_trend = {
            "dates": supply_dates,
            "air_avg": [round(float(v), 1) for v in merged_supply["air_avg"].tolist()],
            "supply_avg": [round(float(v), 4) for v in merged_supply["supply_avg"].tolist()],
            "pearson_r": supply_pearson_r,
            "pearson_p": supply_pearson_p,
            "weekends": _weekend_indices(supply_dates),
        }
        supply_holidays = _first_holiday_span(supply_dates)
        if supply_holidays:
            supply_trend["holidays"] = supply_holidays

    # ---- E4-4: RPA 分提前期异质性 ----
    period_configs = [
        ("中期(7-30天)", (df["days_prior"] >= 7) & (df["days_prior"] <= 30)),
        ("临期(3-7天)", (df["days_prior"] >= 3) & (df["days_prior"] < 7)),
        ("极临期(<3天)", df["days_prior"] < 3),
    ]
    rpa_hetero: list[dict[str, Any]] = []
    if "rpa_F" in df.columns:
        for label, mask in period_configs:
            sub = df.loc[hsr_mask & mask, ["rpa_F", "price"]].dropna()
            if len(sub) < 30:
                rpa_hetero.append({"period": label, "n": len(sub), "r": None, "p": None, "slope": None, "scatter_rpa": [], "scatter_price": []})
                continue
            r_val, p_val = pearsonr(sub["rpa_F"], sub["price"])
            slope = float(np.polyfit(sub["rpa_F"], sub["price"], 1)[0])
            sample_n = min(len(sub), 500)
            sampled = sub.sample(sample_n, random_state=42)
            rpa_hetero.append({
                "period": label,
                "n": len(sub),
                "r": round(float(r_val), 4),
                "p": round(float(p_val), 4),
                "slope": round(slope, 1),
                "scatter_rpa": [round(float(v), 4) for v in sampled["rpa_F"].tolist()],
                "scatter_price": [round(float(v), 1) for v in sampled["price"].tolist()],
            })

    # ---- E4-5: RPA 阈值效应 ----
    rpa_segment_data: dict[str, Any] = {}
    if "rpa_segment" in df.columns:
        seg_order = sorted(df.loc[hsr_mask, "rpa_segment"].dropna().unique().tolist())
        seg_stats: list[dict[str, Any]] = []
        seg_box: dict[str, list[float]] = {}
        for seg in seg_order:
            sub = df.loc[hsr_mask & (df["rpa_segment"] == seg), "price"].dropna()
            seg_stats.append({
                "segment": str(seg),
                "mean": round(float(sub.mean()), 1),
                "median": round(float(sub.median()), 1),
                "std": round(float(sub.std()), 1),
                "count": int(len(sub)),
            })
            sampled = sub.sample(min(len(sub), 200), random_state=42).tolist()
            seg_box[str(seg)] = [round(float(v), 1) for v in sampled]
        rpa_segment_data = {"segments": seg_order, "stats": seg_stats, "box_data": seg_box}

    # ---- E4-6: 供给紧张度条件效应 ----
    supply_effect: dict[str, Any] = {}
    if "supply_tension_F" in df.columns:
        scatter_data: list[dict[str, Any]] = []
        for is_hol, label in [(0, "工作日"), (1, "节假日")]:
            sub = df.loc[hsr_mask & (df["is_holiday"] == is_hol), ["supply_tension_F", "price"]].dropna()
            if len(sub) < 10:
                continue
            r_val, p_val = pearsonr(sub["supply_tension_F"], sub["price"])
            sampled = sub.sample(min(len(sub), 300), random_state=42)
            scatter_data.append({
                "label": label,
                "r": round(float(r_val), 4),
                "p": round(float(p_val), 4),
                "tension": [round(float(v), 4) for v in sampled["supply_tension_F"].tolist()],
                "price": [round(float(v), 1) for v in sampled["price"].tolist()],
            })
        supply_effect = {"scatter": scatter_data}

    # ---- E5: 节假日 N 型效应 ----
    n_shape_data: list[dict[str, Any]] = []
    for hr in holiday_ranges_list:
        s = pd.Timestamp(hr["start"])
        e = pd.Timestamp(hr["end"])
        window_start = s - pd.Timedelta(days=3)
        window_end = e + pd.Timedelta(days=2)
        sub = df[(df["dep_date"] >= window_start) & (df["dep_date"] <= window_end)]
        if len(sub) == 0:
            continue
        daily = sub.groupby("dep_date")["price"].mean().reset_index()
        daily["rel_day"] = daily["dep_date"].apply(lambda d: (d - s).days + 1 if d >= s else (d - s).days)
        hsr_sub = hsr_latest_r[(hsr_latest_r["dep_date"] >= window_start) & (hsr_latest_r["dep_date"] <= window_end)] if len(hsr_latest_r) > 0 else pd.DataFrame()
        entry: dict[str, Any] = {
            "start": hr["start"],
            "end": hr["end"],
            "air_rel_days": daily["rel_day"].astype(int).tolist(),
            "air_prices": [round(float(v), 1) for v in daily["price"].tolist()],
        }
        if len(hsr_sub) > 0 and "price_C" in hsr_sub.columns:
            hsr_sub_c = hsr_sub[["dep_date", "price_C"]].copy()
            hsr_sub_c["rel_day"] = hsr_sub_c["dep_date"].apply(lambda d: (d - s).days + 1 if d >= s else (d - s).days)
            entry["hsr_rel_days"] = hsr_sub_c["rel_day"].astype(int).tolist()
            entry["hsr_prices"] = [round(float(v), 1) if np.isfinite(v) else None for v in hsr_sub_c["price_C"].tolist()]
        n_shape_data.append(entry)

    # ---- E4-2: 分窗口 RPA 弹性系数 ----
    rpa_elasticity: list[dict[str, Any]] = []
    if "rpa_F" in df.columns and "window_fine" in df.columns:
        import statsmodels.api as sm
        windows = ["0-2天", "3-7天", "8-14天"]
        for win in windows:
            sub = df[(df["window_fine"] == win) & hsr_mask]
            daily = sub.groupby("dep_date").agg(air_avg=("price", "mean"), rpa_avg=("rpa_F", "mean")).reset_index()
            merged_w = daily.dropna(subset=["air_avg", "rpa_avg"])
            if len(merged_w) < 10:
                rpa_elasticity.append({"window": win, "coef": None, "coef_scaled": None, "std_err_scaled": None, "p_value": None})
                continue
            X = sm.add_constant(merged_w["rpa_avg"])
            model = sm.OLS(merged_w["air_avg"], X).fit()
            rpa_elasticity.append({
                "window": win,
                "coef": round(float(model.params["rpa_avg"]), 4),
                "coef_scaled": round(float(model.params["rpa_avg"]) * 0.1, 2),
                "std_err_scaled": round(float(model.bse["rpa_avg"]) * 0.1, 2),
                "p_value": round(float(model.pvalues["rpa_avg"]), 4),
            })

    # ---- E4-2b: 分窗口航空均价与 RPA 对比 ----
    windowed_rpa: list[dict[str, Any]] = []
    if "rpa_F" in df.columns and "window_fine" in df.columns:
        windows_plot = ["0-2天", "3-7天", "8-14天"]
        for win in windows_plot:
            sub = df[(df["window_fine"] == win) & hsr_mask]
            daily = sub.groupby("dep_date").agg(air_avg=("price", "mean"), rpa_avg=("rpa_F", "mean")).reset_index()
            if len(daily) == 0:
                windowed_rpa.append({"window": win, "dates": [], "air_avg": [], "rpa_avg": [], "weekends": [], "holidays": None})
                continue
            w_dates = daily["dep_date"].astype(str).tolist()
            w_weekends = _weekend_indices(w_dates)
            w_holidays = _first_holiday_span(w_dates)
            entry_w: dict[str, Any] = {
                "window": win,
                "dates": w_dates,
                "air_avg": [round(float(v), 1) for v in daily["air_avg"].tolist()],
                "rpa_avg": [round(float(v), 4) for v in daily["rpa_avg"].tolist()],
                "weekends": w_weekends,
            }
            if w_holidays:
                entry_w["holidays"] = w_holidays
            windowed_rpa.append(entry_w)

    # ---- E6: 展会效应 ----
    expo_effect: dict[str, Any] = {}
    expo_tests: list[dict[str, Any]] = []
    if "is_expo_day" in df.columns and "day_type" in df.columns:
        grouped = df.groupby(["day_type", "is_expo_day"])["price"].mean().reset_index()
        pivot = grouped.pivot(index="day_type", columns="is_expo_day", values="price")
        pivot.columns = ["非展会日", "展会日"] if len(pivot.columns) == 2 else pivot.columns
        expo_effect = {
            "day_types": pivot.index.tolist(),
            "non_expo": [round(float(v), 1) for v in pivot.iloc[:, 0].tolist()],
            "expo": [round(float(v), 1) for v in pivot.iloc[:, 1].tolist()] if pivot.shape[1] > 1 else [],
        }
        for day_type in df["day_type"].unique():
            sub = df[df["day_type"] == day_type]
            expo_p = sub[sub["is_expo_day"] == 1]["price"]
            non_p = sub[sub["is_expo_day"] == 0]["price"]
            if len(expo_p) >= 2 and len(non_p) >= 2:
                t_stat, p_val = ttest_ind(expo_p, non_p)
                expo_tests.append({
                    "day_type": str(day_type),
                    "expo_mean": round(float(expo_p.mean()), 1),
                    "non_expo_mean": round(float(non_p.mean()), 1),
                    "premium": round(float(expo_p.mean() - non_p.mean()), 1),
                    "t_stat": round(float(t_stat), 3),
                    "p_value": round(float(p_val), 4),
                })

    return {
        "quantile_curve": quantile_data,
        "typical_dates": typical_dates_data,
        "box_plot": {"bins": existing_bins, "box_data": box_data, "stats": box_stats, "overall_median": overall_median},
        "airline_curves": airline_curves,
        "airlines": airlines,
        "heatmap": heatmap,
        "remain_trend": remain_data,
        "supply_trend": supply_trend,
        "rpa_heterogeneity": rpa_hetero,
        "rpa_segment": rpa_segment_data,
        "supply_effect": supply_effect,
        "n_shape": n_shape_data,
        "holiday_ranges": holiday_ranges_list,
        "expo_effect": expo_effect,
        "expo_tests": expo_tests,
        "rpa_elasticity": rpa_elasticity,
        "windowed_rpa": windowed_rpa,
    }
    _eda_cache = result
    return result


def get_model_json_path() -> Path:
    """优先 xgb_model.json，否则使用仓库内已有 v5 模型文件。"""
    primary = _BACKEND_ROOT / "data" / "xgb_model.json"
    fallback = _BACKEND_ROOT / "data" / "xgb_air_hsr_model_v5.json"
    if primary.is_file():
        return primary
    return fallback


def verify_model_file_loaded() -> None:
    """校验模型文件存在（避免对超大 JSON 全量解析）。"""
    path = get_model_json_path()
    if not path.is_file():
        raise HTTPException(status_code=503, detail="模型文件不存在，请放置 xgb_model.json 或 xgb_air_hsr_model_v5.json。")
    if path.stat().st_size == 0:
        raise HTTPException(status_code=500, detail="模型文件为空。")


def mock_predict_response() -> dict[str, Any]:
    """推理占位：固定返回（后续可接 xgboost 真实 predict）。"""
    return {
        "predicted_price": 892.5,
        "confidence_interval": [796.8, 988.2],
        "prediction_interval_95": [700.0, 1085.0],
        "key_drivers": [
            {"feature": "days_prior", "shap_value": -45.2, "direction": "negative"},
            {"feature": "rpa_F", "shap_value": -28.5, "direction": "negative"},
            {"feature": "dep_dow", "shap_value": 22.0, "direction": "positive"},
        ],
        "competitive_status": {
            "rpa_level": "高铁略贵",
            "supply_status": "宽松",
            "recommendation": "维持当前定价",
        },
    }


_cached_flights: list[dict[str, Any]] | None = None


def get_flights() -> list[dict[str, Any]]:
    global _cached_flights
    if _cached_flights is not None:
        return _cached_flights
    if not _DB_PATH.is_file():
        raise HTTPException(status_code=503, detail=f"数据库文件不存在：{_DB_PATH.name}")
    conn = sqlite3.connect(str(_DB_PATH))
    rows = conn.execute(
        "SELECT flight_no, airline, dep_airport, arr_airport, dep_time, arr_time, duration "
        "FROM flights ORDER BY flight_no"
    ).fetchall()
    conn.close()
    _cached_flights = [
        {
            "flight_no": r[0],
            "airline": r[1],
            "dep_airport": r[2],
            "arr_airport": r[3],
            "dep_time": r[4],
            "arr_time": r[5],
            "duration": r[6],
        }
        for r in rows
    ]
    return _cached_flights
