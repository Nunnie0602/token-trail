from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 200
    ollama_host: str = "http://localhost:11434"
    log_level: str = "INFO"
    log_step_cache_hit: bool = True
    cors_origins: str = "http://localhost:3000"
    prefetch_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
