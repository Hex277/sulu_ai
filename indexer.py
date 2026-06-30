"""
indexer.py
----------
PostgreSQL üzərində ağıllı sənəd indeksasiyası (Smart Sync).
SQL əməliyyatları database_manager.py vasitəsilə idarə olunur.
"""

from pathlib import Path
from config import DATA_DIR, get_db_connection
from file_parser import load_single_document, _is_safe_path
from logger import log_step
from database_manager import save_document_to_db, delete_missing_files

def az_lower(text: str) -> str:
    mapping = {'I': 'ı', 'İ': 'i', 'Ğ': 'ğ', 'Ü': 'ü', 'Ş': 'ş', 'Ö': 'ö', 'Ç': 'ç'}
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text.lower()

def tokenize(text: str) -> list[str]:
    text = az_lower(text)
    words = []
    for w in text.split():
        cleaned = "".join([c for c in w if c.isalnum()])
        if cleaned:
            words.append(cleaned)
    return words

def init_db():
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
        CREATE INDEX IF NOT EXISTS idx_documents_search_vector 
        ON documents USING gin(search_vector);
    """)
    conn.commit()
    cursor.close()
    conn.close()

def get_indexed_metadata() -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT filepath, mtime FROM documents;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    metadata = {}
    for row in rows:
        if isinstance(row, dict):
            metadata[row['filepath']] = row['mtime']
        else:
            metadata[row[0]] = row[1]
    return metadata

def build_index(force: bool = False):
    init_db()
    db_metadata = get_indexed_metadata() if not force else {} 
    local_files = []
    updated_count = 0
    
    for path in sorted(DATA_DIR.rglob("*")):
        if not path.is_file() or not _is_safe_path(path):
            continue
            
        local_mtime = path.stat().st_mtime
        doc_outputs = load_single_document(path)
        if not doc_outputs:
            continue
            
        if isinstance(doc_outputs, dict):
            doc_outputs = [doc_outputs]
            
        for doc_data in doc_outputs:
            filepath_row = doc_data["path"]
            local_files.append(filepath_row)
            
            db_mtime = db_metadata.get(filepath_row)
            
            if force or db_mtime is None or local_mtime > db_mtime:
                clean_filename = doc_data["filename"].replace("_", " ").replace("-", " ")
                full_text_to_index = f"{clean_filename} {doc_data['content']}"
                
                clean_tokens = tokenize(full_text_to_index)
                clean_content_for_fts = " ".join(clean_tokens)

                # Mətn həcmini limitləyirik
                encoded_bytes = clean_content_for_fts.encode('utf-8')
                if len(encoded_bytes) > 900000:
                    clean_content_for_fts = encoded_bytes[:900000].decode('utf-8', errors='ignore')

                # SQL əməliyyatı database_manager-ə ötürüldü
                save_document_to_db(doc_data, clean_content_for_fts)
                updated_count += 1
                
    deleted_count = 0
    if not force:
        deleted_count = delete_missing_files(db_metadata, local_files)
            
    log_step("Indexer", "Ağıllı İndeksasiya", f"{updated_count} sənəd yeniləndi, {deleted_count} sənəd silindi.")
    return updated_count