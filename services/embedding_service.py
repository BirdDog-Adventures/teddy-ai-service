"""
Embedding Service for semantic search and similarity
"""
import openai
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from api.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}", exc_info=True)
            raise
    
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts"""
        try:
            # OpenAI can handle batch embeddings
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}", exc_info=True)
            raise
    
    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def create_property_embedding(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create embedding for property data"""
        # Combine relevant property information into text
        text_parts = []
        
        if property_data.get("address"):
            text_parts.append(f"Address: {property_data['address']}")
        
        if property_data.get("acreage"):
            text_parts.append(f"Acreage: {property_data['acreage']} acres")
        
        if property_data.get("county"):
            text_parts.append(f"County: {property_data['county']}")
        
        if property_data.get("state"):
            text_parts.append(f"State: {property_data['state']}")
        
        if property_data.get("soil_types"):
            soil_info = ", ".join([f"{soil['type']} ({soil['percentage']}%)" 
                                 for soil in property_data['soil_types']])
            text_parts.append(f"Soil Types: {soil_info}")
        
        if property_data.get("current_use"):
            text_parts.append(f"Current Use: {property_data['current_use']}")
        
        if property_data.get("crop_history"):
            crops = ", ".join([crop['crop'] for crop in property_data['crop_history'][-3:]])
            text_parts.append(f"Recent Crops: {crops}")
        
        if property_data.get("features"):
            features = ", ".join(property_data['features'])
            text_parts.append(f"Features: {features}")
        
        # Create combined text
        property_text = " | ".join(text_parts)
        
        # Generate embedding
        embedding = await self.create_embedding(property_text)
        
        return {
            "property_id": property_data.get("property_id"),
            "content": property_text,
            "embedding": embedding,
            "metadata": {
                "acreage": property_data.get("acreage"),
                "county": property_data.get("county"),
                "state": property_data.get("state"),
                "soil_quality": property_data.get("soil_quality")
            }
        }
    
    async def create_insight_embedding(self, insight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create embedding for agricultural insights"""
        # Combine insight information
        text_parts = []
        
        if insight_data.get("insight_type"):
            text_parts.append(f"Type: {insight_data['insight_type']}")
        
        if insight_data.get("title"):
            text_parts.append(f"Title: {insight_data['title']}")
        
        if insight_data.get("description"):
            text_parts.append(f"Description: {insight_data['description']}")
        
        if insight_data.get("recommendations"):
            recs = " ".join(insight_data['recommendations'])
            text_parts.append(f"Recommendations: {recs}")
        
        if insight_data.get("tags"):
            tags = ", ".join(insight_data['tags'])
            text_parts.append(f"Tags: {tags}")
        
        # Create combined text
        insight_text = " | ".join(text_parts)
        
        # Generate embedding
        embedding = await self.create_embedding(insight_text)
        
        return {
            "insight_type": insight_data.get("insight_type"),
            "content": insight_text,
            "embedding": embedding,
            "metadata": insight_data
        }
    
    def find_similar_embeddings(
        self,
        query_embedding: List[float],
        embeddings: List[Dict[str, Any]],
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find similar embeddings using cosine similarity"""
        results = []
        
        for item in embeddings:
            similarity = self.cosine_similarity(query_embedding, item["embedding"])
            
            if similarity >= threshold:
                results.append({
                    **item,
                    "similarity_score": similarity
                })
        
        # Sort by similarity score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return results[:top_k]
    
    async def search_properties_semantic(
        self,
        query: str,
        property_embeddings: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Semantic search for properties"""
        # Create query embedding
        query_embedding = await self.create_embedding(query)
        
        # Apply filters if provided
        if filters:
            filtered_embeddings = self._apply_filters(property_embeddings, filters)
        else:
            filtered_embeddings = property_embeddings
        
        # Find similar properties
        similar_properties = self.find_similar_embeddings(
            query_embedding,
            filtered_embeddings,
            top_k=top_k
        )
        
        return similar_properties
    
    def _apply_filters(
        self,
        embeddings: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filters to embeddings"""
        filtered = embeddings
        
        if filters.get("min_acreage"):
            filtered = [e for e in filtered 
                       if e.get("metadata", {}).get("acreage", 0) >= filters["min_acreage"]]
        
        if filters.get("max_acreage"):
            filtered = [e for e in filtered 
                       if e.get("metadata", {}).get("acreage", float('inf')) <= filters["max_acreage"]]
        
        if filters.get("county"):
            filtered = [e for e in filtered 
                       if e.get("metadata", {}).get("county", "").lower() == filters["county"].lower()]
        
        if filters.get("state"):
            filtered = [e for e in filtered 
                       if e.get("metadata", {}).get("state", "").lower() == filters["state"].lower()]
        
        if filters.get("soil_quality"):
            filtered = [e for e in filtered 
                       if e.get("metadata", {}).get("soil_quality", "").lower() == filters["soil_quality"].lower()]
        
        return filtered
    
    async def create_query_expansion(self, query: str) -> List[str]:
        """Expand query with related terms for better search"""
        # Use LLM to generate related terms
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Generate 3-5 related search terms for agricultural property search. Return only the terms, one per line."
                    },
                    {
                        "role": "user",
                        "content": f"Original query: {query}"
                    }
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            expanded_terms = response.choices[0].message.content.strip().split('\n')
            return [query] + [term.strip() for term in expanded_terms if term.strip()]
            
        except Exception as e:
            logger.error(f"Error in query expansion: {str(e)}")
            return [query]
