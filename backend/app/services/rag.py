
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
            model_id = getattr(settings, 'GROQ_MODEL', "llama-3.3-70b-versatile")
            data = {
                "messages": [{"role": "user", "content": prompt}],
                "model": model_id,
                "temperature": 0.3
            }
            
            # Simple retry logic for Groq too
            for attempt in range(3):
                try:
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=30)
                    if resp.status_code == 200:
                        content = resp.json()['choices'][0]['message']['content']
                        return GenerationResponse(text=content)
                    elif resp.status_code == 429:
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Groq Error {resp.status_code}: {resp.text}")
                except Exception as e:
                    print(f"Groq Exception: {e}")
            
            print("Groq failed, falling back to Gemini...")
        except Exception as e:
             print(f"Groq Setup Error: {e}, falling back...")

    # Fallback to Gemini (Or Primary if Groq not set)
    for attempt in range(retries):
        try:
            result = model.generate_content(prompt)
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
        self.model = genai.GenerativeModel(settings.GEMINI_CHAT_MODEL)

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
        
        # Combine
        for r, d in enumerate(v_docs):
            scores[d] = scores.get(d, 0) + (0.3 / (k + r + 1))
            if r < len(v_metas): meta_map[d] = v_metas[r]
            
        for r, (d, s, m) in enumerate(bm25_results):
            scores[d] = scores.get(d, 0) + (0.7 / (k + r + 1))
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

        # Prompt
        prompt = f"""أنت باحث قانوني أكاديمي. المرجعية: القانون الجزائري.
تعليمات:
1. أجب بدقة مع الاستشهاد بالمصادر.
2. التنسيق: فقرات واضحة، اقتباس المادة "نص المادة" [رقم المصدر].
3. أضف قائمة المراجع في النهاية.

السؤال: {query}
المصادر: {context}"""

        try:
            response = generate_with_retry(self.model, prompt)
            answer = response.text.replace('"]', '"]\n') # Hack for ref formatting
        except Exception as e:
            print(f"Generation failed after retries: {e}")
            answer = "عذراً، النظام مشغول جداً حالياً (ضغط على الموديل). هذه هي المصادر التي وجدتها، لكن لم أتمكن من صياغة الإجابة النهائية. يرجى المحاولة بعد قليل."
        
        return {"query": query, "answer": answer, "sources": [{"filename": m.get('filename'), "chunk_index": i+1} for i, m in enumerate(final_metas)]}

    def consult(self, situation: str):
        # Expert Lawyer Mode
        # Search for relevant laws (Civil, Penal, Labor depending on keywords)
        docs, metas = self._retrieve(situation, top_k=30)
        
        # Rerank carefully
        reranked = rerank_with_gemini(situation, docs, top_k=7)
        final_docs = [r[0] for r in reranked]
        final_metas = []
        doc_map = {d: m for d, m in zip(docs, metas)} # Optimization
        for d in final_docs: final_metas.append(doc_map.get(d, {}))
        
        context = "\n".join([f"Source {i+1}: {d}" for i, d in enumerate(final_docs)])
        
        prompt = f"""بصفتك محامياً خبيراً في القانون الجزائري، قم بتحليل الوضع التالي وتقديم استشارة قانونية رصينة.

الوضع:
{situation}

المصادر القانونية المتاحة (استخدم ما ينطبق فقط):
{context}

المطلوب (هيكلة الرد):
1. **التحليل القانوني للوقائع**: كيف يكيف القانون هذه الوقائع؟ (تكييف قانوني).
2. **الأسانيد القانونية**: اذكر المواد القانونية التي تنطبق بدقة (مع نصها إن وجد).
3. **التوجيه والاستشارة**: ماذا يجب على العميل أن يفعل؟ (خطوات عملية: شكوى، دعوى، إنذار...).

الأسلوب: خاطب العميل بمهنية، كن مباشراً، واستخدم المصطلحات القانونية الجزائرية الصحيحة."""

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
        وضع المحامي: توليد مذكرات قانونية احترافية
        Advocate Mode: Generate professional legal pleadings
        """
        facts = case_data.get('facts', '')
        charges = " ".join(case_data.get('charges', []))
        defendant_name = case_data.get('defendant_name', 'المتهم')
        court = case_data.get('court', 'المحكمة المختصة')
        case_number = case_data.get('case_number', '')
        
        # Construct search query
        query = f"{pleading_type} {facts} {charges}"
        
        docs, metas = self._retrieve(query, top_k=top_k)
        
        # Build legal context
        context = "\n\n".join([
            f"【النص القانوني {i+1}】\nالمصدر: {metas[i].get('filename', 'غير محدد')}\n{d[:800]}" 
            for i, d in enumerate(docs[:8])
        ])
        
        # Professional prompts by type
        type_instructions = {
            "دفاع": """اكتب **مذكرة دفاع** (Mémoire de Défense) متكاملة تتضمن:
- **الدفوع الشكلية**: البطلان، عدم الاختصاص، سقوط الدعوى...
- **الدفوع الموضوعية**: انتفاء الركن المادي/المعنوي، الإباحة، موانع المسؤولية...
- **الظروف المخففة**: حسن السيرة، الاستفزاز، الحالة الاجتماعية...""",
            
            "استئناف": """اكتب **عريضة استئناف** (Requête d'Appel) تتضمن:
- **أسباب الاستئناف**: مخالفة القانون، الخطأ في تطبيقه، القصور في التسبيب...
- **الطلبات**: إلغاء الحكم المستأنف، التخفيف، البراءة...""",
            
            "نقض": """اكتب **طعن بالنقض** (Pourvoi en Cassation) يتضمن:
- **أوجه الطعن**: مخالفة القانون، انعدام الأساس القانوني، التناقض في الأسباب...
- **السوابق القضائية**: قرارات المحكمة العليا ذات الصلة..."""
        }
        
        instruction = type_instructions.get(pleading_type, type_instructions["دفاع"])
        
        prompt = f"""أنت محامٍ خبير أمام المحاكم الجزائرية، متخصص في الترافع والدفاع الجنائي.
مهمتك: كتابة {pleading_type} احترافية ومقنعة.

═══════════════════════════════════════
📋 بيانات القضية
═══════════════════════════════════════
• رقم القضية: {case_number}
• المحكمة: {court}
• المتهم: {defendant_name}
• التهمة: {charges if charges else 'غير محددة'}

📝 الوقائع:
{facts}

═══════════════════════════════════════
📚 النصوص القانونية المتاحة
═══════════════════════════════════════
{context}

═══════════════════════════════════════
✍️ المطلوب
═══════════════════════════════════════
{instruction}

📌 الهيكل الإلزامي للمذكرة:

**بسم الله الرحمن الرحيم**

**إلى السيد/ة رئيس {court}**

**مذكرة {pleading_type}**
**في القضية رقم: {case_number}**

**أولاً: الوقائع** (ملخص موجز ومركز)

**ثانياً: المناقشة القانونية**
أ) في الشكل: (الدفوع الشكلية إن وجدت)
ب) في الموضوع: (التحليل القانوني مع الاستشهاد بالمواد)

**ثالثاً: الطلبات**
لهذه الأسباب، يلتمس الدفاع من عدالة المحكمة الموقرة...

---
الأسلوب: {style} (رسمي/مقنع/مختصر)
اللغة: العربية القانونية الفصيحة مع المصطلحات القانونية الجزائرية الصحيحة."""

        try:
            response = generate_with_retry(self.model, prompt)
            pleading_text = response.text
        except Exception as e:
            print(f"Pleading generation failed: {e}")
            pleading_text = f"""# مذكرة {pleading_type}

⚠️ عذراً، لم أتمكن من إتمام صياغة المذكرة بسبب ضغط النظام.

## المعلومات المتاحة:
- **المتهم**: {defendant_name}
- **التهمة**: {charges}
- **الوقائع**: {facts[:200]}...

## المصادر القانونية المستخرجة:
يمكنك الاستعانة بالنصوص القانونية أدناه لصياغة مذكرتك يدوياً."""

        return {
            "pleading": pleading_text,
            "metadata": {"total_sources": len(docs), "pleading_type": pleading_type},
            "sources": [{"filename": m.get('filename')} for m in metas[:5]]
        }

    def search_jurisprudence(self, legal_issue: str, chamber=None, top_k=20):
        # Jurisprudence Mode
        filters = {"category": "jurisprudence"} if chamber else None # Narrow down if we had chamber metadata
        docs, metas = self._retrieve(legal_issue, filters=filters, top_k=top_k)
        
        context = "\n".join([f"Arrêt {i+1}: {d}" for i, d in enumerate(docs[:7])])
        
        prompt = f"""بصفتك باحثاً في الاجتهاد القضائي (المحكمة العليا).
المسألة: {legal_issue}
القرارات المستخرجة:
{context}

المطلوب:
حلل اتجاه المحكمة العليا في هذه المسألة.
هل الاستقر متواتر أم متناقض؟
استخرج المبدأ القانوني المكرس."""

        response = generate_with_retry(self.model, prompt)
        return {
            "analysis": response.text,
            "metadata": {"total_sources": len(docs)},
            "sources": [{"filename": m.get('filename'), "relevance_score": 0.9} for m in metas[:5]]
        }

rag_service = RAGService()

def rag_pipeline(query, filters=None, skip_generation=False):
    return rag_service.answer_query(query, filters, skip_generation)
