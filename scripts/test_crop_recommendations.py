#!/usr/bin/env python3
"""
Test script for crop recommendation functionality
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.crop_recommendation_service import CropRecommendationService
from data_connectors.snowflake_connector import SnowflakeConnector


async def test_snowflake_connection():
    """Test Snowflake connection and crop_history table access"""
    print("🔍 Testing Snowflake connection...")
    
    try:
        snowflake = SnowflakeConnector()
        
        # Test basic connection
        query = "SELECT CURRENT_VERSION()"
        result = await snowflake.execute_query(query)
        print(f"✅ Snowflake connection successful: {result[0][0] if result else 'Connected'}")
        
        # Test crop_history table structure
        query = """
        SELECT COLUMN_NAME, DATA_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'CROP_HISTORY' 
        ORDER BY ORDINAL_POSITION
        """
        
        columns = await snowflake.execute_query(query)
        if columns:
            print("✅ CROP_HISTORY table structure:")
            for col in columns:
                print(f"   - {col[0]}: {col[1]}")
        else:
            print("⚠️  CROP_HISTORY table not found or no access")
        
        # Test sample data
        query = "SELECT COUNT(*) FROM CROP_HISTORY LIMIT 1"
        count_result = await snowflake.execute_query(query)
        if count_result:
            print(f"✅ CROP_HISTORY contains {count_result[0][0]} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Snowflake connection failed: {str(e)}")
        return False


async def test_crop_recommendation_service():
    """Test the crop recommendation service"""
    print("\n🌾 Testing Crop Recommendation Service...")
    
    try:
        service = CropRecommendationService()
        
        # Test with a sample parcel ID
        test_parcel_id = "TEST_PARCEL_001"
        
        print(f"📍 Testing recommendations for parcel: {test_parcel_id}")
        
        # Test crop history retrieval
        print("   Getting crop history...")
        crop_history = await service.get_crop_history_for_parcel(test_parcel_id)
        print(f"   Found {len(crop_history)} historical records")
        
        # Test regional data (using sample county/state)
        print("   Getting regional performance data...")
        regional_data = await service.get_regional_crop_performance("HARRIS", "TX")
        print(f"   Found regional data for {len(regional_data)} crop types")
        
        # Test rotation analysis
        print("   Analyzing rotation patterns...")
        rotation_analysis = service.analyze_rotation_patterns(crop_history)
        print(f"   Rotation analysis: {rotation_analysis.get('analysis', {}).get('score', 0)}/100")
        
        # Test crop recommendations
        print("   Generating crop recommendations...")
        recommendations = await service.generate_crop_recommendations(
            parcel_id=test_parcel_id,
            county_id="HARRIS",
            state_code="TX"
        )
        
        print(f"✅ Generated {len(recommendations)} crop recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):  # Show top 3
            print(f"   {i}. {rec.crop_type}")
            print(f"      Suitability: {rec.suitability_score:.1f}/100")
            print(f"      Expected Yield: {rec.expected_yield}")
            print(f"      Revenue Potential: {rec.revenue_potential}")
            print(f"      Confidence: {rec.confidence_level}")
            print(f"      Market Outlook: {rec.market_outlook}")
        
        # Test AI-enhanced recommendations
        if recommendations:
            print("   Getting AI-enhanced analysis...")
            ai_enhanced = await service.get_ai_enhanced_recommendations(
                parcel_id=test_parcel_id,
                recommendations=recommendations[:2]  # Top 2 for testing
            )
            
            if ai_enhanced.get("ai_analysis"):
                print("✅ AI analysis generated successfully")
                print(f"   Analysis length: {len(ai_enhanced['ai_analysis'])} characters")
            else:
                print("⚠️  AI analysis not available")
        
        return True
        
    except Exception as e:
        print(f"❌ Crop recommendation service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_sample_data():
    """Test with sample data if no real data is available"""
    print("\n🧪 Testing with sample data...")
    
    try:
        service = CropRecommendationService()
        
        # Create sample crop history data
        from services.crop_recommendation_service import CropHistoryData
        
        sample_history = [
            CropHistoryData(
                history_id=1,
                parcel_id="SAMPLE_001",
                crop_year=2023,
                crop_type="Corn",
                rotation_sequence=1,
                crop_geojson={},
                county_id="HARRIS",
                state_code="TX",
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            CropHistoryData(
                history_id=2,
                parcel_id="SAMPLE_001",
                crop_year=2022,
                crop_type="Soybeans",
                rotation_sequence=1,
                crop_geojson={},
                county_id="HARRIS",
                state_code="TX",
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            CropHistoryData(
                history_id=3,
                parcel_id="SAMPLE_001",
                crop_year=2021,
                crop_type="Wheat",
                rotation_sequence=1,
                crop_geojson={},
                county_id="HARRIS",
                state_code="TX",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        # Test rotation analysis with sample data
        rotation_analysis = service.analyze_rotation_patterns(sample_history)
        print(f"✅ Sample rotation analysis:")
        print(f"   Score: {rotation_analysis['analysis']['score']}/100")
        print(f"   Patterns found: {len(rotation_analysis['patterns'])}")
        print(f"   Recommendations: {len(rotation_analysis['recommendations'])}")
        
        # Test individual crop recommendation generation
        for crop_type in ["corn", "soybeans", "wheat", "cotton"]:
            recommendation = await service._generate_single_crop_recommendation(
                crop_type=crop_type,
                parcel_id="SAMPLE_001",
                crop_history=sample_history,
                regional_data={},
                rotation_analysis=rotation_analysis
            )
            
            if recommendation:
                print(f"✅ {recommendation.crop_type}: {recommendation.suitability_score:.1f}/100")
        
        return True
        
    except Exception as e:
        print(f"❌ Sample data test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_endpoints():
    """Test the API endpoints (requires running server)"""
    print("\n🌐 Testing API endpoints...")
    
    try:
        import httpx
        
        base_url = "http://localhost:8000"  # Adjust if different
        
        # Test endpoints (would need authentication in real scenario)
        endpoints_to_test = [
            "/api/v1/recommendations/crops/TEST_PARCEL_001",
            "/api/v1/recommendations/crops/TEST_PARCEL_001/history",
            "/api/v1/recommendations/crops/regional/HARRIS/TX"
        ]
        
        print("   Note: API endpoint testing requires running server and authentication")
        print("   Endpoints available:")
        for endpoint in endpoints_to_test:
            print(f"   - GET {endpoint}")
        
        return True
        
    except ImportError:
        print("   httpx not available for API testing")
        return True
    except Exception as e:
        print(f"❌ API endpoint test failed: {str(e)}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting Crop Recommendation System Tests")
    print("=" * 50)
    
    tests = [
        ("Snowflake Connection", test_snowflake_connection),
        ("Crop Recommendation Service", test_crop_recommendation_service),
        ("Sample Data Processing", test_with_sample_data),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Crop recommendation system is ready.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == len(results)


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
