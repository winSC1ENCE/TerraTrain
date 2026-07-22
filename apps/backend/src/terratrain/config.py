from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]
    # Matches http(s)://localhost:<port> and http(s)://127.0.0.1:<port>
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://terratrain:terratrain@localhost:5432/terratrain"
    )
    database_pool_size: int = 10
    database_pool_max_overflow: int = 20

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen2.5:14b"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_request_timeout: int = 180
    ollama_max_agent_turns: int = 6

    # LLM / Embedding Providers
    # "ollama" or "gemini"
    llm_provider: str = "ollama"
    embedding_provider: str = "ollama"

    # Gemini
    gemini_api_key: str = ""
    gemini_chat_model: str = "models/gemini-3.5-flash"
    gemini_embed_model: str = "models/gemini-embedding-001"
    gemini_api_base: str = "https://generativelanguage.googleapis.com/v1beta/openai"

    @property
    def resolved_llm_provider(self) -> str:
        if self.llm_provider == "ollama" and self.gemini_api_key:
            return "gemini"
        return self.llm_provider

    @property
    def resolved_embedding_provider(self) -> str:
        if self.embedding_provider == "ollama" and self.gemini_api_key:
            return "gemini"
        return self.embedding_provider

    # Intervals.icu
    intervals_api_base_url: str = "https://intervals.icu/api/v1"

    # Security
    secret_key: str = "change-me"
    encryption_key: str = "change-me"

    # Auth / JWT sessions
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    access_token_cookie_name: str = "terratrain_access"
    refresh_token_cookie_name: str = "terratrain_refresh"
    # Double-submit CSRF token: readable by JS (NOT httpOnly), echoed back as a
    # header on state-changing requests and compared server-side.
    csrf_cookie_name: str = "terratrain_csrf"
    csrf_header_name: str = "X-CSRF-Token"
    # Explicit override for the Secure cookie flag; None => resolve from app_env.
    secure_cookies_override: bool | None = None

    @property
    def secure_cookies(self) -> bool:
        """Cookies require HTTPS in production; disabled for local http development."""
        if self.secure_cookies_override is not None:
            return self.secure_cookies_override
        return self.app_env == "production"

    # Initial admin seed (first boot only, if no admin user exists)
    initial_admin_email: str = "admin@terratrain.app"

    # RAG
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 5
    data_dir: str = "/data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
