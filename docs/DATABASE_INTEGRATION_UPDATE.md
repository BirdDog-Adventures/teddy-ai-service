# Database Integration Update

## Overview
The chat API has been updated to integrate with the actual Snowflake database instead of returning mock/hardcoded data. This ensures that property-specific questions now return real data from your database.

## Changes Made

### 1. LLM Service Integration (`services/llm_service.py`)

#### Added Snowflake Connector
```python
from data_connectors.snowflake_connector import SnowflakeConnector

class LLMService:
    def __init__(self):
        # ... existing code ...
        self.snowflake_connector = SnowflakeConnector()
```

#### Updated Soil Analysis Function
The `_get_soil_analysis()` function now:
- Fetches real property boundaries from `REGRID_PARCELS` table
- Retrieves actual soil data from `SSURGO_MAPUNIT`, `SSURGO_COMPONENT`, and `SSURGO_CHORIZON` tables
- Processes SSURGO soil data to calculate:
  - Soil texture classification using USDA soil triangle
  - Quality scores based on pH, organic matter, drainage, and hydrologic group
  - Detailed soil composition (sand, silt, clay percentages)
  - Property-specific recommendations

#### Added Helper Functions
- `_determine_soil_texture()`: USDA soil texture triangle classification
- `_calculate_soil_quality_score()`: Multi-factor soil quality scoring
- `_generate_soil_recommendations()`: Property-specific soil management recommendations

### 2. Chat Endpoint Integration (`api/endpoints/chat.py`)

#### Updated Property Context Function
The `_get_property_context()` function now:
- Fetches real property data from Snowflake using the `SnowflakeConnector`
- Returns actual property information including:
  - Address, city, state, county
  - Acreage and assessed value
  - Land use code and owner information
  - Parcel ID for reference

## Database Schema Requirements

### Required Tables
1. **REGRID_PARCELS**: Property boundary and basic information
   - `property_id`, `parcel_id`, `address`, `city`, `state`, `acreage`, etc.

2. **SSURGO_MAPUNIT**: Soil map unit data
   - `MUKEY`, `MUSYM`, `MUNAME`, `GEOMETRY_WKT`

3. **SSURGO_COMPONENT**: Soil component data
   - `MUKEY`, `COKEY`, `COMPNAME`, `COMPPCT_R`, `DRAINAGECL`, `HYDGRP`

4. **SSURGO_CHORIZON**: Soil horizon data
   - `COKEY`, `PH1TO1H2O_R`, `SANDTOTAL_R`, `SILTTOTAL_R`, `CLAYTOTAL_R`, `OM_R`

### Spatial Relationships
The system uses spatial joins to find soil data that intersects with property boundaries:
```sql
JOIN property_bounds pb ON ST_Intersects(m.GEOMETRY_WKT, pb.geometry)
```

## API Response Changes

### Before (Mock Data)
```json
{
  "property_id": "9060",
  "soil_types": [
    {
      "type": "Clay Loam",
      "percentage": 60,
      "quality_score": 85,
      "ph": 6.5
    }
  ],
  "overall_quality": "High"
}
```

### After (Real Database Data)
```json
{
  "property_id": "9060",
  "property_info": {
    "address": "123 Farm Road",
    "city": "Austin",
    "state": "TX",
    "acreage": 247.5,
    "county": "Travis"
  },
  "soil_types": [
    {
      "type": "Clay Loam",
      "component_name": "Houston Black",
      "percentage": 65,
      "quality_score": 78.5,
      "ph": 6.8,
      "organic_matter": 2.3,
      "drainage": "moderately well drained",
      "hydrologic_group": "D",
      "texture_composition": {
        "sand": 25.2,
        "silt": 32.1,
        "clay": 42.7
      }
    }
  ],
  "overall_quality": "Medium",
  "overall_quality_score": 78.5,
  "average_ph": 6.8,
  "average_organic_matter": 2.3,
  "recommendations": [
    "Consider lime application to raise soil pH for optimal crop growth",
    "Heavy clay soils benefit from reduced tillage and organic matter additions",
    "Regular soil testing every 2-3 years is recommended for optimal management"
  ]
}
```

## Error Handling

### Property Not Found
```json
{
  "property_id": "invalid_id",
  "error": "Property not found in database",
  "soil_types": [],
  "overall_quality": "Unknown"
}
```

### No Soil Data Available
```json
{
  "property_id": "9060",
  "property_info": { /* property details */ },
  "error": "No soil data available for this property",
  "soil_types": [],
  "overall_quality": "Unknown"
}
```

### Database Connection Issues
```json
{
  "property_id": "9060",
  "error": "Failed to retrieve soil data: Connection timeout",
  "soil_types": [],
  "overall_quality": "Unknown"
}
```

## Configuration Requirements

### Snowflake Connection Settings
Ensure these environment variables are set in your `.env` file:
```
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password  # OR use private key
SNOWFLAKE_PRIVATE_KEY_PATH=path/to/private_key.pem
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_ROLE=your_role
```

## Testing the Integration

### Test Property-Specific Questions
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze the soil data for this property",
    "conversation_type": "soil_analysis",
    "property_id": "9060"
  }'
```

### Expected Behavior
1. **Valid Property ID**: Returns real soil data from SSURGO database
2. **Invalid Property ID**: Returns error message indicating property not found
3. **Property with No Soil Data**: Returns property info but indicates no soil data available
4. **Database Connection Issues**: Returns error message with connection details

## Performance Considerations

### Caching
- Property context is cached for 1 hour to reduce database queries
- Cache key format: `property_context:{property_id}`

### Query Optimization
- Spatial queries use indexes on geometry columns
- Component data is filtered to major components only (`MAJCOMPFLAG = 'Yes'`)
- Results are limited and ordered by relevance

## Future Enhancements

### Additional Data Sources
- Crop history from CDL (Cropland Data Layer)
- Market pricing data
- Weather and climate data
- Conservation program eligibility

### Enhanced Analysis
- Multi-year soil trend analysis
- Comparison with neighboring properties
- Crop suitability modeling based on soil characteristics
- Economic analysis integration

## Troubleshooting

### Common Issues

1. **"Property not found" for valid IDs**
   - Check if property exists in `REGRID_PARCELS` table
   - Verify property_id format matches database

2. **"No soil data available"**
   - Check if SSURGO data covers the property location
   - Verify spatial relationships between parcels and soil data

3. **Connection timeouts**
   - Check Snowflake connection settings
   - Verify network connectivity and credentials

4. **Slow response times**
   - Check if spatial indexes exist on geometry columns
   - Consider query optimization for large datasets

### Debug Mode
Enable debug logging to see detailed query execution:
```python
import logging
logging.getLogger('data_connectors.snowflake_connector').setLevel(logging.DEBUG)
```

## Migration Notes

### Backward Compatibility
- The API response format has been enhanced but maintains backward compatibility
- Existing mock data functions are preserved for fallback scenarios
- Error responses follow the same structure as before

### Data Validation
- All database values are validated before processing
- Null values are handled gracefully with appropriate defaults
- Spatial data is validated for proper format and projection
