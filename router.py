import time
from openai import OpenAI
from config import LLM_BASE_URL, LLM_API_KEY, ROUTER_MODEL

# 'from server import logs' sətri silindi - circular import xətasının qarşısını almaq üçün.

client = OpenAI(
    base_url=LLM_BASE_URL, 
    api_key=LLM_API_KEY,
    timeout=300.0
)

def route_query_to_file(user_query: str, file_list: list, chat_history: list = None, last_file: str = None):
    """
    İstifadəçi sualını uyğun fayla yönləndirir.
    Geri qaytarır: (seçilən_fayl, loqlar_siyahısı)
    """
    router_logs = [] # Loqları burada toplayırıq
    
    if not file_list:
        router_logs.append({"type": "error", "label": "Router", "msg": "Fayl siyahısı boşdur."})
        return None, router_logs

    # Tarixçəni mətn formatına salırıq
    history_str = ""
    if chat_history:
        for role, msg_content in chat_history:
            history_str += f"{role}: {msg_content}\n"

    last_file_display = last_file if (last_file and last_file in file_list) else "Müəyyən edilməyib"

    system_prompt = (
        "Sən bir fayl yönləndiricisisən. İstifadəçinin sualına uyğun ən münasib faylı YALNIZ aşağıdakı siyahıdan seç.\n"
        "QAYDALAR:\n"
        "1. Cavab olaraq YALNIZ faylın TAM ADINI yaz — başqa heç nə yazma (məsələn: 'data.xlsx').\n"
        "2. Siyahıda olmayan, uydurma ad YAZMA.\n"
        "3. Əgər sual qısadırsa və ya kontekst lazımdırsa, ən uyğun faylı seç.\n"
        "4. Ən uyğun fayl tapılmırsa, siyahıdakı birinci faylı qaytar.\n"
        "5. Əgər istifadəçi 'o', 'onun', 'həmin sənəd' kimi ifadələr işlədirsə və ya sual əvvəlki söhbətin davamidırsa, mütləq 'SON SEÇİLƏN FAYL'-ı qaytar.\n\n"
        f"MÖVCUD FAYLLAR (YALNIZ BUNLARDAN BİRİNİ SEÇ):\n" +
        "\n".join(f"- {f}" for f in file_list) +
        f"\n\n📍 KONTEKST: Hazırda müzakirə olunan fayl: {last_file_display}\n"
        f"KEÇMİŞ SÖHBƏT:\n{history_str}"
    )
    
    user_prompt = f"Sual: '{user_query}'\nSeçilən fayl (YALNIZ siyahıdakı tam adı yaz):"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=ROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            answer = response.choices[0].message.content.strip().replace('"', '').replace("'", "").strip()
            
            router_logs.append({"type": "query", "label": "Router AI", "msg": f"AI cavabı: '{answer}' (Cəhd {attempt+1})"})

            # 1. Tam uyğunluq yoxlayırıq
            for file_name in file_list:
                if file_name.lower() == answer.lower():
                    router_logs.append({"type": "success", "label": "Router", "msg": f"Dəqiq uyğunluq tapıldı: {file_name}"})
                    return file_name, router_logs
            
            # 2. Qismən uyğunluq yoxlayırıq
            for file_name in file_list:
                if file_name.lower() in answer.lower() or answer.lower() in file_name.lower():
                    router_logs.append({"type": "info", "label": "Router", "msg": f"Qismən uyğunluq tapıldı: {file_name}"})
                    return file_name, router_logs
            
            # 3. Fallback rejimi
            router_logs.append({"type": "warning", "label": "Router", "msg": f"'{answer}' siyahıda yoxdur, fallback işləyir..."})
            
            if last_file and last_file in file_list:
                return last_file, router_logs
            else:
                return file_list[0], router_logs

        except Exception as e:
            error_msg = f"Cəhd {attempt+1} uğursuz: {str(e)}"
            router_logs.append({"type": "error", "label": "Router Xətası", "msg": error_msg})
            if attempt < 2:
                time.sleep(1)
            else:
                fallback = last_file if (last_file and last_file in file_list) else (file_list[0] if file_list else None)
                return fallback, router_logs