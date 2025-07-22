# Database Schema Implementation Guide

## Overview

The Teddy AI Service has been updated to support configurable PostgreSQL schemas. This allows the application to use a custom schema (like `teddy-ai`) instead of the default `public` schema.

## 🔧 Changes Made

### 1. Configuration Updates

**File**: `api/core/config.py`
- Added `DATABASE_SCHEMA: Optional[str] = None` setting
- Supports environment variable `DATABASE_SCHEMA`

**File**: `api/core/dependencies.py`
- Added schema configuration to SQLAlchemy Base metadata
- Schema is applied to all database models when specified

```python
# Configure schema for all models if specified
if settings.DATABASE_SCHEMA:
    Base.metadata.schema = settings.DATABASE_SCHEMA
```

### 2. Database Setup

**File**: `scripts/setup_database.sql`
- Added `CREATE SCHEMA IF NOT EXISTS teddy_ai;`
- Added proper permissions for the schema
- Includes commented search path configuration

### 3. Environment Configuration

**Local Development** (`.env`):
```bash
DATABASE_SCHEMA=teddy-ai
```

**AWS Deployment**:
- `DATABASE_SCHEMA` environment variable is already configured in AWS Secrets Manager
- Retrieved from `arn:aws:secretsmanager:us-east-1:551565094761:secret:dev-teddy-ai-secrets-PBJ87M:DATABASE_SCHEMA::`

**Example Configuration** (`.env.example`):
```bash
DATABASE_SCHEMA=teddy-ai
```

## 🗄️ Schema Usage

### Current Behavior

| Environment | Schema Configuration | Actual Schema Used |
|-------------|---------------------|-------------------|
| **Local Dev** | `DATABASE_SCHEMA=teddy-ai` | `teddy-ai` |
| **AWS Dev** | From Secrets Manager | `teddy-ai` |
| **AWS Prod** | From Secrets Manager | `teddy-ai` |

### Backward Compatibility

- If `DATABASE_SCHEMA` is not set or empty, tables will be created in the default `public` schema
- Existing deployments without schema configuration will continue to work

## 📊 Database Tables

All PostgreSQL tables will be created in the specified schema:

### Authentication Tables (when `ENABLE_AUTHENTICATION=true`)
- `teddy_ai.users` - User accounts and profiles
- `teddy_ai.conversations` - Chat conversation metadata
- `teddy_ai.messages` - Individual chat messages

### Application Tables
- `teddy_ai.property_embeddings` - Vector embeddings for properties
- `teddy_ai.insight_embeddings` - Vector embeddings for insights
- `teddy_ai.property_insight_cache` - Cached property analysis results
- `teddy_ai.search_history` - User search history
- `teddy_ai.user_preferences` - User preference settings
- `teddy_ai.ml_model_metadata` - ML model information

## 🚀 Deployment Process

### Local Development Setup

1. **Create Schema**:
   ```sql
   psql -d teddy_service_db -f scripts/setup_database.sql
   ```

2. **Update Environment**:
   ```bash
   # In .env file
   DATABASE_SCHEMA=teddy_ai
   ```

3. **Run Application**:
   ```bash
   python -m uvicorn api.main:app --reload
   ```

### AWS Deployment

The schema configuration is already set up in AWS:

1. **Secrets Manager**: Contains `DATABASE_SCHEMA=teddy_ai`
2. **ECS Task Definition**: Pulls schema from secrets
3. **Application**: Automatically uses the configured schema

## 🔍 Verification

### Check Schema Usage

```sql
-- List all tables in teddy_ai schema
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname = 'teddy_ai';

-- Check current search path
SHOW search_path;

-- Verify table creation
\dt teddy_ai.*
```

### Application Logs

Look for SQLAlchemy table creation logs:
```
INFO: Creating tables in schema: teddy_ai
INFO: Table teddy_ai.users created successfully
```

## 🛠️ Troubleshooting

### Common Issues

1. **Schema Not Found**
   ```
   ERROR: schema "teddy_ai" does not exist
   ```
   **Solution**: Run `scripts/setup_database.sql` to create the schema

2. **Permission Denied**
   ```
   ERROR: permission denied for schema teddy_ai
   ```
   **Solution**: Grant proper permissions:
   ```sql
   GRANT ALL ON SCHEMA teddy_ai TO your_user;
   GRANT USAGE ON SCHEMA teddy_ai TO your_user;
   ```

3. **Tables in Wrong Schema**
   ```
   Tables created in 'public' instead of 'teddy_ai'
   ```
   **Solution**: Verify `DATABASE_SCHEMA` environment variable is set

### Debug Commands

```bash
# Check environment variable
echo $DATABASE_SCHEMA

# Verify database connection
python -c "from api.core.config import settings; print(f'Schema: {settings.DATABASE_SCHEMA}')"

# Test database connection
python -c "from api.core.dependencies import engine; print(engine.url)"
```

## 📈 Migration Notes

### From Public Schema to teddy_ai Schema

If you have existing data in the `public` schema:

1. **Export Data**:
   ```sql
   pg_dump -n public -t users -t conversations -t messages > backup.sql
   ```

2. **Update Schema References**:
   ```bash
   sed 's/public\./teddy_ai\./g' backup.sql > backup_teddy_ai.sql
   ```

3. **Import to New Schema**:
   ```sql
   psql -d teddy_service_db -f backup_teddy_ai.sql
   ```

### Zero-Downtime Migration

For production environments:

1. Create new schema alongside existing
2. Run application with new schema
3. Migrate data in background
4. Switch traffic to new schema
5. Remove old schema after verification

## 🔐 Security Considerations

### Schema Isolation

- Each application instance can use its own schema
- Provides logical separation of data
- Easier to manage permissions per application

### Recommended Permissions

```sql
-- Create dedicated user for teddy-ai
CREATE USER teddy_ai_user WITH PASSWORD 'secure_password';

-- Grant schema permissions
GRANT USAGE ON SCHEMA teddy_ai TO teddy_ai_user;
GRANT ALL ON ALL TABLES IN SCHEMA teddy_ai TO teddy_ai_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA teddy_ai TO teddy_ai_user;

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA teddy_ai 
GRANT ALL ON TABLES TO teddy_ai_user;
```

## 📝 Configuration Reference

### Environment Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DATABASE_SCHEMA` | PostgreSQL schema name | `teddy_ai` | No |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:port/db` | Yes |

### SQLAlchemy Configuration

The schema is applied at the metadata level:

```python
# All models inherit the schema
Base.metadata.schema = settings.DATABASE_SCHEMA

# Results in table names like: teddy_ai.users, teddy_ai.conversations
```

---

**Implementation Date**: July 21, 2025  
**Status**: ✅ Complete  
**Compatibility**: Backward compatible with existing deployments
