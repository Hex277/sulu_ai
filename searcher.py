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

def search_documents(query: str) -> list[dict]:
    cleaned_query = az_lower(query.strip())
    tokenized_query = tokenize(cleaned_query)
    
    if not tokenized_query:
        tokenized_query = cleaned_query.split()
        
    if not tokenized_query:
        return []
        
    tokenized_query = [t for t in tokenized_query if t.strip()]
    ts_query_str = " | ".join([f"{token}:*" for token in tokenized_query])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # --- ULTRA DEBUG BLOKU START ---
    # 1. Bazadakı sənədlərin search_vector daxilində REAL olaraq hansı sözlər var?
    cursor.execute("SELECT filename, search_vector FROM documents LIMIT 2;")
    vector_samples = cursor.fetchall()
    
    debug_vectors = []
    for r in vector_samples:
        fname = r["filename"] if isinstance(r, dict) else r[0]
        s_vec = r["search_vector"] if isinstance(r, dict) else r[1]
        debug_vectors.append({"fayl": fname, "vektor_kontenti": str(s_vec)})
        
    # 2. Bizim axtardığımız ts_query_str-i Postgres necə parse edir?
    cursor.execute("SELECT to_tsquery('simple', %s)::text AS parsed_query;", (ts_query_str,))
    pq_row = cursor.fetchone()
    parsed_q_str = pq_row["parsed_query"] if isinstance(pq_row, dict) else pq_row[0]
    
    log_step("FTS Deep Inspection", "Postgres Daxili Tokenləri", {
        "bazadaki_real_vektorlar": debug_vectors,
        "postgres_gozuyle_tsquery": parsed_q_str,
        "bizim_gonderdiyimiz_raw_tsquery": ts_query_str
    })
    # --- ULTRA DEBUG BLOKU END ---
    # Əsas FTS Sorğusu
    cursor.execute("""
        SELECT filepath, filename, content, 
               ts_rank(search_vector, to_tsquery('simple', %s)) AS score
        FROM documents
        WHERE search_vector @@ to_tsquery('simple', %s)
          AND ts_rank(search_vector, to_tsquery('simple', %s)) > 0
        ORDER BY score DESC
        LIMIT %s;
    """, (ts_query_str, ts_query_str, ts_query_str, TOP_K_RESULTS))
    
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
            for token in tokenized_query:
                for m in re.finditer(re.escape(token), lower_content):
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