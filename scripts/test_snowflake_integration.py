#!/usr/bin/env python3
"""
Test script to verify Snowflake data integration is working correctly
"""
import asyncio
import sys
import os
import json
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_connectors.snowflake_connector import SnowflakeConnector
from api.core.config import settings

async def test_snowflake_connection():
    """Test basic Snowflake connection"""
    print("🔌 Testing Snowflake Connection...")
    print(f"   Account: {settings.SNOWFLAKE_ACCOUNT}")
    print(f"   User: {settings.SNOWFLAKE_USER}")
    print(f"   Database: {settings.SNOWFLAKE_DATABASE}")
    print(f"   Schema: {settings.SNOWFLAKE_SCHEMA}")
    print(f"   Warehouse: {settings.SNOWFLAKE_WAREHOUSE}")
    print(f"   Role: {settings.SNOWFLAKE_ROLE}")
    print(f"   Private Key Path: {settings.SNOWFLAKE_PRIVATE_KEY_PATH}")
    print("-" * 60)
    
    try:
        connector = SnowflakeConnector()
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()
            print(f"✅ Connection successful! Snowflake version: {version[0]}")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

async def test_property_boundaries(property_id: str):
    """Test property boundaries retrieval"""
    print(f"\n🏠 Testing Property Boundaries for ID: {property_id}")
    print("-" * 60)
    
    try:
        connector = SnowflakeConnector()
        property_data = await connector.get_property_boundaries(property_id)
        
        if property_data:
            print("✅ Property data found!")
            print(f"   Parcel ID: {property_data.get('PARCEL_ID')}")
            print(f"   Address: {property_data.get('ADDRESS')}")
            print(f"   City: {property_data.get('CITY')}")
            print(f"   State: {property_data.get('STATE_CODE')}")
            print(f"   County: {property_data.get('COUNTY_ID')}")
            print(f"   Acres: {property_data.get('ACRES')}")
            print(f"   Owner: {property_data.get('OWNER_NAME')}")
            print(f"   Total Value: ${property_data.get('TOTAL_VALUE'):,}" if property_data.get('TOTAL_VALUE') else "   Total Value: N/A")
            print(f"   Land Value: ${property_data.get('LAND_VALUE'):,}" if property_data.get('LAND_VALUE') else "   Land Value: N/A")
            print(f"   Use Code: {property_data.get('USECODE')}")
            print(f"   Use Description: {property_data.get('USEDESC')}")
            print(f"   Zoning: {property_data.get('ZONING')}")
            print(f"   Latitude: {property_data.get('LATITUDE')}")
            print(f"   Longitude: {property_data.get('LONGITUDE')}")
            return property_data
        else:
            print(f"❌ No property data found for ID: {property_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving property data: {str(e)}")
        return None

async def test_soil_data(property_id: str):
    """Test soil data retrieval"""
    print(f"\n🌱 Testing Soil Data for Property ID: {property_id}")
    print("-" * 60)
    
    try:
        connector = SnowflakeConnector()
        soil_data = await connector.get_soil_data(property_id)
        
        if soil_data:
            print(f"✅ Found {len(soil_data)} soil records!")
            
            for i, soil in enumerate(soil_data[:3], 1):  # Show first 3 records
                print(f"\n   Soil Record {i}:")
                print(f"     MUKEY: {soil.get('MUKEY')}")
                print(f"     Map Unit Symbol: {soil.get('MAP_UNIT_SYMBOL')}")
                print(f"     Soil Series: {soil.get('SOIL_SERIES')}")
                print(f"     Soil Type: {soil.get('SOIL_TYPE')}")
                print(f"     Component %: {soil.get('COMPONENT_PERCENTAGE')}%")
                print(f"     Fertility Class: {soil.get('FERTILITY_CLASS')}")
                print(f"     pH Level: {soil.get('PH_LEVEL')}")
                print(f"     Organic Matter: {soil.get('ORGANIC_MATTER_PCT')}%")
                print(f"     Drainage Class: {soil.get('DRAINAGE_CLASS')}")
                print(f"     Hydrologic Group: {soil.get('HYDROLOGIC_GROUP')}")
                print(f"     Agricultural Capability: {soil.get('AGRICULTURAL_CAPABILITY')}")
                print(f"     Confidence Score: {soil.get('CONFIDENCE_SCORE')}")
                print(f"     Match Quality: {soil.get('MATCH_QUALITY')}")
                
            if len(soil_data) > 3:
                print(f"\n   ... and {len(soil_data) - 3} more soil records")
                
            return soil_data
        else:
            print(f"❌ No soil data found for property ID: {property_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving soil data: {str(e)}")
        return None

