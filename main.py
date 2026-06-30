import sys
from indexer import build_index
from searcher import search_documents, log_step
from generator import optimize_query, generate_answer
from logger import reset_logs, export_logs_to_file
from config import get_db_connection 
from memory import ChatMemory  # 🌟 Yeni yaddaş modulu əlavə edildi

def main():
    # 🌟 TEST ÜÇÜN İSTİFADƏÇİ ID (Gələcəkdə bu dinamik olacaq)
    CURRENT_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
    memory = ChatMemory(user_id=CURRENT_USER_ID)
    
    print("=" * 60)
    print("          SÜLÜ AI - POSTGRESQL FTS BAŞLADILIR          ")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents;")
        row = cursor.fetchone()
        if row:
            doc_count = row[0] if not isinstance(row, dict) else list(row.values())[0]
        else:
            doc_count = 0
        conn.close()
    except Exception as e:
        print(f"⚠️ Verilənlər bazasına qoşularkən xəta: {e}")
        doc_count = 0

    if doc_count == 0:
        print("▶️ Baza boşdur. İlk indeksləmə başladılır...")
        updated_count = build_index(force=True)
        print(f"\n[UĞURLU] İlk indeksasiya tamamlandı! Bazaya {updated_count} fayl yazıldı.")
    else:
        print(f"✅ Sistem hazırdır! Bazada {doc_count} sənəd var.")

    print("Sistemdən çıxmaq üçün 'exit' yazın.\n")
    while True:
        try:
            query = input("\nSorğunuzu daxil edin: ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "çıxış"]:
                print("Sistem dayandırıldı. Sağ olun!")
                break
                
            reset_logs()
            print("Axtarılır və cavab hazırlanır...")
            
            history = memory.get_history(limit=5)
            
            # 2. Axtarış et
            optimized_query = optimize_query(query)
            search_results = search_documents(optimized_query)
            if not search_results:
                search_results = search_documents(query)
                
            # 3. Cavabı al
            answer = generate_answer(query, search_results, history=history)
            
            # 4. YADDAŞA YAZMA ARDICILLIĞI:
            # Öncə istifadəçinin sualını yaz
            memory.add_message("user", query)
            # Sonra AI-ın cavabını yaz
            memory.add_message("assistant", answer)
            
            print("\n" + "=" * 25 + " SÜLÜ AI CAVABI " + "=" * 25)
            print(answer)
            print("=" * 66)
            
            export_logs_to_file("debug_fts.json")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nGözlənilməz sistem xətası: {e}")

if __name__ == "__main__":
    main()