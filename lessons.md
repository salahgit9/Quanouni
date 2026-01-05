🚀 Prompt: Deploying FastAPI RAG Application to Render Cloud
Context
You are helping deploy a FastAPI-based RAG (Retrieval-Augmented Generation) application to Render.com. The application uses:

FastAPI backend with Supabase (PostgreSQL + pgvector)
BM25 in-memory search index
Google Gemini API for embeddings and generation
Frontend served as static files
I have successfully deployed a similar application to Render and encountered critical issues that you must avoid. Here are the lessons learned:

⚠️ Critical Issue #1: ModuleNotFoundError on Startup
Symptom
ModuleNotFoundError: No module named 'app'
Root Cause
The 
Dockerfile
 had incorrect WORKDIR configuration. When the container copied files to /app, but the Python imports used from app.services import ..., the paths didn't match.

Solution
Modify the Dockerfile:

# Copy project files
COPY . .
# CRITICAL: Change working directory to backend/
WORKDIR /app/backend
# Update CMD to use correct module path
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
Key Point: The WORKDIR must match the Python import structure. If your code uses from app.services import X, the working directory must be the parent of the app/ folder.

⚠️ Critical Issue #2: Missing Dependencies
Symptom
ModuleNotFoundError: No module named 'langchain_text_splitters'
Root Cause
Not all dependencies were listed in 
requirements.txt
. This happens when you install packages locally but forget to add them to the file.

Solution
Audit your imports: Review all 
.py
 files and verify every import is in 
requirements.txt
.
Use pip freeze (but be careful, it includes transitive dependencies):
pip freeze > requirements.txt
For this project, the missing package was:
langchain-text-splitters
Prevention
Before deploying, run a fresh virtual environment test:

python -m venv test_env
test_env\Scripts\activate
pip install -r requirements.txt
# Try importing all your modules
⚠️ Critical Issue #3: Weak Answers After Deployment (Data Staleness)
Symptom
After deploying to Render, the application returns generic answers like "Source 1", "Source 2" instead of actual document titles.

Root Cause
The data in Supabase was uploaded BEFORE code changes that added filename metadata. Old data lacks this field, causing broken references.

Solution
ALWAYS clear and re-upload data after metadata schema changes:

Open Supabase Dashboard → SQL Editor
Run:
DELETE FROM chunk;
DELETE FROM documents;
Re-upload all files through the application UI.
Restart Render service (Manual Deploy → Deploy latest commit).
Rule of Thumb: Whenever you modify the metadata structure in your ingestion code, you MUST clear and re-upload all data.

⚠️ Critical Issue #4: Accuracy Degradation with Large Datasets (THE BIG ONE)
Symptom
App works perfectly with 3-5 small books (~1000 chunks).
After uploading 5+ large books (~10,000+ chunks), answer quality drops dramatically.
References become incomplete or incorrect.
Root Cause
Supabase API has a default row limit of 1000 rows per query.

The BM25 initialization code was:

response = supabase.table("chunk").select("content,metadata").execute()
This fetches only the first 1000 rows, ignoring the rest. The BM25 index was incomplete, leading to poor search results.

Solution
Implement pagination to fetch ALL data:

