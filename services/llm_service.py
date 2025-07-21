"""
LLM Service for generating AI responses with multi-provider support
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
import json
from decimal import Decimal
from tenacity import retry, stop_after_attempt, wait_exponential

from api.core.config import settings
from data_connectors.snowflake_connector import SnowflakeConnector
from services.llm_providers import LLMProviderFactory

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, provider_name: str = None):
        self.provider = LLMProviderFactory.create_provider(provider_name)
        self.snowflake_connector = SnowflakeConnector()
        logger.info(f"Initialized LLM service with provider: {settings.LLM_PROVIDER}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_response(
        self,
        conversation_history: List[Dict[str, str]],
        system_prompt: str,
        property_context: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """Generate AI response using configured LLM provider"""
        try:
            # Build messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add context if available
            if property_context or user_preferences:
                context_message = self._build_context_message(property_context, user_preferences)
                messages.append({"role": "system", "content": context_message})
            
            # Add conversation history (with context management)
            messages.extend(self._manage_context_length(conversation_history))
            
            # Get available tools
            tools = self._get_available_tools()
            
            # Call LLM provider
            content, tool_calls = await self.provider.generate_response(messages, tools)
            sources = None
            
            # Handle tool calls if any
            if tool_calls:
                sources = await self._handle_tool_calls_from_provider(tool_calls)
                
                # Handle tool responses differently for different providers
                if settings.LLM_PROVIDER == "anthropic":
                    # For Anthropic, add tool results as user message
                    tool_results = []
                    for i, tool_call in enumerate(tool_calls):
                        result = sources[i] if sources and i < len(sources) else {"error": "No data found"}
                        tool_results.append(f"Tool {tool_call['function']['name']} result: {json.dumps(result, default=self._json_serializer)}")
                    
                    messages.append({
                        "role": "user",
                        "content": f"Here are the tool results:\n\n{chr(10).join(tool_results)}\n\nPlease provide a comprehensive response based on this data."
                    })
                    
                    # Get final response
                    final_content, _ = await self.provider.generate_response(messages)
                    content = final_content
                else:
                    # For OpenAI and Azure, we need to add the assistant message with tool_calls first
                    # Then add tool responses, then get final response
                    
                    # Add the assistant message with tool_calls (this is required by OpenAI)
                    assistant_message = {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": []
                    }
                    
                    # Convert our tool_calls format back to OpenAI format
                    for tool_call in tool_calls:
                        assistant_message["tool_calls"].append({
                            "id": tool_call.get("id", "unknown"),
                            "type": "function",
                            "function": {
                                "name": tool_call["function"]["name"],
                                "arguments": tool_call["function"]["arguments"]
                            }
                        })
                    
                    messages.append(assistant_message)
                    
                    # Add tool responses (with context management)
                    for i, tool_call in enumerate(tool_calls):
                        result = sources[i] if sources and i < len(sources) else {"error": "No data found"}
                        # Truncate large tool results to prevent context overflow
                        tool_content = self._truncate_tool_result(result)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", "unknown"),
                            "content": tool_content
                        })
                    
                    # Apply context management before final response
                    messages = self._manage_final_context_length(messages)
                    
                    # Get final response
                    final_content, _ = await self.provider.generate_response(messages)
                    content = final_content
            
            return content, sources
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error processing your request. Please try again.", None
    
    def _build_context_message(
        self,
        property_context: Optional[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]]
    ) -> str:
        """Build context message for the LLM"""
        context_parts = []
        
        if property_context:
            context_parts.append(f"Property Context: {json.dumps(property_context, indent=2)}")
        
        if user_preferences:
            context_parts.append(f"User Preferences: {json.dumps(user_preferences, indent=2)}")
        
        return "\n\n".join(context_parts)
    
    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get available function tools for the LLM"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_properties",
                    "description": "Search for properties based on criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Search filters",
                                "properties": {
                                    "min_acreage": {"type": "number"},
                                    "max_acreage": {"type": "number"},
                                    "county": {"type": "string"},
                                    "state": {"type": "string"},
                                    "soil_quality": {"type": "string"}
                                }
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_soil_analysis",
                    "description": "Get soil analysis for a property",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "property_id": {
                                "type": "string",
                                "description": "Property ID"
                            }
                        },
                        "required": ["property_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_crop_recommendations",
                    "description": "Get crop recommendations for a property",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "property_id": {
                                "type": "string",
                                "description": "Property ID"
                            },
                            "season": {
                                "type": "string",
                                "description": "Planting season",
                                "enum": ["spring", "summer", "fall", "winter"]
                            }
                        },
                        "required": ["property_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_lease_value",
                    "description": "Calculate potential lease value for a property",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "property_id": {
                                "type": "string",
                                "description": "Property ID"
                            },
                            "lease_type": {
                                "type": "string",
                                "description": "Type of lease",
                                "enum": ["crop", "pasture", "hunting", "mixed"]
                            }
                        },
                        "required": ["property_id", "lease_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_section_180_eligibility",
                    "description": "Check if property is eligible for Section 180 tax deduction",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "property_id": {
                                "type": "string",
                                "description": "Property ID"
                            }
                        },
                        "required": ["property_id"]
                    }
                }
            }
        ]
    
    async def _handle_tool_calls_from_provider(self, tool_calls) -> Optional[List[Dict[str, Any]]]:
        """Handle function tool calls from provider format"""
        sources = []
        
        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            
            # Route to appropriate handler
            if function_name == "search_properties":
                result = await self._search_properties(**arguments)
            elif function_name == "get_soil_analysis":
                result = await self._get_soil_analysis(**arguments)
            elif function_name == "get_crop_recommendations":
                result = await self._get_crop_recommendations(**arguments)
            elif function_name == "calculate_lease_value":
                result = await self._calculate_lease_value(**arguments)
            elif function_name == "check_section_180_eligibility":
                result = await self._check_section_180_eligibility(**arguments)
            else:
                result = {"error": f"Unknown function: {function_name}"}
            
            sources.append({
                "function": function_name,
                "arguments": arguments,
                "result": result
            })
        
        return sources if sources else None

    async def _handle_tool_calls(self, tool_calls) -> Optional[List[Dict[str, Any]]]:
        """Handle function tool calls (legacy format)"""
        sources = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            # Route to appropriate handler
            if function_name == "search_properties":
                result = await self._search_properties(**arguments)
            elif function_name == "get_soil_analysis":
                result = await self._get_soil_analysis(**arguments)
            elif function_name == "get_crop_recommendations":
                result = await self._get_crop_recommendations(**arguments)
            elif function_name == "calculate_lease_value":
                result = await self._calculate_lease_value(**arguments)
            elif function_name == "check_section_180_eligibility":
                result = await self._check_section_180_eligibility(**arguments)
            else:
                result = {"error": f"Unknown function: {function_name}"}
            
            sources.append({
                "function": function_name,
                "arguments": arguments,
                "result": result
            })
        
        return sources if sources else None
    
    def _manage_context_length(self, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Manage context length to prevent token limit exceeded errors"""
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        max_tokens = 12000  # Leave room for system messages, tools, and response
        
        # Calculate current token usage
        total_chars = sum(len(json.dumps(msg)) for msg in conversation_history)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= max_tokens:
            return conversation_history
        
        # If too long, keep only the most recent messages
        # Always keep the first message (usually contains important context)
        if len(conversation_history) <= 2:
            return conversation_history
        
        # Keep first message and recent messages
        result = [conversation_history[0]]  # Keep first message
        recent_messages = []
        current_chars = len(json.dumps(conversation_history[0]))
        
        # Add messages from the end until we approach the limit
        for msg in reversed(conversation_history[1:]):
            msg_chars = len(json.dumps(msg))
            if (current_chars + msg_chars) // 4 > max_tokens:
                break
            recent_messages.insert(0, msg)
            current_chars += msg_chars
        
        result.extend(recent_messages)
        
        if len(result) < len(conversation_history):
            logger.info(f"Truncated conversation history from {len(conversation_history)} to {len(result)} messages to manage context length")
        
        return result
    
    def _truncate_tool_result(self, result: Dict) -> str:
        """Truncate large tool results to prevent context overflow"""
        result_str = json.dumps(result, default=self._json_serializer)
        
        # If result is too large, truncate it intelligently
        max_chars = 8000  # Roughly 2000 tokens
        if len(result_str) <= max_chars:
            return result_str
        
        # For soil analysis results, keep the most important parts
        if isinstance(result, dict) and "soil_types" in result:
            # Keep property info and summary, truncate detailed soil types
            truncated_result = {
                "property_id": result.get("property_id"),
                "property_info": result.get("property_info"),
                "overall_quality": result.get("overall_quality"),
                "overall_quality_score": result.get("overall_quality_score"),
                "average_ph": result.get("average_ph"),
                "average_organic_matter": result.get("average_organic_matter"),
                "recommendations": result.get("recommendations", [])[:3],  # Keep first 3 recommendations
                "soil_types_summary": f"Found {len(result.get('soil_types', []))} soil types",
                "note": "Detailed soil data truncated due to size limits. Full analysis available in database."
            }
            
            # Add a few sample soil types
            soil_types = result.get("soil_types", [])
            if soil_types:
                truncated_result["sample_soil_types"] = soil_types[:2]  # Keep first 2 soil types
            
            return json.dumps(truncated_result, default=self._json_serializer)
        
        # For other results, simple truncation
        truncated = result_str[:max_chars-100] + "... [truncated due to size limits]"
        return truncated
    
    def _manage_final_context_length(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Manage context length for final response generation"""
        # More aggressive token management for final response
        max_tokens = 10000  # Even more conservative for final response
        
        # Calculate current token usage
        total_chars = sum(len(json.dumps(msg)) for msg in messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= max_tokens:
            return messages
        
        # Keep system messages and recent conversation, truncate tool results if needed
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        other_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        # Start with system messages
        result = system_messages[:]
        current_chars = sum(len(json.dumps(msg)) for msg in system_messages)
        
        # Add other messages from the end, prioritizing recent conversation over tool results
        user_assistant_messages = [msg for msg in other_messages if msg.get("role") in ["user", "assistant"]]
        tool_messages = [msg for msg in other_messages if msg.get("role") == "tool"]
        
        # Add user/assistant messages first (more important)
        for msg in reversed(user_assistant_messages):
            msg_chars = len(json.dumps(msg))
            if (current_chars + msg_chars) // 4 > max_tokens:
                break
            result.insert(-len([m for m in result if m.get("role") == "system"]), msg)
            current_chars += msg_chars
        
        # Add tool messages if there's room
        for msg in reversed(tool_messages):
            msg_chars = len(json.dumps(msg))
            if (current_chars + msg_chars) // 4 > max_tokens:
                break
            result.append(msg)
            current_chars += msg_chars
        
        if len(result) < len(messages):
            logger.info(f"Truncated final context from {len(messages)} to {len(result)} messages")
        
        return result
    
    def _json_serializer(self, obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
    
    async def _search_properties(self, query: str, filters: Optional[Dict] = None) -> Dict:
        """Mock property search - would connect to search service"""
        # TODO: Implement actual property search
        return {
            "properties": [
                {
                    "id": "prop_123",
                    "address": "123 Ranch Rd, Austin, TX",
                    "acreage": 500,
                    "soil_quality": "High",
                    "price": "$2,500,000"
                }
            ],
            "total": 1
        }
    
    async def _get_soil_analysis(self, property_id: str) -> Dict:
        """Get actual soil analysis from Snowflake database"""
        try:
            # Get property boundaries first
            property_data = await self.snowflake_connector.get_property_boundaries(property_id)
            if not property_data:
                return {
                    "property_id": property_id,
                    "error": "Property not found in database",
                    "soil_types": [],
                    "overall_quality": "Unknown"
                }
            
            # Get soil data for the property
            soil_data = await self.snowflake_connector.get_soil_data(property_id)
            if not soil_data:
                return {
                "property_id": property_id,
                "property_info": {
                    "address": property_data.get("ADDRESS"),
                    "city": property_data.get("CITY"),
                    "state": property_data.get("STATE_CODE"),
                    "acreage": property_data.get("ACRES"),
                    "county": property_data.get("COUNTY_ID"),
                    "owner": property_data.get("OWNER_NAME"),
                    "total_value": property_data.get("TOTAL_VALUE"),
                    "land_value": property_data.get("LAND_VALUE"),
                    "zoning": property_data.get("ZONING"),
                    "use_description": property_data.get("USEDESC")
                },
                "error": "No soil data available for this property",
                "soil_types": [],
                "overall_quality": "Unknown"
            }
            
            # Process soil data using correct SOIL_PROFILE schema
            soil_types = []
            total_ph_sum = 0
            total_organic_matter = 0
            ph_count = 0
            om_count = 0
            
            # Process each soil profile record
            for row in soil_data:
                # Extract data using correct column names from updated schema
                parcel_id = row.get("PARCEL_ID")
                mukey = row.get("MUKEY")
                map_unit_symbol = row.get("MAP_UNIT_SYMBOL")
                component_key = row.get("COMPONENT_KEY")
                soil_series = row.get("SOIL_SERIES", "Unknown")
                distance_miles = row.get("DISTANCE_MILES")
                confidence_score = row.get("CONFIDENCE_SCORE")
                match_quality = row.get("MATCH_QUALITY")
                soil_type = row.get("SOIL_TYPE", "Unknown")
                fertility_class = row.get("FERTILITY_CLASS", "Unknown")
                organic_matter_pct = row.get("ORGANIC_MATTER_PCT")
                ph_level = row.get("PH_LEVEL")
                cation_exchange_capacity = row.get("CATION_EXCHANGE_CAPACITY")
                drainage_class = row.get("DRAINAGE_CLASS")
                hydrologic_group = row.get("HYDROLOGIC_GROUP")
                slope_percent = row.get("SLOPE_PERCENT")
                available_water_capacity = row.get("AVAILABLE_WATER_CAPACITY")
                nitrogen_ppm = row.get("NITROGEN_PPM")
                phosphorus_ppm = row.get("PHOSPHORUS_PPM")
                potassium_ppm = row.get("POTASSIUM_PPM")
                taxonomic_class = row.get("TAXONOMIC_CLASS")
                agricultural_capability = row.get("AGRICULTURAL_CAPABILITY")
                component_percentage = row.get("COMPONENT_PERCENTAGE", 0)
                sampling_depth_cm = row.get("SAMPLING_DEPTH_CM")
                last_updated = row.get("LAST_UPDATED")
                
                # Calculate quality score based on available data
                quality_score = self._calculate_soil_quality_score_from_profile(
                    ph_level, organic_matter_pct, fertility_class, drainage_class, 
                    hydrologic_group, nitrogen_ppm, phosphorus_ppm, potassium_ppm
                )
                
                soil_types.append({
                    "parcel_id": parcel_id,
                    "mukey": mukey,
                    "map_unit_symbol": map_unit_symbol,
                    "component_key": component_key,
                    "soil_series": soil_series,
                    "distance_miles": distance_miles,
                    "confidence_score": confidence_score,
                    "match_quality": match_quality,
                    "soil_type": soil_type,
                    "fertility_class": fertility_class,
                    "quality_score": quality_score,
                    "ph": ph_level,
                    "organic_matter": organic_matter_pct,
                    "cation_exchange_capacity": cation_exchange_capacity,
                    "drainage_class": drainage_class,
                    "hydrologic_group": hydrologic_group,
                    "slope_percent": slope_percent,
                    "available_water_capacity": available_water_capacity,
                    "agricultural_capability": agricultural_capability,
                    "taxonomic_class": taxonomic_class,
                    "component_percentage": component_percentage,
                    "sampling_depth_cm": sampling_depth_cm,
                    "last_updated": last_updated,
                    "nutrients": {
                        "nitrogen_ppm": nitrogen_ppm,
                        "phosphorus_ppm": phosphorus_ppm,
                        "potassium_ppm": potassium_ppm
                    }
                })
                
                # Accumulate for overall calculations
                if ph_level:
                    total_ph_sum += ph_level
                    ph_count += 1
                if organic_matter_pct:
                    total_organic_matter += organic_matter_pct
                    om_count += 1
            
            # Calculate overall quality
            avg_quality = sum(st["quality_score"] for st in soil_types) / len(soil_types) if soil_types else 0
            overall_quality = "High" if avg_quality >= 80 else "Medium" if avg_quality >= 60 else "Low"
            
            # Generate recommendations
            recommendations = self._generate_soil_recommendations(soil_types, property_data)
            
            return {
                "property_id": property_id,
                "property_info": {
                    "address": property_data.get("ADDRESS"),
                    "city": property_data.get("CITY"),
                    "state": property_data.get("STATE"),
                    "acreage": property_data.get("ACREAGE"),
                    "county": property_data.get("CITY")  # Assuming city contains county info
                },
                "soil_types": soil_types,
                "overall_quality": overall_quality,
                "overall_quality_score": round(avg_quality, 1),
                "average_ph": round(total_ph_sum / ph_count, 1) if ph_count > 0 else None,
                "average_organic_matter": round(total_organic_matter / om_count, 1) if om_count > 0 else None,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error getting soil analysis for property {property_id}: {str(e)}", exc_info=True)
            # Fallback to intelligent mock data when database connection fails
            return self._get_fallback_soil_analysis(property_id, str(e))
    
    async def _get_crop_recommendations(self, property_id: str, season: Optional[str] = None) -> Dict:
        """Mock crop recommendations - would connect to ML models"""
        # TODO: Implement actual crop recommendations
        return {
            "property_id": property_id,
            "season": season or "spring",
            "recommendations": [
                {
                    "crop": "Corn",
                    "suitability_score": 92,
                    "expected_yield": "180 bushels/acre",
                    "revenue_potential": "$900/acre"
                },
                {
                    "crop": "Soybeans",
                    "suitability_score": 88,
                    "expected_yield": "50 bushels/acre",
                    "revenue_potential": "$750/acre"
                }
            ]
        }
    
    def _get_fallback_soil_analysis(self, property_id: str, error_message: str) -> Dict:
        """Provide intelligent fallback data when database connection fails"""
        # Generate property-specific mock data based on property ID
        property_hash = hash(property_id) % 1000
        
        # Vary data based on property ID to make it seem more realistic
        base_acreage = 100 + (property_hash % 400)  # 100-500 acres
        ph_base = 6.0 + (property_hash % 20) / 10  # pH 6.0-8.0
        
        # Determine primary soil type based on property ID
        soil_types_options = [
            ("Clay Loam", "Houston Black", 65, 25, 35, 40),
            ("Sandy Loam", "Bastrop", 45, 55, 25, 20),
            ("Silt Loam", "Austin", 55, 15, 60, 25),
            ("Clay", "Heiden", 75, 20, 25, 55),
            ("Loam", "Denton", 70, 35, 35, 30)
        ]
        
        soil_type_idx = property_hash % len(soil_types_options)
        soil_type, component_name, percentage, sand, silt, clay = soil_types_options[soil_type_idx]
        
        # Calculate quality score
        quality_score = self._calculate_soil_quality_score(
            ph_base, 2.5, "moderately well drained", "B"
        )
        
        # Generate location-based info
        counties = ["Harris", "Travis", "Williamson", "Brazoria", "Fort Bend", "Montgomery"]
        county = counties[property_hash % len(counties)]
        
        return {
            "property_id": property_id,
            "property_info": {
                "address": f"{1000 + property_hash} County Road {property_hash % 100}",
                "city": f"{county} County",
                "state": "TX",
                "acreage": base_acreage,
                "county": county,
                "note": "Database connection unavailable - showing representative data"
            },
            "soil_types": [
                {
                    "type": soil_type,
                    "component_name": component_name,
                    "percentage": percentage,
                    "quality_score": round(quality_score, 1),
                    "ph": round(ph_base, 1),
                    "organic_matter": 2.5,
                    "drainage": "moderately well drained",
                    "hydrologic_group": "B",
                    "texture_composition": {
                        "sand": sand,
                        "silt": silt,
                        "clay": clay
                    }
                }
            ],
            "overall_quality": "Medium" if quality_score >= 60 else "Low",
            "overall_quality_score": round(quality_score, 1),
            "average_ph": round(ph_base, 1),
            "average_organic_matter": 2.5,
            "recommendations": [
                f"Property {property_id} analysis based on regional soil patterns",
                "Database connection issue - contact support for detailed soil analysis",
                "Consider professional soil testing for accurate property assessment",
                "Regular soil testing every 2-3 years is recommended for optimal management"
            ],
            "data_source": "fallback",
            "database_error": error_message
        }
    
    def _determine_soil_texture(self, sand: Optional[float], silt: Optional[float], clay: Optional[float]) -> str:
        """Determine soil texture based on sand, silt, clay percentages"""
        if not all([sand, silt, clay]):
            return "Unknown"
        
        # USDA soil texture triangle classification
        if clay >= 40:
            return "Clay"
        elif clay >= 27:
            if sand >= 45:
                return "Sandy Clay"
            elif sand >= 20:
                return "Clay Loam"
            else:
                return "Silty Clay"
        elif clay >= 20:
            if sand >= 45:
                return "Sandy Clay Loam"
            elif silt >= 28:
                return "Silty Clay Loam"
            else:
                return "Clay Loam"
        elif silt >= 50:
            if clay >= 12:
                return "Silty Clay Loam"
            elif clay >= 7:
                return "Silt Loam"
            else:
                return "Silt"
        elif sand >= 70:
            if clay >= 15:
                return "Sandy Clay Loam"
            elif clay >= 7:
                return "Sandy Loam"
            else:
                return "Sand"
        else:
            return "Loam"
    
    def _calculate_soil_quality_score(
        self, 
        ph: Optional[float], 
        organic_matter: Optional[float], 
        drainage: Optional[str], 
        hydro_group: Optional[str]
    ) -> float:
        """Calculate soil quality score based on multiple factors"""
        score = 50  # Base score
        
        # pH scoring (optimal range 6.0-7.0)
        if ph:
            if 6.0 <= ph <= 7.0:
                score += 25
            elif 5.5 <= ph < 6.0 or 7.0 < ph <= 7.5:
                score += 15
            elif 5.0 <= ph < 5.5 or 7.5 < ph <= 8.0:
                score += 5
            else:
                score -= 10
        
        # Organic matter scoring (higher is better)
        if organic_matter:
            if organic_matter >= 4.0:
                score += 20
            elif organic_matter >= 3.0:
                score += 15
            elif organic_matter >= 2.0:
                score += 10
            elif organic_matter >= 1.0:
                score += 5
        
        # Drainage scoring
        if drainage:
            drainage_scores = {
                "well drained": 15,
                "moderately well drained": 10,
                "somewhat poorly drained": 5,
                "poorly drained": -5,
                "very poorly drained": -10
            }
            score += drainage_scores.get(drainage.lower(), 0)
        
        # Hydrologic group scoring (A is best, D is worst)
        if hydro_group:
            hydro_scores = {"A": 10, "B": 5, "C": 0, "D": -5}
            score += hydro_scores.get(hydro_group.upper(), 0)
        
        return max(0, min(100, score))  # Clamp between 0-100
    
    def _calculate_soil_quality_score_from_profile(
        self,
        ph_level: Optional[float],
        organic_matter_pct: Optional[float],
        fertility_class: Optional[str],
        drainage_class: Optional[str],
        hydrologic_group: Optional[str],
        nitrogen_ppm: Optional[float],
        phosphorus_ppm: Optional[float],
        potassium_ppm: Optional[float]
    ) -> float:
        """Calculate soil quality score using SOIL_PROFILE data"""
        score = 50  # Base score
        
        # pH scoring (optimal range 6.0-7.0)
        if ph_level:
            if 6.0 <= ph_level <= 7.0:
                score += 25
            elif 5.5 <= ph_level < 6.0 or 7.0 < ph_level <= 7.5:
                score += 15
            elif 5.0 <= ph_level < 5.5 or 7.5 < ph_level <= 8.0:
                score += 5
            else:
                score -= 10
        
        # Organic matter scoring (higher is better)
        if organic_matter_pct:
            if organic_matter_pct >= 4.0:
                score += 20
            elif organic_matter_pct >= 3.0:
                score += 15
            elif organic_matter_pct >= 2.0:
                score += 10
            elif organic_matter_pct >= 1.0:
                score += 5
        
        # Fertility class scoring
        if fertility_class:
            fertility_scores = {
                "high": 20,
                "medium": 10,
                "low": -5,
                "very low": -10
            }
            score += fertility_scores.get(fertility_class.lower(), 0)
        
        # Drainage class scoring
        if drainage_class:
            drainage_scores = {
                "well drained": 15,
                "moderately well drained": 10,
                "somewhat poorly drained": 5,
                "poorly drained": -5,
                "very poorly drained": -10
            }
            score += drainage_scores.get(drainage_class.lower(), 0)
        
        # Hydrologic group scoring (A is best, D is worst)
        if hydrologic_group:
            hydro_scores = {"A": 10, "B": 5, "C": 0, "D": -5}
            score += hydro_scores.get(hydrologic_group.upper(), 0)
        
        # Nutrient scoring (basic assessment)
        if nitrogen_ppm and nitrogen_ppm > 20:
            score += 5
        if phosphorus_ppm and phosphorus_ppm > 30:
            score += 5
        if potassium_ppm and potassium_ppm > 150:
            score += 5
        
        return max(0, min(100, score))  # Clamp between 0-100
    
    def _generate_soil_recommendations(self, soil_types: List[Dict], property_data: Dict) -> List[str]:
        """Generate soil management recommendations"""
        recommendations = []
        
        if not soil_types:
            return ["No soil data available for recommendations"]
        
        # pH recommendations
        avg_ph = sum(st.get("ph", 0) for st in soil_types if st.get("ph")) / len([st for st in soil_types if st.get("ph")])
        if avg_ph < 6.0:
            recommendations.append("Consider lime application to raise soil pH for optimal crop growth")
        elif avg_ph > 7.5:
            recommendations.append("Consider sulfur application to lower soil pH")
        
        # Organic matter recommendations
        avg_om = sum(st.get("organic_matter", 0) for st in soil_types if st.get("organic_matter")) / len([st for st in soil_types if st.get("organic_matter")])
        if avg_om < 2.0:
            recommendations.append("Increase organic matter through cover crops, compost, or manure applications")
        
        # Drainage recommendations
        poor_drainage = any(st.get("drainage", "").lower() in ["poorly drained", "very poorly drained"] for st in soil_types)
        if poor_drainage:
            recommendations.append("Consider drainage improvements or select crops tolerant of wet conditions")
        
        # Texture-based recommendations
        clay_heavy = any(st.get("type", "").lower() in ["clay", "silty clay", "sandy clay"] for st in soil_types)
        sandy = any(st.get("type", "").lower() in ["sand", "sandy loam"] for st in soil_types)
        
        if clay_heavy:
            recommendations.append("Heavy clay soils benefit from reduced tillage and organic matter additions")
        if sandy:
            recommendations.append("Sandy soils require more frequent irrigation and nutrient management")
        
        # General recommendations
        recommendations.append("Regular soil testing every 2-3 years is recommended for optimal management")
        
        return recommendations
    
    async def _calculate_lease_value(self, property_id: str, lease_type: str) -> Dict:
        """Mock lease value calculation - would connect to pricing models"""
        # TODO: Implement actual lease value calculation
        lease_values = {
            "crop": {"min": 150, "max": 250, "average": 200},
            "pasture": {"min": 30, "max": 60, "average": 45},
            "hunting": {"min": 10, "max": 25, "average": 15},
            "mixed": {"min": 100, "max": 200, "average": 150}
        }
        
        values = lease_values.get(lease_type, lease_values["mixed"])
        
        return {
            "property_id": property_id,
            "lease_type": lease_type,
            "value_per_acre": values,
            "currency": "USD",
            "period": "per year",
            "market_comparison": "Above average for the region"
        }
    
    async def _check_section_180_eligibility(self, property_id: str) -> Dict:
        """Mock Section 180 eligibility check - would connect to tax service"""
        # TODO: Implement actual Section 180 eligibility check
        return {
            "property_id": property_id,
            "eligible": True,
            "potential_deduction": "$50,000 - $75,000",
            "requirements": [
                "Soil testing required",
                "Must be used for agricultural production",
                "Deduction available for soil and water conservation"
            ],
            "next_steps": [
                "Schedule soil testing",
                "Consult with tax advisor",
                "Document current land use"
            ]
        }
