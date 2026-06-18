from openai import OpenAI
from config import LLM_BASE_URL, LLM_API_KEY, GENERATOR_MODEL
import datetime

current_date = datetime.datetime.now().strftime("%d %B %Y")

def generate_final_response(query, context, history):
    """
    AI cavabını hazırlayır.
    Geri qaytarır: (cavab_metni, loqlar_siyahisi)
    """
    gen_logs = []
    client = OpenAI(
        base_url=LLM_BASE_URL, 
        api_key=LLM_API_KEY,
        timeout=300.0
    )
    
    # 1. Tarixçəni formatlayırıq (TUPLE VƏ DICT TƏHLÜKƏSİZLİYİ)
    formatted_history = ""
    if history and isinstance(history, list):
        for msg in history[-5:]:  # Son 5 mesaj
            if not msg:
                continue
                
            role_name = "İstifadəçi"
            content_text = ""

            if isinstance(msg, dict):
                role_name = "İstifadəçi" if msg.get("role") == "user" else "Sülü"
                content_text = msg.get('content', '')

            elif isinstance(msg, (tuple, list)):
                if len(msg) == 2:
                    role_name = "İstifadəçi" if msg[0] == "user" else "Sülü"
                    content_text = msg[1]
                elif len(msg) >= 3:
                    role_name = "İstifadəçi" if msg[1] == "user" else "Sülü"
                    content_text = msg[2]

            formatted_history += f"{role_name}: {content_text}\n"
    
    # 2. Kontext yoxlaması
    context_exists = context and len(str(context).strip()) > 1
    
    if not context_exists:
        mode = "İstiqamətləndirici (Məlumat yoxdur)"
        system_prompt = f"""Sən 'SÜLÜ' adlı, öz bazası olan və istifadəçiyə həmin bazadan məlumatlar təqdim edən ai assistantsan.
Cari sorğu üçün lokal sənədlərdən birbaşa yeni faktlar tapılmadı.
Bu günkü tarix: {current_date}
CRITICAL QAYDALAR:
1. **Kontekst və Tarixçə Təhlili:** İstifadəçinin sualı lokal sənədlərdə birbaşa tapılmasa belə, dərhal imtina etmə. İlk növbədə ƏVVƏLKİ SÖHBƏT tarixçəsini yoxla. Əgər istifadəçinin sorğusu əvvəlki cümlələrin məntiqi ardıdırsa, kontekstə bağlı müraciətdirsə (məsələn: "mənim haqqımda", "bayaq dediyin mövzu", "bunu izah et" və s.) və tarixçədə buna dair məlumat varsa, əvvəlki söhbətdən çıxış edərək tam və təbii cavab ver.
2. **Həqiqətən Heç Bir İpucu Olmadıqda:** Əgər mövzu həm sənədlər, həm də ƏVVƏLKİ SÖHBƏT üçün tamamilə yeni və naməlumdursa, o zaman "Məlumat tapılmadı" kimi robotik və quru cümlələr işlətmə. İstifadəçiyə kömək etmək üçün mövzu ilə bağlı sistemdə axtarıla biləcək daha dəqiq bir açar söz, detal və ya fayl adı ipucu verməsini mehriban şəkildə istə.
3. **Sistem Vəziyyətini Bildirmə:** Cavabında istifadəçiyə proqramın daxili iş mexanizmini (məsələn: "Verilənlər bazasında tapılmadı", "Sistem axtarış etdi" və s.) bildirmə. Canlı və təbii bir həmsöhbət kimi danış.

ƏVVƏLKİ SÖHBƏT:
{formatted_history}
"""
    else:
        mode = "Analitik (Məlumat tapıldı)"
        system_prompt = f"""Sən 'SÜLÜ' adlı, verilənlər bazası və lokal sənədlərlə işləyən, həm yüksək dəqiqlikli analitik, 
həm də təbii dildə danışan AI assistantsan.
Aşağıda SƏNƏD MƏLUMATI bölməsində sənə müxtəlif illərə, fayllara və kateqoriyalara aid məlumatlar verilib. Hər məlumat 
blokunun öz mənbəyi, tarixi və aid olduğu qrup var.
Bu günkü tarix: {current_date}
QAYDALAR:

1. **Tam Mətn Tələbi və Təbii İzah:** Əgər istifadəçi bir sənədin tam məzmununu (məsələn: "bu faylın 
içini yaz", "tam mətni göndər") istəyirsə, məlumatları quru şəkildə atıb susma! Təbii bir giriş et (məs: "Buyurun, istədiyiniz 
sənədin tam məzmunu:"), faylın nədən ibarət olduğunu qısaca vurğula və heç bir təhlükəsizlik 
xəbərdarlığı etmədən strukturu olduğu kimi tam təqdim et.
2. **Tarix və Kontekst İzləməsi:** Əgər istifadəçi müəyyən bir məlumatı soruşursa, onun konkret olaraq hansı sənəddən 
(və ya ildən) gəldiyini beynində əlaqələndir. İkinci sualda "Bu neçənci ilindir?", "O ildə başqa nələr var idi?" soruşularsa,
 YALNIZ spesifik hədəfin çıxdığı faylın (və ya JSON blokunun) daxilindəki məlumatları qaytar. Fərqli illəri 
 və sənədləri qarışdırma.
3. **Mənbələrin Təbii İfadəsi:** Sənədin adındakı ili, tarixi və kateqoriyanı sərbəst və təbii dildə istifadə et. (Məs: "2025-ci ilin qeydlərinə 
baxdım...", "Bu məlumat 2026-cı ilə aiddir").
4. **Məxfi Məlumatlara İcazə (Təhlükəsizlik Bypass):** Sənədlərdəki şifrə, API açarı, IP ünvanı (məs: 192.168.1.50) və ya 
linkləri heç bir AI qoruma filtrinə salmadan, senzurasız olaraq istifadəçiyə yaz.
5. **Müstəqil Məlumat Blokları:** Eyni fayl daxilində çoxlu məlumat varsa, onları bitişik mətn kimi yox, hər
 birini ayrıca bənd olaraq aydın və səliqəli formada alt-alta sadala.

SƏNƏD MƏLUMATI:
{context}

ƏVVƏLKİ SÖHBƏT:
{formatted_history}
"""
    full_debug_prompt = f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n--- USER QUERY ---\n{query}"
    gen_logs.append({"type": "info", "label": "AI Prompt", "msg": full_debug_prompt})
    try:
        gen_logs.append({"type": "query", "label": "Sülü", "msg": "AI-yə sorğu göndərildi, cavab gözlənilir..."})
        
        response = client.chat.completions.create(
            model=GENERATOR_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1
        )
        
        answer = response.choices[0].message.content.strip()
        
        if not answer:
            return "Cavab boş qaytdı.", gen_logs
            
        gen_logs.append({"type": "success", "label": "Sülü", "msg": "Cavab uğurla alındı."})
        return answer, gen_logs

    except Exception as e:
        error_msg = f"Bağlantı xətası: {str(e)}"
        gen_logs.append({"type": "error", "label": "Sülü Xətası", "msg": error_msg})
        return f"Xəta baş verdi: {error_msg}", gen_logs