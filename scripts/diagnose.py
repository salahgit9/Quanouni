"""
QUANOUNI Diagnostic Script
Tests: Groq API, Gemini API, Supabase RPC
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

def test_groq():
    print("\n" + "="*50)
    print("🧪 TEST 1: GROQ API")
    print("="*50)
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found in .env!")
        return False
    
    print(f"   API Key: {api_key[:10]}...{api_key[-5:]}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    print(f"   Model: {model}")
    
    data = {
        "messages": [{"role": "user", "content": "قل مرحبا"}],
        "model": model,
        "max_tokens": 50
    }
    
    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                           headers=headers, json=data, timeout=30)
        
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            print(f"   ✅ SUCCESS: {content[:50]}")
            return True
        else:
            print(f"   ❌ FAILED: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")
        return False

def test_gemini():
    print("\n" + "="*50)
    print("🧪 TEST 2: GEMINI API")
    print("="*50)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env!")
        return False
    
    print(f"   API Key: {api_key[:10]}...{api_key[-5:]}")
    
    model = os.getenv("VITE_GEMINI_CHAT_MODEL", "gemini-1.5-flash-latest")
    print(f"   Model from env: {model}")
    
    # Try different model names
    models_to_try = [
        model,
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-pro",
        "gemini-1.0-pro"
    ]
    
    for m in models_to_try:
        print(f"\n   Trying model: {m}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        
        data = {
            "contents": [{"parts": [{"text": "قل مرحبا"}]}]
        }
        
        try:
            resp = requests.post(url, json=data, timeout=30)
            
            if resp.status_code == 200:
                content = resp.json()['candidates'][0]['content']['parts'][0]['text']
                print(f"   ✅ SUCCESS with {m}: {content[:50]}")
                return m  # Return the working model name
            else:
                print(f"   ❌ {m}: {resp.status_code} - {resp.text[:100]}")
        except Exception as e:
            print(f"   ❌ {m}: Exception - {e}")
    
    return False

def test_supabase_rpc():
    print("\n" + "="*50)
    print("🧪 TEST 3: SUPABASE RPC (match_documents)")
    print("="*50)
    
    url = os.getenv("VITE_SUPABASE_URL")
    key = os.getenv("VITE_SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("❌ Supabase credentials not found!")
        return False
    
    print(f"   URL: {url}")
    print(f"   Key: {key[:15]}...")
    
    # Create a dummy embedding (768 dimensions)
    dummy_embedding = [0.01] * 768
    
    rpc_url = f"{url}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query_embedding": dummy_embedding,
        "match_count": 3,
        "filter_category": None
    }
    
    try:
        resp = requests.post(rpc_url, headers=headers, json=payload, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ SUCCESS: Retrieved {len(data)} documents")
            if data:
                print(f"   First doc: {data[0].get('content', 'N/A')[:50]}...")
            return True
        else:
            print(f"   ❌ FAILED: {resp.status_code}")
            print(f"   Response: {resp.text[:300]}")
            return False
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "🔍 QUANOUNI DIAGNOSTIC REPORT 🔍".center(50))
    
    groq_ok = test_groq()
    gemini_model = test_gemini()
    db_ok = test_supabase_rpc()
    
    print("\n" + "="*50)
    print("📊 SUMMARY")
    print("="*50)
    print(f"   Groq API:    {'✅ Working' if groq_ok else '❌ FAILED'}")
    print(f"   Gemini API:  {'✅ Working (model: ' + gemini_model + ')' if gemini_model else '❌ FAILED'}")
    print(f"   Supabase DB: {'✅ Working' if db_ok else '❌ FAILED'}")
    
    if gemini_model and gemini_model != os.getenv("VITE_GEMINI_CHAT_MODEL"):
        print(f"\n⚠️ RECOMMENDATION: Update VITE_GEMINI_CHAT_MODEL in .env to: {gemini_model}")
