import os
import sys
import uuid
from typing import List

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from supabase import create_client, Client
from app.core.config import settings

def debug_supabase():
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_KEY
    print(f"Connecting to Supabase: {url}")
    supabase: Client = create_client(url, key)
    
    # 1. Test Document Insertion
    print("\n--- Testing Document Insertion ---")
    doc_data = {
        "filename": "DEBUG_TEST_FILE.txt",
        "total_chunks": 1,
        "category": "debug"
    }
    try:
        response = supabase.table("documents").insert(doc_data).execute()
        print(f"Success! Doc ID: {response.data[0]['id']}")
        doc_id = response.data[0]['id']
    except Exception as e:
        print(f"FAILED to insert document: {e}")
        return

    # 2. Test Chunk Insertion
    print("\n--- Testing Chunk Insertion ---")
    # Generate a dummy 768-dim vector
    dummy_embedding = [0.1] * 768
    
    chunk_data = {
        "document_id": doc_id,  # UUID from step 1
        "chunk_index": 0,
        "content": "This is a debug chunk content.",
        "embedding": dummy_embedding,
        "metadata": {"test": "true"}
    }
    
    try:
        response = supabase.table("chunk").insert(chunk_data).execute()
        print(f"Success! Chunk inserted: {response.data}")
    except Exception as e:
        print(f"FAILED to insert chunk: {e}")
        # Try to print more details is possible
        if hasattr(e, 'code'): print(f"Error Code: {e.code}")
        if hasattr(e, 'details'): print(f"Error Details: {e.details}")
        if hasattr(e, 'hint'): print(f"Error Hint: {e.hint}")

if __name__ == "__main__":
    debug_supabase()