def initialize_from_db(self):
    """Fetches ALL chunks from Supabase with pagination."""
    print("🔄 Building BM25 index from database...")
    try:
        supabase = get_supabase()
        
        all_chunks = []
        page_size = 1000
        start = 0
        
        print(f"🔄 Fetching chunks from DB in batches of {page_size}...")
        
        while True:
            end = start + page_size - 1
            response = supabase.table("chunk").select("content,metadata").range(start, end).execute()
            
            batch = response.data
            if not batch:
                break
            
            all_chunks.extend(batch)
            print(f"   - Fetched batch {start}-{end} (Total: {len(all_chunks)})")
            
            if len(batch) < page_size:
                break
                
            start += page_size
        
        if not all_chunks:
            print("⚠️ No chunks found in database. BM25 index will be empty.")
            return
        corpus = [chunk['content'] for chunk in all_chunks]
        metadatas = [chunk['metadata'] for chunk in all_chunks]
        
        print(f"✅ Fetched TOTAL {len(corpus)} chunks from DB. Building index...")
        
        # Build index
        tokenized_corpus = [doc.split(" ") for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.corpus = corpus
        self.metadatas = metadatas
        
        print("✅ BM25 index built successfully.")
        
    except Exception as e:
        print(f"❌ Error building BM25 from DB: {e}")
Verification in Logs: After deployment, check Render logs for:

✅ Fetched TOTAL 11349 chunks from DB. Building index...
If you see this number match your actual chunk count, pagination is working correctly.

⚠️ Critical Issue #5: Gemini API Rate Limiting
Symptom
429 You exceeded your current quota... limit: 20
Root Cause
The free tier of Gemini API has strict rate limits (15-20 requests per minute). A single RAG query can trigger 3-4 API calls (query expansion, reranking, generation), quickly exhausting the quota.

Solutions
Option 1: Wait (Temporary) The error message tells you exactly how long to wait:

Please retry in 51.913043936s
Wait ~1 minute and retry.

Option 2: Generate New API Key (Temporary) Create a new API key in a NEW Google Cloud project to get a fresh quota:

Go to Google AI Studio
Click "Create API key"
IMPORTANT: Choose "Create API key in a new project" (not existing)
Copy the new key
Update on Render:

Go to Render Dashboard → Your Service → Environment
Edit GEMINI_API_KEY variable
Paste new key → Save Changes
Render will auto-restart
Option 3: Upgrade to Paid Plan (Permanent) Enable billing in Google Cloud Console:

Go to Google Cloud Console
Enable billing for your project
You'll get pay-as-you-go pricing (very cheap, ~$0.0001 per request)
Rate limits are removed
📋 Pre-Deployment Checklist
Before deploying to Render, verify:

1. Dockerfile
# ✅ Correct WORKDIR
WORKDIR /app/backend
# ✅ Correct CMD path
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
2. requirements.txt
fastapi
uvicorn
python-dotenv
google-generativeai
chromadb  # if using
supabase
python-multipart
requests
numpy
pydantic
pydantic-settings
rank_bm25
langchain-text-splitters  # ⚠️ Don't forget this!
3. .gitignore
# Prevent tracking local cache files
backend/data/
*.pkl
data/chroma_db/
.env
4. Environment Variables on Render
GEMINI_API_KEY=your_key_here
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_GEMINI_CHAT_MODEL=gemini-1.5-pro-002
VITE_GEMINI_EMBEDDING_MODEL=models/text-embedding-004
5. Code Changes
✅ BM25 service has 
initialize_from_db()
 with pagination
✅ 
main.py
 has startup event calling bm25_service.initialize_from_db()
✅ Ingestion uses 
add_documents()
 not 
build_index()
🧪 Verification Steps After Deployment
1. Check Logs for BM25 Build
Look for:

🔄 Fetching chunks from DB in batches of 1000...
   - Fetched batch 0-999 (Total: 1000)
   - Fetched batch 1000-1999 (Total: 2000)
   ...
✅ Fetched TOTAL 11349 chunks from DB. Building index...
✅ BM25 index built successfully.
If the total matches your expected chunk count → ✅ SUCCESS.

2. Test with Sample Query
Upload a test document, then ask a question and verify:

✅ References show actual filenames (not "Source 1")
✅ Page numbers appear if available
✅ Answer is comprehensive and accurate
3. Monitor for 429 Errors
If you see repeated 429 errors, switch to a paid Gemini plan or implement retry logic with exponential backoff.

🔄 Data Management Best Practices
When to Clear Database
Clear Supabase data (and restart Render) when:

You modify the metadata structure in ingestion code
You change chunking logic (chunk_size, overlap)
You add new metadata fields (e.g., page_number, filename)
How to Clear Data
-- In Supabase SQL Editor
DELETE FROM chunk;
DELETE FROM documents;
Then in Render:

Go to Settings → Manual Deploy → Deploy latest commit
This triggers a restart with fresh BM25 index
After Clearing
Re-upload all documents through the UI
Verify logs show correct chunk count
Test queries to confirm accuracy
🎯 Summary: The Golden Rule
"On cloud platforms like Render, the filesystem is ephemeral. NEVER rely on local files. Always rebuild state (like BM25) from a persistent source (like Supabase) on startup, using PAGINATION to fetch ALL data."

🚀 Final Deployment Command Sequence
# 1. Update code
git add .
git commit -m "feat: Cloud-ready with pagination and fixes"
git push
# 2. Render will auto-deploy (if enabled)
# OR manually: Render Dashboard → Manual Deploy → Deploy latest commit
# 3. Clear Supabase (if metadata changed)
DELETE FROM chunk;
DELETE FROM documents;
# 4. Restart Render service
# Render Dashboard → Manual Deploy → Deploy latest commit
# 5. Re-upload documents through UI
# 6. Verify logs:
# ✅ "Fetched TOTAL X chunks from DB"
# ✅ X matches your expected count
# 7. Test with queries
# ✅ Accurate answers with correct references
💡 Pro Tips
Always test locally first with a fresh virtual environment.
Monitor Render logs during first deployment to catch errors early.
Use Manual Deploy instead of auto-deploy for critical updates.
Keep a backup of your 
.env
 file (but NEVER commit it to Git).
Document your metadata schema so you know when to clear data.
Good luck with your deployment! If you follow this guide, you'll avoid the painful debugging I went through. 🎉