async def test_comprehensive_analysis(property_id: str):
    """Test comprehensive analysis retrieval"""
    print(f"\n📊 Testing Comprehensive Analysis for Property ID: {property_id}")
    print("-" * 60)
    
    try:
        connector = SnowflakeConnector()
        analysis_data = await connector.get_comprehensive_analysis(property_id)
        
        if analysis_data:
            print("✅ Comprehensive analysis found!")
            print(f"   Parcel Acres: {analysis_data.get('PARCEL_ACRES')}")
            print(f"   Dominant Cover Type: {analysis_data.get('DOMINANT_COVER_TYPE')}")
            print(f"   Dominant Cover %: {analysis_data.get('DOMINANT_COVER_PERCENTAGE')}%")
            print(f"   Agricultural %: {analysis_data.get('AGRICULTURAL_PERCENTAGE')}%")
            print(f"   Forest %: {analysis_data.get('FOREST_PERCENTAGE')}%")
            print(f"   Developed %: {analysis_data.get('DEVELOPED_PERCENTAGE')}%")
            print(f"   Dominant Crop: {analysis_data.get('DOMINANT_CROP')}")
            print(f"   Agricultural Classification: {analysis_data.get('AGRICULTURAL_CLASSIFICATION')}")
            print(f"   Section 180 Potential: {analysis_data.get('SECTION_180_POTENTIAL')}")
            print(f"   Investment Opportunity: {analysis_data.get('INVESTMENT_OPPORTUNITY_FLAG')}")
            return analysis_data
        else:
            print(f"❌ No comprehensive analysis found for property ID: {property_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving comprehensive analysis: {str(e)}")
        return None

async def test_climate_data(property_id: str):
    """Test climate data retrieval"""
    print(f"\n🌤️  Testing Climate Data for Property ID: {property_id}")
    print("-" * 60)
    
    try:
        connector = SnowflakeConnector()
        climate_data = await connector.get_climate_data(property_id)
        
        if climate_data:
            print("✅ Climate data found!")
            print(f"   Data Year: {climate_data.get('DATA_YEAR')}")
            print(f"   Annual Precipitation: {climate_data.get('ANNUAL_PRECIPITATION_INCHES')}\"")
            print(f"   Growing Degree Days: {climate_data.get('GROWING_DEGREE_DAYS')}")
            print(f"   Avg Temperature: {climate_data.get('AVG_TEMPERATURE_F')}°F")
            print(f"   Max Temperature: {climate_data.get('MAX_TEMPERATURE_F')}°F")
            print(f"   Min Temperature: {climate_data.get('MIN_TEMPERATURE_F')}°F")
            print(f"   Climate Classification: {climate_data.get('CLIMATE_CLASSIFICATION')}")
            print(f"   Weather Station: {climate_data.get('WEATHER_STATION_NAME')}")
            print(f"   Station Distance: {climate_data.get('STATION_DISTANCE_MILES')} miles")
            return climate_data
        else:
            print(f"❌ No climate data found for property ID: {property_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving climate data: {str(e)}")
        return None

async def test_crop_history(property_id: str):
    """Test crop history retrieval"""
    print(f"\n🌾 Testing Crop History for Property ID: {property_id}")
    print("-" * 60)
    
    try:
        connector = SnowflakeConnector()
        crop_data = await connector.get_crop_history(property_id)
        
        if crop_data:
            print(f"✅ Found {len(crop_data)} crop history records!")
            
            for i, crop in enumerate(crop_data[:5], 1):  # Show first 5 records
                print(f"   Year {crop.get('CROP_YEAR')}: {crop.get('CROP_TYPE')} (Sequence: {crop.get('ROTATION_SEQUENCE')})")
                
            return crop_data
        else:
            print(f"❌ No crop history found for property ID: {property_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving crop history: {str(e)}")
        return None

async def test_section_180_estimates(property_id: str):
    """Test Section 180 estimates retrieval"""
    print(f"\n💰 Testing Section 180 Estimates for Property ID: {property_id}")
    print("-" * 60)
    
    try:
        connector = SnowflakeConnector()
        section_180_data = await connector.get_section_180_estimates(property_id)
        
        if section_180_data:
            print("✅ Section 180 estimates found!")
            print(f"   Total Deduction: ${section_180_data.get('TOTAL_DEDUCTION'):,}" if section_180_data.get('TOTAL_DEDUCTION') else "   Total Deduction: N/A")
            print(f"   Nitrogen Value: ${section_180_data.get('NITROGEN_VALUE'):,}" if section_180_data.get('NITROGEN_VALUE') else "   Nitrogen Value: N/A")
            print(f"   Phosphorus Value: ${section_180_data.get('PHOSPHORUS_VALUE'):,}" if section_180_data.get('PHOSPHORUS_VALUE') else "   Phosphorus Value: N/A")
            print(f"   Potassium Value: ${section_180_data.get('POTASSIUM_VALUE'):,}" if section_180_data.get('POTASSIUM_VALUE') else "   Potassium Value: N/A")
            print(f"   Confidence Score: {section_180_data.get('CONFIDENCE_SCORE')}")
            print(f"   Methodology: {section_180_data.get('METHODOLOGY')}")
            return section_180_data
        else:
            print(f"❌ No Section 180 estimates found for property ID: {property_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving Section 180 estimates: {str(e)}")
        return None

