import os
import sys
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.database import insert_document_record, insert_chunks_records
from app.services.embedding import get_embedding

DATA_DIR = Path("d:/TEST/QUANOUNI/new/data/laws")
TARGET_FILE = "قانون الاستثمار.txt" # Small file for testing

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "المادة", "\n", ".", " ", ""],
    length_function=len,
    keep_separator=True
)

def debug_ingest_single_law():
    file_path = DATA_DIR / TARGET_FILE
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    print(f"Processing single file: {TARGET_FILE}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    chunks = text_splitter.split_text(content)
    print(f"  > Generated {len(chunks)} chunks.")
    
    # 1. Insert Document Parent
    try:
        print("  > Inserting document record...")
        doc_record = insert_document_record(
            filename=TARGET_FILE, 
            total_chunks=len(chunks),
            category="loi"
        )
        doc_id = doc_record['id']
        print(f"  > BEFORE INSERT: Received Doc ID: {doc_id} (Type: {type(doc_id)})")
        print(f"  > Full Doc Record: {doc_record}")
    except Exception as e:
        print(f"Error creating doc record: {e}")
        return

    # 2. Process Chunks
    chunks_data = []
    print(f"  > Embedding {len(chunks)} chunks...")
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
                    "filename": TARGET_FILE,
                    "chunk_index": i,
                    "category": "loi"
                }
            })
        except Exception as e:
            print(f"Error embedding chunk {i}: {e}")
            break

    # 3. Insert Chunks
    if chunks_data:
        try:
            print(f"  > Inserting {len(chunks_data)} chunks into 'chunk' table...")
            response = insert_chunks_records(chunks_data)
            print("  > Insert successful!")
            print(f"  > Response: {response}")
        except Exception as e:
            print("  > ERROR INSERTING CHUNKS:")
            print(f"  > {e}")
            if hasattr(e, 'code'): print(f"  > Code: {e.code}")
            if hasattr(e, 'details'): print(f"  > Details: {e.details}")
            if hasattr(e, 'hint'): print(f"  > Hint: {e.hint}")

if __name__ == "__main__":
    debug_ingest_single_law()
