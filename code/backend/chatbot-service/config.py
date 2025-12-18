"""
챗봇 백엔드 설정 로더.

- OpenAI / Azure OpenAI 제공자(provider) 지원
- `backend/config.yml`(공용) + `chatbot-service/config.yml`(서비스별) + 환경변수(.env) 조합
"""
import os
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 디렉토리
SERVICE_DIR = Path(__file__).parent                    # code/backend/chatbot-service
BACKEND_DIR = SERVICE_DIR.parent                       # code/backend

# 환경변수 로드(backend 레벨 먼저, 그 다음 서비스 레벨 override)
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=False)
load_dotenv(dotenv_path=SERVICE_DIR / ".env", override=True)

# 설정 파일(backend 레벨 먼저, 그 다음 서비스 레벨 override)
BACKEND_CONFIG_FILE = BACKEND_DIR / "config.yml"
SERVICE_CONFIG_FILE = SERVICE_DIR / "config.yml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """딕셔너리를 재귀적으로 병합합니다(override가 우선)."""
    out: dict[str, Any] = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


class LLMConfig(BaseSettings):
    """LLM 제공자 설정"""
    provider: Literal["openai", "azure_openai", "mock"] = "mock"
    
    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000
    
    # Azure OpenAI settings
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_endpoint: str = ""
    azure_openai_deployment_name: str = ""
    azure_openai_temperature: float = 0.7
    azure_openai_max_tokens: int = 2000


class ServerConfig(BaseSettings):
    """서버 설정"""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


def load_config():
    """config.yml 및 환경변수에서 설정을 로드합니다."""
    backend_cfg: dict[str, Any] = {}
    service_cfg: dict[str, Any] = {}

    if BACKEND_CONFIG_FILE.exists():
        with open(BACKEND_CONFIG_FILE, "r", encoding="utf-8") as f:
            backend_cfg = yaml.safe_load(f) or {}

    if SERVICE_CONFIG_FILE.exists():
        with open(SERVICE_CONFIG_FILE, "r", encoding="utf-8") as f:
            service_cfg = yaml.safe_load(f) or {}

    # 중요:
    # - LLM 설정은 `backend/config.yml`에서 공용으로 제어(서비스별 override는 기본적으로 비권장)
    # - 서버 설정(host/port/CORS)은 `chatbot-service/config.yml`로 서비스별 override 가능
    config_data = dict(backend_cfg)
    
    # LLM 설정 추출
    # - backend/config.yml 우선(공용/강제)
    # - backend 설정이 없으면 service config.yml로 fallback(로컬 기본값)
    llm_data = (backend_cfg.get("llm") or service_cfg.get("llm") or {})
    provider = llm_data.get("provider", "mock")
    
    # OpenAI 설정
    openai_data = llm_data.get("openai", {})
    openai_api_key = os.getenv(
        "OPENAI_API_KEY",
        openai_data.get("api_key", "").replace("${OPENAI_API_KEY}", os.getenv("OPENAI_API_KEY", ""))
    )
    
    # Azure OpenAI 설정
    azure_data = llm_data.get("azure_openai", {})
    azure_openai_api_key = os.getenv(
        "AZURE_OPENAI_API_KEY",
        azure_data.get("api_key", "").replace("${AZURE_OPENAI_API_KEY}", os.getenv("AZURE_OPENAI_API_KEY", ""))
    )
    azure_openai_endpoint = os.getenv(
        "AZURE_OPENAI_ENDPOINT",
        azure_data.get("endpoint", "").replace("${AZURE_OPENAI_ENDPOINT}", os.getenv("AZURE_OPENAI_ENDPOINT", ""))
    )
    azure_openai_deployment_name = os.getenv(
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        azure_data.get("deployment_name", "").replace("${AZURE_OPENAI_DEPLOYMENT_NAME}", os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", ""))
    )
    azure_openai_api_version = os.getenv(
        "AZURE_OPENAI_API_VERSION",
        azure_data.get("api_version", "").replace("${AZURE_OPENAI_API_VERSION:-2024-12-01-preview}", os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"))
    )
    # api_version이 비었거나 템플릿 문자열이면 기본값 사용
    if not azure_openai_api_version or "${" in azure_openai_api_version:
        azure_openai_api_version = "2024-12-01-preview"
    
    llm_config = LLMConfig(
        provider=provider,
        openai_api_key=openai_api_key,
        openai_model=openai_data.get("model", "gpt-4o-mini"),
        openai_base_url=openai_data.get("base_url", "https://api.openai.com/v1"),
        openai_temperature=openai_data.get("temperature", 0.7),
        openai_max_tokens=openai_data.get("max_tokens", 2000),
        azure_openai_api_key=azure_openai_api_key,
        azure_openai_api_version=azure_openai_api_version,
        azure_openai_endpoint=azure_openai_endpoint,
        azure_openai_deployment_name=azure_openai_deployment_name,
        azure_openai_temperature=azure_data.get("temperature", 0.7),
        azure_openai_max_tokens=azure_data.get("max_tokens", 2000),
    )

    # 실습용 fallback: 인증정보가 없으면 mock 모드로 동작
    if llm_config.provider == "openai" and not llm_config.openai_api_key:
        llm_config.provider = "mock"
    if llm_config.provider == "azure_openai":
        if not (llm_config.azure_openai_api_key and llm_config.azure_openai_endpoint and llm_config.azure_openai_deployment_name):
            llm_config.provider = "mock"
    
    # 서버 설정 추출(backend -> service merge; service가 우선)
    server_data = _deep_merge(backend_cfg.get("server", {}) or {}, service_cfg.get("server", {}) or {})
    server_config = ServerConfig(
        host=server_data.get("host", "0.0.0.0"),
        port=server_data.get("port", 8000),
        cors_origins=server_data.get("cors_origins", ["http://localhost:5173", "http://localhost:3000"]),
    )
    
    return llm_config, server_config


# 전역 설정 인스턴스
llm_config, server_config = load_config()

