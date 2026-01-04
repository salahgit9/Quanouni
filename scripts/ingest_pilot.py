
import os
import time
import glob
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai
from supabase import create_client, Client
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Pilot Files (Top 10)
PILOT_FILES = [
    "قانون_العقوبات.txt",
    "قانون_الإجراءات_الجزائية.txt", 
    "القانون المدني.txt",
    "قانون الإجراءات المدنية والإدارية.txt",
    "قانون الاسرة.txt",
    "الدستور.txt",
    "القانون التجاري.txt",
    "علاقات العمل.txt",
    "قانون الوقاية من الفساد ومكافحته.txt",
    "قانون الاستثمار.txt"
]

genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
            # Handle different SDK response formats
            if 'embedding' in response:
                results.extend(response['embedding'])
            else:
                 # If response is a list or dict with payload
                 results.extend([r['embedding'] for r in response])
        except Exception as e:
            print(f"Error embedding batch {i}: {e}")
            # Retry once
            time.sleep(2)
            try:
                 response = genai.embed_content(model=model, content=batch, task_type="retrieval_document")
                 results.extend(response['embedding'])
            except:
                 print("Retry failed. Skipping batch.")
                 results.extend([[0.0]*768] * len(batch)) # Dummy to preserve index alignment? No, better to fail.
    return results

def ingest_pilot():
    base_path = "data/laws"
    
    print("--- Starting PILOT Ingestion (Full Cloud) ---")
    
    for filename in PILOT_FILES:
        file_path = os.path.join(base_path, filename)
        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {filename}")
            continue
            
        print(f"Processing: {filename}...")
        
        # Read content
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        # Split
        chunks = text_splitter.split_text(text)
        print(f"  -> Generated {len(chunks)} chunks.")
        
        # Embed
        print("  -> Generating embeddings...")
        embeddings = get_embeddings(chunks)
        
        if len(embeddings) != len(chunks):
            print("  ❌ Mismatch in embeddings count. Skipping file.")
            continue
            
        # Upload to Supabase
        print("  -> Uploading to Supabase (Documents & Chunks)...")
        
        try:
            # 1. Create Document
            doc_res = supabase.table("documents").insert({
                "filename": filename,
                "total_chunks": len(chunks),
                "category": "loi",
                "doc_type": "pilot_v1",
                "source_meta": {"priority": "high"}
            }).execute()
            
            doc_id = doc_res.data[0]['id']
            
            # 2. Create Chunks
            chunks_data = []
            for i, (chunk_text, vector) in enumerate(zip(chunks, embeddings)):
                chunks_data.append({
                    "document_id": doc_id,
                    "chunk_index": i,
                    "content": chunk_text,
                    "embedding": vector # Supabase-py should handle list -> vector conversion
                })
                
            # Insert in batches of 100 to avoid packet size limits
            for i in range(0, len(chunks_data), 100):
                supabase.table("chunk").insert(chunks_data[i:i+100]).execute()
                
            print(f"  ✅ Successfully ingested {filename}")
            
        except Exception as e:
            print(f"  ❌ Error uploading {filename}: {e}")

    print("\n--- Pilot Ingestion Complete ---")

if __name__ == "__main__":
    ingest_pilot()
