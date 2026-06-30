import psycopg2
from config import get_db_connection

def init_memory_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_user_id ON chat_history(user_id);
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DEBUG: init_memory_db xətası: {e}")

class ChatMemory:
    def __init__(self, user_id: str):
        self.user_id = user_id
        init_memory_db()

    def add_message(self, role: str, content: str):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s)",
                (str(self.user_id), str(role), str(content))
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"DEBUG: add_message xətası: {e}")

    def get_history(self, limit: int = 5):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Parametrləri explicit olaraq tuple formatında ötürürük
            # LIMIT üçün ədədi int() ilə çeviririk
            query = """
                SELECT role, content 
                FROM chat_history 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            cursor.execute(query, (str(self.user_id), int(limit)))
            
            rows = cursor.fetchall()
            # Məlumatları alırıq
            history = [{"role": row['role'], "content": row['content']} for row in rows]
            
            # Xronoloji düzülüş (tərs çeviririk)
            history.reverse()
            
            cursor.close()
            conn.close()
            return history
        except Exception as e:
            print(f"DEBUG: get_history xətası: {e}")
            return []