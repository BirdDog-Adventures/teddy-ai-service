# Teddy AI Service - BirdDog Land Intelligence Platform

Teddy is an AI-powered land intelligence platform that provides conversational AI capabilities, semantic search, and intelligent insights for landowners, farmers, hunters, and internal users.

## Overview

Teddy leverages advanced AI/ML technologies to analyze property data, soil information, agricultural patterns, and market trends to provide actionable insights and recommendations. The service integrates with BirdDog's existing data infrastructure including Snowflake (for SSURGO soil data and Regrid parcel data) and the operational PostgreSQL database.

## Key Features

- **Conversational AI Interface**: Natural language chat for property queries and insights
- **Semantic Search**: Advanced search capabilities across properties, soil data, and documents
- **Intelligent Insights**: ML-powered land scoring, crop recommendations, and revenue optimization
- **Personalized Recommendations**: Tailored suggestions for property discovery and optimization
- **Real-time Data Integration**: Live connections to Snowflake and operational databases

## Architecture

```
teddy-ai-service/
├── api/                    # FastAPI application
│   ├── core/              # Core configurations and dependencies
│   ├── endpoints/         # API endpoints
│   └── models/           # Pydantic models and schemas
├── services/              # Business logic services
├── data_connectors/       # Database and external API connectors
├── ml_models/            # Machine learning models
├── utils/                # Utility functions
└── tests/                # Test suite
```

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Access to BirdDog's Snowflake instance
- Access to BirdDog's PostgreSQL database
- OpenAI API key
- Redis for caching

## Installation

1. Clone the repository:
```bash
cd birddog-AI-services/teddy-ai-service
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the environment file and configure:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Create a `.env` file with the following variables:

```env
# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=Teddy AI Service
DEBUG=false

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview
EMBEDDING_MODEL=text-embedding-3-small

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/birddog_db

# Snowflake Configuration
SNOWFLAKE_ACCOUNT=JJODRXK-BIRDDOGAWS
SNOWFLAKE_USER=BIRDDOG_SA
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_DATABASE=BIRDDOG_DATA
SNOWFLAKE_SCHEMA=CURATED
SNOWFLAKE_WAREHOUSE=BIRDDOG_WH

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# External APIs
USDA_API_KEY=your-usda-api-key
WEATHER_API_KEY=your-weather-api-key
```

## Running the Service

### Development

```bash
# Run with hot reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Production

```bash
# Run with Gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Chat Endpoints
- `POST /api/v1/chat/message` - Send a message to the AI assistant
- `GET /api/v1/chat/history/{conversation_id}` - Get conversation history
- `DELETE /api/v1/chat/conversation/{conversation_id}` - Clear a conversation

### Search Endpoints
- `POST /api/v1/search/properties` - Semantic search for properties
- `POST /api/v1/search/insights` - Search agricultural insights
- `GET /api/v1/search/suggestions` - Get search suggestions

### Insights Endpoints
- `GET /api/v1/insights/property/{property_id}` - Get property insights
- `GET /api/v1/insights/portfolio/{user_id}` - Portfolio analysis
- `POST /api/v1/insights/compare` - Compare multiple properties

### Recommendations Endpoints
- `GET /api/v1/recommendations/properties/{user_id}` - Property recommendations
- `GET /api/v1/recommendations/crops/{property_id}` - Crop recommendations
- `GET /api/v1/recommendations/revenue/{property_id}` - Revenue optimization

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov=services --cov=ml_models

# Run specific test file
pytest tests/test_chat_service.py
```

## Development

### Code Style

We use Black for code formatting and flake8 for linting:

```bash
# Format code
black .

# Run linter
flake8 .
```

### Adding New Features

1. Create new endpoints in `api/endpoints/`
2. Add business logic in `services/`
3. Update schemas in `api/models/`
4. Add tests in `tests/`
5. Update documentation

## Monitoring

The service includes Prometheus metrics exposed at `/metrics`. Key metrics:
- Request count and latency
- AI model inference time
- Database query performance
- Cache hit rates

## Deployment

### Kubernetes

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/
```

### Environment Variables

Ensure all required environment variables are set in your deployment environment.

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Submit a pull request

## License

Proprietary - BirdDog, Inc.
