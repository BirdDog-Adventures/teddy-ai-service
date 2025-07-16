# Teddy AI Service Architecture

## Overview

The Teddy AI Service is a comprehensive land intelligence platform that leverages AI/ML technologies to provide insights for landowners, farmers, hunters, and internal users. The service integrates with BirdDog's existing data infrastructure including Snowflake (SSURGO soil data, Regrid parcel data) and operational PostgreSQL database.

## Technology Stack

- **Framework**: FastAPI (Python 3.9+)
- **AI/ML**: OpenAI GPT-4, Embeddings, scikit-learn
- **Databases**: PostgreSQL with pgvector, Snowflake, Redis
- **Task Queue**: Celery with Redis
- **Containerization**: Docker & Docker Compose
- **Monitoring**: Prometheus, Grafana

## Service Architecture

```
birddog-AI-services/
└── teddy-ai-service/
    ├── api/                    # FastAPI application
    │   ├── core/              # Core configurations
    │   │   ├── config.py      # Settings management
    │   │   ├── security.py    # Authentication/authorization
    │   │   └── dependencies.py # Shared dependencies
    │   ├── endpoints/         # API endpoints
    │   │   ├── chat.py       # Conversational AI
    │   │   ├── search.py     # Semantic search
    │   │   ├── insights.py   # Property insights
    │   │   └── recommendations.py # ML recommendations
    │   ├── models/           # Data models
    │   │   ├── schemas.py    # Pydantic schemas
    │   │   └── database.py   # SQLAlchemy models
    │   └── main.py          # Application entry point
    ├── services/            # Business logic
    │   ├── llm_service.py   # LLM integration
    │   ├── embedding_service.py # Vector embeddings
    │   └── search_service.py # Search functionality
    ├── data_connectors/     # External data sources
    │   └── snowflake_connector.py # Snowflake integration
    ├── ml_models/          # Machine learning models
    └── utils/              # Utility functions
```

## Key Features

### 1. Conversational AI Interface
- Natural language chat for property queries
- Context-aware responses using property and user data
- Multi-turn conversations with memory
- Specialized conversation types:
  - General inquiries
  - Property-specific discussions
  - Soil analysis
  - Crop recommendations
  - Lease assistance
  - Tax optimization

### 2. Semantic Search
- Vector embeddings for all property data
- Hybrid search combining keyword and semantic similarity
- Faceted search with filters:
  - Location (county, state, coordinates)
  - Property characteristics (acreage, soil quality)
  - Financial metrics
  - Agricultural features

### 3. Intelligent Insights
- **Land Quality Scoring**: ML model analyzing soil data, topography, and historical yields
- **Crop Recommendations**: Based on soil analysis, climate data, and market trends
- **Revenue Optimization**: Suggestions for leasing, Section 180, conservation programs
- **Risk Assessment**: Weather patterns, flood zones, drought susceptibility

### 4. Personalized Recommendations
- Property discovery suggestions based on user preferences
- Lease matching between landowners and farmers
- Conservation program eligibility alerts
- Tax optimization opportunities

## API Endpoints

### Chat Endpoints
- `POST /api/v1/chat/message` - Send message to AI assistant
- `GET /api/v1/chat/history/{conversation_id}` - Get conversation history
- `DELETE /api/v1/chat/conversation/{conversation_id}` - Clear conversation

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

## Data Integration

### Snowflake Integration
- **SSURGO Soil Data**: Detailed soil characteristics, quality metrics
- **Regrid Parcel Data**: Property boundaries, ownership, assessments
- **Crop History**: Historical crop data from USDA CDL
- **Market Data**: Agricultural commodity prices and trends

### PostgreSQL Database
- User profiles and preferences
- Conversation history
- Property embeddings for semantic search
- Cached insights and recommendations
- Search history and analytics

### External APIs
- USDA APIs for real-time agricultural data
- Weather APIs for climate insights
- Market price APIs for crop valuations
- Satellite imagery APIs for land monitoring

## Security

- JWT-based authentication with Auth0 integration
- Role-based access control (RBAC)
- Rate limiting per user
- Data encryption at rest and in transit
- API key management for external services

## Deployment

### Local Development
```bash
# Install dependencies
make install

# Run locally
make run

# Run tests
make test
```

### Docker Deployment
```bash
# Build and start services
make docker-build
make docker-up

# Stop services
make docker-down
```

### Production Deployment
- Kubernetes-ready with health checks
- Horizontal scaling for API and workers
- Database connection pooling
- Redis for caching and session management
- Prometheus metrics for monitoring

## Performance Targets

- API response time: <200ms (P95)
- Search response: <500ms (P95)
- Chat response: <3s including AI generation
- Concurrent users: 10,000+
- Uptime: 99.99%

## Future Enhancements

1. **Advanced ML Models**
   - Custom fine-tuned models for agricultural domain
   - Computer vision for satellite imagery analysis
   - Time series forecasting for crop yields

2. **Real-time Features**
   - WebSocket support for live chat
   - Real-time property monitoring alerts
   - Market price streaming

3. **Mobile Optimization**
   - Progressive Web App (PWA) support
   - Offline capability for field use
   - Mobile-specific API optimizations

4. **Integration Expansion**
   - Payment processing for leases
   - Insurance provider APIs
   - Government subsidy programs
   - Agricultural equipment marketplaces
