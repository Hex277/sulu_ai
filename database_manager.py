import psycopg2
from config import get_db_connection

def save_document_to_db(doc_data, clean_content):
    """Sənədi bazaya yazır və ya yeniləyir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
        clean_content
    ))
    
    conn.commit()
    cursor.close()
    conn.close()

def delete_missing_files(local_files_list):
    """Bazada olub, qovluqda olmayan faylları silir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Bazadakı siyahını al və olmayanları sil
    cursor.execute("DELETE FROM documents WHERE filepath NOT IN %s", (tuple(local_files_list),))
    
    conn.commit()
    cursor.close()
    conn.close()