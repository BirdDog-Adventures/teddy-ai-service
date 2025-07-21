"""
Chat endpoint for conversational AI interface
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import logging
import json
from decimal import Decimal

from api.core.dependencies import get_db, cache, rate_limiter, get_optional_current_user
from api.core.security import get_current_active_user
from api.models import database as models
from api.models import schemas
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter()

# Services will be initialized lazily
_llm_service = None
_embedding_service = None

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

def get_embedding_service():
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def _convert_decimals_to_float(obj):
    """Recursively convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: _convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_float(item) for item in obj]
    else:
        return obj


@router.post("/message", response_model=schemas.ChatResponse)
async def send_message(
    request: schemas.ChatRequest,
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Send a message to the AI assistant"""
    try:
        from api.core.config import settings
        
        # Rate limiting (skip in demo mode)
        if settings.ENABLE_AUTHENTICATION:
            await rate_limiter(str(current_user.id))
        
        # Handle conversation management based on authentication mode
        conversation_id = None
        conversation_history = []
        
        if settings.ENABLE_AUTHENTICATION:
            # Full database-backed conversation management
            if request.conversation_id:
                conversation = db.query(models.Conversation).filter(
                    models.Conversation.id == request.conversation_id,
                    models.Conversation.user_id == current_user.id
                ).first()
                
                if not conversation:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Conversation not found"
                    )
            else:
                # Create new conversation
                conversation = models.Conversation(
                    user_id=current_user.id,
                    conversation_type=request.conversation_type,
                    property_id=request.property_id,
                    meta_data=request.context or {}
                )
                db.add(conversation)
                db.commit()
                db.refresh(conversation)
            
            # Save user message
            user_message = models.Message(
                conversation_id=conversation.id,
                role="user",
                content=request.message,
                meta_data=request.context or {}
            )
            db.add(user_message)
            
            # Get conversation history
            messages = db.query(models.Message).filter(
                models.Message.conversation_id == conversation.id
            ).order_by(models.Message.created_at).all()
            
            # Prepare context for LLM
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            conversation_id = str(conversation.id)
        else:
            # Demo mode - simple conversation without database persistence
            conversation_id = request.conversation_id or "demo-conversation"
            # In demo mode, we only have the current message
            conversation_history = [{"role": "user", "content": request.message}]
        
        # Add system prompt based on conversation type
        system_prompt = _get_system_prompt(request.conversation_type, request.property_id)
        
        # Get property context if discussing specific property
        property_context = None
        if request.property_id:
            property_context = await _get_property_context(request.property_id, db)
        
        # Get user preferences (skip in demo mode)
        user_preferences = None
        if settings.ENABLE_AUTHENTICATION:
            user_preferences = await _get_user_preferences(current_user.id, db)
        
        # Generate AI response
        ai_response, sources = await get_llm_service().generate_response(
            conversation_history=conversation_history,
            system_prompt=system_prompt,
            property_context=property_context,
            user_preferences=user_preferences
        )
        
        # Save AI response to database (only if authentication is enabled)
        if settings.ENABLE_AUTHENTICATION:
            # Save AI response (convert Decimal objects to float for JSON serialization)
            clean_sources = _convert_decimals_to_float(sources) if sources else None
            assistant_message = models.Message(
                conversation_id=conversation.id,
                role="assistant",
                content=ai_response,
                meta_data={"sources": clean_sources} if clean_sources else {}
            )
            db.add(assistant_message)
            
            # Update conversation
            conversation.updated_at = assistant_message.created_at
            db.commit()
        
        # Generate suggestions
        suggestions = await _generate_suggestions(
            request.conversation_type,
            ai_response,
            property_context
        )
        
        return schemas.ChatResponse(
            conversation_id=conversation_id,
            response=ai_response,
            sources=sources,
            suggestions=suggestions,
            metadata={
                "conversation_type": request.conversation_type,
                "property_id": request.property_id,
                "demo_mode": not settings.ENABLE_AUTHENTICATION
            }
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.get("/history/{conversation_id}", response_model=schemas.ConversationHistory)
async def get_conversation_history(
    conversation_id: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversation history"""
    try:
        # Validate conversation ownership
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get messages
        messages = db.query(models.Message).filter(
            models.Message.conversation_id == conversation.id
        ).order_by(models.Message.created_at).all()
        
        # Convert to response format
        chat_messages = [
            schemas.ChatMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.created_at,
                metadata=msg.meta_data
            )
            for msg in messages
        ]
        
        return schemas.ConversationHistory(
            conversation_id=str(conversation.id),
            messages=chat_messages,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at or conversation.created_at,
            conversation_type=conversation.conversation_type,
            metadata=conversation.meta_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation history"
        )


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation"""
    try:
        # Validate conversation ownership
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Delete conversation (messages will cascade)
        db.delete(conversation)
        db.commit()
        
        return {"success": True, "message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )


def _get_system_prompt(conversation_type: str, property_id: Optional[str] = None) -> str:
    """Get system prompt based on conversation type"""
    base_prompt = """You are Teddy, an AI assistant for BirdDog's land intelligence platform. 
    You help landowners, farmers, and hunters make informed decisions about rural properties.
    You have access to property data, soil information, agricultural insights, and market trends.
    Be helpful, accurate, and provide actionable insights."""
    
    type_prompts = {
        "general": "Answer questions about land management, agriculture, and property optimization.",
        "property_inquiry": f"You are discussing property {property_id}. Provide detailed insights about this specific property.",
        "soil_analysis": "Focus on soil quality, composition, and agricultural potential.",
        "crop_recommendation": "Provide crop recommendations based on soil, climate, and market conditions.",
        "lease_assistance": "Help with agricultural lease terms, pricing, and negotiations.",
        "tax_optimization": "Provide information about Section 180 tax deductions and other agricultural tax benefits."
    }
    
    return f"{base_prompt}\n\n{type_prompts.get(conversation_type, type_prompts['general'])}"


async def _get_property_context(property_id: str, db: Session) -> Optional[dict]:
    """Get property context from cache or database"""
    # Check cache first
    cache_key = f"property_context:{property_id}"
    cached_context = await cache.get(cache_key)
    
    if cached_context:
        import json
        return json.loads(cached_context)
    
    # Fetch from Snowflake database
    try:
        from data_connectors.snowflake_connector import SnowflakeConnector
        snowflake_connector = SnowflakeConnector()
        
        # Get property boundaries and basic info
        property_data = await snowflake_connector.get_property_boundaries(property_id)
        if not property_data:
            return None
        
        # Build context from real data using correct column names
        context = {
            "property_id": property_id,
            "parcel_id": property_data.get("PARCEL_ID"),
            "address": property_data.get("ADDRESS"),
            "city": property_data.get("CITY"),
            "state": property_data.get("STATE_CODE"),
            "county": property_data.get("COUNTY_ID"),
            "zip_code": property_data.get("ZIP_CODE"),
            "acreage": property_data.get("ACRES"),
            "total_value": property_data.get("TOTAL_VALUE"),
            "land_value": property_data.get("LAND_VALUE"),
            "improvement_value": property_data.get("IMPROVEMENT_VALUE"),
            "owner_name": property_data.get("OWNER_NAME"),
            "use_code": property_data.get("USECODE"),
            "use_description": property_data.get("USEDESC"),
            "zoning": property_data.get("ZONING"),
            "zoning_description": property_data.get("ZONING_DESCRIPTION")
        }
        
        # Cache for future use
        import json
        await cache.set(cache_key, json.dumps(context), ttl=3600)
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting property context for {property_id}: {str(e)}", exc_info=True)
        return None


async def _get_user_preferences(user_id: str, db: Session) -> Optional[dict]:
    """Get user preferences"""
    prefs = db.query(models.UserPreference).filter(
        models.UserPreference.user_id == user_id
    ).first()
    
    if prefs:
        return {
            "preferred_crops": prefs.preferred_crops,
            "preferred_locations": prefs.preferred_locations,
            "acreage_range": {
                "min": prefs.min_acreage,
                "max": prefs.max_acreage
            }
        }
    
    return None


async def _generate_suggestions(
    conversation_type: str,
    ai_response: str,
    property_context: Optional[dict]
) -> Optional[list]:
    """Generate follow-up suggestions"""
    suggestions = {
        "general": [
            "Tell me about soil quality analysis",
            "What crops are best for my region?",
            "How can I optimize my land revenue?"
        ],
        "property_inquiry": [
            "What crops would grow best here?",
            "What's the lease value for this property?",
            "Is this property eligible for Section 180?"
        ],
        "soil_analysis": [
            "What amendments would improve soil quality?",
            "Compare with nearby properties",
            "Show historical soil data"
        ],
        "crop_recommendation": [
            "What's the expected yield?",
            "Show market prices for these crops",
            "What's the planting calendar?"
        ],
        "lease_assistance": [
            "Generate a lease agreement template",
            "What are typical lease terms in this area?",
            "How do I find qualified farmers?"
        ],
        "tax_optimization": [
            "Calculate my Section 180 deduction",
            "What documentation do I need?",
            "Show other tax incentives"
        ]
    }
    
    return suggestions.get(conversation_type, suggestions["general"])
