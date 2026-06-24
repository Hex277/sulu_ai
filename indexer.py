"""
indexer.py
----------
PostgreSQL üzərində ağıllı sənəd indeksasiyası (Smart Sync).
Yalnız yeni və dəyişən faylları indeksləyir, silinənləri bazadan təmizləyir.
"""

import psycopg2
from pathlib import Path
from config import DATA_DIR, get_db_connection
from file_parser import load_single_document, _is_safe_path
from logger import log_step

def az_lower(text: str) -> str:
    """Azərbaycan hərflərini nəzərə alan lower-case funksiyası"""
    mapping = {'I': 'ı', 'İ': 'i', 'Ğ': 'ğ', 'Ü': 'ü', 'Ş': 'ş', 'Ö': 'ö', 'Ç': 'ç'}
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text.lower()

def tokenize(text: str) -> list[str]:
    """Mətni sözlərə parçalayır və təmizləyir"""
    text = az_lower(text)
    words = []
    for w in text.split():
        cleaned = "".join([c for c in w if c.isalnum()])
        if cleaned:
            words.append(cleaned)
    return words

def init_db():
    """Baza cədvəlini yaradır və mtime sütununu əlavə edir"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            filepath TEXT UNIQUE,
            filename TEXT,
            content TEXT,
            mtime DOUBLE PRECISION,
            search_vector tsvector
        );
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_search_vector 
        ON documents USING gin(search_vector);
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

def get_indexed_metadata() -> dict:
    """Bazada hal-hazırda mövcud olan faylların mtime məlumatlarını təhlükəsiz çəkir"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT filepath, mtime FROM documents;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # FIX: Həm DictCursor, həm də Tuple Cursor dəstəyi (Xətanın qarşısını alır)
    metadata = {}
    for row in rows:
        if isinstance(row, dict):
            metadata[row['filepath']] = row['mtime']
        else:
            metadata[row[0]] = row[1]
    return metadata



def build_index(force: bool = True):  # Force default olaraq True edildi
    """Ağıllı sinxronizasiya mühərriki (Məcburi yeniləmə dəstəyi ilə)"""
    init_db()
    
    db_metadata = get_indexed_metadata() if not force else {} # Əgər force-dursa, keşi sıfırla
    local_files = []
    updated_count = 0
    deleted_count = 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for path in sorted(DATA_DIR.rglob("*")):
        if not path.is_file() or not _is_safe_path(path):
            continue
            
        filepath_rel = str(path.relative_to(DATA_DIR))
        local_files.append(filepath_rel)
        
        local_mtime = path.stat().st_mtime
        db_mtime = db_metadata.get(filepath_rel)
        
        # Force True olduqda və ya fayl yeniləndikdə indekslə
        if force or db_mtime is None or local_mtime > db_mtime:
            doc_data = load_single_document(path)
            if doc_data:
                # Fayl adını (uzantısız) və kontentini tam birləşdiririk
                clean_filename = path.stem.replace("_", " ").replace("-", " ")
                full_text_to_index = f"{clean_filename} {doc_data['filename']} {doc_data['content']}"
                
                clean_tokens = tokenize(full_text_to_index)
                clean_content_for_fts = " ".join(clean_tokens)

                cursor.execute("""
                    INSERT INTO documents (filepath, filename, content, mtime, search_vector)
                    VALUES (%s, %s, %s, %s, to_tsvector('simple', %s))
                    ON CONFLICT (filepath) 
                    DO UPDATE SET 
                        content = EXCLUDED.content,
                        mtime = EXCLUDED.mtime,
                        search_vector = EXCLUDED.search_vector;
                """, (
                    doc_data["path"], 
                    doc_data["filename"], 
                    doc_data["content"], 
                    doc_data["mtime"], 
                    clean_content_for_fts
                ))
                updated_count += 1
                
    # Əgər force deyilsə, silinenleri təmizlə
    if not force:
        for db_file in db_metadata.keys():
            if db_file not in local_files:
                cursor.execute("DELETE FROM documents WHERE filepath = %s;", (db_file,))
                deleted_count += 1
            
    conn.commit()
    cursor.close()
    conn.close()
    
    log_step("Indexer", "Məcburi İndeksasiya", f"{updated_count} sənəd sıfırdan indeksləndi.")
    return updated_count