async def test_property_search():
    """Test property search functionality"""
    print(f"\n🔍 Testing Property Search")
    print("-" * 60)
    
    try:
        connector = SnowflakeConnector()
        
        # Test search with filters
        filters = {
            "min_acreage": 100,
            "max_acreage": 1000,
            "state": "TX"
        }
        
        properties = await connector.search_properties_by_criteria(filters, limit=5)
        
        if properties:
            print(f"✅ Found {len(properties)} properties matching criteria!")
            
            for i, prop in enumerate(properties, 1):
                print(f"\n   Property {i}:")
                print(f"     Parcel ID: {prop.get('PARCEL_ID')}")
                print(f"     Address: {prop.get('ADDRESS')}")
                print(f"     City: {prop.get('CITY')}, {prop.get('STATE_CODE')}")
                print(f"     County: {prop.get('COUNTY_ID')}")
                print(f"     Acres: {prop.get('ACRES')}")
                print(f"     Owner: {prop.get('OWNER_NAME')}")
                print(f"     Value: ${prop.get('TOTAL_VALUE'):,}" if prop.get('TOTAL_VALUE') else "     Value: N/A")
                
            return properties
        else:
            print(f"❌ No properties found matching criteria")
            return None
            
    except Exception as e:
        print(f"❌ Error searching properties: {str(e)}")
        return None

async def test_llm_integration(property_id: str):
    """Test LLM integration with Snowflake data"""
    print(f"\n🤖 Testing LLM Integration with Snowflake Data")
    print("-" * 60)
    
    try:
        from services.llm_service import LLMService
        
        llm_service = LLMService()
        
        # Test soil analysis function call
        conversation_history = [
            {"role": "user", "content": f"Analyze the soil for property {property_id}"}
        ]
        
        system_prompt = """You are Teddy, an AI assistant for BirdDog's land intelligence platform. 
        You help landowners, farmers, and hunters make informed decisions about rural properties.
        You have access to property data, soil information, agricultural insights, and market trends.
        Be helpful, accurate, and provide actionable insights."""
        
        print(f"   Calling LLM service for property {property_id}...")
        response, sources = await llm_service.generate_response(
            conversation_history=conversation_history,
            system_prompt=system_prompt,
            property_context=None,
            user_preferences=None
        )
        
        print(f"✅ LLM Response received!")
        print(f"   Response length: {len(response)} characters")
        print(f"   Number of sources: {len(sources) if sources else 0}")
        
        if sources:
            for i, source in enumerate(sources, 1):
                print(f"\n   Source {i}: {source.get('function')}")
                if 'result' in source:
                    result = source['result']
                    if 'property_id' in result:
                        print(f"     Property ID: {result['property_id']}")
                    if 'soil_types' in result:
                        print(f"     Soil types found: {len(result['soil_types'])}")
                    if 'overall_quality' in result:
                        print(f"     Overall quality: {result['overall_quality']}")
        
        print(f"\n   AI Response Preview:")
        print(f"   {response[:200]}...")
        
        return response, sources
        
    except Exception as e:
        print(f"❌ Error testing LLM integration: {str(e)}")
        return None, None

async def main():
    """Main test function"""
    print("🚀 Snowflake Integration Test Suite")
    print("=" * 60)
    
    # Test properties - you can modify these
    test_property_ids = [
        "9060"  # Known property ID
       # "90916",  # Another test ID
       # "40167"   # Another test ID
    ]
    
    # Test 1: Basic connection
    connection_ok = await test_snowflake_connection()
    if not connection_ok:
        print("\n❌ Cannot proceed - Snowflake connection failed!")
        return
    
    # Test 2: Property search
    await test_property_search()
    
    # Test 3-8: Test each property ID
    for property_id in test_property_ids:
        print(f"\n{'='*60}")
        print(f"🏠 TESTING PROPERTY ID: {property_id}")
        print(f"{'='*60}")
        
        # Test property boundaries
        property_data = await test_property_boundaries(property_id)
        if not property_data:
            print(f"⚠️  Skipping other tests for {property_id} - no property data found")
            continue
        
        # Test soil data
        soil_data = await test_soil_data(property_id)
        
        # Test comprehensive analysis
        await test_comprehensive_analysis(property_id)
        
        # Test climate data
        await test_climate_data(property_id)
        
        # Test crop history
        await test_crop_history(property_id)
        
        # Test Section 180 estimates
        await test_section_180_estimates(property_id)
        
        # Test LLM integration if we have soil data
        if soil_data:
            await test_llm_integration(property_id)
        
        print(f"\n✅ Completed testing for property {property_id}")
    
    print(f"\n{'='*60}")
    print("🎉 Snowflake Integration Test Suite Complete!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
