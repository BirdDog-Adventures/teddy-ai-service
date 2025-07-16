# Troubleshooting Chat Endpoint Internal Server Error

## Current Status

The Teddy AI Service is running successfully with:
- ✅ Authentication working (register/login endpoints functional)
- ✅ Database connected with pgvector support
- ✅ OpenAI API key configured and working (verified via standalone script)
- ❌ Chat endpoint returning 500 Internal Server Error

## Verified Working Components

1. **OpenAI API Key**: Confirmed working via `scripts/test_openai.py`
2. **Authentication**: JWT tokens are being generated and validated correctly
3. **Database**: All tables created successfully with proper schema

## Potential Issues to Investigate

### 1. Check Server Logs
The actual error details will be in the terminal where the service is running. Look for:
- Stack traces after the 500 error
- Specific error messages about missing dependencies or configuration

### 2. Common Causes of Chat Endpoint Errors

#### a) Redis Connection Issue
The chat endpoint uses Redis for caching. Check if Redis is running:
```bash
redis-cli ping
```

If not running, start Redis:
```bash
# macOS
brew services start redis

# or manually
redis-server
```

#### b) Async/Await Issues
The chat endpoint uses async functions. The error might be related to:
- Missing `await` keywords
- Synchronous code in async context
- Event loop issues

#### c) Rate Limiter Configuration
The endpoint uses a rate limiter that might need Redis. To temporarily disable it for testing:
1. Comment out the rate limiting line in the chat endpoint
2. Or ensure Redis is running

### 3. Debugging Steps

#### Step 1: Check the Terminal Logs
Look at the terminal where `uvicorn` is running. The actual error will be displayed there.

#### Step 2: Test Without Rate Limiting
Temporarily modify `api/endpoints/chat.py`:
```python
# Comment out this line:
# await rate_limiter(str(current_user.id))
```

#### Step 3: Test Simple Endpoint
Try the test endpoint first:
```bash
curl -X GET http://localhost:8000/api/v1/test/test \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Step 4: Enable Debug Mode
In `.env`, set:
```
DEBUG=true
LOG_LEVEL=DEBUG
```

Then restart the service.

### 4. Quick Fixes to Try

#### Fix 1: Install Redis (if not installed)
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
```

#### Fix 2: Disable Rate Limiting (Temporary)
In `api/core/dependencies.py`, modify the rate_limiter to be a no-op:
```python
async def rate_limiter(key: str):
    # Temporarily disabled
    pass
```

#### Fix 3: Check Snowflake Connection
The error might be from Snowflake initialization. Temporarily disable Snowflake in the chat flow.

### 5. Getting Detailed Error Information

To see the exact error:

1. **Check the terminal** where the service is running
2. **Look for the stack trace** after the 500 error
3. **Copy the error message** - it will indicate the exact issue

Common error patterns:
- `ConnectionError`: Redis not running
- `ImportError`: Missing dependency
- `AttributeError`: Code issue
- `TypeError`: Async/await mismatch

### 6. Alternative Testing Approach

Create a minimal chat endpoint for testing:
```python
@router.post("/test-chat")
async def test_chat(current_user: models.User = Depends(get_current_active_user)):
    return {"message": "Chat endpoint accessible", "user": current_user.email}
```

## Next Steps

1. **Check the terminal logs** for the actual error
2. **Start Redis** if not running
3. **Try the debugging steps** above
4. **Share the error message** from the terminal for specific help

The most likely cause is Redis not running, as the chat endpoint uses it for rate limiting and caching.
