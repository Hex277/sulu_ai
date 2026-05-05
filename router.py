import time
from openai import OpenAI
from config import LLM_BASE_URL, LLM_API_KEY, ROUTER_MODEL

client = OpenAI(
    base_url=LLM_BASE_URL, 
    api_key=LLM_API_KEY,
    timeout=300.0
)

def route_query_to_file(user_query: str, file_list: list, chat_history: list = None, last_file: str = None) -> str:
    if not file_list:
        return None

    # Tarixçəni mətn formatına salırıq
    history_str = ""
    if chat_history:
        for role, msg_content in chat_history:
            history_str += f"{role}: {msg_content}\n"

    # FIX: last_file yalnız fayl siyahısındadırsa göstəririk,
    # əks halda AI "Yoxdur" sözünü fayl adı kimi qaytarır
    last_file_display = last_file if (last_file and last_file in file_list) else "Müəyyən edilməyib"

    system_prompt = (
        "Sən bir fayl yönləndiricisisən. İstifadəçinin sualına uyğun ən münasib faylı YALNIZ aşağıdakı siyahıdan seç.\n"
        "QAYDALAR:\n"
        "1. Cavab olaraq YALNIZ faylın TAM ADINI yaz — başqa heç nə yazma.\n"
        "2. Siyahıda olmayan, uydurma ad YAZMA.\n"
        "3. Əgər sual qısadırsa və ya kontekst lazımdırsa, ən uyğun faylı seç.\n"
        "4. Ən uyğun fayl tapılmırsa, siyahıdakı birinci faylı qaytar.\n\n"
        f"MÖVCUD FAYLLAR (YALNIZ BUNLARDAN BİRİNİ SEÇ):\n" +
        "\n".join(f"- {f}" for f in file_list) +
        f"\n\nSON SEÇİLƏN FAYL (kontekst üçün): {last_file_display}\n"
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
            
            # 1. Tam uyğunluq yoxlayırıq (case-insensitive)
            for file_name in file_list:
                if file_name.lower() == answer.lower():
                    return file_name
            
            # 2. Qismən uyğunluq yoxlayırıq (AI bəzən uzantısız yazır)
            for file_name in file_list:
                if file_name.lower() in answer.lower() or answer.lower() in file_name.lower():
                    return file_name
            
            # 3. FIX: AI siyahıdan kənar cavab verdi — güvənli fallback
            print(f"   ⚠️  Router '{answer}' qaytardı amma siyahıda yoxdur. Fallback işləyir...")
            if last_file and last_file in file_list:
                print(f"   ↳ Fallback: son seçilən fayl → '{last_file}'")
                return last_file
            else:
                print(f"   ↳ Fallback: siyahının birinci faylı → '{file_list[0]}'")
                return file_list[0]

        except Exception as e:
            print(f"⚠️ Router Cəhdi {attempt+1} uğursuz oldu: {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                return last_file if (last_file and last_file in file_list) else (file_list[0] if file_list else None)