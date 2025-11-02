"""
Test script for the Chat API with field analysis integration

Usage:
    python test_chat_api.py
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_chat_with_location():
    """Test chat API with location coordinates (triggers field analysis)"""
    print("\n" + "="*60)
    print("TEST 1: Chat with Location (Field Analysis)")
    print("="*60)
    
    thread_id = "test-thread-1"
    url = f"{BASE_URL}/chat/{thread_id}"
    
    # Test with location coordinates (Lahore, Pakistan)
    payload = {
        "query": "میرے کھیت کا تجزیہ کریں 31.5497 74.3436"
    }
    
    print(f"\n📤 Request URL: {url}")
    print(f"📤 Request Body: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"\n📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if "field_analysis" in data and data["field_analysis"]:
                print("\n🌾 Field Analysis Data Received!")
        else:
            print(f"\n❌ Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")

def test_chat_with_location_english():
    """Test chat API with location in English"""
    print("\n" + "="*60)
    print("TEST 2: Chat with Location (English)")
    print("="*60)
    
    thread_id = "test-thread-2"
    url = f"{BASE_URL}/chat/{thread_id}"
    
    # Test with location coordinates (Karachi, Pakistan)
    payload = {
        "query": "Analyze my field at 24.8607 67.0011"
    }
    
    print(f"\n📤 Request URL: {url}")
    print(f"📤 Request Body: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"\n📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\n❌ Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")

def test_chat_without_location():
    """Test chat API without location (normal chat)"""
    print("\n" + "="*60)
    print("TEST 3: Chat without Location (Normal Chat)")
    print("="*60)
    
    thread_id = "test-thread-3"
    url = f"{BASE_URL}/chat/{thread_id}"
    
    payload = {
        "query": "What is the best time to plant wheat in Pakistan?"
    }
    
    print(f"\n📤 Request URL: {url}")
    print(f"📤 Request Body: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"\n📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\n❌ Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")

def test_chat_history():
    """Test chat history endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Chat History")
    print("="*60)
    
    thread_id = "test-thread-1"
    url = f"{BASE_URL}/chat/{thread_id}/history"
    
    print(f"\n📤 Request URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"\n📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\n❌ Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")

def test_health_check():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("TEST 0: Health Check")
    print("="*60)
    
    url = f"{BASE_URL}/health"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"\n📥 Status Code: {response.status_code}")
        print(f"✅ Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Server not running or not accessible: {e}")
        print("💡 Make sure the server is running: python main.py")
        return False
    return True

if __name__ == "__main__":
    print("\n" + "🧪"*30)
    print("Chat API Testing Suite")
    print("🧪"*30)
    
    # First check if server is running
    if not test_health_check():
        print("\n❌ Server is not running. Please start it first:")
        print("   python main.py")
        exit(1)
    
    # Run all tests
    test_chat_with_location()
    test_chat_with_location_english()
    test_chat_without_location()
    test_chat_history()
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")

