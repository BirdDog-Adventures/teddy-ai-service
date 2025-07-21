"""
Recommendations endpoint for personalized property and optimization suggestions
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from api.core.dependencies import get_db, cache, get_optional_current_user
from api.core.security import get_current_active_user
from api.models import database as models
from api.models import schemas
from services.crop_recommendation_service import CropRecommendationService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize crop recommendation service
crop_service = CropRecommendationService()


@router.get("/properties/{user_id}", response_model=schemas.RecommendationResponse)
async def get_property_recommendations(
    user_id: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get personalized property recommendations for a user"""
    try:
        # Verify access
        if str(current_user.id) != user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view these recommendations"
            )
        
        # TODO: Implement ML-based property recommendations
        mock_recommendations = [
            schemas.PropertyRecommendation(
                property_id="prop_456",
                score=92.5,
                reason="Matches your preferred acreage range and soil quality requirements",
                property_details={
                    "address": "456 Farm Road, Austin, TX",
                    "acreage": 750,
                    "price": "$3,200,000"
                },
                match_factors=["Location", "Soil Quality", "Price Range", "Water Access"]
            ),
            schemas.PropertyRecommendation(
                property_id="prop_789",
                score=88.0,
                reason="Excellent crop production history in your preferred region",
                property_details={
                    "address": "789 Ranch Lane, Houston, TX",
                    "acreage": 1200,
                    "price": "$4,500,000"
                },
                match_factors=["Crop History", "Region", "Size"]
            )
        ]
        
        # Get user preferences
        user_prefs = db.query(models.UserPreference).filter(
            models.UserPreference.user_id == user_id
        ).first()
        
        return schemas.RecommendationResponse(
            recommendations=mock_recommendations,
            user_preferences={
                "preferred_crops": user_prefs.preferred_crops if user_prefs else [],
                "preferred_locations": user_prefs.preferred_locations if user_prefs else [],
                "acreage_range": {
                    "min": user_prefs.min_acreage if user_prefs else None,
                    "max": user_prefs.max_acreage if user_prefs else None
                }
            } if user_prefs else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting property recommendations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve property recommendations"
        )


