"""配置：从环境变量 / .env 读取，绝不硬编码密钥。

新增：网页端设置写入（/settings）的运行时覆盖 + 持久化到 .env + 掩码显示。
密钥仅存本机 .env（已被 .gitignore 排除），不进版本库、不出本机。
"""
from __future__ import annotations
from typing import Literal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "月明家长回复生成器 MVP"
    llm_provider: Literal["deepseek", "ollama"] = "deepseek"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "qwen2.5:7b"


settings = Settings()

# —— 运行时覆盖（网页设置写入，无需重启即生效）——
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RUNTIME: dict = {"deepseek_api_key": None, "llm_provider": None}


def effective_api_key() -> str:
    return (_RUNTIME.get("deepseek_api_key") or settings.deepseek_api_key or "").strip()


def effective_provider() -> str:
    return (_RUNTIME.get("llm_provider") or settings.llm_provider or "deepseek")


def effective_base_url() -> str:
    return settings.ollama_base_url if effective_provider() == "ollama" else settings.deepseek_base_url


def effective_model() -> str:
    return settings.ollama_model if effective_provider() == "ollama" else settings.deepseek_model


def effective_llm_enabled() -> bool:
    if effective_provider() == "deepseek":
        return bool(effective_api_key())
    return True


def mask_key(k: str) -> str:
    k = k or ""
    if len(k) <= 6:
        return "****" if k else ""
    return k[:3] + "****" + k[-3:]


def save_settings(key: str, provider: str) -> None:
    """持久化到 .env 并立即生效（运行时覆盖）。"""
    env_path = _PROJECT_ROOT / ".env"
    lines: dict = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            kk, _, vv = line.partition("=")
            lines[kk.strip()] = vv.strip()
    if key:
        lines["DEEPSEEK_API_KEY"] = key
    else:
        # 显式清空：网页端留空保存即移除密钥
        lines.pop("DEEPSEEK_API_KEY", None)
    if provider:
        lines["LLM_PROVIDER"] = provider
    env_path.write_text("\n".join(f"{kk}={vv}" for kk, vv in lines.items()) + "\n", encoding="utf-8")
    _RUNTIME["deepseek_api_key"] = key or None
    _RUNTIME["llm_provider"] = provider or None
