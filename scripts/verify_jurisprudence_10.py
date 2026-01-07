import requests
import json
import time

API_URL = "http://127.0.0.1:8000/api"

# 10 Questions derived from data/jurisprudence
QUESTIONS = [
    "ما هي شروط بطلان الاعتراف المنتزع بالإكراه؟",
    "ما هي شروط قيام حالة الدفاع الشرعي؟",
    "ما هو الجزاء المترتب على تفتيش مسكن دون رضا صاحبه أو إذن قضائي؟",
    "هل ينتفي القصد الجنائي في السرقة إذا اعتقد الجاني ملكيته للمال؟",
    "هل يكفي ذكر ثبوت التهمة دون بيان الأدلة في حكم الإدانة؟",
    "هل تخضع السلطة التقديرية للقاضي في منح الظروف المخففة للرقابة؟",
    "ما أثر تجاوز مدة التوقيف للنظر القانونية على الإجراءات؟",
    "هل يجوز الحكم بالسجن عند انتفاء الركن المعنوي للجريمة؟",
    "ما هي اجتهادات المحكمة في الخلع والطلاق؟",
    "ما هي المبادئ المستقرة في جرائم المخدرات؟"
]

def verify_jurisprudence():
    print("⚖️ STARTING JURISPRUDENCE EVALUATION (10 QUESTIONS)\n")
    
    # 1. Login
    try:
        print("🔑 Logging in...")
        auth_resp = requests.post(f"{API_URL}/login", json={"username": "salah", "password": "password123"})
        if not auth_resp.ok:
            print(f"❌ Login failed: {auth_resp.text}")
            return
        token = auth_resp.json()['token']
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful.\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 2. Run Queries
    results = []
    
    for i, q in enumerate(QUESTIONS, 1):
        print(f"❓ Q{i}: {q}")
        start_time = time.time()
        
        try:
            payload = {
                "legal_issue": q,
                "chamber": None, # General search across all chambers
                "top_k": 10
            }
            
            resp = requests.post(f"{API_URL}/legal/jurisprudence", json=payload, headers=headers)
            duration = time.time() - start_time
            
            if resp.ok:
                data = resp.json()
                sources = data.get('sources', [])
                num_sources = len(sources)
                analysis_preview = data.get('analysis', '')[:100].replace('\n', ' ')
                
                print(f"   ✅ Answered in {duration:.2f}s")
                print(f"   📄 Sources Found: {num_sources}")
                
                if num_sources > 0:
                    top_source = sources[0]
                    print(f"   🏆 Top Source: {top_source.get('filename')} (Score: {top_source.get('relevance_score')})")
                    # Check for citations in analysis
                    has_citation = "قرار رقم" in data.get('analysis', '')
                    print(f"   📝 Citation Detected: {'YES' if has_citation else 'NO'}")
                else:
                    print("   ⚠️ NO SOURCES FOUND")
                    
                print("-" * 60)
                
            else:
                print(f"   ❌ API Error: {resp.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            
        # Delay to avoid rate limits
        time.sleep(5)

if __name__ == "__main__":
    verify_jurisprudence()
