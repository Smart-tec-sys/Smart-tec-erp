# -*- coding: utf-8 -*-
from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SmartTec ERP"
    APP_VERSION: str = "0.1.0"
    DB_URL: str = "sqlite:///./smarttec.db"
    CORS_ALLOWED: list = ["*"]
    AUTO_CREATE_SCHEMA: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
