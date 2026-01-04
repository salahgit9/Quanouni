
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

# Configuration
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: credentials not found in env vars.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def clear_database():
    print("WARNING: This will delete ALL data from 'documents' and 'chunk' tables.")
    confirm = input("Are you sure? (Type 'yes' to confirm): ")
    
    if confirm != "yes":
        print("Aborted.")
        return

    print("Deleting chunks...")
    # Supabase Delete requires a filter. To delete all, we can use a condition that is always true or better, delete documents cascade.
    # If we delete documents, chunks should be deleted via CASCADE if configured.
    # Let's check schema: "document_id uuid references documents(id) on delete cascade" -> YES.
    
    try:
        # We can't delete * easily without Service Key usually if RLS is on.
        # But assuming we have write access (since we can insert).
        # We need a filter. id is not null usually works.
        res = supabase.table("documents").delete().neq("filename", "PLACEHOLDER_IMPOSSIBLE").execute()
        print(f"Deleted documents. Response: {len(res.data)} items removed.")
    except Exception as e:
        print(f"Error deleting: {e}")
        print("Trying to delete chunks explicitly first...")
        try:
             supabase.table("chunk").delete().neq("content", "PLACEHOLDER").execute()
             supabase.table("documents").delete().neq("filename", "PLACEHOLDER").execute()
        except Exception as e2:
             print(f"Double failure: {e2}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    clear_database()
