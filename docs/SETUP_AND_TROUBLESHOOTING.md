# Teddy AI Service - Setup and Troubleshooting Guide

## Overview

This document details the setup process and troubleshooting steps taken to successfully launch the Teddy AI Service. The service is now running on **http://0.0.0.0:8000** with full functionality.

## Issues Resolved

### 1. Configuration Issues ✅

#### Problem
- Pydantic validation errors due to missing `SNOWFLAKE_PASSWORD`
- Conflicting Snowflake authentication methods

#### Solution
- Made `SNOWFLAKE_PASSWORD` optional in the configuration
- Added support for `SNOWFLAKE_PRIVATE_KEY_PATH` for key-based authentication
- Updated the Snowflake connector to support both password and private key authentication methods

```python
# In api/core/config.py
SNOWFLAKE_PASSWORD: Optional[str] = None
SNOWFLAKE_PRIVATE_KEY_PATH: Optional[str] = None
```

### 2. Database Model Issues ✅

#### Problem
- SQLAlchemy error: "Attribute name 'metadata' is reserved"
- Missing VECTOR type in SQLAlchemy
- PostgreSQL missing pgvector extension

#### Solution
- Renamed all `metadata` columns to `meta_data` to avoid conflicts with SQLAlchemy's reserved attribute
- Fixed Vector type imports to use `pgvector.sqlalchemy.Vector` instead of non-existent `sqlalchemy.dialects.postgresql.VECTOR`
- Created pgvector extension in PostgreSQL:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Missing Dependencies ✅

#### Problem
Multiple missing Python packages causing import errors during startup.

#### Solution
Installed all required packages:

```bash
pip install pydantic-settings
pip install psycopg2-binary
pip install "python-jose[cryptography]"
pip install "passlib[bcrypt]==1.7.4"
pip install redis
pip install fastapi
pip install "uvicorn[standard]"
pip install openai==1.96.1
pip install tenacity==8.2.3
pip install pgvector==0.2.4
pip install pandas==2.2.2
```

**Note**: For Python 3.13 compatibility, psycopg2-binary was installed from source.

### 4. Service Initialization Issues ✅

#### Problem
- Services being instantiated at module level causing initialization errors
- OpenAI client initialization failing due to version mismatch

#### Solution
- Implemented lazy initialization for LLM and embedding services:

```python
# Services will be initialized lazily
_llm_service = None
_embedding_service = None

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
```

- Upgraded OpenAI client to latest version (1.96.1)

### 5. Database Connection Issues ✅

#### Problem
- PostgreSQL not accessible on port 5433
- Vector database `birddog_vectors` didn't exist

#### Solution
- Ensured PostgreSQL was running on port 5433
- Updated `VECTOR_DB_URL` to use the same database as the main application:

```bash
# In .env
VECTOR_DB_URL=postgresql://postgres:KQS6pBSrFpFgO6Jo7sxy@localhost:5433/teddy_service_db
```

## Current Service Status

### Running Services
- ✅ FastAPI application on http://0.0.0.0:8000
- ✅ PostgreSQL database on localhost:5433
- ✅ All database tables created with pgvector support

### Available Endpoints

#### Authentication (`/api/v1/auth/`)
- `POST /register` - Register new user
- `POST /login` - Login and receive JWT token
- `POST /refresh` - Refresh access token

#### Chat (`/api/v1/chat/`)
- `POST /message` - Send message to AI assistant
- `GET /history/{conversation_id}` - Get conversation history
- `DELETE /conversation/{conversation_id}` - Delete conversation

#### Search (`/api/v1/search/`)
- `POST /properties` - Semantic property search
- `POST /insights` - Search for agricultural insights
- `GET /suggestions` - Get search suggestions

#### Insights (`/api/v1/insights/`)
- `GET /property/{property_id}` - Get property insights
- `GET /portfolio/{user_id}` - Get portfolio analysis
- `POST /compare` - Compare multiple properties

#### Recommendations (`/api/v1/recommendations/`)
- `GET /properties/{user_id}` - Get property recommendations
- `GET /crops/{property_id}` - Get crop recommendations
- `GET /revenue/{property_id}` - Get revenue optimization suggestions

## Testing the API

A test script is available at `scripts/test_api.py` that demonstrates:
1. User registration
2. Authentication
3. Making authenticated API calls

Run it with:
```bash
cd birddog-AI-services/teddy-ai-service
python scripts/test_api.py
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

Key environment variables in `.env`:
```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5433/teddy_service_db
VECTOR_DB_URL=postgresql://postgres:password@localhost:5433/teddy_service_db

# OpenAI
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4-turbo-preview
EMBEDDING_MODEL=text-embedding-3-small

# Snowflake (using private key auth)
SNOWFLAKE_ACCOUNT=JJODRXK-BIRDDOGAWS
SNOWFLAKE_USER=BIRDDOG_GEOVIEWER
SNOWFLAKE_PRIVATE_KEY_PATH="/path/to/rsa_key.p8"

# Redis
REDIS_URL=redis://localhost:6379/0
```

## Common Issues and Solutions

### Issue: "Address already in use"
**Solution**: Kill the process using the port
```bash
lsof -ti:8000 | xargs kill -9
```

### Issue: "type 'vector' does not exist"
**Solution**: Create pgvector extension in PostgreSQL
```bash
psql -d your_database -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Issue: "Module not found" errors
**Solution**: Ensure virtual environment is activated and all dependencies are installed
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Authentication returns 401
**Solution**: This is expected behavior. Register a user first, then login to get an access token.

## Next Steps

1. Configure Redis for caching (currently optional)
2. Set up proper SSL certificates for production
3. Configure monitoring and logging
4. Set up CI/CD pipeline
5. Create comprehensive test suite

## Support

For additional support or questions about the Teddy AI Service, please refer to:
- Architecture documentation: `ARCHITECTURE.md`
- API documentation: http://localhost:8000/docs
- Main README: `README.md`
