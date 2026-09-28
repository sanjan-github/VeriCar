import os


class Settings:
    """Runtime configuration loaded from environment variables."""

    app_name: str = os.getenv("APP_NAME", "VeriCar")
    app_env: str = os.getenv("APP_ENV", "development")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()
