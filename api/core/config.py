"""
Configuration settings for Teddy AI Service
"""
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Teddy AI Service"
    DEBUG: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                # Handle JSON array format
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    # If JSON parsing fails, fall back to comma-separated
                    return [i.strip() for i in v.split(",")]
            else:
                # Handle comma-separated format
                return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENABLE_AUTHENTICATION: bool = True  # Set to False for development/demo

    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # openai, anthropic, google, ollama, azure
    LLM_MODEL: str = "gpt-3.5-turbo"
    MAX_TOKENS: int = 4000
    TEMPERATURE: float = 0.7
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_BASE_URL: Optional[str] = None  # For custom endpoints
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Google Configuration
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-pro"
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_DEPLOYMENT_NAME: Optional[str] = None
    
    # Ollama Configuration (for local models)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    
    # Embedding Configuration
    EMBEDDING_PROVIDER: str = "openai"  # openai, sentence-transformers
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Database Configuration
    DATABASE_URL: str
    DATABASE_SCHEMA: Optional[str] = None  # PostgreSQL schema name (e.g., 'teddy_ai')
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
    REDIS_URL: Optional[str] = None
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
