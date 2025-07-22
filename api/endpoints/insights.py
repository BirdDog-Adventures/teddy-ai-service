"""
Insights endpoint for property intelligence and analysis
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import json

from api.core.dependencies import get_db, cache, get_optional_current_user
from api.core.security import get_current_active_user
from api.models import database as models
from api.models import schemas
from data_connectors.snowflake_connector import SnowflakeConnector
from services.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter()

# Services will be initialized lazily
_snowflake_connector = None
_llm_service = None

def get_snowflake_connector():
    global _snowflake_connector
    if _snowflake_connector is None:
        _snowflake_connector = SnowflakeConnector()
    return _snowflake_connector

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


@router.get("/property/{property_id}")
async def get_property_insights(
    property_id: str,
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Get comprehensive insights for a specific property using real data and LLM analysis"""
    try:
        from api.core.config import settings
        
        # Get Snowflake connector
        snowflake_conn = get_snowflake_connector()
        
        # Gather comprehensive property data
        property_data = await _gather_comprehensive_property_data(snowflake_conn, property_id)
        
        if not property_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {property_id} not found"
            )
        
        # Generate LLM-powered insights
        insights = await _generate_property_insights(property_data)
        
        # Calculate overall property score
        overall_score = _calculate_property_score(property_data)
        
        # Format response
        return {
            "success": True,
            "property_id": property_id,
            "overall_score": overall_score,
            "insights": insights,
            "data_summary": {
                "parcel_data": bool(property_data.get("parcel_profile")),
                "soil_data": bool(property_data.get("soil_profile")),
                "crop_history": bool(property_data.get("crop_history")),
                "climate_data": bool(property_data.get("climate_data")),
                "topography_data": bool(property_data.get("topography_data")),
                "comprehensive_analysis": bool(property_data.get("comprehensive_analysis"))
            },
            "raw_data": property_data if settings.ENABLE_AUTHENTICATION else None  # Only show raw data in auth mode
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting property insights for {property_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve property insights"
        )


async def _gather_comprehensive_property_data(snowflake_conn: SnowflakeConnector, property_id: str) -> Dict[str, Any]:
    """Gather all available data for a property from Snowflake"""
    property_data = {}
    
    try:
        # 1. Get parcel profile (basic property information)
        logger.info(f"Fetching parcel profile for {property_id}")
        parcel_profile = await snowflake_conn.get_property_boundaries(property_id)
        if parcel_profile:
            property_data["parcel_profile"] = parcel_profile
        
        # 2. Get soil profile data
        logger.info(f"Fetching soil profile for {property_id}")
        soil_profile = await snowflake_conn.get_soil_data(property_id)
        if soil_profile:
            property_data["soil_profile"] = soil_profile
        
        # 3. Get crop history
        logger.info(f"Fetching crop history for {property_id}")
        crop_history = await snowflake_conn.get_crop_history(property_id, years=10)
        if crop_history:
            property_data["crop_history"] = crop_history
        
        # 4. Get climate data
        logger.info(f"Fetching climate data for {property_id}")
        climate_data = await snowflake_conn.get_climate_data(property_id)
        if climate_data:
            property_data["climate_data"] = climate_data
        
        # 5. Get topography data
        logger.info(f"Fetching topography data for {property_id}")
        topography_data = await snowflake_conn.get_topography_data(property_id)
        if topography_data:
            property_data["topography_data"] = topography_data
        
        # 6. Get comprehensive analysis
        logger.info(f"Fetching comprehensive analysis for {property_id}")
        comprehensive_analysis = await snowflake_conn.get_comprehensive_analysis(property_id)
        if comprehensive_analysis:
            property_data["comprehensive_analysis"] = comprehensive_analysis
        
        # 7. Get Section 180 estimates
        logger.info(f"Fetching Section 180 estimates for {property_id}")
        section_180_estimates = await snowflake_conn.get_section_180_estimates(property_id)
        if section_180_estimates:
            property_data["section_180_estimates"] = section_180_estimates
        
        logger.info(f"Gathered data for {property_id}: {list(property_data.keys())}")
        return property_data
        
    except Exception as e:
        logger.error(f"Error gathering property data for {property_id}: {str(e)}", exc_info=True)
        return property_data


async def _generate_property_insights(property_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive insights using LLM analysis"""
    try:
        llm_service = get_llm_service()
        
        # Prepare data summary for LLM
        data_summary = _prepare_data_summary_for_llm(property_data)
        
        # Create system prompt for property analysis
        system_prompt = """You are an expert agricultural and land analysis consultant. 
        Analyze the provided property data and generate comprehensive insights covering:
        
        1. SOIL QUALITY ANALYSIS
        - Soil composition and health
        - Agricultural suitability
        - Improvement recommendations
        
        2. AGRICULTURAL POTENTIAL
        - Best crop recommendations
        - Yield expectations
        - Rotation strategies
        
        3. LAND USE OPTIMIZATION
        - Current vs optimal land use
        - Revenue maximization opportunities
        - Conservation considerations
        
        4. INVESTMENT ANALYSIS
        - Property valuation insights
        - Market positioning
        - Risk assessment
        
        5. REGULATORY OPPORTUNITIES
        - Tax incentives (Section 180, etc.)
        - Conservation programs
        - Compliance considerations
        
        Provide specific, actionable insights based on the data. Be concise but comprehensive.
        Format your response as structured insights with clear categories and recommendations."""
        
        # Generate insights using LLM
        conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please analyze this property data and provide comprehensive insights:\n\n{data_summary}"}
        ]
        
        insights_text, _ = await llm_service.generate_response(
            conversation_history=conversation_history,
            system_prompt=system_prompt
        )
        
        # Parse and structure the insights
        structured_insights = _parse_llm_insights(insights_text)
        
        return structured_insights
        
    except Exception as e:
        logger.error(f"Error generating LLM insights: {str(e)}", exc_info=True)
        return {
            "error": "Failed to generate AI insights",
            "basic_analysis": _generate_basic_insights(property_data)
        }


def _prepare_data_summary_for_llm(property_data: Dict[str, Any]) -> str:
    """Prepare a structured summary of property data for LLM analysis"""
    summary_parts = []
    
    # Parcel Profile Summary
    if "parcel_profile" in property_data:
        parcel = property_data["parcel_profile"]
        
        # Safe formatting for monetary values - convert Decimal to float
        total_value = parcel.get('TOTAL_VALUE')
        total_value_str = f"${float(total_value):,.0f}" if total_value is not None else 'N/A'
        
        land_value = parcel.get('LAND_VALUE')
        land_value_str = f"${float(land_value):,.0f}" if land_value is not None else 'N/A'
        
        summary_parts.append(f"""
PROPERTY OVERVIEW:
- Parcel ID: {parcel.get('PARCEL_ID', 'N/A')}
- Address: {parcel.get('ADDRESS', 'N/A')}, {parcel.get('CITY', 'N/A')}, {parcel.get('STATE_CODE', 'N/A')}
- County: {parcel.get('COUNTY_ID', 'N/A')}
- Total Acreage: {parcel.get('ACRES', 'N/A')} acres
- Total Value: {total_value_str}
- Land Value: {land_value_str}
- Use Code: {parcel.get('USECODE', 'N/A')} - {parcel.get('USEDESC', 'N/A')}
- Zoning: {parcel.get('ZONING', 'N/A')} - {parcel.get('ZONING_DESCRIPTION', 'N/A')}
""")
    
    # Soil Profile Summary
    if "soil_profile" in property_data:
        soil_data = property_data["soil_profile"]
        if soil_data:
            summary_parts.append("\nSOIL ANALYSIS:")
            for i, soil in enumerate(soil_data[:3]):  # Top 3 soil components
                summary_parts.append(f"""
- Soil Component {i+1} ({soil.get('COMPONENT_PERCENTAGE', 'N/A')}% of property):
  * Series: {soil.get('SOIL_SERIES', 'N/A')}
  * Type: {soil.get('SOIL_TYPE', 'N/A')}
  * Fertility Class: {soil.get('FERTILITY_CLASS', 'N/A')}
  * pH Level: {soil.get('PH_LEVEL', 'N/A')}
  * Organic Matter: {soil.get('ORGANIC_MATTER_PCT', 'N/A')}%
  * Drainage: {soil.get('DRAINAGE_CLASS', 'N/A')}
  * Agricultural Capability: {soil.get('AGRICULTURAL_CAPABILITY', 'N/A')}
  * Available Water Capacity: {soil.get('AVAILABLE_WATER_CAPACITY', 'N/A')}
""")
    
    # Crop History Summary
    if "crop_history" in property_data:
        crop_history = property_data["crop_history"]
        if crop_history:
            summary_parts.append(f"\nCROP HISTORY ({len(crop_history)} records):")
            crop_summary = {}
            for crop in crop_history:
                crop_type = crop.get('CROP_TYPE', 'Unknown')
                year = crop.get('CROP_YEAR', 'Unknown')
                if crop_type not in crop_summary:
                    crop_summary[crop_type] = []
                crop_summary[crop_type].append(year)
            
            for crop_type, years in crop_summary.items():
                summary_parts.append(f"- {crop_type}: {len(years)} years ({min(years) if years else 'N/A'}-{max(years) if years else 'N/A'})")
    
    # Climate Data Summary
    if "climate_data" in property_data:
        climate = property_data["climate_data"]
        summary_parts.append(f"""
CLIMATE DATA:
- Annual Precipitation: {climate.get('ANNUAL_PRECIPITATION_INCHES', 'N/A')} inches
- Growing Degree Days: {climate.get('GROWING_DEGREE_DAYS', 'N/A')}
- Average Temperature: {climate.get('AVG_TEMPERATURE_F', 'N/A')}°F
- Climate Classification: {climate.get('CLIMATE_CLASSIFICATION', 'N/A')}
""")
    
    # Topography Summary
    if "topography_data" in property_data:
        topo = property_data["topography_data"]
        summary_parts.append(f"""
TOPOGRAPHY:
- Mean Elevation: {topo.get('MEAN_ELEVATION_FT', 'N/A')} ft
- Elevation Range: {topo.get('MIN_ELEVATION_FT', 'N/A')} - {topo.get('MAX_ELEVATION_FT', 'N/A')} ft
- Slope: {topo.get('SLOPE_PERCENT', 'N/A')}%
- Terrain Analysis: {topo.get('TERRAIN_ANALYSIS', 'N/A')}
""")
    
    # Comprehensive Analysis Summary
    if "comprehensive_analysis" in property_data:
        comp = property_data["comprehensive_analysis"]
        summary_parts.append(f"""
LAND COVER ANALYSIS:
- Dominant Cover Type: {comp.get('DOMINANT_COVER_TYPE', 'N/A')} ({comp.get('DOMINANT_COVER_PERCENTAGE', 'N/A')}%)
- Agricultural Percentage: {comp.get('AGRICULTURAL_PERCENTAGE', 'N/A')}%
- Forest Percentage: {comp.get('FOREST_PERCENTAGE', 'N/A')}%
- Developed Percentage: {comp.get('DEVELOPED_PERCENTAGE', 'N/A')}%
- Agricultural Classification: {comp.get('AGRICULTURAL_CLASSIFICATION', 'N/A')}
- Section 180 Potential: {comp.get('SECTION_180_POTENTIAL', 'N/A')}
""")
    
    # Section 180 Estimates
    if "section_180_estimates" in property_data:
        s180 = property_data["section_180_estimates"]
        
        # Safe formatting for deduction amount - convert Decimal to float
        total_deduction = s180.get('TOTAL_DEDUCTION')
        deduction_str = f"${float(total_deduction):,.0f}" if total_deduction is not None else 'N/A'
        
        summary_parts.append(f"""
SECTION 180 TAX DEDUCTION ESTIMATES:
- Total Deduction Potential: {deduction_str}
- Confidence Score: {s180.get('CONFIDENCE_SCORE', 'N/A')}/100
- Methodology: {s180.get('METHODOLOGY', 'N/A')}
""")
    
    return "\n".join(summary_parts)


def _parse_llm_insights(insights_text: str) -> Dict[str, Any]:
    """Parse LLM-generated insights into structured format"""
    return {
        "ai_analysis": insights_text,
        "generated_at": "2025-07-20T00:00:00Z",
        "analysis_type": "comprehensive_property_insights",
        "confidence": "high"
    }


def _generate_basic_insights(property_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate basic insights when LLM is not available"""
    insights = {
        "basic_analysis": True,
        "insights": []
    }
    
    # Basic soil analysis
    if "soil_profile" in property_data and property_data["soil_profile"]:
        soil_data = property_data["soil_profile"][0]  # Primary soil component
        insights["insights"].append({
            "category": "Soil Quality",
            "insight": f"Primary soil type is {soil_data.get('SOIL_SERIES', 'Unknown')} with {soil_data.get('DRAINAGE_CLASS', 'unknown')} drainage.",
            "recommendation": "Consider soil testing for detailed nutrient analysis."
        })
    
    # Basic crop history analysis
    if "crop_history" in property_data and property_data["crop_history"]:
        crop_types = set(crop.get('CROP_TYPE') for crop in property_data["crop_history"])
        insights["insights"].append({
            "category": "Agricultural History",
            "insight": f"Property has grown {len(crop_types)} different crop types over the analyzed period.",
            "recommendation": "Diversified crop rotation shows good agricultural management."
        })
    
    return insights


def _calculate_property_score(property_data: Dict[str, Any]) -> float:
    """Calculate an overall property score based on available data"""
    score = 0.0
    factors = 0
    
    # Soil quality factor
    if "soil_profile" in property_data and property_data["soil_profile"]:
        soil_data = property_data["soil_profile"][0]
        if soil_data.get('FERTILITY_CLASS'):
            fertility = soil_data.get('FERTILITY_CLASS', '').lower()
            if 'high' in fertility or 'prime' in fertility:
                score += 90.0
            elif 'good' in fertility or 'moderate' in fertility:
                score += 75.0
            else:
                score += 60.0
            factors += 1
    
    # Agricultural capability factor
    if "comprehensive_analysis" in property_data:
        comp = property_data["comprehensive_analysis"]
        ag_percentage = comp.get('AGRICULTURAL_PERCENTAGE', 0)
        if ag_percentage:
            # Convert to float to handle Decimal types from Snowflake
            ag_percentage_float = float(ag_percentage) if ag_percentage is not None else 0.0
            score += min(ag_percentage_float, 100.0)
            factors += 1
    
    # Crop history factor (diversity and consistency)
    if "crop_history" in property_data and property_data["crop_history"]:
        crop_years = len(set(crop.get('CROP_YEAR') for crop in property_data["crop_history"]))
        crop_types = len(set(crop.get('CROP_TYPE') for crop in property_data["crop_history"]))
        history_score = min((crop_years * 10) + (crop_types * 5), 100.0)
        score += float(history_score)
        factors += 1
    
    # Climate factor
    if "climate_data" in property_data:
        climate = property_data["climate_data"]
        precipitation = climate.get('ANNUAL_PRECIPITATION_INCHES', 0)
        if precipitation:
            # Convert to float to handle Decimal types from Snowflake
            precipitation_float = float(precipitation) if precipitation is not None else 0.0
            # Optimal precipitation range for most crops is 20-40 inches
            if 20 <= precipitation_float <= 40:
                score += 85.0
            elif 15 <= precipitation_float <= 50:
                score += 70.0
            else:
                score += 55.0
            factors += 1
    
    return round(score / factors if factors > 0 else 50.0, 1)


@router.get("/portfolio/{user_id}", response_model=schemas.PortfolioAnalysis)
async def get_portfolio_analysis(
    user_id: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get portfolio analysis for a user's properties"""
    try:
        # Verify access
        if str(current_user.id) != user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this portfolio"
            )
        
        # TODO: Implement actual portfolio analysis
        return schemas.PortfolioAnalysis(
            user_id=user_id,
            total_properties=5,
            total_acreage=2500.0,
            total_value=5000000.0,
            total_revenue=150000.0,
            average_land_score=82.5,
            properties=[],
            insights=["Portfolio is well-diversified", "Consider adding properties in different climate zones"],
            opportunities=[{"type": "lease", "potential_revenue": 50000}]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve portfolio analysis"
        )


@router.post("/compare", response_model=schemas.PropertyComparisonResponse)
async def compare_properties(
    request: schemas.PropertyComparisonRequest,
    current_user = Depends(get_optional_current_user()),
    db: Session = Depends(get_db)
):
    """Compare multiple properties"""
    try:
        from api.core.config import settings
        
        # TODO: Implement property comparison
        return schemas.PropertyComparisonResponse(
            properties=[{"id": pid, "data": {}} for pid in request.property_ids],
            comparison_matrix={
                "acreage": [500, 750, 1000],
                "soil_quality": [85, 78, 92],
                "lease_value": [200, 180, 250]
            },
            recommendations=["Property 3 has the highest revenue potential"]
        )
        
    except Exception as e:
        logger.error(f"Error comparing properties: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare properties"
        )
