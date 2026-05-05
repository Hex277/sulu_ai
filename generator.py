from openai import OpenAI
from config import LLM_BASE_URL, LLM_API_KEY, GENERATOR_MODEL

def generate_final_response(query, context, history):
    client = OpenAI(
        base_url=LLM_BASE_URL, 
        api_key=LLM_API_KEY,
        timeout=300.0
    )
    
    # 1. Tarixçəni (History) siyahıdan təmiz mətnə çeviririk
    formatted_history = ""
    if history and isinstance(history, list):
        for role, content in history:
            name = "İstifadəçi" if role == "user" else "Sülü"
            formatted_history += f"{name}: {content}\n"

    # 2. Kontextin boş olub-olmadığını yoxlayırıq
    context_is_empty = not context or context.strip() == "" or len(context.strip()) < 20

    if context_is_empty:
        # --- CONTEXT YOX: istiqamətləndirici rejim ---
        system_prompt = f"""Sən 'SÜLÜ' adlı universal bir asistansan.
İstifadəçinin sualına uyğun məlumat bazasında heç bir məlumat TAPILMADI.

QAYDALAR:
1. "Məlumat tapılmadı" və ya "Sənəddə yoxdur" kimi quru ifadələr YAZMA.
2. İstifadəçinin sualındakı açar sözləri götür və daha dəqiq detal istə.
3. Qısa, mehriban və istiqamətləndirici ol.
4. TON: Professional və yardımsevər.

ƏVVƏLKİ SÖHBƏT:
{formatted_history}
"""
    else:
        # --- CONTEXT VAR: cavab ver ---
        system_prompt = f"""Sən 'SÜLÜ' adlı universal və analitik bir asistansan.
Aşağıdakı SƏNƏD MƏLUMATI içindəki verilənlərə əsasən istifadəçinin sualını cavablandır.

MÜTLƏQ QAYDALAR:
1. SƏNƏD MƏLUMATI bölməsindəki məlumat cavabın əsası olmalıdır — onu MÜTLƏQ istifadə et.
2. Tapılan məlumatı insan dilinə uyğun, səliqəli və dolğun şəkildə təqdim et.
3. Birdən çox nəticə varsa, hamısını siyahı şəklində göstər.
4. Sənədin strukturunu (JSON, cədvəl) istifadəçiyə hiss etdirmə — sanki mətn oxuyursanmış kimi cavab ver.
5. "Daha ətraflı məlumat verin" kimi yayındırıcı suallar YAZMA — məlumat artıq əlindədir, onu işlət.
6. TON: Professional, yardımsevər.

SƏNƏD MƏLUMATI (BU MƏLUMATLAR ARTIQ TAPILMIŞ VƏ DƏQİQDİR — CAVABINI BURADAN VER):
{context}

ƏVVƏLKİ SÖHBƏT:
{formatted_history}
"""

    try:
        response = client.chat.completions.create(
            model=GENERATOR_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2
        )
        
        answer = response.choices[0].message.content.strip()
        
        if not answer or len(answer) < 2:
            return "Cavab alınmadı, zəhmət olmasa yenidən cəhd edin."
            
        return answer

    except Exception as e:
        return f"Xəta baş verdi: {e}"