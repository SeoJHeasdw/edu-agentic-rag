"""
Configuration management for the chatbot backend.
Supports both OpenAI and Azure OpenAI providers.
"""
import os
import yaml
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the base directory (chatbot-service directory)
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yml"


class LLMConfig(BaseSettings):
    """LLM provider configuration"""
    provider: Literal["openai", "azure_openai"] = "openai"
    
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
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


def load_config():
    """Load configuration from config.yml and environment variables"""
    config_data = {}
    
    # Load YAML config if exists
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
    
    # Extract LLM config
    llm_data = config_data.get("llm", {})
    provider = llm_data.get("provider", "openai")
    
    # Get OpenAI config
    openai_data = llm_data.get("openai", {})
    openai_api_key = os.getenv(
        "OPENAI_API_KEY",
        openai_data.get("api_key", "").replace("${OPENAI_API_KEY}", os.getenv("OPENAI_API_KEY", ""))
    )
    
    # Get Azure OpenAI config
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
    # If api_version is still empty or contains the template string, use default
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
    
    # Extract server config
    server_data = config_data.get("server", {})
    server_config = ServerConfig(
        host=server_data.get("host", "0.0.0.0"),
        port=server_data.get("port", 8000),
        cors_origins=server_data.get("cors_origins", ["http://localhost:5173", "http://localhost:3000"]),
    )
    
    return llm_config, server_config


# Global config instances
llm_config, server_config = load_config()

