"""
Ingestion script for Conseil d'État (مجلس الدولة) jurisprudence.
Each file is treated as a single chunk to preserve decision context.
"""
import os
import re
import sys
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.database import insert_document_record, insert_chunks_records
from app.services.embedding import get_embedding

DATA_DIR = Path("d:/TEST/QUANOUNI/new/data/jurisprudence/مجلس الدولة")
CATEGORY = "jurisprudence_conseil_etat"

def extract_metadata_from_filename(filename: str) -> dict:
    """Extract decision number and date from filename patterns like:
    - 'القرار رقم 033176 المؤرخ في 2007-04-25.txt'
    - 'قرار رقم 006222 مؤرخ في 2003-04-15.txt'
    - '2005-10-18 ‏قرار رقم 020217 مؤرخ في‎.txt'
    """
    decision_num = "Unknown"
    decision_date = "Unknown"
    
    # Try to extract decision number
    num_match = re.search(r'رقم\s*(\d+)', filename)
    if num_match:
        decision_num = num_match.group(1)
    
    # Try to extract date (YYYY-MM-DD format)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if date_match:
        decision_date = date_match.group(1)
    else:
        # Try DD-MM-YYYY or other formats
        date_match2 = re.search(r'(\d{2}-\s*\d{2}-\s*\d{4})', filename)
        if date_match2:
            decision_date = date_match2.group(1).replace(' ', '')
    
    return {
        "decision_number": decision_num,
        "decision_date": decision_date
    }

def ingest_conseil_etat():
    """Main ingestion function"""
    files = list(DATA_DIR.glob("*.txt"))
    print(f"بسم الله الرحمن الرحيم")
    print(f"Found {len(files)} files in {DATA_DIR}")
    print(f"Category: {CATEGORY}")
    print("-" * 50)
    
    success_count = 0
    error_count = 0
    
    for idx, file in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] Processing: {file.name[:50]}...")
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            error_count += 1
            continue
        
        if not content:
            print(f"   ⚠️ Empty file, skipping.")
            continue
        
        # Extract metadata from filename
        file_meta = extract_metadata_from_filename(file.name)
        
        metadata = {
            "source": "conseil_etat",
            "category": CATEGORY,
            "decision_number": file_meta["decision_number"],
            "decision_date": file_meta["decision_date"],
            "filename": file.name
        }
        
        # 1. Insert Document Record
        try:
            doc_record = insert_document_record(
                filename=file.name,
                total_chunks=1,  # One chunk per file
                category=CATEGORY
            )
            doc_id = doc_record['id']
        except Exception as e:
            print(f"   ❌ Error creating document record: {e}")
            error_count += 1
            continue
        
        # 2. Generate Embedding
        try:
            embedding = get_embedding(content)
        except Exception as e:
            print(f"   ❌ Error generating embedding: {e}")
            error_count += 1
            continue
        
        # 3. Insert Chunk
        try:
            chunk_data = [{
                "document_id": doc_id,
                "chunk_index": 0,
                "content": content,
                "embedding": embedding,
                "metadata": metadata
            }]
            insert_chunks_records(chunk_data)
            success_count += 1
            print(f"   ✅ Done (Doc ID: {doc_id})")
        except Exception as e:
            print(f"   ❌ Error inserting chunk: {e}")
            error_count += 1
            continue
    
    print("-" * 50)
    print(f"🏁 Ingestion Complete!")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📊 Total: {len(files)}")

if __name__ == "__main__":
    ingest_conseil_etat()
