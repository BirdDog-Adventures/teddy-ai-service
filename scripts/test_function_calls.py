#!/usr/bin/env python3
"""
Test script to verify function calls are working in the API
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1"
CHAT_ENDPOINT = f"{BASE_URL}/chat/message"

def test_function_call_queries():
    """Test queries that should trigger function calls"""
    
    test_queries = [
        {
            "name": "Soil Analysis Query",
            "message": "Analyze the soil composition and quality for this property",
            "conversation_type": "soil_analysis",
            "property_id": "9060",
            "expected_function": "get_soil_analysis"
        },
        {
            "name": "Crop Recommendation Query", 
            "message": "What crops would grow best on this property based on soil conditions?",
            "conversation_type": "crop_recommendation",
            "property_id": "9060",
            "expected_function": "get_soil_analysis"
        },
        {
            "name": "Property Search Query",
            "message": "Find similar properties with 100-500 acres in Texas",
            "conversation_type": "general",
            "expected_function": "search_properties"
        },
        {
            "name": "Section 180 Query",
            "message": "Is this property eligible for Section 180 tax deductions?",
            "conversation_type": "tax_optimization", 
            "property_id": "9060",
            "expected_function": "check_section_180_eligibility"
        }
    ]
    
    print("🧪 Testing Function Call Queries")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. {query['name']}")
        print(f"   Message: {query['message']}")
        print(f"   Expected Function: {query['expected_function']}")
        print("-" * 40)
        
        # Prepare request
        request_data = {
            "message": query["message"],
            "conversation_type": query["conversation_type"]
        }
        
        if "property_id" in query:
            request_data["property_id"] = query["property_id"]
        
        try:
            # Send request
            response = requests.post(
                CHAT_ENDPOINT,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if function was called
                sources = data.get('sources')
                if sources:
                    print(f"   ✅ Function calls made: {len(sources)}")
                    for j, source in enumerate(sources, 1):
                        function_name = source.get('function', 'Unknown')
                        print(f"      {j}. {function_name}")
                        
                        # Check if expected function was called
                        if function_name == query['expected_function']:
                            print(f"      ✅ Expected function '{query['expected_function']}' was called!")
                        
                else:
                    print(f"   ❌ No function calls made (sources: {sources})")
                
                # Show response preview
                response_text = data.get('response', '')
                print(f"   Response: {response_text[:100]}...")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   🚨 Request failed: {str(e)}")
    
    print(f"\n{'='*60}")
    print("🎉 Function Call Testing Complete!")

if __name__ == "__main__":
    test_function_call_queries()
