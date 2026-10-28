from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки читаются из переменных окружения или файла .env."""

    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg://booking:booking@localhost:5432/booking"


settings = Settings()
