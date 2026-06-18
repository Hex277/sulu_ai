"""
AI Bot - Flask Server
=====================
Bu server:
1. HTML saytdan gələn sualları qəbul edir
2. data/ qovluğunu oxuyur, uyğun fayl tapır
3. OpenAI-yə göndərir
4. Cavabı HTML sayta qaytarır
5. PostgreSQL-də mesajları saxlayır (aktiv etmək üçün aşağıya bax)

Başlatmaq üçün terminalda: python server.py
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

from file_manager import get_file_list, read_file_content
from search_engine import python_lexical_search, anytxt_search, expand_search_query
from router import route_query_to_file
from generator import generate_final_response
from db_manager import save_to_db, get_history as db_get_history, get_synonyms_from_db
from file_manager import read_file_content
# ─── Mühit dəyişənlərini yüklə (.env faylından) ───
load_dotenv()

app = Flask(__name__)
CORS(app)  # HTML saytın bu serverə sorğu göndərməsinə icazə verir

# ─── OpenAI client ───
client = OpenAI(api_key="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")

# ─── Data qovluğunun yolu ───
# Bu fayl server.py ilə eyni qovluqdadırsa düzgündür
DATA_FOLDER = Path(__file__).parent / "data"

# ═══════════════════════════════════════════════════════
#  PostgreSQL İNTEQRASİYASI
#  Aktiv etmək üçün: aşağıdakı False-u True edin
#  və .env faylına DB bilgilərini əlavə edin
# ═══════════════════════════════════════════════════════
USE_POSTGRES = True  # ← True edəndə PostgreSQL aktivləşir

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def get_db():
        """Hər sorğu üçün yeni DB bağlantısı açır"""
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "123")
        )

    def init_db():
        """Cədvəlləri yarat (ilk dəfə işlədəndə)"""
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id UUID PRIMARY KEY,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id UUID REFERENCES sessions(id),
                role VARCHAR(10) NOT NULL,  -- 'user' ya da 'bot'
                content TEXT NOT NULL,
                files_found TEXT[],          -- tapılan faylların adları
                tokens_used INT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✓ PostgreSQL cədvəlləri hazırdır")

    init_db()


# ═══════════════════════════════════════════════════════
#  YARDIMÇI FUNKSİYALAR
# ═══════════════════════════════════════════════════════

def get_data_files():
    """
    data/ qovluğundakı bütün faylların adını qaytarır.
    Bu adlar AI-yə göndərilir ki, hansı faylı açacağını bilsin.
    """
    if not DATA_FOLDER.exists():
        return []
    
    files = []
    for f in DATA_FOLDER.rglob("*"):  # alt qovluqları da oxuyur
        if f.is_file():
            # data/ qovluğuna görəli yol: məs. "satish/2024.txt"
            relative = str(f.relative_to(DATA_FOLDER))
            files.append(relative)
    
    return files


def read_file_content(filename):
    """
    data/ qovluğundan bir faylı oxuyur.
    filename: məs. "satish.txt" ya da "hesabatlar/q4.csv"
    """
    filepath = DATA_FOLDER / filename
    
    # Güvenlik: data/ qovluğundan çıxmağa çalışmasın
    try:
        filepath = filepath.resolve()
        data_folder_resolved = DATA_FOLDER.resolve()
        filepath.relative_to(data_folder_resolved)  # xəta verərsə, kənar yoldur
    except ValueError:
        return None, "Təhlükəsizlik xətası: bu yola icazə yoxdur"
    
    if not filepath.exists():
        return None, f"Fayl tapılmadı: {filename}"
    
    try:
        # .csv, .txt, .md, .json oxu
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read(), None
    except UnicodeDecodeError:
        # UTF-8 olmayan fayllar üçün
        with open(filepath, "r", encoding="latin-1") as f:
            return f.read(), None
    except Exception as e:
        return None, f"Fayl oxuma xətası: {str(e)}"


def find_relevant_file(user_question, file_list):
    """
    AI-dən xahiş edir ki, sualına görə hansı faylı açsın.
    Sadə prompt ilə fayl adı seçdirir.
    """
    if not file_list:
        return None, "data/ qovluğu boşdur"
    
    files_text = "\n".join(f"- {f}" for f in file_list)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Sürətli və ucuz model fayl seçimi üçün
        messages=[
            {
                "role": "system",
                "content": (
                    "Sən bir fayl seçici sistemisin. "
                    "İstifadəçinin sualına görə ən uyğun faylı seç. "
                    "YALNIZ fayl adını yaz, başqa heç nə yazma. "
                    "Heç bir fayl uyğun deyilsə 'NONE' yaz."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Mövcud fayllar:\n{files_text}\n\n"
                    f"Sual: {user_question}\n\n"
                    f"Ən uyğun fayl adı:"
                )
            }
        ],
        max_tokens=50,
        temperature=0
    )
    
    chosen = response.choices[0].message.content.strip()
    
    if chosen == "NONE" or chosen not in file_list:
        # Bəzən AI formatı bir az fərqli yazır, bənzərini axtar
        for f in file_list:
            if chosen.lower() in f.lower() or f.lower() in chosen.lower():
                return f, None
        return None, f"Uyğun fayl tapılmadı (AI seçdi: {chosen})"
    
    return chosen, None


def save_message_to_db(session_id, role, content, files_found=None, tokens=0):
    """
    PostgreSQL-ə mesaj saxlayır.
    USE_POSTGRES=False olduqda heç nə etmir.
    """
    if not USE_POSTGRES:
        return  # Mock rejim, saxlamır
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Əvvəlcə session-u yoxla/yarat
        cur.execute(
            "INSERT INTO sessions (id) VALUES (%s) ON CONFLICT DO NOTHING",
            (session_id,)
        )
        
        # Mesajı əlavə et
        cur.execute(
            """
            INSERT INTO messages (session_id, role, content, files_found, tokens_used)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session_id, role, content, files_found, tokens)
        )
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB xətası: {e}")


