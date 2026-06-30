import psycopg2
from config import get_db_connection

def clear_all_documents():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Bütün cədvəli boşaltmaq üçün əmr
        cursor.execute("TRUNCATE TABLE documents RESTART IDENTITY;")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Bazadakı bütün sənədlər uğurla silindi və ID sayğacı sıfırlandı.")
    except Exception as e:
        print(f"❌ Xəta baş verdi: {e}")

# Funksiyanı işə sal
if __name__ == "__main__":
    clear_all_documents()