@router.get("/crops/{parcel_id}", response_model=schemas.BaseResponse)
async def get_crop_recommendations(
    parcel_id: str,
    county_id: Optional[str] = Query(None, description="County ID for regional analysis"),
    state_code: Optional[str] = Query(None, description="State code for regional analysis"),
    include_ai_analysis: bool = Query(False, description="Include AI-enhanced analysis"),
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Get intelligent crop recommendations based on historical data and analysis"""
    try:
        from api.core.config import settings
        
        # Generate crop recommendations using the service
        recommendations = await crop_service.generate_crop_recommendations(
            parcel_id=parcel_id,
            county_id=county_id,
            state_code=state_code
        )
        
        if not recommendations:
            return schemas.BaseResponse(
                success=True,
                message="No specific recommendations available for this parcel",
                metadata={
                    "parcel_id": parcel_id,
                    "recommendations": [],
                    "note": "Consider providing county_id and state_code for better recommendations"
                }
            )
        
        # Get AI-enhanced analysis if requested
        response_data = {
            "parcel_id": parcel_id,
            "total_recommendations": len(recommendations),
            "recommendations": [rec.__dict__ for rec in recommendations]
        }
        
        if include_ai_analysis:
            ai_enhanced = await crop_service.get_ai_enhanced_recommendations(
                parcel_id=parcel_id,
                recommendations=recommendations
            )
            response_data.update(ai_enhanced)
        
        return schemas.BaseResponse(
            success=True,
            message=f"Generated {len(recommendations)} intelligent crop recommendations",
            metadata=response_data
        )
        
    except Exception as e:
        logger.error(f"Error getting crop recommendations for parcel {parcel_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve crop recommendations"
        )


@router.get("/crops/{parcel_id}/history", response_model=schemas.BaseResponse)
async def get_crop_history(
    parcel_id: str,
    years: int = Query(5, description="Number of years of history to retrieve"),
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Get crop history for a specific parcel"""
    try:
        from api.core.config import settings
        
        # Get crop history
        crop_history = await crop_service.get_crop_history_for_parcel(parcel_id, years)
        
        if not crop_history:
            return schemas.BaseResponse(
                success=True,
                message="No crop history found for this parcel",
                metadata={
                    "parcel_id": parcel_id,
                    "years_requested": years,
                    "history": []
                }
            )
        
        # Analyze rotation patterns
        rotation_analysis = crop_service.analyze_rotation_patterns(crop_history)
        
        # Format history data
        history_data = []
        for record in crop_history:
            history_data.append({
                "history_id": record.history_id,
                "crop_year": record.crop_year,
                "crop_type": record.crop_type,
                "rotation_sequence": record.rotation_sequence,
                "county_id": record.county_id,
                "state_code": record.state_code,
                "created_at": record.created_at.isoformat() if record.created_at else None
            })
        
        return schemas.BaseResponse(
            success=True,
            message=f"Retrieved {len(crop_history)} crop history records",
            metadata={
                "parcel_id": parcel_id,
                "years_requested": years,
                "total_records": len(crop_history),
                "history": history_data,
                "rotation_analysis": rotation_analysis
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting crop history for parcel {parcel_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve crop history"
        )


@router.get("/crops/regional/{county_id}/{state_code}", response_model=schemas.BaseResponse)
async def get_regional_crop_performance(
    county_id: str,
    state_code: str,
    years: int = Query(3, description="Number of years for regional analysis"),
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Get regional crop performance data"""
    try:
        from api.core.config import settings
        
        # Get regional performance data
        regional_data = await crop_service.get_regional_crop_performance(county_id, state_code, years)
        
        if not regional_data:
            return schemas.BaseResponse(
                success=True,
                message="No regional crop data found",
                metadata={
                    "county_id": county_id,
                    "state_code": state_code,
                    "years_analyzed": years,
                    "regional_data": {}
                }
            )
        
        # Calculate summary statistics
        total_frequency = sum(data["frequency"] for data in regional_data.values())
        most_popular_crop = max(regional_data.items(), key=lambda x: x[1]["frequency"])
        
        return schemas.BaseResponse(
            success=True,
            message=f"Retrieved regional crop performance for {county_id}, {state_code}",
            metadata={
                "county_id": county_id,
                "state_code": state_code,
                "years_analyzed": years,
                "total_crop_instances": total_frequency,
                "crop_types_found": len(regional_data),
                "most_popular_crop": {
                    "crop_type": most_popular_crop[0],
                    "frequency": most_popular_crop[1]["frequency"]
                },
                "regional_data": regional_data
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting regional crop performance: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve regional crop performance"
        )


@router.get("/revenue/{property_id}", response_model=schemas.BaseResponse)
async def get_revenue_optimization(
    property_id: str,
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Get revenue optimization recommendations for a property"""
    try:
        from api.core.config import settings
        
        # TODO: Implement revenue optimization analysis
        optimizations = [
            {
                "strategy": "Agricultural Lease",
                "potential_revenue": "$150,000/year",
                "implementation": "Partner with local farmers for crop production",
                "timeline": "3-6 months",
                "requirements": ["Soil testing", "Lease agreement", "Insurance"]
            },
            {
                "strategy": "Section 180 Tax Deduction",
                "potential_savings": "$50,000-$75,000",
                "implementation": "Conduct soil conservation improvements",
                "timeline": "6-12 months",
                "requirements": ["Soil analysis", "Conservation plan", "Tax advisor consultation"]
            },
            {
                "strategy": "Hunting Lease",
                "potential_revenue": "$25,000/year",
                "implementation": "Develop hunting infrastructure and partnerships",
                "timeline": "2-3 months",
                "requirements": ["Wildlife survey", "Insurance", "Access roads"]
            }
        ]
        
        return schemas.BaseResponse(
            success=True,
            message=f"Generated {len(optimizations)} revenue optimization strategies",
            metadata={
                "property_id": property_id,
                "total_potential_revenue": "$225,000/year",
                "optimizations": optimizations
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting revenue optimization: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve revenue optimization recommendations"
        )
