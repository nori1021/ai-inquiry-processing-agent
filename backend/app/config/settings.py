from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config/settings.py → project root is parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ai-inquiry-processing-agent"
    app_env: str = "local"
    debug: bool = True

    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'app.db').as_posix()}"

    ldap_users_path: str = "data/sample/ldap_users.xlsx"
    gac_users_path: str = "data/sample/gac_users.xlsx"
    ldap_companies_path: str = "data/sample/ldap_companies.xlsx"

    similarity_threshold: float = 80.0

    # Confidence gate: values <= this threshold force human review
    confidence_review_threshold: float = 0.99

    # Default AI = local Ollama (zero paid API). Use "mock" for CI/offline.
    ai_provider: str = "ollama"
    approval_provider: str = "mock"
    email_provider: str = "mock"
    graph_enabled: bool = False
    teams_callback_secret: str = "dev-teams-callback-secret"
    teams_webhook_url: str = ""

    # Ollama (supported runtime on low-memory Windows)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    ollama_fallback_model: str = "qwen3:1.7b"
    ollama_temperature: float = 0.1
    ollama_num_ctx: int = 4096
    ollama_timeout_seconds: float = 300.0
    # Never silent-mock when using Ollama unless explicitly enabled (CI escape hatch)
    ollama_allow_mock_fallback: bool = False

    # Limited local RAG — never dump all history into context
    rag_top_k: int = 3

    # Workflow limits
    workflow_max_tool_calls: int = 20
    workflow_max_retries: int = 2
    workflow_step_timeout_seconds: float = 60.0

    # Optional paid APIs — NOT required for MVP; kept for interface swap only
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: float = 30.0

    def resolve_path(self, relative_or_absolute: str) -> Path:
        path = Path(relative_or_absolute)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    @property
    def ldap_users_file(self) -> Path:
        return self.resolve_path(self.ldap_users_path)

    @property
    def gac_users_file(self) -> Path:
        return self.resolve_path(self.gac_users_path)

    @property
    def ldap_companies_file(self) -> Path:
        return self.resolve_path(self.ldap_companies_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
