import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

def test_get_users_forbidden():
    # Create a token for a user that is NOT a superadmin (assuming default is False)
    # We can fake a token for a user that doesn't exist in DB but the dependency might check DB.
    # Actually dependency checks DB. So we need a real user.
    # But since we can't easily create a user in this script without DB access code...
    # We will try to rely on the fact that if we get 401 it means invalid creds, 
    # if we get 403 it means valid creds but not allowed.
    
    # However, to get 403, we need a valid user in DB.
    # Let's try to register a temp user first via the API.
    
    email = "temp_test_user@example.com"
    password = "password123"
    
    # 1. Register
    response = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Temp Test"
    })
    
    # If user already exists, login
    if response.status_code == 400:
        login_response = client.post("/auth/token", data={
            "username": email,
            "password": password
        })
        token = login_response.json().get("access_token")
    else:
        token = response.json().get("access_token")
        
    assert token is not None, "Could not get access token"
    
    # 2. Try to access /users
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/users/", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 403:
        print("✅ SUCCESS: Access forbidden as expected for normal user.")
    elif response.status_code == 200:
        print("❌ FAILURE: Access granted to normal user (Unexpected).")
    else:
        print(f"⚠️ UNEXPECTED: {response.status_code}")

if __name__ == "__main__":
    test_get_users_forbidden()
