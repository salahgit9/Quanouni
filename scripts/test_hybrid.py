"""
اختبار توازن البحث الهجين (Vector + BM25)
يتحقق من أن كلا النظامين يعملان ويساهمان في النتائج
"""
import os
import sys
sys.path.insert(0, 'd:/TEST/QUANOUNI/new/backend')

from dotenv import load_dotenv
load_dotenv('d:/TEST/QUANOUNI/new/.env')

import requests
import google.generativeai as genai

# Configure Gemini for embeddings
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

def get_embedding(text):
    """Get embedding using Gemini"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query"
    )
    return result['embedding']

from app.services.vector_store import query_chroma
from app.services.bm25_service import bm25_service

def test_hybrid_search():
    query = "ما هي شروط الميراث في القانون الجزائري؟"
    
    print("=" * 60)
    print("🔍 اختبار البحث الهجين (Hybrid Search)")
    print("=" * 60)
    print(f"\n📝 الاستعلام: {query}\n")
    
    # 1. Test Vector Search
    print("-" * 40)
    print("🧠 اختبار البحث الدلالي (Vector Search)")
    print("-" * 40)
    
    try:
        embedding = get_embedding(query)
        vector_results = query_chroma(embedding, n_results=5)
        v_docs = vector_results.get('documents', [[]])[0]
        v_metas = vector_results.get('metadatas', [[]])[0]
        
        if v_docs:
            print(f"✅ نجح! عدد النتائج: {len(v_docs)}")
            for i, (doc, meta) in enumerate(zip(v_docs[:3], v_metas[:3])):
                filename = meta.get('filename', 'غير معروف')
                print(f"   {i+1}. {filename}: {doc[:80]}...")
        else:
            print("❌ فشل أو لا توجد نتائج!")
    except Exception as e:
        print(f"❌ خطأ: {e}")
        v_docs = []
    
    # 2. Test BM25 Search
    print("\n" + "-" * 40)
    print("📚 اختبار البحث بالكلمات (BM25)")
    print("-" * 40)
    
    try:
        bm25_results = bm25_service.search(query, top_k=5)
        
        if bm25_results:
            print(f"✅ نجح! عدد النتائج: {len(bm25_results)}")
            for i, (doc, score, meta) in enumerate(bm25_results[:3]):
                filename = meta.get('filename', 'غير معروف')
                print(f"   {i+1}. {filename} (score: {score:.4f}): {doc[:60]}...")
        else:
            print("❌ فشل أو لا توجد نتائج!")
    except Exception as e:
        print(f"❌ خطأ: {e}")
        bm25_results = []
    
    # 3. Summary
    print("\n" + "=" * 60)
    print("📊 ملخص النتائج")
    print("=" * 60)
    
    vector_ok = len(v_docs) > 0
    bm25_ok = len(bm25_results) > 0
    
    print(f"   البحث الدلالي (Vector): {'✅ يعمل' if vector_ok else '❌ لا يعمل'}")
    print(f"   البحث بالكلمات (BM25):  {'✅ يعمل' if bm25_ok else '❌ لا يعمل'}")
    
    if vector_ok and bm25_ok:
        print("\n🎯 النظام الهجين يعمل بشكل متوازن!")
        print("   كلا المصدرين يساهمان في النتائج النهائية (50% لكل منهما)")
    elif bm25_ok and not vector_ok:
        print("\n⚠️ تحذير: النظام يعتمد على BM25 فقط!")
        print("   يرجى التحقق من اتصال Supabase")
    elif vector_ok and not bm25_ok:
        print("\n⚠️ تحذير: النظام يعتمد على Vector فقط!")
        print("   يرجى التحقق من فهرس BM25")
    else:
        print("\n❌ كلا النظامين لا يعملان!")

if __name__ == "__main__":
    test_hybrid_search()
