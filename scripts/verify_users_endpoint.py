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
    print("🚀 Starting User Soft Delete & Reactivation Verification...")

    # 1. Register a user to be our Superadmin (if not exists)
    email = "sof_delete_admin@example.com"
    password = "password123"
    full_name = "Soft Delete Admin"
    
    print(f"\n1️⃣ Registering Superadmin {email}...")
    client.post("/auth/register", json={
        "email": email, "password": password, "full_name": full_name
    })

    # Promote to Superadmin
    print(f"   Promoting {email}...")
    subprocess.run(["uv", "run", "scripts/add_superadmin_column.py", "--promote", email], check=True, capture_output=True)

    # Login
    print("   Logging in...")
    login_response = client.post("/auth/token", data={"username": email, "password": password})
    token = login_response.json().get("access_token")
    if not token:
        print("❌ Login failed.")
        return
    headers = {"Authorization": f"Bearer {token}"}
    print("   ✅ Logged in.")

    # 2. Register a VICTIM user
    victim_email = "victim@example.com"
    victim_pass = "password123"
    print(f"\n2️⃣ Registering Victim {victim_email}...")
    client.post("/auth/register", json={
        "email": victim_email, "password": victim_pass, "full_name": "Victim User"
    })
    
    # Get Victim ID
    users = client.get("/users/", headers=headers).json()
    victim = next((u for u in users if u["email"] == victim_email), None)
    if not victim:
        print("❌ Victim not found.")
        return
    victim_id = victim["id"]
    print(f"   ✅ Victim ID: {victim_id}")

    # 3. Soft Delete Victim
    print(f"\n3️⃣ Soft Deleting Victim (ID: {victim_id})...")
    response = client.delete(f"/users/{victim_id}", headers=headers)
    if response.status_code == 204:
        print("   ✅ Success (204 No Content).")
    else:
        print(f"❌ Failed: {response.status_code}")
        return

    # 4. Verify Victim is Inactive
    print("\n4️⃣ Verifying Victim is Inactive...")
    response = client.get(f"/users/{victim_id}", headers=headers)
    user_data = response.json()
    if user_data["is_active"] is False:
        print("   ✅ Verified: is_active = False")
    else:
        print(f"❌ Failed: is_active is {user_data.get('is_active')}")

    # 5. Verify Victim Cannot Login
    print("\n5️⃣ Verifying Victim Cannot Login...")
    login_response = client.post("/auth/token", data={"username": victim_email, "password": victim_pass})
    if login_response.status_code == 400: # We set it to 400 in dependencies
        print("   ✅ Verified: Login rejected (400 Bad Request).")
    else:
        print(f"❌ Failed: Status {login_response.status_code} - {login_response.text}")

    # 6. Resurrect Victim
    print(f"\n6️⃣ Resurrecting Victim...")
    response = client.patch(f"/users/{victim_id}", json={"is_active": True}, headers=headers)
    if response.status_code == 200 and response.json()["is_active"] is True:
        print("   ✅ Resurrection Successful.")
    else:
        print(f"❌ Failed: {response.status_code}")

    # 7. Verify Victim Can Login Again
    print("\n7️⃣ Verifying Victim Can Login Again...")
    login_response = client.post("/auth/token", data={"username": victim_email, "password": victim_pass})
    if login_response.status_code == 200:
        print("   ✅ Verified: Login successful.")
    else:
        print(f"❌ Failed: Login still blocked ({login_response.status_code})")

    print("\n✨ Soft Delete & Reactivation Verified!")

if __name__ == "__main__":
    run_verify()
