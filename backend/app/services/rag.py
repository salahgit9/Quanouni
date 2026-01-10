
import google.generativeai as genai
from app.core.config import settings
from app.services.embedding import get_embedding
from app.services.vector_store import query_chroma
import re
import time
import requests
import json
from google.api_core import exceptions
from dataclasses import dataclass
from typing import Optional

_gemini_configured = False

@dataclass
class GenerationResponse:
    text: str


def generate_with_retry(model, prompt, retries=5, delay=4):
    # Check if Groq is enabled (Preferred for Generation)
    if hasattr(settings, 'GROQ_API_KEY') and settings.GROQ_API_KEY:
        try:
            # Groq API Call
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            # Fallback to stable model if the configured one fails
            model_id = getattr(settings, 'GROQ_MODEL', None) or "llama-3.1-70b-versatile"
            print(f"[Groq] Using model: {model_id}")
            data = {
                "messages": [{"role": "user", "content": prompt}],
                "model": model_id,
                "temperature": 0.3,
                "max_tokens": 4096
            }
            
            # Simple retry logic for Groq too
            for attempt in range(3):
                try:
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=120)
                    if resp.status_code == 200:
                        content = resp.json()['choices'][0]['message']['content']
                        return GenerationResponse(text=content)
                    elif resp.status_code == 429:
                        print(f"Groq Rate Limit, waiting {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Groq Error {resp.status_code}: {resp.text[:500]}")
                except requests.exceptions.Timeout:
                    print(f"Groq Timeout (attempt {attempt+1}/3)")
                    continue
                except Exception as e:
                    print(f"Groq Exception: {type(e).__name__}: {e}")
            
            print("Groq failed, falling back to Gemini...")
        except Exception as e:
             print(f"Groq Setup Error: {e}, falling back...")

    # Fallback to Gemini (Or Primary if Groq not set)
    for attempt in range(retries):
        try:
            # Explicitly set max output tokens for long pleadings
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.7
            )
            result = model.generate_content(prompt, generation_config=generation_config)
            return GenerationResponse(text=result.text)
        except exceptions.ResourceExhausted as e:
            if attempt < retries - 1:
                print(f"Gemini Quota exceeded, waiting {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e
        except Exception as e:
            raise e

def configure_gemini():
    global _gemini_configured
    if not _gemini_configured:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True

def detect_language(text: str) -> str:
    """Detect the language of the query"""
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    total_chars = len([c for c in text if c.isalpha()])
    
    if total_chars == 0:
        return "ar"
    
    arabic_ratio = arabic_chars / total_chars
    
    if arabic_ratio > 0.3:
        return "ar"
    
    french_words = ['le', 'la', 'les', 'de', 'et', 'dans', 'pour', 'sont', 'peut', 'comment', 'quels', 'quel']
    text_lower = text.lower()
    if any(word in text_lower.split() for word in french_words):
        return "fr"
    
    return "en"

def rerank_with_gemini(query: str, chunks: list[str], top_k: int = 3) -> list[tuple[str, float]]:
    configure_gemini()
    model = genai.GenerativeModel(settings.GEMINI_CHAT_MODEL)
    
    chunks_text = ""
    for i, chunk in enumerate(chunks[:10], 1):
        chunks_text += f"\n\n### Chunk {i}:\n{chunk[:500]}...\n"
    
    prompt = f"""قيّم مدى صلة كل chunk بالسؤال التالي. أعط درجة من 0 إلى 10 لكل chunk.
السؤال: {query}
Chunks: {chunks_text}
التعليمات:
- 10: إجابة مباشرة
- 5-9: صلة جزئية
- 0-4: غير ذي صلة
الإجابة JSON فقط: {{"1": 8, ...}}"""
    
    try:
        response = generate_with_retry(model, prompt)
        import json
        json_match = re.search(r'\{[^}]+\}', response.text)
        if json_match:
            scores = json.loads(json_match.group())
            ranked = []
            for i, chunk in enumerate(chunks[:10], 1):
                score = float(scores.get(str(i), 0)) / 10.0
                ranked.append((chunk, score))
            for chunk in chunks[10:]:
                ranked.append((chunk, 0.1))
            ranked.sort(key=lambda x: x[1], reverse=True)
            return ranked[:top_k]
        return [(chunk, 0.5) for chunk in chunks[:top_k]]
    except Exception as e:
        # Avoid printing full exception if it contains Arabic
        return [(chunk, 0.5) for chunk in chunks[:top_k]]

class RAGService:
    def __init__(self):
        configure_gemini()
        # Fix model name: ensure we use a valid model ID
        model_name = settings.GEMINI_CHAT_MODEL or "gemini-2.0-flash"
        # validation: remove models/ prefix if present to be safe, or just use as is. 
        # Actually newer SDKs prefer no prefix for some endpoints.
        self.model = genai.GenerativeModel(model_name)

    def _retrieve(self, query, filters=None, top_k=20):
        # 1. Vector Search
        try:
            query_embedding = get_embedding(query, is_query=True)
            vector_results = query_chroma(query_embedding, n_results=top_k, where=filters)
            v_docs = vector_results['documents'][0] if vector_results and 'documents' in vector_results else []
            v_metas = vector_results['metadatas'][0] if vector_results and 'metadatas' in vector_results else []
        except Exception as e:
            print(f"Vector search failed")
            v_docs, v_metas = [], []

        # 2. BM25 Search
        from app.services.bm25_service import bm25_service
        bm25_results = bm25_service.search(query, top_k=top_k, filters=filters)

        # 3. RRF Fusion
        k = 60
        scores = {}
        meta_map = {}
        
        # Combine (balanced weights for semantic + keyword search)
        for r, d in enumerate(v_docs):
            scores[d] = scores.get(d, 0) + (0.5 / (k + r + 1))  # Vector: 50%
            if r < len(v_metas): meta_map[d] = v_metas[r]
            
        for r, (d, s, m) in enumerate(bm25_results):
            scores[d] = scores.get(d, 0) + (0.5 / (k + r + 1))  # BM25: 50%
            meta_map[d] = m

        ranked_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        final_docs = [d for d, s in ranked_docs[:15]]
        final_metas = [meta_map.get(d, {}) for d in final_docs]
        
        return final_docs, final_metas

    def answer_query(self, query: str, filters: dict = None, skip_generation: bool = False):
        # Standard Research Mode
        docs, metas = self._retrieve(query, filters)
        
        # Rerank
        if not skip_generation:
            reranked = rerank_with_gemini(query, docs, top_k=5)
            # Re-map metadata
            final_docs = [r[0] for r in reranked]
            final_metas = []
            for d in final_docs:
                # Find meta again (inefficient but safe)
                try: 
                    idx = docs.index(d)
                    final_metas.append(metas[idx])
                except: final_metas.append({})
        else:
            final_docs, final_metas = docs[:5], metas[:5]

        # Context formatting
        context = ""
        for i, (doc, meta) in enumerate(zip(final_docs, final_metas), 1):
            title = meta.get('filename', f'Source {i}').replace('.txt', '')
            context += f"\n\n### [مصدر {i}: {title}]\n{doc}\n"

        if skip_generation:
            return {"answer": "Retrieval Only", "context": final_docs, "metadatas": final_metas}

        # Prompt - Professional Legal Research (v2.0)
        prompt = f"""أنت **باحث قانوني متخصص في القانون الجزائري**، تعمل في مكتبة قانونية أكاديمية.
مرجعيتك الحصرية هي النصوص القانونية المقدمة أدناه فقط.

## مهمتك
تحليل السؤال القانوني وتقديم إجابة دقيقة ومبررة بالنصوص.

## قواعد الإجابة الإلزامية:
1. **لا تختلق معلومات**: إذا لم تجد الإجابة في النصوص المقدمة، قل ذلك صراحة: "لم أجد نصاً صريحاً يجيب على هذا السؤال في المصادر المتاحة."
2. **الاقتباس الدقيق**: عند الاستشهاد بمادة قانونية، اقتبس نصها الحرفي بين علامات تنصيص « ».
3. **الإشارة للمصادر**: استخدم أرقام المصادر [1], [2], [3] بعد كل اقتباس أو معلومة.
4. **التنسيق الإلزامي**:
   - ابدأ بـ **## ملخص الإجابة** (3 أسطر كحد أقصى)
   - ثم **## التحليل القانوني** مع شرح مفصل وأرقام المصادر
   - اختم بـ **## المراجع** (قائمة مرقمة: اسم القانون + رقم المادة إن وجد)
5. **اللغة**: العربية الفصحى القانونية الرسمية. لا تستخدم العامية أبداً.
6. **الموضوعية**: لا تُبدِ رأياً شخصياً. التزم بما جاء في النصوص.

## النصوص القانونية المتاحة:
{context}

## السؤال:
{query}

## الإجابة:"""

        try:
            response = generate_with_retry(self.model, prompt)
            answer = response.text.replace('"]', '"]\n') # Hack for ref formatting
        except Exception as e:
            print(f"Generation failed after retries: {e}")
            answer = "عذراً، النظام مشغول جداً حالياً (ضغط على الموديل). هذه هي المصادر التي وجدتها، لكن لم أتمكن من صياغة الإجابة النهائية. يرجى المحاولة بعد قليل."
        
        return {"query": query, "answer": answer, "sources": [{"filename": m.get('filename'), "chunk_index": i+1} for i, m in enumerate(final_metas)]}

    def _extract_search_query(self, situation: str) -> str:
        """استخراج ذكي للكلمات المفتاحية باستخدام LLM لتحسين دقة البحث"""
        try:
            prompt = f"""أنت خبير قانوني ذكي. مهمتك هي تحليل موقف قانوني واستخراج أفضل كلمات البحث للعثور على القوانين والمراجع المناسبة.
            
الموقف:
{situation[:2000]}

استخرج ما يلي في سطر واحد فقط:
1. نوع القضية (مثلاً: ميراث، عمل، جنائي، أحوال شخصية)
2. 5 إلى 10 كلمات مفتاحية دقيقة للبحث في النصوص القانونية (مثلاً: استخدم "تسريح تعسفي" بدلاً من "طرد"، "قسمة تركة" بدلاً من "تقسيم الإرث")

تنسيق الإجابة المطلوب:
[نوع القضية] كلمات مفتاحية

أجب فقط بالسطر المطلوب بدون أي مقدمات أو شرح."""

            # استخدام الموديل لاستخراج الكلمات المفتاحية
            # نستخدم نفس دالة التوليد الموثوقة لدينا
            response = generate_with_retry(self.model, prompt)
            
            if response and hasattr(response, 'text'):
                extracted_text = response.text.strip()
                print(f"[Smart Extract] LLM Output: {extracted_text}")
                
                # دمج وصف الموقف (أول 50 كلمة للسياق) مع الكلمات المستخرجة ذكياً
                # هذا يضمن وجود السياق الأصلي + المصطلحات القانونية الدقيقة
                words = situation.split()[:50]
                combined_query = " ".join(words) + " " + extracted_text
                return combined_query
            
            print("[Smart Extract] Empty response, falling back.")
            return " ".join(situation.split()[:80])

        except Exception as e:
            print(f"[Smart Extract] Error: {e}")
            # Fallback to simple truncation
            return " ".join(situation.split()[:80])

    def consult(self, situation: str):
        """وضع المستشار القانوني - استشارة قانونية احترافية"""
        # استخراج استعلام بحث مركز من الموقف
        search_query = self._extract_search_query(situation)
        
        # Search for relevant laws AND jurisprudence using focused query
        docs, metas = self._retrieve(search_query, top_k=20)
        
        # Rerank using original situation for context relevance
        reranked = rerank_with_gemini(situation, docs, top_k=5)
        final_docs = [r[0] for r in reranked]
        final_metas = []
        doc_map = {d: m for d, m in zip(docs, metas)}
        for d in final_docs: final_metas.append(doc_map.get(d, {}))
        
        # Format context with source type indication (full text like Legal Search)
        context = ""
        for i, (doc, meta) in enumerate(zip(final_docs, final_metas), 1):
            source_name = meta.get('filename', f'مصدر {i}').replace('.txt', '')
            source_type = "اجتهاد قضائي" if "قرار" in source_name or "اجتهاد" in source_name else "نص قانوني"
            context += f"\n\n### [{source_type} - مصدر {i}: {source_name}]\n{doc}\n"
        
        # Professional Legal Consultant Prompt (v2.0)
        prompt = f"""أنت **محامٍ أول معتمد لدى المحكمة العليا الجزائرية** بخبرة 20 سنة في الترافع والاستشارات.
تقدم استشارات قانونية دقيقة ومهنية للموكلين، مستنداً إلى النصوص القانونية واجتهادات المحكمة العليا.

## الموقف القانوني المعروض:
{situation}

## المصادر القانونية المتاحة:
(تشمل نصوص القوانين، اجتهادات المحكمة العليا، وقرارات مجلس الدولة)
{context}

---

## هيكلة الاستشارة (التزم بهذا الترتيب):

### 1. التكييف القانوني ⚖️
- ما هو نوع القضية؟ (مدني / جزائي / إداري / أسرة / عمل / تجاري)
- ما هي الوقائع القانونية المؤثرة؟
- من هم الأطراف وما صفاتهم القانونية؟

### 2. الأساس القانوني 📚
- **النصوص القانونية**: اذكر المواد المنطبقة مع نصها بين « » [رقم المصدر]
- **الاجتهاد القضائي**: إن وجد قرار من المحكمة العليا يدعم الموقف، اذكره

### 3. التوجيه العملي 🎯
- ما الإجراء الواجب؟ (شكوى / دعوى / صلح / تظلم / استئناف)
- أمام أي جهة؟ (محكمة ابتدائية / مجلس قضائي / محكمة عليا / إدارة)
- ما الوثائق والأدلة اللازمة؟

### 4. التحذيرات القانونية ⚠️
- آجال التقادم أو السقوط (إن وجدت)
- المخاطر المحتملة إن لم يُتخذ إجراء سريع
- نقاط ضعف الموقف القانوني (إن وجدت)

### 5. الخلاصة والتوصية 📌
- ملخص الموقف في 3 أسطر كحد أقصى
- التوصية النهائية الواضحة

---
⚠️ **تنويه**: هذه استشارة قانونية أولية مبنية على المعلومات المقدمة. يُنصح بمراجعة محامٍ متخصص لدراسة ملف القضية كاملاً."""

        try:
            response = generate_with_retry(self.model, prompt)
            consultation_text = response.text
        except Exception as e:
            print(f"Consultation generation failed: {e}")
            consultation_text = "عذراً، لم أتمكن من صياغة الاستشارة النهائية بسبب ضغط النظام. يرجى مراجعة المصادر أدناه."

        return {
            "consultation": consultation_text,
            "sources": [{"filename": m.get('filename')} for m in final_metas]
        }

    def draft_pleading(self, case_data: dict, pleading_type="دفاع", style="formel", top_k=30):
        """
        وضع المحامي: توليد مذكرات قانونية احترافية باستخدام هيكلية المرافعات الذهبية
        Advocate Mode: Generate professional legal pleadings
        """
        facts = case_data.get('facts', '')
        charges = " ".join(case_data.get('charges', []))
        defendant_name = case_data.get('defendant_name', 'المتهم')
        court = case_data.get('court', 'المحكمة المختصة')
        case_number = case_data.get('case_number', '')
        
        # 1. Smart Extraction from Case Data
        # Combine facts and charges for context extraction
        case_context = f"التهمة: {charges}. الوقائع: {facts}"
        search_query = self._extract_search_query(case_context)
        print(f"[Pleading] Smart Query: {search_query}")

        # 2. Retrieval
        docs, metas = self._retrieve(search_query, top_k=top_k)
        
        # 3. Reranking using Gemini
        # Select best 5 sources relevant to the case facts
        reranked = rerank_with_gemini(case_context, docs, top_k=5)
        final_docs = [r[0] for r in reranked]
        final_metas = []
        
        # Match metadata back to reranked docs
        doc_map = {d: m for d, m in zip(docs, metas)}
        for d in final_docs: final_metas.append(doc_map.get(d, {}))
        
        # 4. Build Legal Context (Full Text - No Truncation)
        context = ""
        for i, (doc, meta) in enumerate(zip(final_docs, final_metas), 1):
            source_name = meta.get('filename', f'مصدر {i}').replace('.txt', '')
            source_type = "اجتهاد قضائي" if "قرار" in source_name or "اجتهاد" in source_name else "نص قانوني"
            context += f"\n\n### [{source_type} - مصدر {i}: {source_name}]\n{doc}\n"
    
        # 5. Professional "Golden Pleading" Prompt
        prompt = f"""أنت محامٍ جزائري خبير "نابغ" (Top-Tier Lawyer) أمام المحكمة العليا ومجلس الدولة.
مهمتك: صياغة **{pleading_type}** احترافية جداً تحاكي "المرافعات الذهبية" من حيث البلاغة، الحجة الدامغة، والهيكلة الصارمة.

═══════════════════════════════════════
📋 ملف القضية
═══════════════════════════════════════
• الجهة القضائية: {court}
• رقم الملف: {case_number}
• الأطراف: المتهم {defendant_name} ضد النيابة العامة/الضحية
• التهمة: {charges if charges else 'غير محددة'}

📝 وقائع القضية (كما وردت في الملف):
{facts}

═══════════════════════════════════════
📚 الذخيرة القانونية (السند)
═══════════════════════════════════════
استخدم هذه النصوص بذكاء لتدعيم دفوعك (يجب ذكر رقم المادة واسم القانون بدقة). لا تذكر نصوصاً لم ترد هنا إلا إذا كنت متأكداً منها 100%:
{context}

═══════════════════════════════════════
⚖️ الهيكلة الذهبية المطلوبة (إلزامية)
═══════════════════════════════════════
يجب أن تتبع مذكرتك الهيكل التالي بدقة:

1. **الديباجة الاحترافية**: (إلى السيد رئيس المحكمة... لفائدة المتهم... ضد...)
2. **أولاً: موجز الوقائع**: (صياغة قانونية محايدة ومركزة للوقائع).
3. **ثانياً: الإجراءات**: (ذكر الإجراءات المتخذة باختصار).
4. **ثالثاً: المناقشة القانونية (قلب المرافعة)**:
   أ- **في الشكل (الدفوع الشكلية)**: (تحقق من: بطلان الإجراءات، التقادم، الاختصاص - إن وجدت ثغرات).
   ب- **في الموضوع (الدفوع الموضوعية)**:
      - مناقشة أركان التهمة (المادي والمعنوي) وتفنيدها.
      - تحليل أدلة الإثبات وكشف التناقضات.
      - استثمار النصوص القانونية {context} لصالح الموكل.
      - الاستشهاد بالاجتهاد القضائي (إن وجد في المصادر).
5. **رابعاً: الطلبات الختامية**: (أصلياً: البراءة/الإلغاء، احتياطياً: التخفيف/إعادة التكييف).

═══════════════════════════════════════
💡 توجيهات الأسلوب ("اللمسة الذهبية")
═══════════════════════════════════════
- استخدم لغة قانونية جزيلة ورصينة (مثال: "حيث أن الثابت..."، "ولما كان من المقرر...").
- كن هجومياً في الحق، مفنداً لأدلة الخصم بالحجة والبرهان.
- اربط النص القانوني بالواقعة مباشرة ("حيث أن المادة X تشترط... وحيث أن موكلي لم يقم بـ...").
- التزم بأسلوب {style}.

ابدأ صياغة المرافعة فوراً:"""

        try:
            response = generate_with_retry(self.model, prompt)
            pleading_text = response.text
        except Exception as e:
            print(f"Pleading generation failed: {e}")
            pleading_text = f"""# مذكرة {pleading_type}

⚠️ عذراً، لم أتمكن من إتمام صياغة المذكرة بسبب خطأ تقني.

## المعلومات المتاحة:
- **المتهم**: {defendant_name}
- **التهمة**: {charges}
- **الوقائع**: {facts[:200]}...

## المصادر القانونية المستخرجة:
{context}

يرجى إعادة المحاولة."""

        return {
            "pleading": pleading_text,
            "metadata": {"total_sources": len(docs), "pleading_type": pleading_type},
            "sources": [{"filename": m.get('filename')} for m in final_metas[:10]]
        }


    def search_jurisprudence(self, legal_issue: str, chamber=None, top_k=20):
        # Jurisprudence Mode - Filter by both Supreme Court and Conseil d'État
        # Note: RPC match_documents does not support list filters, so we fetch all and filter in Python
        # filters = {"category": ["jurisprudence", "jurisprudence_conseil_etat"]}
        
        # If chamber is specified, append it to query
        search_query = legal_issue
        if chamber:
             search_query += f" ({chamber})"
             
        # Fetch broad (50) then filter
        raw_docs, raw_metas = self._retrieve(search_query, filters=None, top_k=50)
        
        docs = []
        metas = []
        target_categories = ["jurisprudence", "jurisprudence_conseil_etat"]
        
        for d, m in zip(raw_docs, raw_metas):
            if m.get("category") in target_categories:
                docs.append(d)
                metas.append(m)
        
        # Slice to requested top_k
        docs = docs[:top_k]
        metas = metas[:top_k]
        
        # Limit context to avoid token limit (Groq max ~12K tokens)
        truncated_docs = [d[:1200] for d in docs[:5]]  # 5 docs, 1200 chars each
        context = "\n".join([f"Arrêt {i+1}: {d}" for i, d in enumerate(truncated_docs)])
        
        prompt = f"""بصفتك باحثاً في الاجتهاد القضائي (المحكمة العليا ومجلس الدولة).
المسألة: {legal_issue}
القرارات المستخرجة:
{context}

المطلوب:
1. استخرج المبادئ القانونية بدقة.
2. لكل مبدأ، **يجب** إدراج "نص المبدأ" كما ورد في القرار بين علامتي اقتباس.
3. اذكر رقم القرار وتاريخه والجهة المصدرة (المحكمة العليا أو مجلس الدولة) إن وجد في النص.
4. وضح هل الاجتهاد مستقر أم هناك تناقض.

التنسيق المطلوب:
- **المبدأ:** [شرح المبدأ]
- **النص المقتبس:** "...[النص]..."
- **المرجع:** قرار رقم [X] بتاريخ [Y] - [الجهة] (إن وجد)"""

        response = generate_with_retry(self.model, prompt)
        
        # Include text snippets in sources for UI
        enriched_sources = []
        for doc, meta in zip(docs[:5], metas[:5]):
             enriched_sources.append({
                 "filename": meta.get('filename'),
                 "relevance_score": 0.9,
                 "snippet": doc[:200] + "..." # Snippet for UI
             })

        return {
            "analysis": response.text,
            "metadata": {"total_sources": len(docs)},
            "sources": enriched_sources
        }

rag_service = RAGService()

def rag_pipeline(query, filters=None, skip_generation=False):
    return rag_service.answer_query(query, filters, skip_generation)
