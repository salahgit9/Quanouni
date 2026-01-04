import os
import re
import sys
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.database import insert_document_record, insert_chunks_records
from app.services.embedding import get_embedding

DATA_DIR = Path("d:/TEST/QUANOUNI/new/data/jurisprudence")

def parse_multi_decision_file(filepath, content):
    """Parse files linked to specific chambers like criminal chamber containing multiple decisions delimited by ---"""
    raw_decisions = content.split('---')
    parsed = []
    
    for raw in raw_decisions:
        raw = raw.strip()
        if not raw: continue
            
        # Extract Metadata
        decision_match = re.search(r'القرار رقم\s*(\d+)', raw)
        decision_num = decision_match.group(1) if decision_match else "Unknown"
        
        date_match = re.search(r'المؤرخ في\s*(\d{2}/\d{2}/\d{4})', raw)
        decision_date = date_match.group(1) if date_match else "Unknown"
        
        chamber_match = re.search(r'###\s*( الغرفة .+)', raw)
        chamber = chamber_match.group(1).strip() if chamber_match else "Unknown"
        
        metadata = {
            "source": "supreme_court",
            "decision_number": decision_num,
            "decision_date": decision_date,
            "chamber": chamber,
            "category": "jurisprudence",
            "filename": filepath.name
        }
        parsed.append({"content": raw, "metadata": metadata})
    return parsed

def parse_topic_file(filepath, content):
    """Parse files named by topic (e.g., قتل.txt) from محكمة_عليا folder. 
       These often contain lists of principles or short summaries."""
    # Assuming these files might contain one or more snippets. 
    # If they use --- separator, proceed. If not, treat as one block or split by newlines if it looks like a list.
    
    topic = filepath.stem # e.g., 'قتل'
    
    if '---' in content:
         duplicates = content.split('---')
    else:
         # Check if it looks like a list of principles (numbered)
         # For now, let's treat chunks of text separated by double newlines as separate if large, 
         # or just chunk by size. But let's stick to logical splitting if possible.
         # Fallback: Just chunk by size or double newline.
         duplicates = [content] # Treat whole file as one context for now if small

    parsed = []
    for i, raw in enumerate(duplicates):
        raw = raw.strip()
        if not raw: continue
        
        metadata = {
            "source": "supreme_court_keywords",
            "topic": topic,
            "category": "jurisprudence",
            "filename": filepath.name,
            "files_subpath": str(filepath.parent.name)
        }
        
        # If the file is huge, we might want to split it by window
        # But 'topic' files usually contain condensed principles.
        parsed.append({"content": raw, "metadata": metadata})
        
    return parsed

def ingest_jurisprudence():
    # Recursive search for .txt files
    files = list(DATA_DIR.rglob("*.txt"))
    print(f"Found {len(files)} files in {DATA_DIR} (recursive)")
    
    for file in files:
        print(f"Processing {file.name}...")
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file.name}: {e}")
            continue

        # Determine strategy
        if 'اجتهادات_الغرفة' in file.name:
            decisions = parse_multi_decision_file(file, content)
        else:
            # Topic based files in subfolders
            decisions = parse_topic_file(file, content)

        if not decisions:
            print("No content found.")
            continue

        print(f"  > Found {len(decisions)} content chunks.")
        
        # 1. Insert Document Parent
        try:
            # Now passing category explicitly
            doc_record = insert_document_record(
                filename=file.name, 
                total_chunks=len(decisions),
                category="jurisprudence" 
            )
            doc_id = doc_record['id']
            print(f"  > Created Doc ID: {doc_id}")
        except Exception as e:
            print(f"Error creating doc record: {e}")
            continue

        # 2. Process Chunks
        chunks_data = []
        for i, dec in enumerate(decisions):
            try:
                embedding = get_embedding(dec['content'])
                chunks_data.append({
                    "document_id": doc_id,
                    "chunk_index": i,
                    "content": dec['content'],
                    "embedding": embedding,
                    "metadata": dec['metadata']
                })
            except Exception as e:
                print(f"Error embedding chunk: {e}")

        # 3. Batch Insert
        if chunks_data:
            try:
                # Chunk into batches of 50 to avoid request size limits if many chunks
                batch_size = 50
                for i in range(0, len(chunks_data), batch_size):
                    batch = chunks_data[i:i + batch_size]
                    insert_chunks_records(batch)
                    print(f"    > Inserted batch {i//batch_size + 1}")
                print("  > Done.")
            except Exception as e:
                print(f"Error inserting chunks: {e}")

if __name__ == "__main__":
    ingest_jurisprudence()
