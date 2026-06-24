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

def generate_answer(query: str, search_results: list[dict]) -> str:
    """
    Tapılmış sənəd kəsiklərinə əsaslanaraq və ya ümumi biliklərdən istifadə edərək 
    hibrid GPT modeli ilə cavab generasiya edir.
    """
    
    # 1. Konteksti yoxla və yığ
    if not search_results:
        # Əgər BM25 heç nə tapmayıbsa, funksiyanı dayandırmırıq! 
        # AI-a açıq şəkildə bazanın boş olduğunu bildiririk.
        context_str = "[SİSTEM MƏLUMATI: Sənədlər bazasında bu suala uyğun heç bir lokal fayl və ya məlumat tapılmadı.]"
    else:
        context_parts = []
        for res in search_results:
            context_parts.append(f"--- Mənbə Sənəd: {res['path']} (Axtarış Uyğunluğu: {res['score']}) ---\n{res['context']}")
            
        context_str = "\n\n".join(context_parts)
        
        # Token/Simvol limitini yoxla və tənzimlə
        # (Qeyd: MAX_PROMPT_CHARS-in config-dən gəldiyinə əmin ol)
        if len(context_str) > MAX_PROMPT_CHARS:
            context_str = context_str[:MAX_PROMPT_CHARS] + "\n... [Mətn çox uzun olduğu üçün sistem tərəfindən kəsildi] ..."

    # 2. Hibrid AI üçün Çoxşaxəli Sistem Promptu
    system_prompt = (

        "Sən daxili sənədlərə və ümumi biliklərə əsaslanan ağıllı hibrid süni intellekt asistentisən.\n\n"

        "Aşağıdakı 3 SSENARİYƏ ciddi şəkildə əməl et:\n\n"

        

        "SSENARİ 1 - Daxili Məlumat var:\n"

        "Əgər sənə təqdim edilən 'Kontekst Məlumatları'nda real sənəd mətnləri varsa, YALNIZ o məlumatlara əsaslanaraq cavab ver. Cavabında mütləq istifadə etdiyin sənədə/mənbəyə istinad etdiyini vurğula.\n\n"

        

        "SSENARİ 2 - Daxili Məlumat yoxdur, amma sual LOKAL/XÜSUSİ xarakterlidir:\n"

        "Əgər heç bir kontekst tapılmayıbsa ([SİSTEM MƏLUMATI...]) VƏ istifadəçi spesifik daxili siyahılar, təşkilati sənədlər, şəxsi məlumatlar, daxili layihələr və ya qapalı sistemlər barədə məlumat axtarırsa:\n"

        "- Verilən məlumatlar daxilində istifadəçi sualına cavab yoxdursa sadəcə nəzakətlə bildir ki: 'Təəssüf ki, sənədlər bazasında bu suala uyğun məlumat tapılmadı.'\n\n"

        

        "SSENARİ 3 - Kontekst yoxdur, amma sual QLOBAL/ÜMUMİ xarakterlidir:\n"

        "Əgər kontekst tapılmayıbsa, AMMA istifadəçi ümumi söhbət edirsə (salamlaşma), kodlaşdırma köməyi istəyirsə, ümumi texnoloji terminləri və ya dünyəvi faktları soruşursa:\n"

        "- Öz daxili LLM biliklərinə əsaslanaraq sərbəst, ətraflı və faydalı cavab ver.\n\n"

        

        "QAYDA: Bütün cavabların rəsmi, aydın, peşəkar və tamamilə Azərbaycan dilində olmalıdır."

    )
    
    user_prompt = f"Kontekst Məlumatları:\n{context_str}\n\nİstifadəçinin Sualı: {query}\n\nYekun Cavab:"
    
    try:
        response = client.chat.completions.create(
            model=MAIN_MODEL, # config-dən gəlir
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