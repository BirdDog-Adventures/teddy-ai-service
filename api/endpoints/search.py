"""
Search endpoint for semantic property and insight search
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from api.core.dependencies import get_db, cache, get_optional_current_user
from api.core.security import get_current_active_user
from api.models import database as models
from api.models import schemas
from services.embedding_service import EmbeddingService
from services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter()

# Services will be initialized lazily
_embedding_service = None
_search_service = None

def get_embedding_service():
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

def get_search_service():
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service


@router.post("/properties", response_model=schemas.PropertySearchResponse)
async def search_properties(
    request: schemas.PropertySearchRequest,
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Semantic search for properties"""
    try:
        from api.core.config import settings
        
        # Log search history (only if authentication is enabled)
        if settings.ENABLE_AUTHENTICATION and current_user:
            search_history = models.SearchHistory(
                user_id=current_user.id,
                search_type="property",
                query=request.query,
                filters=request.filters or {}
            )
            db.add(search_history)
        
        # Perform search
        results = await get_search_service().search_properties(
            query=request.query,
            filters=request.filters,
            location=request.location,
            radius_miles=request.radius_miles,
            limit=request.limit,
            offset=request.offset
        )
        
        # Update search history with results count (only if authentication is enabled)
        if settings.ENABLE_AUTHENTICATION and current_user:
            search_history.results_count = len(results)
            db.commit()
        
        return schemas.PropertySearchResponse(
            results=results,
            total_count=len(results),  # TODO: Get actual total from search service
            facets=None  # TODO: Implement faceted search
        )
        
    except Exception as e:
        logger.error(f"Error in property search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search properties"
        )


@router.post("/insights", response_model=schemas.BaseResponse)
async def search_insights(
    request: schemas.InsightSearchRequest,
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Search for agricultural insights"""
    try:
        from api.core.config import settings
        
        # Log search history (only if authentication is enabled)
        if settings.ENABLE_AUTHENTICATION and current_user:
            search_history = models.SearchHistory(
                user_id=current_user.id,
                search_type="insight",
                query=request.query,
                filters={
                    "insight_types": request.insight_types,
                    "property_ids": request.property_ids,
                    "date_range": request.date_range
                }
            )
            db.add(search_history)
        
        # TODO: Implement insight search
        results = []
        
        # Update search history with results count (only if authentication is enabled)
        if settings.ENABLE_AUTHENTICATION and current_user:
            search_history.results_count = len(results)
            db.commit()
        
        return schemas.BaseResponse(
            success=True,
            message=f"Found {len(results)} insights"
        )
        
    except Exception as e:
        logger.error(f"Error in insight search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search insights"
        )


@router.get("/suggestions", response_model=schemas.BaseResponse)
async def get_search_suggestions(
    query: str,
    search_type: str = "property",
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on partial query"""
    try:
        from api.core.config import settings
        
        # TODO: Implement search suggestions
        suggestions = [
            f"{query} in Texas",
            f"{query} with high soil quality",
            f"{query} for lease"
        ]
        
        return schemas.BaseResponse(
            success=True,
            message="Search suggestions retrieved",
            metadata={"suggestions": suggestions}
        )
        
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get search suggestions"
        )
