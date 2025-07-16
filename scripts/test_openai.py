#!/usr/bin/env python3
"""
Test OpenAI API connection
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.core.config import settings
from openai import OpenAI

def test_openai():
    print(f"Testing OpenAI API with key: {settings.OPENAI_API_KEY[:10]}...")
    
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            max_tokens=50
        )
        
        print(f"Success! Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    test_openai()
