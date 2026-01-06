import requests
import re
from rank_bm25 import BM25Okapi
from typing import List, Tuple
from app.core.config import settings

class BM25Service:
    def __init__(self):
        self.bm25 = None
        self.corpus = []  # List of texts (chunks)
        self.metadatas = []  # List of metadata
        self._loaded = False

    def load_from_supabase(self, category: str = None):
        """Load all chunks from Supabase and build BM25 index."""
        if self._loaded:
            return  # Already loaded
        
        print("Loading chunks from Supabase for BM25 index...")
        
        headers = {
            "apikey": settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Get all chunks with their metadata
        # Use pagination for large datasets
        all_chunks = []
        offset = 0
        limit = 1000
        
        while True:
            # Join with documents table to get metadata
            url = f"{settings.SUPABASE_URL}/rest/v1/chunk?select=id,content,document_id,documents(filename,category,source_meta)&offset={offset}&limit={limit}"
            resp = requests.get(url, headers=headers, timeout=60)
            
            if resp.status_code != 200:
                print(f"Error loading chunks: {resp.status_code} - {resp.text}")
                break
            
            data = resp.json()
            if not data:
                break
            
            all_chunks.extend(data)
            offset += limit
            
            if len(data) < limit:
                break
        
        print(f"Loaded {len(all_chunks)} chunks from Supabase")
        
        if not all_chunks:
            return
        
        # Build corpus and metadata
        self.corpus = []
        self.metadatas = []
        
        for chunk in all_chunks:
            content = chunk.get('content', '')
            
            # Flatten metadata from joined 'documents' dict
            doc_info = chunk.get('documents', {})
            metadata = {
                'filename': doc_info.get('filename') if doc_info else 'Unknown',
                'category': doc_info.get('category') if doc_info else None,
                'source_meta': doc_info.get('source_meta') if doc_info else {}
            }
            
            if content:
                self.corpus.append(content)
                self.metadatas.append(metadata)
        
        # Build BM25 index with Arabic-aware tokenization
        if self.corpus:
            tokenized_corpus = [self._arabic_tokenize(doc) for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
            self._loaded = True
            print(f"BM25 index built with {len(self.corpus)} documents (Arabic tokenizer enabled)")

    def _arabic_tokenize(self, text: str) -> List[str]:
        """Arabic-aware tokenizer with diacritics removal and letter normalization."""
        if not text:
            return []
        # 1. Remove diacritics (tashkeel)
        text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
        # 2. Normalize Alef variants (أ إ آ ا -> ا)
        text = re.sub(r'[أإآ]', 'ا', text)
        # 3. Normalize Ya and Taa Marbuta (ى -> ي, ة -> ه)
        text = text.replace('ى', 'ي').replace('ة', 'ه')
        # 4. Split on whitespace and punctuation (Arabic + Latin)
        tokens = re.split(r'[\s،.؛:؟!\-\(\)\[\]«»"\'/\\]+', text)
        # 5. Remove empty and very short tokens
        return [t.strip() for t in tokens if len(t.strip()) > 1]

    def search(self, query: str, top_k: int = 5, filters: dict = None) -> List[Tuple[str, float, dict]]:
        """Search the corpus using BM25."""
        # Lazy loading
        if not self._loaded:
            self.load_from_supabase()
        
        if not self.bm25:
            return []

        tokenized_query = self._arabic_tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        results = []
        for i, score in enumerate(scores):
            if score > 0:
                meta = self.metadatas[i] if i < len(self.metadatas) else {}
                
                # Apply filters
                if filters:
                    match = True
                    for key, value in filters.items():
                        if meta.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                        
                results.append((self.corpus[i], score, meta))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

# Global instance
bm25_service = BM25Service()
