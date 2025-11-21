import requests
import json

def test_backend_connection():
    print("🧪 Testing backend connection...")
    
    # Test 1: Health endpoint
    print("1. Testing health endpoint...")
    try:
        health_response = requests.get("http://localhost:8000/health")
        print(f"   ✅ Health endpoint: {health_response.status_code}")
        print(f"   📝 Response: {health_response.text}")
    except Exception as e:
        print(f"   ❌ Health endpoint failed: {e}")
        return
    
    # Test 2: Check if auth endpoint exists
    print("2. Testing auth endpoint existence...")
    try:
        auth_response = requests.get("http://localhost:8000/api/v1/auth/login")
        print(f"   📝 Auth endpoint GET: {auth_response.status_code}")
    except Exception as e:
        print(f"   ❌ Auth endpoint check failed: {e}")
        return
    
    # Test 3: Test login with correct credentials
    print("3. Testing login with correct credentials...")
    try:
        login_data = {
            "username": "admin@nourdistribution.com",
            "password": "ChangeThisPassword123!"
        }
        login_response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data=login_data
        )
        print(f"   📝 Login POST response: {login_response.status_code}")
        if login_response.status_code == 200:
            print(f"   ✅ Login successful!")
            print(f"   🔑 Token: {login_response.json().get('access_token', 'No token')}")
        else:
            print(f"   ❌ Login failed: {login_response.text}")
    except Exception as e:
        print(f"   ❌ Login test failed: {e}")
    
    # Test 4: Test login with form data (OAuth2 style)
    print("4. Testing login with form data...")
    try:
        form_data = {
            "username": "admin@nourdistribution.com",
            "password": "ChangeThisPassword123!"
        }
        login_response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"   📝 Form login response: {login_response.status_code}")
        if login_response.status_code == 200:
            print(f"   ✅ Form login successful!")
            print(f"   🔑 Token: {login_response.json().get('access_token', 'No token')}")
        else:
            print(f"   ❌ Form login failed: {login_response.text}")
    except Exception as e:
        print(f"   ❌ Form login test failed: {e}")

if __name__ == "__main__":
    test_backend_connection()