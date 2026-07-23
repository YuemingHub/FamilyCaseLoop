"""FastAPI 接口。仅绑定 127.0.0.1（对齐安全设计：单主机、零公网、不暴露 0.0.0.0）。

新增：
- GET  /settings  —— 返回掩码后的 key、provider、llm_enabled（不泄露明文）
- POST /settings  —— 网页端写入 key/provider，持久化到 .env 并立即生效
- GET  /          —— 单页可视化工作台（密钥设置 + 决策可视化 + 回复展示）
"""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .schemas import ReplyRequest, ReplyResult
from .reply_gen import generate
from .config import (settings, effective_api_key, effective_provider,
                     effective_llm_enabled, mask_key, save_settings)
from .web import INDEX_HTML

app = FastAPI(title=settings.app_name, version="1.1.0")

# 同行引导前端（B 任务）：接线返回仓库根 guide/index.html，不写逻辑
GUIDE_HTML = (Path(__file__).resolve().parent.parent.parent / "guide" / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_enabled": effective_llm_enabled(),
        "provider": effective_provider(),
    }


class SettingsIn(BaseModel):
    api_key: str = ""
    provider: str = "deepseek"


@app.get("/settings")
def get_settings():
    return {
        "provider": effective_provider(),
        "api_key_masked": mask_key(effective_api_key()),
        "has_key": bool(effective_api_key()),
        "llm_enabled": effective_llm_enabled(),
    }


@app.post("/settings")
def post_settings(body: SettingsIn):
    # 仅接受非空值覆盖；空字符串表示"不修改该项"
    key = body.api_key.strip()
    provider = body.provider.strip() or effective_provider()
    save_settings(key, provider)
    return {
        "ok": True,
        "provider": effective_provider(),
        "api_key_masked": mask_key(effective_api_key()),
        "has_key": bool(effective_api_key()),
        "llm_enabled": effective_llm_enabled(),
    }


@app.post("/reply", response_model=ReplyResult)
def reply(req: ReplyRequest):
    return generate(req)


@app.post("/analyze", response_model=ReplyResult)
def analyze(req: ReplyRequest):
    req.mode = "analyze"
    return generate(req)


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(INDEX_HTML)


@app.get("/guide", response_class=HTMLResponse)
def guide():
    return HTMLResponse(GUIDE_HTML)
