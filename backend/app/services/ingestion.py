import shutil
import os
import uuid
from fastapi import UploadFile, HTTPException
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.embedding import get_batch_embeddings
from app.services.vector_store import add_documents_to_chroma
from app.services.database import insert_document_record, insert_chunks_records

UPLOAD_DIR = "data"

def save_uploaded_file(file: UploadFile) -> str:
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed")
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return file_path

def read_file_content(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def chunk_text(text: str) -> list[str]:
    """
    Split text into chunks using RecursiveCharacterTextSplitter.
    Optimized for Arabic text with smaller, more focused chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,  # Optimized for better context recall
        chunk_overlap=150,  # Increased overlap to prevent context loss
        separators=["\n\n", "\n", "。", ".", " ", ""],
        length_function=len,
    )
    chunks = text_splitter.split_text(text)
    return chunks

def process_document(file_path: str):
    content = read_file_content(file_path)
    chunks = chunk_text(content)
    filename = os.path.basename(file_path)
    
    # 1. Store Document in Supabase
    doc_record = insert_document_record(filename, len(chunks))
    doc_id = doc_record['id']
    
    # 2. Generate Embeddings
    embeddings = get_batch_embeddings(chunks)
    
    # 3. Prepare Data for Chroma and Supabase
    chroma_ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"document_id": doc_id, "chunk_index": i, "filename": filename} for i in range(len(chunks))]
    
    supabase_chunks_data = []
    for i, chunk in enumerate(chunks):
        supabase_chunks_data.append({
            "document_id": doc_id,
            "chunk_index": i,
            "content": chunk,
            "embedding_id": chroma_ids[i]
        })
        
    # 4. Store in ChromaDB
    add_documents_to_chroma(ids=chroma_ids, documents=chunks, metadatas=metadatas, embeddings=embeddings)
    
    # 5. Store Chunks in Supabase
    insert_chunks_records(supabase_chunks_data)
    
    # 6. Update BM25 Index
    # Note: This is inefficient for large datasets as it rebuilds the index every time.
    # For production, consider a more incremental approach or periodic rebuilds.
    from app.services.bm25_service import bm25_service
    
    # We need to add the new chunks to the existing corpus and rebuild
    current_corpus = bm25_service.corpus + chunks
    current_metadatas = bm25_service.metadatas + metadatas
    bm25_service.build_index(current_corpus, current_metadatas)
    
    return {
        "file_path": file_path,
        "total_chars": len(content),
        "total_chunks": len(chunks),
        "document_id": doc_id,
        "status": "processed_and_stored"
    }
