# How to Ask Questions About Specific Properties

## Overview
The Teddy AI chat API supports property-specific conversations that provide detailed insights about individual properties. This guide explains how to structure your requests to get the most relevant information about specific properties.

## API Endpoint
```
POST /api/v1/chat/message
```

## Property-Specific Chat Request Structure

### Basic Property Question
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What crops would grow best on this property?",
    "conversation_type": "property_inquiry",
    "property_id": "PROPERTY_123"
  }'
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | Your question about the property |
| `conversation_type` | string | No | Type of conversation (see types below) |
| `property_id` | string | No | Specific property identifier |
| `conversation_id` | string | No | Continue existing conversation |
| `context` | object | No | Additional context data |

### Conversation Types for Properties

1. **`property_inquiry`** - General property questions
   - "Tell me about this property"
   - "What's the overall assessment?"
   - "Show me property details"

2. **`soil_analysis`** - Soil-focused questions
   - "What's the soil quality like?"
   - "What soil types are present?"
   - "How does the soil affect crop choices?"

3. **`crop_recommendation`** - Agricultural potential
   - "What crops would grow best here?"
   - "What's the expected yield for corn?"
   - "Compare crop profitability options"

4. **`lease_assistance`** - Leasing and revenue
   - "What's the fair lease rate for this property?"
   - "How much revenue could this generate?"
   - "Find potential lessees"

5. **`tax_optimization`** - Tax benefits
   - "Is this property eligible for Section 180?"
   - "What tax deductions are available?"
   - "Calculate potential tax savings"

## Example Conversations

### Starting a Property-Specific Conversation
```json
{
  "message": "I want to learn about property FARM_456",
  "conversation_type": "property_inquiry",
  "property_id": "FARM_456"
}
```

**Response:**
```json
{
  "success": true,
  "conversation_id": "conv_789",
  "response": "I'd be happy to help you learn about property FARM_456. This is a 500-acre property in Travis County, TX, currently used as pasture with high soil quality. What specific aspects would you like to explore?",
  "suggestions": [
    "What crops would grow best here?",
    "What's the lease value for this property?",
    "Is this property eligible for Section 180?"
  ],
  "metadata": {
    "conversation_type": "property_inquiry",
    "property_id": "FARM_456"
  }
}
```

### Continuing the Conversation
```json
{
  "message": "What's the soil composition?",
  "conversation_id": "conv_789",
  "conversation_type": "soil_analysis"
}
```

### Advanced Property Questions

#### Soil Analysis
```json
{
  "message": "Analyze the soil quality and recommend improvements",
  "conversation_type": "soil_analysis",
  "property_id": "FARM_456",
  "context": {
    "focus_areas": ["drainage", "nutrients", "ph_levels"]
  }
}
```

#### Crop Recommendations
```json
{
  "message": "What crops would be most profitable for the next 5 years?",
  "conversation_type": "crop_recommendation",
  "property_id": "FARM_456",
  "context": {
    "timeframe": "5_years",
    "priority": "profitability"
  }
}
```

#### Lease Valuation
```json
{
  "message": "Calculate fair lease rates for different crop types",
  "conversation_type": "lease_assistance",
  "property_id": "FARM_456",
  "context": {
    "lease_type": "cash_rent",
    "comparison_radius": "10_miles"
  }
}
```

## Property Context Information

When you specify a `property_id`, the AI assistant automatically retrieves:

- **Property Details**: Acreage, location, current use
- **Soil Data**: Quality scores, composition, drainage
- **Historical Data**: Past crops, yields, management
- **Market Context**: Local prices, lease rates, trends
- **Regulatory Info**: Zoning, conservation programs, tax benefits

## Best Practices

### 1. Be Specific with Property IDs
```json
// Good
"property_id": "HARRIS_COUNTY_PARCEL_123456"

// Less specific
"property_id": "farm1"
```

### 2. Use Appropriate Conversation Types
Match your question type to get the most relevant system prompts and suggestions.

### 3. Provide Context for Complex Questions
```json
{
  "message": "Compare this property to similar ones in the area",
  "property_id": "FARM_456",
  "context": {
    "comparison_criteria": ["soil_quality", "lease_rates", "crop_yields"],
    "radius_miles": 25,
    "property_size_range": [400, 600]
  }
}
```

### 4. Continue Conversations for Follow-ups
Use the returned `conversation_id` to maintain context across multiple questions about the same property.

## Error Handling

### Property Not Found
```json
{
  "success": false,
  "error": "Property INVALID_123 not found in database",
  "error_code": "PROPERTY_NOT_FOUND"
}
```

### Invalid Conversation Type
```json
{
  "success": false,
  "error": "Invalid conversation type: invalid_type",
  "error_code": "INVALID_CONVERSATION_TYPE"
}
```

## Sample Questions by Category

### General Property Inquiry
- "Give me an overview of this property"
- "What are the key features and characteristics?"
- "How does this property compare to others in the area?"

### Soil Analysis
- "What's the soil quality score?"
- "What soil types are present?"
- "What amendments would improve soil health?"
- "Show me the soil drainage characteristics"

### Crop Recommendations
- "What crops are best suited for this soil?"
- "What's the expected yield for soybeans?"
- "Compare profitability of different crop rotations"
- "What's the optimal planting schedule?"

### Lease and Revenue
- "What's the fair cash rent for this property?"
- "Calculate potential revenue from different crops"
- "Find qualified farmers for leasing"
- "Generate a lease agreement template"

### Tax Optimization
- "Is this property eligible for Section 180 deductions?"
- "What conservation programs are available?"
- "Calculate potential tax savings"
- "What documentation is needed for tax benefits?"

## Integration Tips

### Frontend Integration
```javascript
// Example frontend function
async function askPropertyQuestion(propertyId, question, conversationType = 'property_inquiry') {
  const response = await fetch('/api/v1/chat/message', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: question,
      conversation_type: conversationType,
      property_id: propertyId
    })
  });
  
  return response.json();
}

// Usage
const result = await askPropertyQuestion(
  'FARM_456', 
  'What crops would grow best here?',
  'crop_recommendation'
);
```

### Mobile App Integration
Use the same API structure but consider caching conversation history locally for offline viewing.

## Next Steps

1. **Search for Properties**: Use the `/api/v1/search/properties` endpoint to find property IDs
2. **Get Property Insights**: Use `/api/v1/insights/property/{property_id}` for detailed analysis
3. **Continue Conversations**: Always use the returned `conversation_id` for follow-up questions
4. **Explore Suggestions**: Use the returned suggestions to guide users to relevant follow-up questions
