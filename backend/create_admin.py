import asyncio
import sys
import os
from passlib.context import CryptContext

# Ensure we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.database import get_supabase

# Setup Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

async def create_admin(username, password, email=None, full_name="System Admin"):
    supabase = get_supabase()
    
    print(f"Checking if user '{username}' exists...")
    # check if user exists
    try:
        res = supabase.table("users").select("*").eq("username", username).execute()
        if res.data:
            print(f"⚠️ User '{username}' already exists. Upgrading to ADMIN and resetting password...")
            hashed_pwd = get_password_hash(password)
            supabase.table("users").update({
                "role": "admin",
                "password_hash": hashed_pwd
            }).eq("username", username).execute()
            print(f"✅ User '{username}' upgraded to ADMIN with new password!")
            return
    except Exception as e:
        print(f"⚠️ Error checking/upgrading user: {e}")

    print(f"Creating admin user '{username}'...")
    user_data = {
        "username": username,
        "password_hash": get_password_hash(password),
        "email": email,
        "full_name": full_name,
        "role": "admin"  # Explicitly setting admin role
    }

    try:
        data = supabase.table("users").insert(user_data).execute()
        print(f"✅ Admin user '{username}' created successfully!")
    except Exception as e:
        print(f"❌ Error creating admin: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password> [email]")
    else:
        username = sys.argv[1]
        password = sys.argv[2]
        email = sys.argv[3] if len(sys.argv) > 3 else None
        
        asyncio.run(create_admin(username, password, email))
