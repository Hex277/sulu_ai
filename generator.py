import datetime
from openai import OpenAI
from config import OPENAI_API_KEY, MAIN_MODEL, OPTIMIZER_MODEL, get_db_connection
from logger import log_step

client = OpenAI(api_key=OPENAI_API_KEY)

def get_all_indexed_filenames() -> list[str]:
    """Bazadakı aktiv indekslənmiş faylların unikal (əsl) siyahısını qaytarır."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # filename əvəzinə filepath çəkirik, çünki filepath formatımız belədir: "fayl.xlsx#row_3"
        cursor.execute("SELECT filepath FROM documents")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        real_files = set()
        for r in rows:
            filepath = r['filepath']
            # '#' simvolundan əvvəlki hissəni alırıq (yəni əsl faylın adını)
            base_filepath = filepath.split('#')[0]
            # Əgər qovluq yolu varsa, yalnız faylın adını saxlayırıq (məs: fayl.xlsx)
            real_file_name = base_filepath.split('/')[-1].split('\\')[-1]
            real_files.add(real_file_name)
            
        return list(real_files)
    except Exception as e:
        print(f"DEBUG: get_all_filenames xətası: {e}")
        return []
def optimize_query(original_query: str) -> str:
    try:
        system_prompt = (
            "Sən istifadəçi sorğusunun niyyətini (intent) analiz edən axtarış köməkçisisən.\n"
            "QƏTİ QAYDALAR:\n"
            "1. Əgər istifadəçi sadəcə salamlaşır, hal-əhval tutur, təşəkkür edir və ya daxili sənədlərə ehtiyac duymayan ümumi söhbət edirsə, YALNIZ 'NO_DATA' cavabını qaytar.\n"
            "2. Əgər istifadəçi müəllimlər, vaqonlar, sənədlər və ya hər hansı məlumat bazası ilə bağlı siyahı istəyirsə, bu niyyəti aşkar et və əlaqədar açar sözləri çıxar.\n"
            "3. Digər bütün hallarda (şəxs adı, vəzifə, sənəd məzmunu) sorğudakı açar sözləri çıxar və boşluqla ayıraraq qaytar.\n"
            "4. Heç bir əlavə şərh, cümlə və ya izah vermə. Cavabın YALNIZ 'NO_DATA' və ya təmiz 'açar sözlər' siyahısı olmalıdır."
        )
        response = client.chat.completions.create(
            model=OPTIMIZER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": original_query}
            ],
            temperature=0.0 # Sabit və dəqiq qərar verməsi üçün 0.0 edirik
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"DEBUG: optimize_query xətası: {e}")
        return original_query
def truncate_text(text, max_chars=4000):
    """Mətni kəsmək üçün köməkçi funksiya"""
    if len(text) > max_chars:
        return text[:max_chars] + "\n... [Mətn çox uzun olduğu üçün kəsildi] ..."
    return text
def generate_answer(query: str, search_results: list[dict], history: list[dict]):
    # 1. Sistemdəki bütün faylların siyahısını dinamik əldə edirik
    available_files = get_all_indexed_filenames()
    files_list_str = ", ".join(available_files) if available_files else "Heç bir sənəd tapılmadı."
    
    # 2. Kontekst məlumatlarını hazırlayırıq
    if search_results:
        context_parts = []
        for r in search_results:
            truncated_context = truncate_text(r['context'], max_chars=2000)
            context_parts.append(f"--- MƏNBƏ FAYL: {r['filename']} (Relevanlıq: {r['score']}) ---\n{r['context']} ---\n{truncated_context}")
        context_str = "\n\n".join(context_parts)
    else:
        context_str = "Sual ilə bağlı daxili sənədlərdən heç bir uyğun kontekst tapılmadı."
    
    # 3. Sistem Promptu (AI-ın görməsi və düşünməsi üçün fayl siyahısı daxil edilib)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_prompt = (
        f"Sən 'Sülü AI' adlı ağıllı hibrid asistansan.\n"
        f"Cari tarix: {current_time}\n"
        f"Sistemdəki aktiv fayllar: [{files_list_str}]\n\n"
        "TƏLİMATLAR:\n"
        "1. İntent Analizi: İstifadəçinin sorğusunun məqsədini (gündəlik söhbət, konkret məlumat axtarışı və ya bütöv sənəd tələbi) müəyyən et və davranışını buna uyğun tənzimlə.\n"
        "2. Təbii Ünsiyyət: Gündəlik və sadə söhbətlər zamanı sənəd bazasını nəzərə almadan, təbii və adekvat cavablar ver.\n"
        "3. Məlumata Sadiqlik: Daxili sənədlərlə bağlı sorğularda YALNIZ sənə təqdim olunan 'Kontekst Məlumatları'na əsaslan. Əgər kontekstdə bütöv siyahı və ya məlumat bazası varsa, onu gizlətmə, tam və strukturlaşdırılmış şəkildə təqdim et.\n"
        "4. Reallıq: Tələb olunan daxili məlumat təqdim olunan kontekstdə [BOŞ]-dursa və ya tapılmırsa, qətiyyən uydurma; məlumatın bazada olmadığını aydın bildir.\n"
        "5. Keçmiş mesajları (history) daim nəzərə alaraq, sualın arxasındakı əsas məntiqi anlamağa çalış."
    )
    
    # 4. OpenAI Mesaj Strukturunu Qurun (Rol ayrımı və mükəmməl yaddaş ötürülməsi)
    messages = [{"role": "system", "content": system_prompt}]
    
    # Söhbət tarixçəsini ardıcıl əlavə edirik
    for msg in history:
        messages.append({"role": msg['role'], "content": msg['content']})
        
    # Yeni sualı və genişləndirilmiş konteksti ən sona əlavə edirik
    final_user_content = f"Kontekst Məlumatları:\n{context_str}\n\nİstifadəçinin Sualı: {query}"
    messages.append({"role": "user", "content": final_user_content})
    
    # Debug məlumatlarını loglayırıq
    log_step("AI Generator", "Göndərilən Sistem Promptu (Fayl Siyahısı ilə)", system_prompt)
    log_step("AI Generator", "AI-a Gedən Yekun Mesaj Strukturlaşdırılması", messages)
    
    try:
        response = client.chat.completions.create(
            model=MAIN_MODEL,
            messages=messages,
            temperature=0.1
        )
        answer = response.choices[0].message.content
        log_step("AI Generator", "Yekun Generasiya Olunmuş Cavab", answer)
        return answer
    except Exception as e:
        print(f"DEBUG: generate_answer xətası: {e}")
        return "Bağışlayın, cavab hazırlanarkən AI mühərrikində xəta baş verdi."