
from app.services.database import get_supabase
from app.core.config import settings

def query_chroma(query_embedding: list[float], n_results: int = 20, where: dict = None):
    import requests
    
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_KEY
    rpc_url = f"{url}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "count=none"
    }
    
    # Prepare filters
    category_filter = where.get("category") if where else None
    
    payload = {
        "query_embedding": query_embedding,
        "match_count": n_results,
        "filter_category": category_filter
    }

    try:
        response = requests.post(rpc_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"Supabase RPC Error {response.status_code}: {response.text}")
            return {'documents': [[]], 'distances': [[]], 'metadatas': [[]]}
            
        data = response.json()
        
        documents = []
        distances = []
        metadatas = []
        
        for item in data:
            documents.append(item['content'])
            distances.append(item['similarity'])
            metadatas.append(item['metadata'])
            
        return {
            'documents': [documents],
            'distances': [distances],
            'metadatas': [metadatas]
        }
        
    except Exception as e:
        print(f"Supabase Vector Search Exception: {e}")
        return {'documents': [[]], 'distances': [[]], 'metadatas': [[]]}

def add_documents_to_chroma(ids: list[str], documents: list[str], metadatas: list[dict], embeddings: list[list[float]]):
    """
    Legacy function stub. 
    In the new Cloud Architecture, we insert directly to Supabase via ingest scripts.
    This stub prevents ImportErrors in ingestion.py.
    """
    print("WARNING: add_documents_to_chroma called but ignored (Cloud Migration). Use Supabase directly.")
    pass


