
import requests
import json
import time

API_URL = "http://127.0.0.1:8000/api"

scenarios = [
    {
        "category": "Mيراث (Inheritance)",
        "question": "توفي أب وترك زوجة و3 أولاد وبنت، كيف تقسم التركة؟",
        "consultant_situation": "توفي والدي رحمه الله وترك منزلاً ومبلغاً مالياً. الورثة هم والدتي (زوجته) و3 إخوة ذكور وأخت واحدة. نريد معرفة القسمة الشرعية والقانونية للإرث."
    },
    {
        "category": "عمل (Labor)",
        "question": "ما هي حقوق العامل في حالة الفصل التعسفي؟",
        "consultant_situation": "أعمل في شركة خاصة منذ 5 سنوات بعقد غير محدد المدة. فجأة قام المدير بفصلي دون سابق إنذار أو خطأ جسيم من طرفي. ما هي حقوقي القانونية وكيف أطالب بالتعويض؟"
    },
    {
        "category": "جنائي (Penal - Theft)",
        "question": "ما هي عقوبة السرقة مع توافر ظرف الليل؟",
        "consultant_situation": "تعرض متجري للسرقة ليلاً. تم القبض على السارق. أريد معرفة العقوبة المتوقعة عليه في القانون الجزائي وهل يعتبر الليل ظرفاً مشدداً؟"
    },
    {
        "category": "مدني (Civil - Rent)",
        "question": "كيف يتم فسخ عقد الإيجار لعدم دفع الأجرة؟",
        "consultant_situation": "قمت بتأجير شقتي لشخص بعقد موثق، لكنه توقف عن دفع الإيجار منذ 6 أشهر ويرفض الخروج. كيف أسترجع شقتي وأحصل على أموالي؟"
    },
    {
        "category": "أسرة (Family - Khul)",
        "question": "ما هي إجراءات الخلع وما يترتب عليها؟",
        "consultant_situation": "أريد رفع دعوى خلع ضد زوجي لاستحالة العشرة بيننا. سؤالي: ما هي الإجراءات القانونية؟ وهل أفقد حق الحضانة أو النفقة للأولاد؟ وما هو المبلغ الذي يجب أن أدفعه؟"
    },
    {
        "category": "إداري (Administrative)",
        "question": "ما هي شروط دعوى إلغاء القرار الإداري؟",
        "consultant_situation": "صدر قرار من البلدية بهدم سور منزلي بحجة عدم المطابقة. أرى أن القرار تعسفي وغير قانوني. كيف أرفع دعوى لإلغاء هذا القرار أمام المحكمة الإدارية؟"
    },
    {
        "category": "تجاري (Commercial - Bankruptcy)",
        "question": "ما هي آثار إفلاس التاجر؟",
        "consultant_situation": "أنا تاجر وتراكمت علي الديون وعجزت عن سدادها. هل يجب أن أعلن إفلاسي؟ وما هي الآثار القانونية لذلك على ممتلكاتي الخاصة؟"
    },
    {
        "category": "مرور (Traffic)",
        "question": "ما هي عقوبة جنحة الفرار بعد حادث مرور؟",
        "consultant_situation": "ارتكبت حادث مرور بسيط بسبب الارتباك وهربت من المكان خوفاً. تم استدعائي من الشرطة لاحقاً. ماذا يترتب علي قانوناً بتهمة الفرار؟"
    },
    {
        "category": "عقاري (Real Estate - Undivided)",
        "question": "كيف يتم الخروج من حالة الشياع في العقار؟",
        "consultant_situation": "نملك قطعة أرض أنا وإخوتي على الشيوع (ميراث). أحد الإخوة يرفض القسمة أو البيع. كيف يمكنني قانوناً الخروج من الشياع والحصول على نصيبي مفرزاً؟"
    },
    {
        "category": "إجراءات (Procedural - Appeal)",
        "question": "ما هي آجال الاستئناف في القضايا الجزائية؟",
        "consultant_situation": "صدر حكم غيابي ضدي بغرامة مالية. أريد أن أعارضه أو أستأنفه. كم يوماً لدي لتقديم الاستئناف وهل تحتسب أيام العطل؟"
    }
]

def test_research(scenario):
    print(f"\n--- Testing Research Mode: {scenario['category']} ---")
    try:
        start = time.time()
        # Assuming research endpoint is passed as query params or body depending on implementation.
        # Based on previous context, usually POST /api/query or GET /api/search
        # Checking routes.py previously: @router.post("/query")
        payload = {"query": scenario['question'], "filters": {}}
        response = requests.post(f"{API_URL}/query", json=payload, timeout=120)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success ({duration:.2f}s)")
            print(f"Answer Preview: {data.get('answer', '')[:200]}...")
            sources = data.get('sources', [])
            print(f"Sources Cited: {len(sources)}")
            for s in sources[:3]: # Show top 3
                print(f" - {s.get('filename')} (Page/Chunk: {s.get('chunk_index', '?')})")
            return True, data
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def test_consultant(scenario):
    print(f"\n--- Testing Consultant Mode: {scenario['category']} ---")
    try:
        start = time.time()
        payload = {"situation": scenario['consultant_situation']}
        response = requests.post(f"{API_URL}/legal-consultant", json=payload, timeout=120)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success ({duration:.2f}s)")
            
            # Look for smart extraction logs in backend output (can't see here, but user can)
            # We evaluate the answer content/sources
            answer = data.get('answer', '')
            print(f"Answer Preview: {answer[:200]}...")
            sources = data.get('sources', [])
            print(f"Sources Cited: {len(sources)}")
            for s in sources[:3]:
                print(f" - {s.get('filename')} (Chunk: {s.get('chunk_index', '?')})")
            return True, data
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

if __name__ == "__main__":
    results = []
    print(f"Starting Evaluation on {API_URL}")
    for sc in scenarios:
        res_ok, res_data = test_research(sc)
        con_ok, con_data = test_consultant(sc)
        results.append({
            "category": sc["category"],
            "research": "OK" if res_ok else "FAIL",
            "consultant": "OK" if con_ok else "FAIL"
        })
        time.sleep(2) # Brief pause between requests

    print("\n\n=== Final Report ===")
    print(f"{'Category':<30} | {'Research':<10} | {'Consultant':<10}")
    print("-" * 56)
    for r in results:
        print(f"{r['category']:<30} | {r['research']:<10} | {r['consultant']:<10}")
