"""
generator.py
------------
OpenAI API vasitəsilə sorğunun optimallaşdırılması və tapılan 
kontekst əsasında yekun cavabın hazırlanması modulu.
"""

from openai import OpenAI
from config import OPENAI_API_KEY, MAIN_MODEL, OPTIMIZER_MODEL, MAX_PROMPT_CHARS
from logger import log_step

# OpenAI müştərisini başlat
client = OpenAI(api_key=OPENAI_API_KEY)

def optimize_query(original_query: str) -> str:
    """
    Axtarışın dəqiqliyini artırmaq üçün sorğunu optimallaşdırır.
    Ad və termin variasiyalarını (məs. 'Elvin' -> 'Elvin müəllim') nəzərə alır.
    """
    try:
        system_prompt = (
            "Sən axtarış sorğusu üçün sorğunu optimallaşdıran köməkçisən. "
            "İstifadəçinin sualındakı əsas adları, terminləri və açar sözləri çıxar. "
            "Əgər şəxs adı varsa, onun mümkün variasiyalarını da əlavə et (məsələn, 'Həsən' yazılıbsa 'Həsən müəllim', 'Həsən müəllimin'). "
            "Gereksiz cümlə qurma, YALNIZ boşluqla ayrılmış açar sözləri qaytar."
        )
        
        response = client.chat.completions.create(
            model=OPTIMIZER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": original_query}
            ],
            temperature=0.2
        )
        optimized = response.choices[0].message.content.strip()
        log_step("Query Optimizer", "Orijinal sorğu -> Genişləndirilmiş sorğu", f"{original_query} -> {optimized}")
        return optimized
    except Exception as e:
        log_step("Query Optimizer", "Xəta baş verdi (orijinal sorğu istifadə olunacaq)", str(e))
        return original_query
def generate_answer(query: str, search_results: list[dict], history: list = None) -> str:
    """
    Tapılmış sənəd kəsikləri və keçmiş söhbət (history) əsasında cavab verir.
    """
    
    # 1. Konteksti (Sənədlər) yoxla və yığ
    if not search_results:
        context_str = "[SİSTEM MƏLUMATI: Sənədlər bazasında bu suala uyğun heç bir lokal fayl və ya məlumat tapılmadı.]"
    else:
        context_parts = []
        for res in search_results:
            context_parts.append(f"--- Mənbə Sənəd: {res['path']} (Axtarış Uyğunluğu: {res['score']}) ---\n{res['context']}")
        context_str = "\n\n".join(context_parts)
        
        if len(context_str) > MAX_PROMPT_CHARS:
            context_str = context_str[:MAX_PROMPT_CHARS] + "\n... [Mətn çox uzun olduğu üçün kəsildi] ..."

    # 2. Keçmiş söhbəti (History) formatla
    history_str = ""
    if history:
        history_str = "Keçmiş söhbət tarixi:\n" + "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in history])
    
    # 3. Sistem Promptu
    system_prompt = (
        "Sən daxili sənədlərə və ümumi biliklərə əsaslanan ağıllı hibrid süni intellekt asistentisən.\n"
        "İstifadəçinin keçmiş mesajlarını (history) nəzərə alaraq cavab ver.\n\n"
        "SSENARİ 1 (Daxili məlumat var): Yalnız kontekstə əsaslan, birdən çox variant varsa sadala.\n"
        "SSENARİ 2 (Lokal məlumat yoxdur): Xüsusi daxili məsələdirsə, bilmədiyini bildir.\n"
        "SSENARİ 3 (Ümumi/Qlobal sual): Daxili biliklərinlə ətraflı cavab ver."
    )
    
    # 4. Yekun Prompt (History + Context + Query)
    user_prompt = f"{history_str}\n\nKontekst Məlumatları:\n{context_str}\n\nİstifadəçinin Sualı: {query}\n\nYekun Cavab:"
    
    try:
        response = client.chat.completions.create(
            model=MAIN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1 
        )
        answer = response.choices[0].message.content.strip()
        log_step("AI Generator", "Yekun Generasiya Olunmuş Cavab", answer)
        return answer
    except Exception as e:
        log_step("AI Generator", "Xəta baş verdi", str(e))
        return f"Cavab hazırlanarkən API xətası baş verdi: {str(e)}"