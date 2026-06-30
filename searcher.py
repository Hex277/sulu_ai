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
    # Orijinal təmizlənmiş sorğu
    cleaned_query = az_lower(query.strip())
    
    stopwords = {
        "yaz", "tap", "goster", "göstər", "olan", "haqqinda", "haqqında", "haqda",
        "barede", "barədə", "fayli", "faylı", "daxili", "daxilinde", "daxilində", 
        "daxilindəki", "ve", "və", "ile", "ilə", "edir", "eden", "edən", 
        "kimdir", "nedir", "nədir", "siyahisini", "siyahısını", "melumati", "məlumatı",
        "melumat", "məlumat", "ver", "bax", "siyahı", "siyahisi"
    }
    
    raw_tokens = tokenize(cleaned_query)
    filtered_tokens = [w for w in raw_tokens if w not in stopwords]
    
    if not filtered_tokens:
        filtered_tokens = raw_tokens
        
    # --- 🌟 DUAL SİMVOL GENİŞLƏNDİRİLMƏSİ ---
    # Həm orijinal sözü, həm də onun ingilis variantını sorğuya əlavə edirik.
    # Məsələn: ['müəllim'] -> ['müəllim', 'muellim']
    expanded_tokens = []
    for token in filtered_tokens:
        expanded_tokens.append(token)
        normalized = normalize_aze_text(token)
        if normalized != token:
            expanded_tokens.append(normalized)
            
    # Postgres plainto_tsquery üçün düz mətn formatına salırıq
    final_search_text = " ".join(expanded_tokens)
    
    if not final_search_text.strip():
        return []

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # plainto_tsquery həm fayl adındakı 'muellim'-i, həm də daxildəki 'elvin'-i tapacaq.
    cursor.execute("""
        SELECT filepath, filename, content, 
               ts_rank(search_vector, plainto_tsquery('simple', %s)) AS score
        FROM documents
        WHERE search_vector @@ plainto_tsquery('simple', %s)
        ORDER BY score DESC
        LIMIT %s;
    """, (final_search_text, final_search_text, TOP_K_RESULTS))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        if isinstance(row, dict):
            filepath = row.get("filepath")
            filename = row.get("filename")
            content = row.get("content", "")
            score = row.get("score", 0.0)
        else:
            filepath, filename, content, score = row
            
        if len(content) <= FULL_TEXT_CHAR_LIMIT:
            context_text = content
            is_full = True
        else:
            is_full = False
            snippets = []
            lower_content = az_lower(content)
            
            found_positions = []
            # Snippet çıxararkən həm orijinal, həm də normallaşdırılmış sözləri mətndə axtarırıq
            for token in expanded_tokens:
                for m in re.finditer(re.escape(token), lower_content):
                    found_positions.append(m.start())
                # Əlavə olaraq mətndə ingiliscə yazılıbsa onu da tutmaq üçün:
                for m in re.finditer(re.escape(normalize_aze_text(token)), lower_content):
                    found_positions.append(m.start())
            
            found_positions = sorted(list(set(found_positions)))
            
            for pos in found_positions[:MAX_SNIPPETS_PER_FILE]:
                start = max(0, pos - SNIPPET_WINDOW)
                end = min(len(content), pos + SNIPPET_WINDOW)
                snippets.append(content[start:end].strip())
            
            if not snippets:
                context_text = content[:FULL_TEXT_CHAR_LIMIT]
            else:
                context_text = "\n\n... [kəsik] ...\n\n".join(snippets)
        
        results.append({
            "path": filepath,
            "filename": filename,
            "score": round(score, 3),
            "context": context_text,
            "is_full_text": is_full
        })
        
    log_step("Postgres FTS Search", "Tapılan sənədlər", results)
    return results