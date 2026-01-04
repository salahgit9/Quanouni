import os
import sys
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.database import insert_document_record, insert_chunks_records
from app.services.embedding import get_embedding

DATA_DIR = Path("d:/TEST/QUANOUNI/new/data/laws")

# Use a splitter optimized for Arabic text structure
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "المادة", "\n", ".", " ", ""],
    length_function=len,
    keep_separator=True
)

def ingest_pilot_laws():
    files = list(DATA_DIR.rglob("*.txt"))
    # PILOT MODE: Take only first 10 files
    files = files[:10]
    
    print(f"--- PILOT MODE: Processing {len(files)} files ---")
    
    for file in files:
        print(f"Processing {file.name}...")
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file.name}: {e}")
            continue

        if not content.strip():
            print("Empty file. Skipping.")
            continue
            
        chunks = text_splitter.split_text(content)
        print(f"  > Generated {len(chunks)} chunks.")
        
        # 1. Insert Document Parent
        try:
            doc_record = insert_document_record(
                filename=file.name, 
                total_chunks=len(chunks),
                category="loi"
            )
            doc_id = doc_record['id']
            print(f"  > Doc Inserted. ID: {doc_id}")
        except Exception as e:
            print(f"Error creating doc record: {e}")
            continue

        # 2. Process Chunks
        chunks_data = []
        for i, chunk_text in enumerate(chunks):
            try:
                embedding = get_embedding(chunk_text)
                chunks_data.append({
                    "document_id": doc_id,
                    "chunk_index": i,
                    "content": chunk_text,
                    "embedding": embedding,
                    "metadata": {
                        "source": "law_file",
                        "filename": file.name,
                        "chunk_index": i,
                        "category": "loi"
                    }
                })
            except Exception as e:
                print(f"Error embedding chunk {i}: {e}")
                # Don't break completely, try next chunk
                continue

        # 3. Batch Insert
        if chunks_data:
            try:
                batch_size = 50
                for i in range(0, len(chunks_data), batch_size):
                    batch = chunks_data[i:i + batch_size]
                    response = insert_chunks_records(batch)
                    print(f"    > Inserted batch {i//batch_size + 1} ({len(batch)} chunks)")
            except Exception as e:
                print("    > ERROR INSERTING BATCH:")
                print(f"    > {e}")
                # Try to print specific attributes if available
                if hasattr(e, 'message'): print(f"    > Message: {e.message}")
                if hasattr(e, 'code'): print(f"    > Code: {e.code}")
                if hasattr(e, 'details'): print(f"    > Details: {e.details}")
                if hasattr(e, 'hint'): print(f"    > Hint: {e.hint}")

if __name__ == "__main__":
    ingest_pilot_laws()
