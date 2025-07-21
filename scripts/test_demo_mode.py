#!/usr/bin/env python3
"""
Test script for demo mode (authentication disabled)
"""
import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
CHAT_ENDPOINT = f"{BASE_URL}/chat/message"

def test_demo_mode():
    """Test chat API in demo mode (no authentication required)"""
    
    # Test message
    test_message = {
        "message": "Tell me about soil analysis for property 12345",
        "conversation_type": "soil_analysis",
        "property_id": "12345",
        "context": {
            "demo": True
        }
    }
    
    print("🧪 Testing Demo Mode (No Authentication)")
    print(f"📡 Sending request to: {CHAT_ENDPOINT}")
    print(f"💬 Message: {test_message['message']}")
    print("-" * 50)
    
    try:
        # Send request without authentication headers
        response = requests.post(
            CHAT_ENDPOINT,
            json=test_message,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Demo mode working correctly")
            print(f"🤖 AI Response: {data.get('response', 'No response')[:200]}...")
            print(f"🆔 Conversation ID: {data.get('conversation_id')}")
            print(f"🏷️  Demo Mode: {data.get('metadata', {}).get('demo_mode', 'Not specified')}")
            
            if data.get('sources'):
                print(f"📚 Sources: {len(data['sources'])} source(s) found")
            
            if data.get('suggestions'):
                print(f"💡 Suggestions: {len(data['suggestions'])} suggestion(s)")
                for i, suggestion in enumerate(data['suggestions'][:3], 1):
                    print(f"   {i}. {suggestion}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"🚨 Request failed: {str(e)}")
        print("💡 Make sure the server is running: python -m uvicorn api.main:app --reload")

def test_with_property_id():
    """Test with a specific property ID"""
    
    test_message = {
        "message": "What crops would grow best on this property?",
        "conversation_type": "crop_recommendation", 
        "property_id": "48201000010001",  # Real property ID from your data
        "context": {
            "demo": True,
            "location": "Texas"
        }
    }
    
    print("\n🌾 Testing Crop Recommendations for Specific Property")
    print(f"🏠 Property ID: {test_message['property_id']}")
    print(f"💬 Message: {test_message['message']}")
    print("-" * 50)
    
    try:
        response = requests.post(
            CHAT_ENDPOINT,
            json=test_message,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Property-specific analysis working")
            print(f"🤖 AI Response: {data.get('response', 'No response')[:300]}...")
            
            if data.get('sources'):
                print(f"📚 Sources: {len(data['sources'])} source(s) found")
                # Show first source details
                first_source = data['sources'][0] if data['sources'] else {}
                if 'result' in first_source:
                    result = first_source['result']
                    if 'property_info' in result:
                        prop_info = result['property_info']
                        print(f"🏠 Property: {prop_info.get('address', 'Unknown address')}")
                        print(f"📏 Acreage: {prop_info.get('acreage', 'Unknown')} acres")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"🚨 Request failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Teddy AI Service - Demo Mode Test")
    print("=" * 50)
    
    # Test basic demo mode
    test_demo_mode()
    
    # Test with property-specific query
    test_with_property_id()
    
    print("\n" + "=" * 50)
    print("✨ Demo mode testing complete!")
    print("\n💡 To enable authentication, set ENABLE_AUTHENTICATION=true in .env")
    print("💡 To test different LLM providers, change LLM_PROVIDER in .env")
