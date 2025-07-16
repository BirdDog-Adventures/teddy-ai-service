# Teddy AI Service - Authentication Guide

## Overview

The Teddy AI Service uses JWT (JSON Web Token) based authentication. All API endpoints except `/health`, `/docs`, and authentication endpoints require a valid JWT token.

## Authentication Flow

1. **Register** a new user account
2. **Login** with email and password to receive a JWT token
3. **Include** the token in the Authorization header for all subsequent requests

## API Endpoints

### 1. Register a New User

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "viewer",
  "is_active": true,
  "created_at": "2025-01-16T10:00:00Z"
}
```

### 2. Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body (form-data):**
```
username: user@example.com
password: securepassword123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Get Current User Info

**Endpoint:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <your-access-token>
```

**Response:**
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "viewer",
  "is_active": true,
  "created_at": "2025-01-16T10:00:00Z"
}
```

### 4. Refresh Token

**Endpoint:** `POST /api/v1/auth/refresh`

**Headers:**
```
Authorization: Bearer <your-access-token>
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Using Authentication in Requests

After logging in, include the JWT token in the Authorization header:

```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer <your-access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about soil quality analysis",
    "conversation_type": "general"
  }'
```

## Python Example

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# 1. Register
register_data = {
    "email": "test@example.com",
    "password": "testpassword123",
    "first_name": "Test",
    "last_name": "User"
}
response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
print(f"Registration: {response.status_code}")

# 2. Login
login_data = {
    "username": "test@example.com",
    "password": "testpassword123"
}
response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
token_data = response.json()
access_token = token_data["access_token"]

# 3. Use authenticated endpoint
headers = {"Authorization": f"Bearer {access_token}"}
chat_data = {
    "message": "Hello, can you help me?",
    "conversation_type": "general"
}
response = requests.post(
    f"{BASE_URL}/chat/message", 
    json=chat_data,
    headers=headers
)
print(f"Chat response: {response.json()}")
```

## JavaScript/Fetch Example

```javascript
// Register
const registerResponse = await fetch('http://localhost:8000/api/v1/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'test@example.com',
    password: 'testpassword123',
    first_name: 'Test',
    last_name: 'User'
  })
});

// Login
const formData = new FormData();
formData.append('username', 'test@example.com');
formData.append('password', 'testpassword123');

const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  body: formData
});

const { access_token } = await loginResponse.json();

// Use authenticated endpoint
const chatResponse = await fetch('http://localhost:8000/api/v1/chat/message', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Hello, can you help me?',
    conversation_type: 'general'
  })
});
```

## Token Details

- **Token Type:** JWT (JSON Web Token)
- **Algorithm:** HS256
- **Expiration:** 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Claims:** 
  - `sub`: User email
  - `user_id`: User UUID
  - `exp`: Expiration timestamp

## User Roles

The system supports the following user roles:
- `viewer` - Default role, read-only access
- `landowner` - Property owner with full access to their properties
- `farmer` - Agricultural professional with specific permissions
- `hunter` - Hunting lease holder with limited access
- `admin` - Full system access

## Security Best Practices

1. **Never share your JWT token** - Treat it like a password
2. **Use HTTPS in production** - Tokens should only be transmitted over secure connections
3. **Store tokens securely** - In web apps, use httpOnly cookies or secure storage
4. **Implement token refresh** - Use the refresh endpoint before tokens expire
5. **Logout properly** - Clear stored tokens when users log out

## Troubleshooting

### 401 Unauthorized
- Check if the token is included in the Authorization header
- Verify the token hasn't expired (30 minutes by default)
- Ensure the header format is correct: `Bearer <token>`

### 404 Not Found on Auth Endpoints
- Verify the service has restarted after adding auth endpoints
- Check the URL includes `/api/v1/auth/`

### Invalid Credentials
- Email is case-sensitive
- Password must match exactly
- User must be active (`is_active: true`)

## Testing with Swagger UI

1. Navigate to http://localhost:8000/docs
2. Use the `/auth/register` endpoint to create a user
3. Use the `/auth/login` endpoint to get a token
4. Click the "Authorize" button (lock icon)
5. Enter: `Bearer <your-token>`
6. Now all endpoints will include your authentication
