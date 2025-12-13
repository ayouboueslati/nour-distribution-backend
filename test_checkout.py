"""
Test the checkout endpoint with proper Body parameter
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"
GUEST_SESSION_ID = "test-session-123"

# Test payload matching frontend structure
payload = {
    "is_company": False,
    "b2c_data": {
        "first_name": "Test",
        "last_name": "User",
        "phone": "98123456",
        "email": "test@example.com",
        "address": "Test Address, Tunis",
        "delivery_notes": "Test notes",
        "preferred_contact": "phone"
    },
    "b2b_data": None
}

print("Testing checkout endpoint...")
print(f"URL: {BASE_URL}/carts/guest/{GUEST_SESSION_ID}/checkout")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(
        f"{BASE_URL}/carts/guest/{GUEST_SESSION_ID}/checkout",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 422:
        print("\n❌ Still getting 422 - Body() not working")
        print("Error details:", response.json())
    elif response.status_code == 404:
        print("\n⚠️ Cart not found (expected - we need to create cart first)")
    else:
        print(f"\n✅ Got response: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
