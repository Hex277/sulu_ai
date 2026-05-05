import time
import uuid
import json
from file_manager import get_file_list, read_file_content
from search_engine import python_lexical_search, deep_content_search 
from router import route_query_to_file
from generator import generate_final_response
from db_manager import save_to_db, get_history, get_synonyms_from_db

def main():
    print("🚀 Universal AI Terminalı (HYBRID GRANULAR RAG) işə düşdü...")
    session_id = str(uuid.uuid4())
    print(f"🆔 Session ID: {session_id}")

    available_files = get_file_list()
    print(f"📁 Mövcud fayllar ({len(available_files)} ədəd): {available_files}")
    
    last_selected_file = None 

    print("📥 Sinonim bazası yüklənir...")
    db_synonyms = get_synonyms_from_db()
    print(f"✅ {len(db_synonyms)} sinonim qrupu yükləndi.")
    if db_synonyms:
        print(f"   ↳ Nümunə sinonim qrupları (ilk 3): {db_synonyms[:3]}")

    while True:
        user_query = input("\n👤 Sualınız: ")
        if user_query.lower() in ['exit', 'quit', 'cix', 'çıx']: break

        print(f"\n📝 Daxil edilən sorğu: '{user_query}' (uzunluq: {len(user_query)} simvol)")
        start_total = time.time()
        
        # --- 0. TARİXÇƏ ÇƏKİLMƏSİ ---
        print("\n" + "🔍"*3 + "="*22 + " DEBUG: CHAT HISTORY " + "="*22 + "🔍"*3)
        t0 = time.time()
        chat_history = get_history(session_id, limit=5)
        print(f"   ↳ Tarixçə çəkilmə müddəti: {time.time()-t0:.4f} san")
        print(f"   ↳ Tapılan mesaj sayı: {len(chat_history)}")
        
        if not chat_history:
            print("   ⚠️  Tarixçə boşdur (ilk sorğu və ya boş session).")
        else:
            for i, msg in enumerate(chat_history):
                role, content = msg[0], msg[1]
                print(f"   [{i+1}] {role.upper():10s} → {content[:80]}{'...' if len(content)>80 else ''}")
        print("🔍" + "="*70 + "\n")

        # --- 1. AXTARIŞ VƏ QƏRAR MƏNTİQİ ---
        print("─"*30 + " [1/4] HİBRİD AXTARIŞ " + "─"*30)
        print(f"   ↳ Son seçilən fayl (last_selected_file): {last_selected_file}")
        start_search = time.time()
        
        combined_context = ""
        selected_files = []
        search_mode = "NONE"

        # A. Fayl adları üzrə axtarış
        print("\n🔤 [A] LEKSİKAL AXTARIŞ (Fayl adları üzrə)...")
        t1 = time.time()
        name_results = python_lexical_search(user_query, available_files, db_synonyms)
        print(f"   ↳ Leksikal axtarış müddəti: {time.time()-t1:.4f} san")
        
        if name_results:
            print(f"   ↳ Leksikal axtarış NƏTİCƏLƏRİ ({len(name_results)} fayl):")
            for rank, (fname, score) in enumerate(name_results, 1):
                print(f"      #{rank}  '{fname}'  →  xal: {score}")
            
            search_mode = "FILENAME"
            selected_files = [f[0] for f in name_results[:3]]
            print(f"\n🎯 Seçilən fayllar (top 3): {selected_files}")
            
            for f_name in selected_files:
                print(f"   📂 Oxunur: '{f_name}'...")
                t_read = time.time()
                content = read_file_content(f_name)
                print(f"      ↳ Oxuma müddəti: {time.time()-t_read:.4f} san | Məzmun uzunluğu: {len(content)} simvol")
                combined_context += f"\n--- MƏNBƏ FAYL (Tam): {f_name} ---\n{content}\n"
        
        else:
            print("   ❌ Leksikal axtarış nəticə vermədi.")
            
            # B. Faylların İÇİNDƏ sətir-səviyyəli axtarış
            print(f"\n🔬 [B] DƏRİN MƏZMUN AXTARIŞI (İlk {min(10, len(available_files))} fayl üzrə)...")
            candidates = available_files[:10]
            print(f"   ↳ Namizəd fayllar: {candidates}")
            t2 = time.time()
            content_results = deep_content_search(user_query, candidates)
            print(f"   ↳ Dərin axtarış müddəti: {time.time()-t2:.4f} san")
            
            if content_results:
                print(f"   ↳ Dərin axtarış NƏTİCƏLƏRİ ({len(content_results)} faylda tapıldı):")
                for fname, rows in content_results.items():
                    print(f"      📄 '{fname}' → {len(rows)} uyğun sətir")
                    for ri, row in enumerate(rows[:3], 1):  # İlk 3 sətri göstər
                        preview = str(row)[:100]
                        print(f"         Sətir {ri}: {preview}{'...' if len(str(row))>100 else ''}")
                
                search_mode = "GRANULAR"
                selected_files = list(content_results.keys())[:3]
                print(f"\n🎯 Seçilən fayllar (top 3): {selected_files}")
                
                for f_name in selected_files:
                    rows = content_results[f_name]
                    combined_context += f"\n--- MƏNBƏ FAYL (Sətirlər): {f_name} ---\n"
                    combined_context += json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
                    print(f"   ✅ '{f_name}' kontextə əlavə edildi ({len(rows)} sətir).")
            else:
                print("   ❌ Dərin axtarış da nəticə vermədi.")
                
                # C. Router-ə keçid
                print(f"\n🧭 [C] AI ROUTER işə düşür...")
                print(f"   ↳ Router-ə göndərilən sorğu: '{user_query}'")
                print(f"   ↳ Router-ə göndərilən fayl siyahısı: {available_files}")
                print(f"   ↳ Router-ə göndərilən son fayl: {last_selected_file}")
                print(f"   ↳ Router-ə göndərilən tarixçə uzunluğu: {len(chat_history)} mesaj")
                
                search_mode = "ROUTER"
                t3 = time.time()
                res = route_query_to_file(user_query, available_files, chat_history, last_selected_file)
                router_time = time.time() - t3
                
                print(f"\n   🎯 ROUTER QƏRARI:")
                print(f"      ↳ Seçilən fayl:    '{res}'")
                print(f"      ↳ Router müddəti:  {router_time:.2f} san")
                
                if res:
                    if res in available_files:
                        print(f"      ✅ Router cavabı fayl siyahısında tapıldı.")
                    else:
                        print(f"      ⚠️  XƏBƏRDARLIQ: Router '{res}' qaytardı amma bu fayl siyahısında YOXdur!")
                    
                    selected_files = [res]
                    print(f"   📂 Oxunur: '{res}'...")
                    t_read = time.time()
                    content = read_file_content(res)
                    print(f"      ↳ Oxuma müddəti: {time.time()-t_read:.4f} san | Məzmun uzunluğu: {len(content)} simvol")
                    combined_context = f"\n--- MƏNBƏ FAYL (Router): {res} ---\n{content}"
                else:
                    print(f"      ❌ Router heç bir fayl seçmədi (None qaytardı).")

        search_time = time.time() - start_search
        
        print(f"\n📊 AXTARIŞ XÜLASƏSİ:")
        print(f"   ↳ Rejim:               {search_mode}")
        print(f"   ↳ Seçilən fayllar:     {selected_files if selected_files else 'Heç biri'}")
        print(f"   ↳ Context uzunluğu:    {len(combined_context)} simvol")
        print(f"   ↳ Ümumi axtarış vaxtı: {search_time:.4f} san")
        
        if selected_files:
            last_selected_file = selected_files[0]
            print(f"   ↳ Yeni last_selected_file: '{last_selected_file}'")

        # --- 2. GENERATOR (SÜLÜ) ---
        print("\n" + "─"*30 + " [3/4] GENERATOR (SÜLÜ) " + "─"*30)
        print(f"   ↳ Generator modeli:   {__import__('config').GENERATOR_MODEL}")
        print(f"   ↳ Sorğu uzunluğu:     {len(user_query)} simvol")
        print(f"   ↳ Context uzunluğu:   {len(combined_context)} simvol")
        print(f"   ↳ Tarixçə:            {len(chat_history)} mesaj")
        print(f"   ⏳ AI cavabı gözlənilir...")
        
        start_generator = time.time()
        final_answer = generate_final_response(user_query, combined_context, chat_history)
        generator_time = time.time() - start_generator
        
        print(f"   ✅ Cavab alındı! ({generator_time:.2f} san, {len(final_answer)} simvol)")

        # --- 3. BAZAYA YAZMA ---
        print("\n" + "─"*30 + " [4/4] BAZAYA YAZMA " + "─"*30)
        db_assistant_msg = final_answer
        if selected_files:
            source_tag = "Sətir-səviyyəli" if search_mode == "GRANULAR" else "Tam fayl"
            db_assistant_msg += f"\n\n[Mənbələr ({source_tag}): {', '.join(selected_files)}]"

        print(f"   💾 İstifadəçi mesajı yazılır (session: {session_id[:8]}...)...")
        t_db1 = time.time()
        save_to_db(session_id, "user", user_query)
        print(f"      ↳ User yazıldı ({time.time()-t_db1:.4f} san)")
        
        t_db2 = time.time()
        save_to_db(session_id, "assistant", db_assistant_msg)
        print(f"      ↳ Assistant yazıldı ({time.time()-t_db2:.4f} san)")

        total_time = time.time() - start_total

        # --- NƏTİCƏ ÇAPI ---
        print("\n" + "="*70)
        print(f"🤖 Sülü Cavabı:\n{final_answer}")
        print("─" * 70)
        print(f"📊 PERFORMANS XÜLASƏSİ:")
        print(f"   ↳ Axtarış Rejimi:     {search_mode}")
        print(f"   ↳ Seçilən Fayllar:    {', '.join(selected_files) if selected_files else 'Yoxdur'}")
        print(f"   ↳ Context ölçüsü:     {len(combined_context)} simvol")
        print(f"   ↳ Axtarış Müddəti:    {search_time:.4f} san")
        print(f"   ↳ Generator AI:       {generator_time:.2f} san")
        print(f"   ↳ ÜMUMİ VAXT:         {total_time:.2f} san")
        print("="*70)

if __name__ == "__main__":
    main()