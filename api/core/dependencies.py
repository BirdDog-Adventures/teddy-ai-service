"""
Common dependencies for the API
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import redis
from snowflake.connector import connect as snowflake_connect
from snowflake.connector.connection import SnowflakeConnection

from api.core.config import settings

# PostgreSQL Database Setup
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis Setup
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_db() -> Generator[Session, None, None]:
    """Get PostgreSQL database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> redis.Redis:
    """Get Redis client"""
    return redis_client


def get_snowflake_connection() -> Generator[SnowflakeConnection, None, None]:
    """Get Snowflake connection"""
    conn = None
    try:
        conn = snowflake_connect(
            account=settings.SNOWFLAKE_ACCOUNT,
            user=settings.SNOWFLAKE_USER,
            password=settings.SNOWFLAKE_PASSWORD,
            database=settings.SNOWFLAKE_DATABASE,
            schema=settings.SNOWFLAKE_SCHEMA,
            warehouse=settings.SNOWFLAKE_WAREHOUSE,
            role=settings.SNOWFLAKE_ROLE,
        )
        yield conn
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to Snowflake: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


class RateLimiter:
    """Rate limiting dependency"""
    
    def __init__(self, requests: int = settings.RATE_LIMIT_REQUESTS, 
                 period: int = settings.RATE_LIMIT_PERIOD):
        self.requests = requests
        self.period = period
        self.redis = redis_client
    
    async def __call__(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        key = f"rate_limit:{user_id}"
        
        try:
            current = self.redis.incr(key)
            if current == 1:
                self.redis.expire(key, self.period)
            
            if current > self.requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {self.period} seconds."
                )
            
            return True
        except redis.RedisError:
            # If Redis is down, allow the request
            return True


# Create rate limiter instance
rate_limiter = RateLimiter()


class Cache:
    """Cache dependency for storing temporary data"""
    
    def __init__(self, redis_client: redis.Redis = redis_client):
        self.redis = redis_client
        self.default_ttl = settings.REDIS_CACHE_TTL
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return self.redis.get(key)
        except redis.RedisError:
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.default_ttl
            return self.redis.setex(key, ttl, value)
        except redis.RedisError:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            return bool(self.redis.delete(key))
        except redis.RedisError:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return bool(self.redis.exists(key))
        except redis.RedisError:
            return False


# Create cache instance
cache = Cache()
