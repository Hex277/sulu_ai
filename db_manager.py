import psycopg2

def get_connection():
    """Verilənlər bazasına bağlantı yaradır"""
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="123",  # Şifrəni bura daxil etmisən
        host="localhost",
        port="5432"
    )

# --- SİNONİM FUNKSİYALARI ---

def get_synonyms_from_db():
    """Postgres-dən bütün sinonim qruplarını (ARRAY) çəkir"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # public.synonym_groups cədvəlindən sözlər massivini çəkirik
        cur.execute("SELECT words FROM public.synonym_groups")
        rows = cur.fetchall()
        
        cur.close()
        # Nəticəni siyahı daxilində siyahı kimi qaytarır: [['gözəl', 'qəşəng'], ['tələbə', 'şagird']]
        return [row[0] for row in rows]
    
    except Exception as e:
        print(f"❌ Sinonim çəkilərkən xəta: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- SÖHBƏT TARİXÇƏSİ FUNKSİYALARI ---
def create_session_table(session_id):
    """Hər yeni söhbət üçün dinamik cədvəl yaradır"""
    conn = get_connection()
    cur = conn.cursor()
    # Cədvəl adında yalnız hərf və rəqəm olmalıdır (məs: chat_user123_2026)
    table_name = f"chat_{session_id}"
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    return table_name

def save_to_db(session_id, role, content):
    """Mesajı bazaya yazır və mütləq COMMIT edir."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # SQL sorğusunda sütun adlarının pgAdmin-dəki ilə eyni olduğundan əmin ol
        # Sənin screenshot-da sütunlar: session_id, role, content
        query = "INSERT INTO chat_history (session_id, role, content) VALUES (%s, %s, %s)"
        cur.execute(query, (session_id, role, content))
        
        # ƏN VACİB HİSSƏ: Dəyişikliyi təsdiqləyirik
        conn.commit()
        
        cur.close()
        # print(f"✅ Mesaj bazaya yazıldı: {role}") # Debug üçün bunu aça bilərsən
    except Exception as e:
        if conn:
            conn.rollback() # Xəta olsa, yarımçıq işi geri qaytar
        print(f"❌ Bazaya yazarkən xəta: {e}")
    finally:
        if conn:
            conn.close()
    
def get_history(session_id, limit=5):
    """Söhbət tarixçəsini strukturlaşdırılmış siyahı kimi qaytarır"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Ən son mesajları götürmək üçün DESC və sonra onları sıralamaq lazımdır
        cur.execute(
            "SELECT role, content FROM chat_history WHERE session_id = %s ORDER BY created_at DESC LIMIT %s",
            (session_id, limit)
        )
        rows = cur.fetchall() # Bu bizə [(role, content), ...] siyahısını verir
        cur.close()
        
        # Mesajlar DESC (yeni-köhnə) gəldiyi üçün onları çeviririk (köhnə-yeni)
        return rows[::-1] 
    
    except Exception as e:
        print(f"❌ Tarixçə oxunarkən xəta: {e}")
        return [] # Xəta halında boş siyahı qaytarırıq
    finally:
        if conn:
            conn.close()