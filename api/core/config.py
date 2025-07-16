"""
Configuration settings for Teddy AI Service
"""
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Teddy AI Service"
    DEBUG: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    MAX_TOKENS: int = 4000
    TEMPERATURE: float = 0.7

    # Database Configuration
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40

    # Snowflake Configuration
    SNOWFLAKE_ACCOUNT: str
    SNOWFLAKE_USER: str
    SNOWFLAKE_PASSWORD: Optional[str] = None
    SNOWFLAKE_PRIVATE_KEY_PATH: Optional[str] = None
    SNOWFLAKE_DATABASE: str = "BIRDDOG_DATA"
    SNOWFLAKE_SCHEMA: str = "CURATED"
    SNOWFLAKE_WAREHOUSE: str = "BIRDDOG_WH"
    SNOWFLAKE_ROLE: str = "DATAENGINEERINGADMIN"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # External APIs
    USDA_API_KEY: Optional[str] = None
    WEATHER_API_KEY: Optional[str] = None
    MAPBOX_ACCESS_TOKEN: Optional[str] = None
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    # Vector Database
    VECTOR_DB_URL: str
    EMBEDDING_DIMENSION: int = 1536

    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
