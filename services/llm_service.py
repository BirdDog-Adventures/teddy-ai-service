"""
LLM Service for generating AI responses
"""
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple
import logging
import json
from tenacity import retry, stop_after_attempt, wait_exponential

from api.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Use gpt-3.5-turbo as gpt-4-turbo-preview might not be available
        self.model = "gpt-3.5-turbo"  # Override config for now
        self.max_tokens = settings.MAX_TOKENS
        self.temperature = settings.TEMPERATURE
    
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
        """Generate AI response using OpenAI"""
        try:
            # Build messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add context if available
            if property_context or user_preferences:
                context_message = self._build_context_message(property_context, user_preferences)
                messages.append({"role": "system", "content": context_message})
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                tools=self._get_available_tools(),
                tool_choice="auto"
            )
            
            # Extract response and any tool calls
            message = response.choices[0].message
            content = message.content
            sources = None
            
            # Handle tool calls if any
            if message.tool_calls:
                sources = await self._handle_tool_calls(message.tool_calls)
                
                # Generate final response with tool results
                messages.append(message.model_dump())
                for tool_call in message.tool_calls:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(sources[0]) if sources else "No data found"
                    })
                
                # Get final response
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                content = final_response.choices[0].message.content
            
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
    
    async def _handle_tool_calls(self, tool_calls) -> Optional[List[Dict[str, Any]]]:
        """Handle function tool calls"""
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
        """Mock soil analysis - would connect to insights service"""
        # TODO: Implement actual soil analysis
        return {
            "property_id": property_id,
            "soil_types": [
                {
                    "type": "Clay Loam",
                    "percentage": 60,
                    "quality_score": 85,
                    "ph": 6.5
                },
                {
                    "type": "Sandy Loam",
                    "percentage": 40,
                    "quality_score": 75,
                    "ph": 6.8
                }
            ],
            "overall_quality": "High",
            "recommendations": [
                "Ideal for corn and soybeans",
                "Consider lime application to optimize pH"
            ]
        }
    
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
