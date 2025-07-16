#!/usr/bin/env python3
"""
Test script for Teddy AI Service API
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_api():
    # Test user registration
    print("1. Testing user registration...")
    register_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    print(f"Registration response: {response.status_code}")
    if response.status_code == 200:
        print(f"User created: {response.json()}")
    else:
        print(f"Registration failed: {response.text}")
    
    # Test login
    print("\n2. Testing login...")
    login_data = {
        "username": "test@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    print(f"Login response: {response.status_code}")
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data["access_token"]
        print(f"Login successful! Token type: {token_data['token_type']}")
        
        # Test authenticated endpoint
        print("\n3. Testing chat endpoint with authentication...")
        headers = {"Authorization": f"Bearer {access_token}"}
        chat_data = {
            "message": "Hello, can you tell me about soil quality analysis?",
            "conversation_type": "general"
        }
        
        response = requests.post(
            f"{BASE_URL}/chat/message", 
            json=chat_data,
            headers=headers
        )
        print(f"Chat response: {response.status_code}")
        if response.status_code == 200:
            print(f"AI Response: {response.json()['response']}")
        else:
            print(f"Chat failed: {response.text}")
    else:
        print(f"Login failed: {response.text}")

if __name__ == "__main__":
    test_api()
