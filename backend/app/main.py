"""FastAPI 应用入口。"""

from __future__ import annotations

import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import competition, eda, model, model_perf, overview, panorama, price

app = FastAPI(title="京沪空铁竞争定价 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(panorama.router)
app.include_router(price.router)
app.include_router(competition.router)
app.include_router(eda.router)
app.include_router(model.router)
app.include_router(model_perf.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def _preload() -> None:
    import threading

    def _worker() -> None:
        try:
            from app.services.data_loader import get_eda_charts
            get_eda_charts()
            print("[preload] EDA 数据已缓存")
        except Exception as exc:
            print(f"[preload] EDA 预加载失败: {exc}")
        try:
            from app.services.model_service import get_model_overview
            get_model_overview()
            print("[preload] 模型概览已缓存")
        except Exception as exc:
            print(f"[preload] 模型概览预加载失败: {exc}")
        try:
            from app.services.model_service import get_model_shap
            get_model_shap()
            print("[preload] SHAP 已缓存")
        except Exception as exc:
            print(f"[preload] SHAP 预加载失败: {exc}")
        try:
            from app.services.model_service import get_model_hsr
            get_model_hsr()
            print("[preload] 高铁贡献已缓存")
        except Exception as exc:
            print(f"[preload] 高铁贡献预加载失败: {exc}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
