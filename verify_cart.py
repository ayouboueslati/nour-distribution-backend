import urllib.request
import urllib.error
import json
import uuid

BASE_URL = "http://localhost:8000/api/v1"
GUEST_ID = str(uuid.uuid4())

print(f"Testing with Guest Session ID: {GUEST_ID}")

def make_request(url, method="GET", data=None):
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header('Content-Type', 'application/json')
        
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req.data = json_data
            
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)

# 1. Get Guest Cart
print("\n--- 1. Get Guest Cart ---")
status, resp = make_request(f"{BASE_URL}/carts/guest/{GUEST_ID}")
print(f"Status: {status}")
print("Response:", resp)

# 2. Get Product
print("\n--- 2. Get Product ---")
# Try accessing without pagination first or checking the route
status, products = make_request(f"{BASE_URL}/products?skip=0&limit=1")
print(f"Products Status: {status}")
if status != 200:
    print(f"Products Error: {products}")
else:
    products_list = products.get('products', [])
    print(f"Products found: {len(products_list)}")
    if len(products_list) > 0:
        product_id = products_list[0]['id']
        print(f"Found product: {product_id}")
        
        # 3. Add Item
        print("\n--- 3. Add Item to Cart ---")
        item_data = {
            "product_id": product_id,
            "quantity": 1
        }
        status, add_resp = make_request(f"{BASE_URL}/carts/guest/{GUEST_ID}/items", "POST", item_data)
        print(f"Status: {status}")
        print("Response:", add_resp)
        
        if status == 200:
            # 4. Checkout
            print("\n--- 4. Guest Checkout ---")
            checkout_data = {
                "client_info": {
                    "first_name": "Test",
                    "last_name": "Guest",
                    "email": f"test.guest.{GUEST_ID}@example.com",
                    "phone": "000000000",
                    "address": "123 Guest St, Guest City",
                    "notes": "Testing guest checkout",
                    # Add required fields just in case
                    "company_name": "",
                    "fiscal_id": ""
                }
            }
            status, check_resp = make_request(f"{BASE_URL}/carts/guest/{GUEST_ID}/checkout", "POST", checkout_data)
            print(f"Status: {status}")
            print("Response:", check_resp)
