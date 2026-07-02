"""
searcher.py
-----------
PostgreSQL bazasında Full-Text Search (FTS) edən və 
tapılan sənədlərdən snippet çıxaran modul.
"""

import re
from config import get_db_connection, TOP_K_RESULTS, FULL_TEXT_CHAR_LIMIT, SNIPPET_WINDOW, MAX_SNIPPETS_PER_FILE
from indexer import tokenize, az_lower
from logger import log_step
def normalize_aze_text(text: str) -> str:
    """Azərbaycan hərflərini ingilis qarşılıqlarına çevirir."""
    mapping = {
        'ə': 'e', 'ç': 'c', 'ş': 's', 'ğ': 'g', 'ö': 'o', 'ü': 'u', 'ı': 'i',
        'MÜƏLLİM': 'muellim' # Ümumi vizual xəritə üçün
    }
    cleaned = text.lower()
    for aze, eng in mapping.items():
        cleaned = cleaned.replace(aze, eng)
    return cleaned
def search_documents(query: str) -> list[dict]:
    cleaned_query = az_lower(query.strip())
    tokens = tokenize(cleaned_query)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. STRATEGİYA: İstifadəçi birbaşa bazadakı fayllardan birinin adını çəkibmi?
    cursor.execute("SELECT DISTINCT filename FROM documents")
    all_indexed_files = [r['filename'] for r in cursor.fetchall()]
    
    targeted_filename = None
    for fname in all_indexed_files:
        fname_lower = az_lower(fname)
        fname_base = fname_lower.split('.')[0] # uzantısız ad (məs: muellim_siyahisi)
        if fname_lower in cleaned_query or fname_base in cleaned_query:
            targeted_filename = fname
            break
            
    # Əgər birbaşa fayl adı tələb olunursa (Məs: "muellim_siyahisi faylının daxilini yaz")
    if targeted_filename:
        cursor.execute("""
            SELECT content 
            FROM documents 
            WHERE filename = %s 
            ORDER BY id ASC
        """, (targeted_filename,))
        rows = cursor.fetchall()
        
        full_text = "\n".join([r['content'] for r in rows])
        # Simvol limitini aşmamaq üçün qoruyucu bənd
        if len(full_text) > 10000:
            full_text = full_text[:10000] + "\n... [Mətn çox uzun olduğu üçün limit daxilində kəsildi] ..."
            
        cursor.close()
        conn.close()
        
        log_step("Axtarış", f"Birbaşa Fayl Marşrutlaşdırma: {targeted_filename}", f"Həcm: {len(full_text)} simvol")
        return [{
            "path": targeted_filename,
            "filename": targeted_filename,
            "score": 1.0,
            "context": f"=== FAYLIN TAM DAXİLİ MƏLUMATI ({targeted_filename}) ===\n{full_text}",
            "is_full_text": True
        }]

    # 2. STRATEGİYA: Standart Full-Text Search (Ada görə axtarış və s.)
    if not tokens:
        cursor.close()
        conn.close()
        return []
        
    fts_query = " & ".join(tokens)
    results = []
    seen_excel_files = set()
    
    try:
        cursor.execute("""
            SELECT filepath, filename, content, ts_rank(search_vector, to_tsquery('simple', %s)) as score
            FROM documents
            WHERE search_vector @@ to_tsquery('simple', %s)
            ORDER BY score DESC
            LIMIT %s
        """, (fts_query, fts_query, TOP_K_RESULTS))
        fts_rows = cursor.fetchall()
    except Exception:
        # FTS-də problem olarsa fallback olaraq ILIKE axtarışı
        cursor.execute("""
            SELECT filepath, filename, content, 1.0 as score 
            FROM documents 
            WHERE content ILIKE %s 
            LIMIT %s
        """, (f"%{cleaned_query}%", TOP_K_RESULTS))
        fts_rows = cursor.fetchall()

    for row in fts_rows:
        filename = row['filename']
        filepath = row['filepath']
        content = row['content']
        score = row['score'] if 'score' in row else 1.0
        
        # Əgər tapılan sətir Excel (.xlsx) və ya CSV-yə aiddirsə, konteksti avtomatik GENİŞLƏNDİRİRİK
        if filename.endswith(('.xlsx', '.csv')):
            if filename in seen_excel_files:
                continue # Bu faylı artıq bütöv şəkildə kontekstə daxil etmişik
            seen_excel_files.add(filename)
            
            # Həmin excel-ə aid olan bütün sətirləri bazadan bütövlüklə çəkirik
            inner_cursor = conn.cursor()
            inner_cursor.execute("SELECT content FROM documents WHERE filename = %s ORDER BY id ASC", (filename,))
            all_table_rows = inner_cursor.fetchall()
            inner_cursor.close()
            
            excel_context = "\n".join([r['content'] for r in all_table_rows])
            if len(excel_context) > 10000:
                excel_context = excel_context[:10000] + "\n... [Cədvəl çox böyükdür, kəsildi] ..."
                
            results.append({
                "path": filepath,
                "filename": filename,
                "score": score + 0.5, # Excel bütövlüyünə görə skoru artırırıq
                "context": f"=== CƏDVƏLİN TAM SİYAHISI ({filename}) ===\n{excel_context}",
                "is_full_text": True
            })
        else:
            # Word, PDF və ya TXT sənədləri üçün standart snippet çıxarılması
            snippets = []
            lower_content = az_lower(content)
            found_positions = []
            for token in tokens:
                for m in re.finditer(re.escape(token), lower_content):
                    found_positions.append(m.start())
            found_positions = sorted(list(set(found_positions)))
            
            for pos in found_positions[:MAX_SNIPPETS_PER_FILE]:
                start = max(0, pos - SNIPPET_WINDOW)
                end = min(len(content), pos + SNIPPET_WINDOW)
                snippets.append(content[start:end].strip())
            
            context_text = "\n\n... [kəsik] ...\n\n".join(snippets) if snippets else content[:FULL_TEXT_CHAR_LIMIT]
            
            results.append({
                "path": filepath,
                "filename": filename,
                "score": round(score, 3),
                "context": context_text,
                "is_full_text": False
            })
            
    cursor.close()
    conn.close()
    return results