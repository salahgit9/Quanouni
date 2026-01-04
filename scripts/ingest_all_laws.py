"""
QANOUNI-AI: Complete Data Ingestion Script
==========================================
This script uploads ALL law documents from the /data folder to Supabase.

Usage:
1. Create new Supabase project
2. Run the SQL schema in Supabase SQL Editor
3. Update .env with new SUPABASE_URL and SUPABASE_KEY
4. Run: python scripts/ingest_all_laws.py
"""

import os
import sys
import time
import glob
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai
from supabase import create_client, Client
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Add parent to path for relative imports if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Missing Supabase credentials in .env file!")
    print("   Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY")
    sys.exit(1)

if not GEMINI_API_KEY:
    print("❌ ERROR: Missing GEMINI_API_KEY in .env file!")
    sys.exit(1)

print(f"✅ Supabase URL: {SUPABASE_URL[:30]}...")
print(f"✅ Gemini API Key: {GEMINI_API_KEY[:10]}...")

genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Text Splitter (optimized for Arabic legal text)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=150,
    separators=["\n\n", "\n", "。", ".", " ", ""],
    length_function=len,
)

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Batch generation of embeddings using Gemini"""
    model = "models/text-embedding-004"
    results = []
    batch_size = 50
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = genai.embed_content(
                model=model,
                content=batch,
                task_type="retrieval_document"
            )
            if 'embedding' in response:
                results.extend(response['embedding'])
            else:
                # Fallback for different SDK versions
                for r in response:
                    results.append(r.get('embedding', [0.0]*768))
        except Exception as e:
            print(f"   ⚠️ Error embedding batch {i}: {e}")
            time.sleep(5)  # Rate limit protection
            try:
                response = genai.embed_content(model=model, content=batch, task_type="retrieval_document")
                results.extend(response['embedding'])
            except Exception as e2:
                print(f"   ❌ Retry failed: {e2}")
                # Fill with zeros to preserve alignment (not ideal but prevents crash)
                results.extend([[0.0]*768] * len(batch))
        
        # Rate limiting
        time.sleep(0.5)
    
    return results

def ingest_all_documents(data_path: str = "data"):
    """Ingest all .txt files from data folder to Supabase"""
    
    # Find all txt files
    all_files = glob.glob(os.path.join(data_path, "**/*.txt"), recursive=True)
    
    if not all_files:
        print(f"❌ No .txt files found in {data_path}")
        return
    
    print(f"\n📚 Found {len(all_files)} documents to ingest.\n")
    
    success_count = 0
    error_count = 0
    
    for idx, file_path in enumerate(all_files, 1):
        filename = os.path.basename(file_path)
        print(f"[{idx}/{len(all_files)}] Processing: {filename}")
        
        try:
            # Read content
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if len(text) < 50:
                print(f"   ⚠️ Skipping (too short): {len(text)} chars")
                continue
            
            # Split into chunks
            chunks = text_splitter.split_text(text)
            print(f"   → {len(chunks)} chunks")
            
            # Generate embeddings
            print(f"   → Embedding...")
            embeddings = get_embeddings(chunks)
            
            if len(embeddings) != len(chunks):
                print(f"   ❌ Embedding mismatch! Expected {len(chunks)}, got {len(embeddings)}")
                error_count += 1
                continue
            
            # Determine category from filepath
            category = "law"
            if "jurisprudence" in file_path.lower():
                category = "jurisprudence"
            elif "ordonnance" in file_path.lower():
                category = "ordonnance"
            
            # Upload to Supabase
            print(f"   → Uploading to Supabase...")
            
            # 1. Create Document record
            doc_res = supabase.table("documents").insert({
                "filename": filename,
                "total_chunks": len(chunks),
                "category": category,
                "metadata": {"source_path": file_path}
            }).execute()
            
            doc_id = doc_res.data[0]['id']
            
            # 2. Create Chunk records (batch insert)
            chunks_data = []
            for i, (chunk_text, vector) in enumerate(zip(chunks, embeddings)):
                chunks_data.append({
                    "document_id": doc_id,
                    "chunk_index": i,
                    "content": chunk_text,
                    "embedding": vector,
                    "metadata": {"filename": filename}
                })
            
            # Insert in batches of 100
            for i in range(0, len(chunks_data), 100):
                batch = chunks_data[i:i+100]
                supabase.table("chunk").insert(batch).execute()
            
            print(f"   ✅ Done!")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            error_count += 1
            continue
    
    print("\n" + "="*50)
    print(f"📊 INGESTION COMPLETE")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Errors:  {error_count}")
    print("="*50)

if __name__ == "__main__":
    # Default path is relative to project root
    data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    print("="*50)
    print("QANOUNI-AI: Full Data Ingestion")
    print("="*50)
    print(f"Data folder: {data_folder}")
    
    # Ask for confirmation
    input("\nPress ENTER to start ingestion (Ctrl+C to cancel)...")
    
    ingest_all_documents(data_folder)
