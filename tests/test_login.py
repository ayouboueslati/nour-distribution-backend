import requests
import json

def test_login():
    print("🧪 Testing login API directly...")
    
    url = "http://localhost:8000/api/v1/auth/login"
    data = {
        "email": "admin@nourdistribution.com",
        "password": "ChangeThisPassword123!"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"📡 Status Code: {response.status_code}")
        print(f"📡 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Login successful!")
            print(f"🔑 Token received: {result.get('access_token')[:50]}...")
            return result
        else:
            print(f"❌ Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"💥 Request failed: {e}")
        return None

if __name__ == "__main__":
    test_login()