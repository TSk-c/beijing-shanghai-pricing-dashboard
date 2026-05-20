"""生成示例 processed_data.parquet（供开发 / Postman 联调）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = BACKEND_ROOT / "data" / "processed_data.parquet"


def main() -> None:
    rng = np.random.default_rng(42)
    n = 4000
    start = np.datetime64("2026-04-08")
    end = np.datetime64("2026-07-16")
    span = (end - start).astype(int) + 1
    qd_int = rng.integers(0, span, size=n)
    query_dates = start + qd_int.astype("timedelta64[D]")
    query_dates_str = pd.to_datetime(query_dates).strftime("%Y-%m-%d")

    prices = rng.normal(920, 160, size=n).clip(400, 2350)
    rpa = 0.85 + 0.25 * np.sin(qd_int.astype(float) / 7) + rng.normal(0, 0.08, size=n)
    rpa = np.clip(rpa, 0.45, 2.2)

    has_hsr = rng.random(n) < 0.26
    hsr_second = np.where(has_hsr, 553.0 + rng.normal(0, 8, size=n), np.nan)
    hsr_first = np.where(has_hsr, 933.0 + rng.normal(0, 12, size=n), np.nan)
    hsr_business = np.where(has_hsr, 1748.0 + rng.normal(0, 40, size=n), np.nan)

    ts_series = pd.to_datetime(pd.Series(query_dates_str))
    is_holiday = ((ts_series >= "2026-05-01") & (ts_series <= "2026-05-05")).astype(int).to_numpy(dtype=int)

    df = pd.DataFrame(
        {
            "query_date": query_dates_str,
            "price": prices.astype(float),
            "rpa": rpa.astype(float),
            "hsr_second": hsr_second,
            "hsr_first": hsr_first,
            "hsr_business": hsr_business,
            "has_hsr": has_hsr.astype(int),
            "is_holiday": is_holiday,
        }
    )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"written {OUT_PATH} rows={len(df)}")


if __name__ == "__main__":
    main()
