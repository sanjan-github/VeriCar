import os


class Settings:
    """Runtime configuration loaded from environment variables."""

    app_name: str = os.getenv("APP_NAME", "VeriCar")
    app_env: str = os.getenv("APP_ENV", "development")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))

    hindsight_base_url: str = os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888")
    hindsight_api_key: str = os.getenv("HINDSIGHT_API_KEY", "")
    hindsight_timeout: float = float(os.getenv("HINDSIGHT_TIMEOUT", "30"))
    hindsight_startup_check: bool = os.getenv("HINDSIGHT_STARTUP_CHECK", "false").lower() == "true"

    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    groq_timeout: float = float(os.getenv("GROQ_TIMEOUT", "20"))


settings = Settings()
