"""
Test endpoint for debugging
"""
from fastapi import APIRouter, Depends
from api.core.security import get_current_active_user
from api.models import database as models

router = APIRouter()

@router.get("/test")
async def test_endpoint(
    current_user: models.User = Depends(get_current_active_user)
):
    """Simple test endpoint"""
    return {
        "message": "Test successful!",
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": f"{current_user.first_name} {current_user.last_name}"
        }
    }

@router.get("/test-openai")
async def test_openai(
    current_user: models.User = Depends(get_current_active_user)
):
    """Test OpenAI connection"""
    try:
        from openai import OpenAI
        from api.core.config import settings
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            max_tokens=50
        )
        
        return {
            "success": True,
            "response": response.choices[0].message.content,
            "model": response.model
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
