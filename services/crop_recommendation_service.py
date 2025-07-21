"""
Crop Recommendation Service
Provides intelligent crop recommendations based on historical data, soil conditions, and market trends
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass

from data_connectors.snowflake_connector import SnowflakeConnector
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class CropHistoryData:
    """Data structure for crop history information"""
    history_id: int
    parcel_id: str
    crop_year: int
    crop_type: str
    rotation_sequence: int
    crop_geojson: Dict[str, Any]
    county_id: str
    state_code: str
    created_at: datetime
    updated_at: datetime


@dataclass
class CropRecommendation:
    """Data structure for crop recommendation"""
    crop_type: str
    suitability_score: float
    expected_yield: str
    revenue_potential: str
    confidence_level: str
    planting_window: Dict[str, str]
    considerations: List[str]
    historical_performance: Dict[str, Any]
    rotation_benefits: List[str]
    market_outlook: str


class CropRecommendationService:
    """Service for generating intelligent crop recommendations"""
    
    def __init__(self):
        self.snowflake = SnowflakeConnector()
        self.llm_service = LLMService()
        
        # Crop rotation knowledge base
        self.rotation_benefits = {
            "corn": {
                "after": ["soybeans", "wheat", "cover_crops"],
                "benefits": ["nitrogen_utilization", "pest_break", "soil_structure"]
            },
            "soybeans": {
                "after": ["corn", "wheat", "cotton"],
                "benefits": ["nitrogen_fixation", "weed_control", "soil_health"]
            },
            "wheat": {
                "after": ["corn", "soybeans", "cotton"],
                "benefits": ["early_harvest", "cover_protection", "pest_management"]
            },
            "cotton": {
                "after": ["corn", "wheat", "cover_crops"],
                "benefits": ["deep_rooting", "soil_aeration", "pest_diversity"]
            }
        }
        
        # Market data (in production, this would come from external APIs)
        self.market_outlook = {
            "corn": {"price_trend": "stable", "demand": "high", "outlook": "positive"},
            "soybeans": {"price_trend": "increasing", "demand": "very_high", "outlook": "very_positive"},
            "wheat": {"price_trend": "stable", "demand": "moderate", "outlook": "stable"},
            "cotton": {"price_trend": "decreasing", "demand": "moderate", "outlook": "cautious"}
        }

    async def get_crop_history_for_parcel(self, parcel_id: str, years: int = 5) -> List[CropHistoryData]:
        """Get crop history for a specific parcel"""
        try:
            query = """
            SELECT 
                HISTORY_ID,
                PARCEL_ID,
                CROP_YEAR,
                CROP_TYPE,
                ROTATION_SEQUENCE,
                CROP_GEOJSON,
                COUNTY_ID,
                STATE_CODE,
                CREATED_AT,
                UPDATED_AT
            FROM CROP_HISTORY 
            WHERE PARCEL_ID = %s 
            AND CROP_YEAR >= %s
            ORDER BY CROP_YEAR DESC, ROTATION_SEQUENCE ASC
            """
            
            current_year = datetime.now().year
            start_year = current_year - years
            
            results = await self.snowflake.execute_query(query, (parcel_id, start_year))
            
            crop_history = []
            for row in results:
                crop_history.append(CropHistoryData(
                    history_id=row[0],
                    parcel_id=row[1],
                    crop_year=row[2],
                    crop_type=row[3],
                    rotation_sequence=row[4],
                    crop_geojson=json.loads(row[5]) if row[5] else {},
                    county_id=row[6],
                    state_code=row[7],
                    created_at=row[8],
                    updated_at=row[9]
                ))
            
            return crop_history
            
        except Exception as e:
            logger.error(f"Error fetching crop history for parcel {parcel_id}: {str(e)}")
            return []

    async def get_regional_crop_performance(self, county_id: str, state_code: str, years: int = 3) -> Dict[str, Any]:
        """Get regional crop performance data"""
        try:
            query = """
            SELECT 
                CROP_TYPE,
                COUNT(*) as frequency,
                AVG(ROTATION_SEQUENCE) as avg_rotation,
                COUNT(DISTINCT PARCEL_ID) as unique_parcels,
                COUNT(DISTINCT CROP_YEAR) as years_grown
            FROM CROP_HISTORY 
            WHERE COUNTY_ID = %s 
            AND STATE_CODE = %s
            AND CROP_YEAR >= %s
            GROUP BY CROP_TYPE
            ORDER BY frequency DESC
            """
            
            current_year = datetime.now().year
            start_year = current_year - years
            
            results = await self.snowflake.execute_query(query, (county_id, state_code, start_year))
            
            regional_data = {}
            for row in results:
                crop_type = row[0].lower()
                regional_data[crop_type] = {
                    "frequency": row[1],
                    "avg_rotation": float(row[2]) if row[2] else 0,
                    "unique_parcels": row[3],
                    "years_grown": row[4],
                    "popularity_score": row[1] / max(1, row[3])  # frequency per parcel
                }
            
            return regional_data
            
        except Exception as e:
            logger.error(f"Error fetching regional data for {county_id}, {state_code}: {str(e)}")
            return {}

    def analyze_rotation_patterns(self, crop_history: List[CropHistoryData]) -> Dict[str, Any]:
        """Analyze crop rotation patterns from history"""
        if not crop_history:
            return {"patterns": [], "recommendations": []}
        
        # Sort by year and rotation sequence
        sorted_history = sorted(crop_history, key=lambda x: (x.crop_year, x.rotation_sequence))
        
        patterns = []
        current_pattern = []
        current_year = None
        
        for crop in sorted_history:
            if current_year != crop.crop_year:
                if current_pattern:
                    patterns.append({
                        "year": current_year,
                        "sequence": current_pattern.copy()
                    })
                current_pattern = []
                current_year = crop.crop_year
            
            current_pattern.append(crop.crop_type.lower())
        
        # Add the last pattern
        if current_pattern:
            patterns.append({
                "year": current_year,
                "sequence": current_pattern.copy()
            })
        
        # Analyze rotation quality
        rotation_analysis = self._evaluate_rotation_quality(patterns)
        
        return {
            "patterns": patterns,
            "analysis": rotation_analysis,
            "recommendations": self._generate_rotation_recommendations(patterns)
        }

    def _evaluate_rotation_quality(self, patterns: List[Dict]) -> Dict[str, Any]:
        """Evaluate the quality of rotation patterns"""
        if not patterns:
            return {"score": 0, "issues": ["No rotation history available"]}
        
        issues = []
        benefits = []
        score = 50  # Base score
        
        # Check for monoculture
        for pattern in patterns:
            if len(set(pattern["sequence"])) == 1:
                issues.append(f"Monoculture detected in {pattern['year']}")
                score -= 20
            else:
                benefits.append(f"Crop diversity in {pattern['year']}")
                score += 10
        
        # Check for beneficial rotations
        for i in range(len(patterns) - 1):
            current_crops = patterns[i]["sequence"]
            next_crops = patterns[i + 1]["sequence"]
            
            for curr_crop in current_crops:
                for next_crop in next_crops:
                    if curr_crop in self.rotation_benefits:
                        if next_crop in self.rotation_benefits[curr_crop]["after"]:
                            benefits.append(f"Beneficial rotation: {curr_crop} → {next_crop}")
                            score += 15
        
        return {
            "score": min(100, max(0, score)),
            "issues": issues,
            "benefits": benefits
        }

    def _generate_rotation_recommendations(self, patterns: List[Dict]) -> List[str]:
        """Generate rotation recommendations based on patterns"""
        recommendations = []
        
        if not patterns:
            recommendations.append("Establish a crop rotation plan to improve soil health")
            return recommendations
        
        # Get the most recent crops
        recent_pattern = patterns[-1] if patterns else {"sequence": []}
        recent_crops = recent_pattern.get("sequence", [])
        
        if not recent_crops:
            recommendations.append("Start with a diverse crop rotation including legumes")
            return recommendations
        
        # Suggest next crops based on rotation benefits
        suggested_crops = set()
        for crop in recent_crops:
            if crop in self.rotation_benefits:
                suggested_crops.update(self.rotation_benefits[crop]["after"])
        
        if suggested_crops:
            recommendations.append(f"Consider rotating to: {', '.join(suggested_crops)}")
        
        # Check for missing crop types
        all_historical_crops = set()
        for pattern in patterns:
            all_historical_crops.update(pattern["sequence"])
        
        if "soybeans" not in all_historical_crops:
            recommendations.append("Consider adding soybeans for nitrogen fixation")
        
        if len(all_historical_crops) < 3:
            recommendations.append("Increase crop diversity to improve soil health and pest management")
        
        return recommendations

    async def generate_crop_recommendations(
        self, 
        parcel_id: str, 
        county_id: str = None, 
        state_code: str = None,
        target_year: int = None
    ) -> List[CropRecommendation]:
        """Generate comprehensive crop recommendations for a parcel"""
        try:
            # Get crop history
            crop_history = await self.get_crop_history_for_parcel(parcel_id)
            
            # If we have history, extract location info
            if crop_history and not (county_id and state_code):
                county_id = crop_history[0].county_id
                state_code = crop_history[0].state_code
            
            # Get regional performance data
            regional_data = {}
            if county_id and state_code:
                regional_data = await self.get_regional_crop_performance(county_id, state_code)
            
            # Analyze rotation patterns
            rotation_analysis = self.analyze_rotation_patterns(crop_history)
            
            # Generate recommendations for each major crop type
            recommendations = []
            crop_types = ["corn", "soybeans", "wheat", "cotton"]
            
            for crop_type in crop_types:
                recommendation = await self._generate_single_crop_recommendation(
                    crop_type, parcel_id, crop_history, regional_data, rotation_analysis
                )
                if recommendation:
                    recommendations.append(recommendation)
            
            # Sort by suitability score
            recommendations.sort(key=lambda x: x.suitability_score, reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating crop recommendations: {str(e)}")
            return []

    async def _generate_single_crop_recommendation(
        self, 
        crop_type: str, 
        parcel_id: str,
        crop_history: List[CropHistoryData],
        regional_data: Dict[str, Any],
        rotation_analysis: Dict[str, Any]
    ) -> Optional[CropRecommendation]:
        """Generate recommendation for a single crop type"""
        try:
            # Calculate base suitability score
            base_score = 50
            
            # Historical performance factor
            historical_performance = self._analyze_historical_performance(crop_type, crop_history)
            base_score += historical_performance["score_adjustment"]
            
            # Regional popularity factor
            regional_factor = 0
            if crop_type in regional_data:
                regional_factor = min(20, regional_data[crop_type]["popularity_score"] * 2)
            base_score += regional_factor
            
            # Rotation benefit factor
            rotation_factor = self._calculate_rotation_benefit(crop_type, crop_history)
            base_score += rotation_factor
            
            # Market outlook factor
            market_factor = self._calculate_market_factor(crop_type)
            base_score += market_factor
            
            # Ensure score is within bounds
            suitability_score = min(100, max(0, base_score))
            
            # Generate detailed recommendation
            recommendation = CropRecommendation(
                crop_type=crop_type.title(),
                suitability_score=suitability_score,
                expected_yield=self._estimate_yield(crop_type, regional_data),
                revenue_potential=self._estimate_revenue(crop_type, regional_data),
                confidence_level=self._calculate_confidence(crop_type, crop_history, regional_data),
                planting_window=self._get_planting_window(crop_type),
                considerations=self._get_crop_considerations(crop_type, crop_history),
                historical_performance=historical_performance,
                rotation_benefits=self._get_rotation_benefits(crop_type),
                market_outlook=self.market_outlook.get(crop_type, {}).get("outlook", "stable")
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating recommendation for {crop_type}: {str(e)}")
            return None

    def _analyze_historical_performance(self, crop_type: str, crop_history: List[CropHistoryData]) -> Dict[str, Any]:
        """Analyze historical performance of a crop type"""
        crop_occurrences = [h for h in crop_history if h.crop_type.lower() == crop_type]
        
        if not crop_occurrences:
            return {
                "years_grown": 0,
                "frequency": 0,
                "last_grown": None,
                "score_adjustment": 0,
                "notes": "No historical data available"
            }
        
        years_grown = len(set(h.crop_year for h in crop_occurrences))
        frequency = len(crop_occurrences)
        last_grown = max(h.crop_year for h in crop_occurrences)
        current_year = datetime.now().year
        
        # Calculate score adjustment
        score_adjustment = 0
        
        # Bonus for successful historical growing
        if years_grown > 0:
            score_adjustment += min(15, years_grown * 3)
        
        # Penalty for recent monoculture
        if frequency > years_grown * 2:
            score_adjustment -= 10
        
        # Bonus for recent success
        if last_grown >= current_year - 2:
            score_adjustment += 5
        
        return {
            "years_grown": years_grown,
            "frequency": frequency,
            "last_grown": last_grown,
            "score_adjustment": score_adjustment,
            "notes": f"Grown {years_grown} years, {frequency} times total"
        }

    def _calculate_rotation_benefit(self, crop_type: str, crop_history: List[CropHistoryData]) -> int:
        """Calculate rotation benefit score for a crop type"""
        if not crop_history:
            return 0
        
        # Get the most recent crops
        recent_crops = [h.crop_type.lower() for h in crop_history[:3]]  # Last 3 entries
        
        if crop_type not in self.rotation_benefits:
            return 0
        
        beneficial_predecessors = self.rotation_benefits[crop_type]["after"]
        
        # Check if any recent crops are beneficial predecessors
        for recent_crop in recent_crops:
            if recent_crop in beneficial_predecessors:
                return 15  # High bonus for beneficial rotation
        
        # Penalty for planting same crop recently
        if crop_type in recent_crops:
            return -10
        
        return 5  # Small bonus for crop diversity

    def _calculate_market_factor(self, crop_type: str) -> int:
        """Calculate market factor score"""
        market_data = self.market_outlook.get(crop_type, {})
        
        outlook = market_data.get("outlook", "stable")
        demand = market_data.get("demand", "moderate")
        
        score = 0
        
        # Outlook factor
        if outlook == "very_positive":
            score += 15
        elif outlook == "positive":
            score += 10
        elif outlook == "stable":
            score += 5
        elif outlook == "cautious":
            score -= 5
        
        # Demand factor
        if demand == "very_high":
            score += 10
        elif demand == "high":
            score += 5
        elif demand == "moderate":
            score += 0
        else:
            score -= 5
        
        return score

    def _estimate_yield(self, crop_type: str, regional_data: Dict[str, Any]) -> str:
        """Estimate expected yield for a crop type"""
        # Base yields (these would come from agricultural databases in production)
        base_yields = {
            "corn": "160-180 bushels/acre",
            "soybeans": "45-55 bushels/acre", 
            "wheat": "40-50 bushels/acre",
            "cotton": "800-1000 lbs/acre"
        }
        
        return base_yields.get(crop_type, "Data not available")

    def _estimate_revenue(self, crop_type: str, regional_data: Dict[str, Any]) -> str:
        """Estimate revenue potential for a crop type"""
        # Base revenue estimates (these would come from market data in production)
        base_revenue = {
            "corn": "$800-$950/acre",
            "soybeans": "$650-$800/acre",
            "wheat": "$300-$400/acre", 
            "cotton": "$600-$800/acre"
        }
        
        return base_revenue.get(crop_type, "Data not available")

    def _calculate_confidence(self, crop_type: str, crop_history: List[CropHistoryData], regional_data: Dict[str, Any]) -> str:
        """Calculate confidence level for recommendation"""
        confidence_score = 50
        
        # Historical data factor
        if crop_history:
            confidence_score += min(25, len(crop_history) * 2)
        
        # Regional data factor
        if crop_type in regional_data:
            confidence_score += min(15, regional_data[crop_type]["frequency"] / 10)
        
        if confidence_score >= 80:
            return "High"
        elif confidence_score >= 60:
            return "Medium"
        else:
            return "Low"

    def _get_planting_window(self, crop_type: str) -> Dict[str, str]:
        """Get planting window for a crop type"""
        windows = {
            "corn": {"start": "April 15", "end": "May 30"},
            "soybeans": {"start": "May 1", "end": "June 15"},
            "wheat": {"start": "September 15", "end": "November 1"},
            "cotton": {"start": "April 1", "end": "May 15"}
        }
        
        return windows.get(crop_type, {"start": "Consult local extension", "end": "office"})

    def _get_crop_considerations(self, crop_type: str, crop_history: List[CropHistoryData]) -> List[str]:
        """Get specific considerations for a crop type"""
        considerations = {
            "corn": [
                "Requires well-drained soil",
                "High nitrogen requirements",
                "Sensitive to drought during pollination",
                "Consider pest management for corn borer"
            ],
            "soybeans": [
                "Fixes nitrogen for following crops",
                "Good for weed management",
                "Monitor for soybean cyst nematode",
                "Requires adequate phosphorus and potassium"
            ],
            "wheat": [
                "Provides early season ground cover",
                "Good for erosion control",
                "Monitor for fungal diseases",
                "Consider variety selection for local climate"
            ],
            "cotton": [
                "Requires warm growing season",
                "Deep rooting improves soil structure",
                "Monitor for bollworm and other pests",
                "Requires careful water management"
            ]
        }
        
        base_considerations = considerations.get(crop_type, ["Consult local agricultural extension office"])
        
        # Add historical considerations
        if crop_history:
            recent_crops = [h.crop_type.lower() for h in crop_history[:2]]
            if crop_type in recent_crops:
                base_considerations.append("Consider rotation to break pest and disease cycles")
        
        return base_considerations

    def _get_rotation_benefits(self, crop_type: str) -> List[str]:
        """Get rotation benefits for a crop type"""
        if crop_type not in self.rotation_benefits:
            return []
        
        benefits_map = {
            "nitrogen_fixation": "Fixes atmospheric nitrogen",
            "nitrogen_utilization": "Efficiently uses soil nitrogen",
            "pest_break": "Breaks pest and disease cycles",
            "soil_structure": "Improves soil structure",
            "weed_control": "Helps control weeds",
            "soil_health": "Enhances overall soil health",
            "early_harvest": "Allows early harvest",
            "cover_protection": "Provides soil cover protection",
            "pest_management": "Aids in pest management",
            "deep_rooting": "Deep roots improve soil aeration",
            "soil_aeration": "Improves soil aeration",
            "pest_diversity": "Promotes beneficial pest diversity"
        }
        
        benefit_keys = self.rotation_benefits[crop_type]["benefits"]
        return [benefits_map.get(key, key) for key in benefit_keys]

    async def get_ai_enhanced_recommendations(
        self, 
        parcel_id: str, 
        recommendations: List[CropRecommendation],
        additional_context: str = ""
    ) -> Dict[str, Any]:
        """Get AI-enhanced recommendations with detailed analysis"""
        try:
            # Prepare context for LLM
            context = f"""
            Parcel ID: {parcel_id}
            
            Crop Recommendations Analysis:
            """
            
            for i, rec in enumerate(recommendations[:3], 1):  # Top 3 recommendations
                context += f"""
                
                {i}. {rec.crop_type}
                   - Suitability Score: {rec.suitability_score}/100
                   - Expected Yield: {rec.expected_yield}
                   - Revenue Potential: {rec.revenue_potential}
                   - Market Outlook: {rec.market_outlook}
                   - Confidence: {rec.confidence_level}
                   - Considerations: {', '.join(rec.considerations[:3])}
                """
            
            if additional_context:
                context += f"\n\nAdditional Context: {additional_context}"
            
            # Generate AI analysis
            prompt = f"""
            Based on the crop recommendation data provided, please provide:
            
            1. A summary of the top recommendation and why it's the best choice
            2. Key factors that influenced the recommendations
            3. Potential risks and mitigation strategies
            4. Long-term rotation strategy suggestions
            5. Market timing considerations
            
            Context:
            {context}
            
            Please provide a comprehensive but concise analysis that would help a farmer make informed decisions.
            """
            
            ai_analysis = await self.llm_service.generate_response(prompt)
            
            return {
                "ai_analysis": ai_analysis,
                "recommendations": [rec.__dict__ for rec in recommendations],
                "summary": {
                    "top_recommendation": recommendations[0].crop_type if recommendations else None,
                    "total_recommendations": len(recommendations),
                    "avg_suitability": sum(r.suitability_score for r in recommendations) / len(recommendations) if recommendations else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-enhanced recommendations: {str(e)}")
            return {
                "ai_analysis": "AI analysis temporarily unavailable",
                "recommendations": [rec.__dict__ for rec in recommendations],
                "summary": {
                    "top_recommendation": recommendations[0].crop_type if recommendations else None,
                    "total_recommendations": len(recommendations),
                    "avg_suitability": sum(r.suitability_score for r in recommendations) / len(recommendations) if recommendations else 0
                }
            }
