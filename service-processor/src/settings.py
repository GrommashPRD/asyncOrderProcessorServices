import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    RABBIT_HOST: str
    RABBIT_PORT: int
    RABBIT_USER: str
    RABBIT_PASS: str
    RABBIT_VHOST: str

    ORDER_CREATED_EXCHANGE: str
    ORDER_CREATED_ROUTING_KEY: str

    ORDER_PROCESSED_EXCHANGE: str
    ORDER_PROCESSED_ROUTING_KEY: str

    PROCESSING_SUCCESS_RATE: float
    MAX_RETRY_ATTEMPTS: int
    RETRY_DELAY_BASE_SECONDS: int
    DLX_NAME: str
    DLQ_NAME: str
    
    LOG_LEVEL: str

    model_config = SettingsConfigDict(
        env_file=".env.dev_processor_example" if Path(".env.dev_processor_example").exists() and not os.getenv("DOCKER_ENV") else None,
        env_file_encoding="utf-8",
    )


settings = Settings()
