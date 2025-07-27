#!/usr/bin/env python3
"""Test Claude 4 response format"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Initialize Claude client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Test simple request
try:
    print("Testing Claude 4 Sonnet...")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        temperature=0.3,
        system="You are a helpful assistant. Always respond in valid JSON format.",
        messages=[
            {
                "role": "user", 
                "content": """Please analyze if these two statements contradict each other and respond in JSON format:
                
Statement 1: "The sky is blue during daytime."
Statement 2: "The sky is always red."

Respond with this JSON structure:
{
    "has_contradiction": true/false,
    "explanation": "your explanation here"
}
"""
            }
        ]
    )
    
    print(f"\nResponse type: {type(response)}")
    print(f"Response content: {response.content}")
    
    if response.content:
        print(f"\nFirst content block type: {response.content[0].type}")
        print(f"First content block text: {response.content[0].text}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 