def load_messages_from_db(session_id):
    """
    Bir session-un bütün mesajlarını PostgreSQL-dən oxuyur.
    """
    if not USE_POSTGRES:
        return []
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT role, content, files_found, tokens_used, created_at
            FROM messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"DB oxuma xətası: {e}")
        return []


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_query = data.get("message", "").strip()
    session_id = data.get("session_id", str(uuid.uuid4()))
    last_selected_file = data.get("last_selected_file", None)
    
    if not user_query:
        return jsonify({"error": "Sual boşdur"}), 400

    logs = []
    def add_log(type_, label, msg):
        logs.append({"type": type_, "label": label, "msg": str(msg)})
        print(f"[{label}] {msg}")

    start_total = time.time()
    add_log("info", "Sistem", "Granular RAG prosesi başladı...")

    # 1. Mövcud fayllar və Sinonimlər
    available_files = get_file_list()
    db_synonyms = get_synonyms_from_db()
    add_log("info", "Data", f"{len(available_files)} fayl və {len(db_synonyms)} sinonim yükləndi.")

    # 2. Tarixçəni çək
    chat_history = db_get_history(session_id)
    if not isinstance(chat_history, list):
        chat_history = []
    add_log("info", "Tarixçə", f"{len(chat_history)} əvvəlki mesaj tapıldı.")

    # --- YENİ: TARİXÇƏNİ STRING FORMATINA SALMAQ ---
    # expand_search_query funksiyasına göndərmək üçün tarixçəni formatlayırıq
    # --- YENİ: TARİXÇƏNİ STRING FORMATINA SALMAQ (TUPLE VƏ DICT TƏHLÜKƏSİZLİYİ) ---
    formatted_history = ""
    for msg in chat_history[-5:]:  # Son 5 mesaj
        if not msg:
            continue
            
        role_name = "İstifadəçi"
        content_text = ""

        # Variant A: Əgər məlumat bazadan dict (lüğət) kimi gəlirsə
        if isinstance(msg, dict):
            role_name = "İstifadəçi" if msg.get("role") == "user" else "Sülü"
            content_text = msg.get('content', '')

        # Variant B: Əgər məlumat bazadan tuple (kortej) kimi gəlirsə
        elif isinstance(msg, (tuple, list)):
            # Əgər tuple daxilində 2 element varsa (role, content) -> məsələn: ("user", "salam")
            if len(msg) == 2:
                role_name = "İstifadəçi" if msg[0] == "user" else "Sülü"
                content_text = msg[1]
            # Əgər tuple daxilində 3 element varsa (id, role, content) -> məsələn: (1, "user", "salam")
            elif len(msg) >= 3:
                role_name = "İstifadəçi" if msg[1] == "user" else "Sülü"
                content_text = msg[2]

        formatted_history += f"{role_name}: {content_text}\n"
    def ai_generator_func(prompt_text):
        try:
            # XƏTANI ARADAN QALDIRMAQ ÜÇÜN: Arqumentləri adla yox, birbaşa mövqeyə görə (query, context, history) ötürürük.
            answer, _ = generate_final_response(prompt_text, "", [])
            return answer.strip()
        except Exception as e:
            print(f"   ⚠️ Generator köməkçi xətası: {e}")
            return user_query

    from search_utils import expand_search_query # Əgər yuxarıda import etməmisənsə
    optimized_query = expand_search_query(user_query, formatted_history, ai_generator_func)
    add_log("info", "Optimallaşdırma", f"Orijinal: '{user_query}' ➔ AnyTXT üçün: '{optimized_query}'")

    combined_context = ""
    selected_files = []
    search_mode = "NONE"

    # --- ADDIM A: LEKSİKAL AXTARIŞ (Fayl adları üzrə) ---
    add_log("query", "Leksikal", "Fayl adları üzrə axtarış gedir...")
    # Leksikal axtarışa da genişləndirilmiş optimized_query-ni göndəririk ki, sinonimləri və tarixləri tuta bilsin
    name_results, lexical_logs = python_lexical_search(optimized_query, available_files, db_synonyms)
    logs.extend(lexical_logs)

    if name_results:
        selected_files = [f[0] for f in name_results[:3]]
        add_log("file", "Leksikal Tapıldı", f"Seçilən: {selected_files}")
        
        # Fayl tapılıb, indi içindən AnyTXT ilə dəqiq sətirləri çəkək
        # DƏYİŞİKLİK: Bura optimized_query ötürülür
        content_results = anytxt_search(optimized_query)
        
        if content_results:
            search_mode = "FILENAME_GRANULAR"
            for f_name, rows in content_results.items():
                if f_name in selected_files:
                    combined_context += f"\n--- MƏNBƏ (Dəqiq Sətirlər): {f_name} ---\n{str(rows)}\n"
            add_log("success", "Məzmun", "Fayl daxilindən uyğun sətirlər tapıldı.")

        # Əgər AnyTXT sətir tapmasa, tapılan faylı tam oxu
        if not combined_context:
            search_mode = "FILENAME_FULL"
            for f_name in selected_files:
                try:
                    import pandas as pd
                    import os
                    f_path = os.path.join("data", f_name) 
                    
                    if f_name.endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(f_path)
                        content = df.to_string(index=False)
                    else:
                        with open(f_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    
                    # ─── YENİ: Leksikal axtarışda da nəhəng faylların qarşısını alırıq ───
                    if len(content) > 15000:
                        content = content[:15000] + "\n\n... [Tam mətn çox uzun olduğu üçün kəsildi] ..."
                        
                    combined_context += f"\n--- MƏNBƏ (Tam Fayl): {f_name} ---\n{content}\n"
                    add_log("info", "Fayl Oxundu", f"{f_name} tam oxundu.")
                except Exception as e:
                    add_log("error", "Oxuma Xətası", str(e))

    # --- ADDIM B: ANYTXT GLOBAL SEARCH (Əgər Leksikal heç nə tapmasa) ---
    if not combined_context:
        add_log("query", "AnyTXT", "Bütün sistem axtarılır...")
        # DƏYİŞİKLİK: AnyTXT artıq istifadəçinin xam inputunu yox, təmizlənmiş və OR məntiqli optimized_query-ni icra edir
        content_results = anytxt_search(optimized_query)
        
        if content_results:
            search_mode = "CONTENT_ONLY"
            
            # YENİ: Universal Çeşidləmə Məntiqi
            # Sorğudakı sözləri kiçik hərflə siyahıya alırıq
            query_words = optimized_query.lower().split()
            
            def sort_score(item):
                f_name = item[0].lower() # Faylın adı
                score = 0
                
                # QAYDA 1: Əgər axtarılan sözlər birbaşa faylın adında varsa, +100 xal!
                for w in query_words:
                    if len(w) > 2 and w in f_name:
                        score += 100
                        
                # QAYDA 2: Tam məzmunu oxunan kiçik fayllara bir az üstünlük veririk (+10 xal)
                if item[1].get("full_content"):
                    score += 10
                    
                return score

            # Nəticələri yığdığımız xala görə yuxarıdan aşağıya sıralayırıq və ən yaxşı 5-ni alırıq
            sorted_results = sorted(content_results.items(), key=sort_score, reverse=True)[:5]
            
            # Dövrü artıq çeşidlənmiş siyahı (sorted_results) üzərindən qururuq
            MAX_CHARS_PER_FILE = 12000 
            
            # Dövrü artıq çeşidlənmiş siyahı (sorted_results) üzərindən qururuq
            for f_name, data in sorted_results:
                
                # 1. İlk növbədə məzmunu təyin edirik
                if data.get("full_content"):
                    main_text = data["full_content"]
                    content_type = "TAPILAN FAYLIN TAM MƏZMUNU"
                else:
                    snippets_list = data.get("snippets", [])
                    main_text = " [... ] ".join(snippets_list).replace("<<", "").replace(">>", "")
                    main_text = " ".join(main_text.split())
                    content_type = "FAYLDAN PARÇALAR (SNIPPET)"
                
                # ─── YENİ: Mətni kəsirik ki, OpenAI 429 xətası verməsin ───
                if len(main_text) > MAX_CHARS_PER_FILE:
                    main_text = main_text[:MAX_CHARS_PER_FILE] + "\n\n... [Mətnin davamı token limiti səbəbindən kəsildi] ..."

                # 2. Qonşu faylları stringə çeviririk
                siblings = data.get("sibling_files", [])
                siblings_str = ", ".join(siblings) if siblings else "Yoxdur"
                
                # 3. AI üçün formatlama
                combined_context += (
                    f"\n---\n"
                    f"📄 MƏNBƏ FAYL: {f_name}\n"
                    f"📅 SON DƏYİŞMƏ TARİXİ: {data.get('mod_date', 'Naməlum')}\n"
                    f"📂 EYNİ QOVLUQDAKI DİGƏR FAYLLAR: {siblings_str}\n"
                    f"🔍 {content_type}:\n{main_text}\n"
                )
            
            add_log("success", "AnyTXT", f"{len(content_results)} mənbə tapıldı, ən uyğun 5-i seçildi.")
            
    if not combined_context:
        add_log("query", "Router", "Heç bir uyğunluq yoxdur, AI Router işə düşür...")
        # DƏYİŞİKLİK: Routerə də optimized_query göndərilir
        res = route_query_to_file(optimized_query, available_files, chat_history, last_selected_file)
        if res and res in available_files:
            search_mode = "ROUTER"
            selected_files = [res]
            content = read_file_content(res) 
            combined_context = f"\n--- MƏNBƏ (Router): {res} ---\n{content}"
            add_log("file", "Router", f"AI '{res}' faylını seçdi.")

    # 3. Generator (AI Cavabı)
    add_log("info", "Sülü", "Cavab hazırlanır...")
    try:
        final_answer, generator_logs = generate_final_response(user_query, combined_context, chat_history)
        logs.extend(generator_logs)
        add_log("success", "Hazırdır", f"Cavab alındı ({time.time()-start_total:.2f} san)")
    except Exception as e:
        add_log("error", "AI Xətası", str(e))
        final_answer = "Bağışlayın, cavab yaradarkən xəta baş verdi."

    # 4. Bazaya Yazma
    db_assistant_msg = final_answer
    if selected_files:
        db_assistant_msg += f"\n\n[Mənbələr: {', '.join(selected_files)}]"
    
    save_to_db(session_id, "user", user_query)
    save_to_db(session_id, "assistant", db_assistant_msg)

    return jsonify({
        "answer": final_answer,
        "logs": logs,
        "session_id": session_id,
        "mode": search_mode,
        "last_selected_file": selected_files[0] if selected_files else None
    })

@app.route("/api/files", methods=["GET"])
def list_files():
    """data/ qovluğundakı faylların siyahısını qaytarır"""
    files = get_data_files()
    return jsonify({"files": files, "count": len(files)})


@app.route("/api/history/<session_id>", methods=["GET"])
def get_history(session_id):
    """Bir session-un mesaj tarixçəsini qaytarır"""
    messages = load_messages_from_db(session_id)
    return jsonify({"messages": messages, "count": len(messages)})


@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    """
    Bütün session-ların siyahısını qaytarır.
    Sidebar üçün: title (ilk user mesajı), preview, tarix, mesaj sayı.
    """
    if not USE_POSTGRES:
        return jsonify({"sessions": [], "note": "PostgreSQL aktiv deyil"})
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                s.id,
                TO_CHAR(s.created_at, 'YYYY-MM-DD') AS date,
                TO_CHAR(s.created_at, 'HH24:MI')    AS time,
                COUNT(m.id)                           AS message_count,
                MAX(m.created_at)                     AS last_message,
                MIN(m.content) FILTER (
                    WHERE m.role = 'user'
                )                                     AS first_user_msg,
                (
                    SELECT content
                    FROM messages m2
                    WHERE m2.session_id = s.id
                      AND m2.role = 'user'
                    ORDER BY m2.created_at ASC
                    OFFSET 1 LIMIT 1
                )                                     AS second_user_msg
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY COALESCE(MAX(m.created_at), s.created_at) DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
 
        sessions = []
        for r in rows:
            d = dict(r)
            # title: ilk user mesajının ilk 40 simvolu, yoxsa "Söhbət"
            raw_title = d.get("first_user_msg") or "Söhbət"
            d["title"]   = raw_title[:40] + ("…" if len(raw_title) > 40 else "")
            # preview: ikinci user mesajı ya da boş
            raw_preview  = d.get("second_user_msg") or ""
            d["preview"] = raw_preview[:55] + ("…" if len(raw_preview) > 55 else "")
            # message_count int-ə çevir (psycopg2 Decimal qaytara bilər)
            d["message_count"] = int(d.get("message_count") or 0)
            sessions.append(d)
 
        return jsonify({"sessions": sessions})
 
    except Exception as e:
        print(f"get_sessions xətası: {e}")
        return jsonify({"error": str(e)}), 500
 
@app.route("/api/status", methods=["GET"])
def status():
    """Serverin vəziyyətini yoxlamaq üçün"""
    files = get_data_files()
    return jsonify({
        "status": "ok",
        "data_folder": str(DATA_FOLDER),
        "data_folder_exists": DATA_FOLDER.exists(),
        "file_count": len(files),
        "postgres": USE_POSTGRES,
        "timestamp": datetime.now().isoformat()
    })


# ═══════════════════════════════════════════════════════
#  SERVERI BAŞLAT
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("AI Bot Server başladı")
    print(f"Ünvan: http://localhost:5000")
    print(f"Data qovluğu: {DATA_FOLDER}")
    print(f"PostgreSQL: {'Aktiv' if USE_POSTGRES else 'Mock rejim'}")
    print("=" * 50)
    print("Dayandırmaq üçün: Ctrl+C")
    print()
    
    app.run(
        host="0.0.0.0",  # Şəbəkədəki bütün cihazlardan əlçatan olsun
        port=5000,
        debug=True  # Kodu dəyişəndə avtomatik yenilənir
    )