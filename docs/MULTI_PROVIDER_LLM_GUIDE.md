# Multi-Provider LLM Guide

The Teddy AI Service now supports multiple LLM providers, giving you flexibility to choose the best model for your needs and budget.

## Supported Providers

### 1. OpenAI (Default)
- **Models**: GPT-3.5-turbo, GPT-4, GPT-4-turbo
- **Features**: Function calling, streaming, high quality responses
- **Best for**: Production use, complex reasoning, function calling

### 2. Anthropic Claude
- **Models**: Claude-3-sonnet, Claude-3-opus, Claude-3-haiku
- **Features**: Large context window, safety-focused, excellent reasoning
- **Best for**: Long documents, safety-critical applications

### 3. Google Gemini
- **Models**: Gemini-pro, Gemini-pro-vision
- **Features**: Multimodal capabilities, competitive pricing
- **Best for**: Cost-effective solutions, image analysis

### 4. Azure OpenAI
- **Models**: Same as OpenAI but hosted on Azure
- **Features**: Enterprise security, compliance, regional deployment
- **Best for**: Enterprise deployments, compliance requirements

### 5. Ollama (Local Models)
- **Models**: Llama2, Mistral, CodeLlama, and many others
- **Features**: Local deployment, no API costs, privacy
- **Best for**: Development, privacy-sensitive applications, cost control

## Configuration

### Environment Variables

Set these in your `.env` file:

```bash
# Primary LLM Configuration
LLM_PROVIDER=openai  # Choose: openai, anthropic, google, azure, ollama
LLM_MODEL=gpt-3.5-turbo
MAX_TOKENS=4000
TEMPERATURE=0.7

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=  # Optional: for custom endpoints

# Anthropic Configuration (optional)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Google Configuration (optional)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_MODEL=gemini-pro

# Azure OpenAI Configuration (optional)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_DEPLOYMENT_NAME=your_deployment_name

# Ollama Configuration (for local models)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

## Setup Instructions

### 1. OpenAI Setup (Default)
```bash
# Install dependencies (already included)
pip install openai>=1.8.0

# Set environment variables
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_api_key_here
export LLM_MODEL=gpt-3.5-turbo
```

### 2. Anthropic Claude Setup
```bash
# Install Anthropic SDK (quote the version to avoid shell issues)
pip install "anthropic>=0.7.0"

# Set environment variables
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your_api_key_here
export LLM_MODEL=claude-3-sonnet-20240229
```

### 3. Google Gemini Setup
```bash
# Install Google AI SDK (quote the version to avoid shell issues)
pip install "google-generativeai>=0.3.0"

# Set environment variables
export LLM_PROVIDER=google
export GOOGLE_API_KEY=your_api_key_here
export LLM_MODEL=gemini-pro
```

### 4. Azure OpenAI Setup
```bash
# Uses same OpenAI SDK
# Set environment variables
export LLM_PROVIDER=azure
export AZURE_OPENAI_API_KEY=your_api_key_here
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_DEPLOYMENT_NAME=your_deployment_name
```

### 5. Ollama Setup (Local Models)
```bash
# Install Ollama (https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Start Ollama server
ollama serve

# Set environment variables
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=llama2
export OLLAMA_BASE_URL=http://localhost:11434
```

## Model Recommendations

### For Production
- **OpenAI GPT-3.5-turbo**: Best balance of cost and performance
- **OpenAI GPT-4**: Highest quality, more expensive
- **Anthropic Claude-3-sonnet**: Excellent reasoning, large context

### For Development
- **Ollama + Llama2**: Free, local, good for testing
- **OpenAI GPT-3.5-turbo**: Reliable, well-documented

### For Enterprise
- **Azure OpenAI**: Enterprise features, compliance
- **Anthropic Claude**: Safety-focused, constitutional AI

### For Cost Optimization
- **Google Gemini-pro**: Competitive pricing
- **Ollama**: No API costs after setup

## Function Calling Support

| Provider | Function Calling | Tool Use | Notes |
|----------|------------------|----------|-------|
| OpenAI | ✅ Full | ✅ | Native support |
| Anthropic | ✅ Full | ✅ | Native tool use |
| Google | ⚠️ Limited | ⚠️ | Basic support |
| Azure | ✅ Full | ✅ | Same as OpenAI |
| Ollama | ❌ None | ❌ | Text generation only |

## Performance Comparison

| Provider | Speed | Quality | Cost | Context |
|----------|-------|---------|------|---------|
| OpenAI GPT-3.5 | Fast | High | Low | 16K |
| OpenAI GPT-4 | Medium | Highest | High | 128K |
| Claude-3-sonnet | Medium | High | Medium | 200K |
| Gemini-pro | Fast | High | Low | 32K |
| Ollama | Variable | Medium | Free | Variable |

## Switching Providers

You can switch providers at runtime by changing the environment variable:

```bash
# Switch to Claude
export LLM_PROVIDER=anthropic

# Restart the service
docker-compose restart teddy-ai-service
```

Or update your `.env` file and restart.

## Troubleshooting

### Common Issues

1. **Import Error**: Install the required SDK for your provider
2. **API Key Error**: Verify your API key is correct and has sufficient credits
3. **Model Not Found**: Check if the model name is correct for your provider
4. **Function Calling Issues**: Some providers have limited function calling support

### Provider-Specific Issues

#### OpenAI
- Check API key validity at https://platform.openai.com/api-keys
- Verify model availability in your region

#### Anthropic
- Ensure you have access to Claude models
- Check rate limits and usage quotas

#### Google
- Enable the Generative AI API in Google Cloud Console
- Verify API key permissions

#### Azure
- Check deployment name matches your Azure resource
- Verify endpoint URL format

#### Ollama
- Ensure Ollama server is running: `ollama serve`
- Check if model is pulled: `ollama list`

## Cost Optimization Tips

1. **Use GPT-3.5-turbo** for most tasks instead of GPT-4
2. **Set appropriate max_tokens** to avoid unnecessary costs
3. **Use Ollama for development** to avoid API costs
4. **Monitor usage** with provider dashboards
5. **Cache responses** when possible

## Security Considerations

1. **API Keys**: Store securely, rotate regularly
2. **Local Models**: Consider for sensitive data
3. **Rate Limiting**: Implement to prevent abuse
4. **Logging**: Be careful not to log sensitive prompts

## Advanced Configuration

### Custom Model Parameters

You can override model parameters per request:

```python
# In your code
llm_service = LLMService(provider_name="anthropic")
response = await llm_service.generate_response(
    conversation_history=messages,
    system_prompt=prompt,
    # Custom parameters will be passed to the provider
)
```

### Fallback Providers

The system automatically falls back to OpenAI if the primary provider fails (if OpenAI API key is available).

### Load Balancing

For high-volume applications, consider:
1. Multiple API keys for the same provider
2. Round-robin between different providers
3. Provider selection based on request type

## Monitoring and Metrics

Track these metrics for each provider:
- Response time
- Error rate
- Token usage
- Cost per request
- Quality scores

## Future Enhancements

Planned features:
- Automatic provider selection based on request type
- Cost-based routing
- Response quality scoring
- A/B testing between providers
- Streaming support for all providers
