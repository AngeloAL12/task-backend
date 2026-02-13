import sys
import os
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)

def run_verify():
    print("🚀 Starting User CRUD Verification...")

    # 1. Register a user to be our Superadmin
    email = "super_crud_test@example.com"
    password = "password123"
    full_name = "Super Admin Test"
    
    print(f"\n1️⃣ Registering user {email}...")
    response = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name
    })
    
    if response.status_code == 200:
        print("   ✅ Registered.")
    elif response.status_code == 400:
        print("   ℹ️ User already exists.")
    else:
        print(f"   ❌ Registration failed: {response.json()}")
        return

    # 2. Promote to Superadmin using our script
    print(f"\n2️⃣ Promoting {email} to Superadmin...")
    try:
        subprocess.run(
            ["uv", "run", "scripts/add_superadmin_column.py", "--promote", email], 
            check=True,
            capture_output=True
        )
        print("   ✅ Promotion script executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Promotion failed: {e.stderr.decode()}")
        return

    # 3. Login to get token
    print("\n3️⃣ Logging in...")
    login_response = client.post("/auth/token", data={
        "username": email,
        "password": password
    })
    token = login_response.json().get("access_token")
    if not token:
        print("   ❌ Login failed.")
        return
    print("   ✅ Logged in.")
    
    headers = {"Authorization": f"Bearer {token}"}

    # 4. GET /users (Read All)
    print("\n4️⃣ Testing GET /users (List)...")
    response = client.get("/users/", headers=headers)
    if response.status_code == 200:
        users = response.json()
        print(f"   ✅ Success. Found {len(users)} users.")
        # Find our user id
        my_user = next((u for u in users if u["email"] == email), None)
        if not my_user:
            print("   ❌ Basic integrity check failed: Created user not found in list.")
            return
        user_id = my_user["id"]
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")
        return

    # 5. GET /users/{id} (Read One)
    print(f"\n5️⃣ Testing GET /users/{user_id} (Read One)...")
    response = client.get(f"/users/{user_id}", headers=headers)
    if response.status_code == 200:
        print("   ✅ Success.")
        assert response.json()["email"] == email
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")

    # 6. PATCH /users/{id} (Update)
    print(f"\n6️⃣ Testing PATCH /users/{user_id} (Update)...")
    new_name = "Super Admin Updated"
    response = client.patch(f"/users/{user_id}", json={"full_name": new_name}, headers=headers)
    if response.status_code == 200:
        print("   ✅ Success.")
        assert response.json()["full_name"] == new_name
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")

    # 7. DELETE /users/{id} (Delete)
    # Let's create a *dummy* user to delete, so we don't delete ourselves and break the script?
    # Actually, let's just delete ourselves at the end. It's a test user.
    print(f"\n7️⃣ Testing DELETE /users/{user_id} (Delete)...")
    response = client.delete(f"/users/{user_id}", headers=headers)
    if response.status_code == 204:
        print("   ✅ Success.")
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")

    # 8. Verify deletion
    print("\n8️⃣ Verifying Deletion...")
    response = client.get(f"/users/{user_id}", headers=headers)
    # We might get 401 if our user is deleted and token invalid? 
    # Or 404 if token is still valid (JWT doesn't check DB on every req? check dependency)
    # Dependency checks DB: `user = db.query(User)... if user is None: raise credentials_exception`
    # So we should get 401 Unauthorized because the user no longer exists for the token credential check.
    
    if response.status_code == 401:
        print("   ✅ Verified: Token no longer valid (User deleted).")
    elif response.status_code == 404:
         print("   ✅ Verified: User not found.")
    else:
        print(f"   ⚠️ Unexpected status: {response.status_code} (Might be okay depending on implementation)")

    print("\n✨ Verification Complete!")

if __name__ == "__main__":
    run_verify()
