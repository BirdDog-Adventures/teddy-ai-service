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

# Database Setup - Handle different database types
def create_database_engine():
    """Create database engine with appropriate parameters based on database type"""
    database_url = settings.DATABASE_URL
    
    # Check if it's SQLite
    if database_url.startswith('sqlite'):
        # SQLite doesn't support pool_size and max_overflow
        return create_engine(
            database_url,
            pool_pre_ping=True,
        )
    else:
        # PostgreSQL and other databases
        return create_engine(
            database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
        )

engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Configure schema for all models if specified
if settings.DATABASE_SCHEMA:
    Base.metadata.schema = settings.DATABASE_SCHEMA

# Redis Setup - Handle disabled Redis gracefully
redis_client = None
if settings.REDIS_URL and settings.REDIS_URL.strip():
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Test connection
        redis_client.ping()
    except (redis.RedisError, Exception):
        redis_client = None


def get_db() -> Generator[Session, None, None]:
    """Get PostgreSQL database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> Optional[redis.Redis]:
    """Get Redis client (returns None if Redis is disabled)"""
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
        # If Redis is disabled, skip rate limiting
        if not self.redis:
            return True
            
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
    
    def __init__(self, redis_client: Optional[redis.Redis] = redis_client):
        self.redis = redis_client
        self.default_ttl = settings.REDIS_CACHE_TTL
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.redis:
            return None
        try:
            return self.redis.get(key)
        except redis.RedisError:
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.redis:
            return False
        try:
            ttl = ttl or self.default_ttl
            return self.redis.setex(key, ttl, value)
        except redis.RedisError:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis:
            return False
        try:
            return bool(self.redis.delete(key))
        except redis.RedisError:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis:
            return False
        try:
            return bool(self.redis.exists(key))
        except redis.RedisError:
            return False


# Create cache instance
cache = Cache()


def get_optional_current_user():
    """
    Optional authentication dependency that returns user if authentication is enabled,
    otherwise returns mock demo user for development/demo mode
    """
    from api.core.security import get_current_user
    
    if settings.ENABLE_AUTHENTICATION:
        # Return the actual dependency function for authentication
        return get_current_user
    else:
        # Return a function that provides mock demo user
        def demo_user():
            return {
                "id": "demo-user",
                "email": "demo@example.com",
                "role": "user",
                "is_active": True
            }
        return demo_user
