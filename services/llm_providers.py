"""
Multi-provider LLM service supporting OpenAI, Anthropic, Google, Azure, and Ollama
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import logging
import json
from decimal import Decimal

from api.core.config import settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""
    
    def __init__(self):
        self.max_tokens = settings.MAX_TOKENS
        self.temperature = settings.TEMPERATURE
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """Generate response from the LLM"""
        pass
    
    def _json_serializer(self, obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider"""
    
    def __init__(self):
        super().__init__()
        try:
            from openai import OpenAI
            # Only set base_url if it's not empty/None/whitespace
            client_kwargs = {"api_key": settings.OPENAI_API_KEY}
            if settings.OPENAI_BASE_URL and settings.OPENAI_BASE_URL.strip():
                client_kwargs["base_url"] = settings.OPENAI_BASE_URL.strip()
            
            self.client = OpenAI(**client_kwargs)
            self.model = settings.LLM_MODEL or settings.OPENAI_MODEL
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """Generate response using OpenAI"""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            response = self.client.chat.completions.create(**kwargs)
            
            message = response.choices[0].message
            content = message.content
            tool_calls = None
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            return content, tool_calls
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self):
        super().__init__()
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            # Use Anthropic-specific model, not the generic LLM_MODEL
            self.model = settings.ANTHROPIC_MODEL
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """Generate response using Anthropic Claude"""
        try:
            # Convert OpenAI format to Anthropic format
            system_messages = []
            claude_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_messages.append(msg["content"])
                else:
                    claude_messages.append(msg)
            
            # If no user/assistant messages, create a default user message
            if not claude_messages:
                claude_messages.append({
                    "role": "user",
                    "content": "Hello, please help me with agricultural and land management questions."
                })
            
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": claude_messages
            }
            
            # Combine all system messages
            if system_messages:
                kwargs["system"] = "\n\n".join(system_messages)
            
            if tools:
                # Convert OpenAI tools format to Anthropic format
                claude_tools = []
                for tool in tools:
                    if tool["type"] == "function":
                        claude_tools.append({
                            "name": tool["function"]["name"],
                            "description": tool["function"]["description"],
                            "input_schema": tool["function"]["parameters"]
                        })
                kwargs["tools"] = claude_tools
            
            response = self.client.messages.create(**kwargs)
            
            content = ""
            tool_calls = None
            
            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": block.id,
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input)
                        }
                    })
            
            return content, tool_calls
            
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider"""
    
    def __init__(self):
        super().__init__()
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            # Use Google-specific model, not the generic LLM_MODEL
            self.model = genai.GenerativeModel(settings.GOOGLE_MODEL)
        except ImportError:
            raise ImportError("Google AI package not installed. Run: pip install google-generativeai")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """Generate response using Google Gemini"""
        try:
            # Convert messages to Gemini format
            prompt = ""
            for msg in messages:
                role = "Human" if msg["role"] == "user" else "Assistant"
                if msg["role"] == "system":
                    role = "System"
                prompt += f"{role}: {msg['content']}\n\n"
            
            prompt += "Assistant: "
            
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            content = response.text
            # Note: Google Gemini function calling would need additional setup
            tool_calls = None
            
            return content, tool_calls
            
        except Exception as e:
            logger.error(f"Google API error: {str(e)}")
            raise


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI provider"""
    
    def __init__(self):
        super().__init__()
        try:
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
            self.model = settings.AZURE_DEPLOYMENT_NAME or settings.LLM_MODEL
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """Generate response using Azure OpenAI"""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            response = self.client.chat.completions.create(**kwargs)
            
            message = response.choices[0].message
            content = message.content
            tool_calls = None
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            return content, tool_calls
            
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {str(e)}")
            raise


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local models"""
    
    def __init__(self):
        super().__init__()
        try:
            import requests
            self.base_url = settings.OLLAMA_BASE_URL
            self.model = settings.LLM_MODEL or settings.OLLAMA_MODEL
            self.session = requests.Session()
        except ImportError:
            raise ImportError("Requests package not installed. Run: pip install requests")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """Generate response using Ollama"""
        try:
            # Convert messages to a single prompt for Ollama
            prompt = ""
            for msg in messages:
                role = msg["role"].title()
                prompt += f"{role}: {msg['content']}\n\n"
            
            prompt += "Assistant: "
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "")
            
            # Ollama doesn't support function calling natively
            tool_calls = None
            
            return content, tool_calls
            
        except Exception as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise


class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(provider_name: str = None) -> BaseLLMProvider:
        """Create an LLM provider instance"""
        provider_name = provider_name or settings.LLM_PROVIDER
        
        providers = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "google": GoogleProvider,
            "azure": AzureOpenAIProvider,
            "ollama": OllamaProvider
        }
        
        if provider_name not in providers:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
        
        try:
            return providers[provider_name]()
        except Exception as e:
            logger.error(f"Failed to initialize {provider_name} provider: {str(e)}")
            # Fallback to OpenAI if available
            if provider_name != "openai" and settings.OPENAI_API_KEY:
                logger.warning(f"Falling back to OpenAI provider")
                return OpenAIProvider()
            raise
