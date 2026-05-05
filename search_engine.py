import re
import os
import pandas as pd
import json
from file_manager import DATA_DIR 


def normalize_text(text: str) -> str:
    """Azərbaycan hərflərini latın ekvivalentlərinə çevirir və kiçik hərflə yazır."""
    chars = {'ə': 'e', 'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
             'Ə': 'e', 'Ç': 'c', 'Ğ': 'g', 'I': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'}
    text = text.lower()
    for az, en in chars.items():
        text = text.replace(az, en)
    return re.sub(r'[^a-z0-9\s]', ' ', text)


def python_lexical_search(user_query, available_files, db_synonyms):
    norm_query = normalize_text(user_query)
    query_words = norm_query.split()
    
    stop_words = {
        'ver', 'verin', 'goster', 'tap', 'mene', 'haqqinda', 
        'siyahisi', 'listini', 'melumat', 'yaz', 'etrafli', 'indi'
    }
    extensions = {'xlsx', 'xls', 'json', 'txt', 'csv'}
    
    results = {}

    for file_name in available_files:
        norm_file_full = normalize_text(file_name)
        file_parts = set(norm_file_full.split()) - extensions
        
        score = 0
        for word in query_words:
            if word in stop_words or len(word) < 2:
                continue 
            
            # 1. BİRBASA UYGUNLUQ
            if word in file_parts:
                score += 25 

            # 2. SİNONİM UYGUNLUQU
            for group in db_synonyms:
                norm_group = [normalize_text(s) for s in group]
                if word in norm_group:
                    if any(syn in file_parts for syn in norm_group):
                        score += 15
            
            # 3. QİSMİ UYGUNLUQ
            if any(word in part or part in word for part in file_parts):
                if score == 0:
                    score += 5

        if score > 0:
            results[file_name] = score

    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


def deep_content_search(query, candidate_files, limit=10, row_limit=20):
    """
    Faylların məzmununda axtarış aparır.
    FIX: İndi həm orijinal sorğu həm də normalize edilmiş versiya ilə axtarır,
    beləliklə Azərbaycan hərfli məlumatlar da tapılır.
    """
    results = {}
    file_count = 0
    
    # Həm orijinal həm normalize versiya ilə axtarış
    query_original = str(query).lower().strip()
    query_normalized = normalize_text(query).strip()
    
    # Hər iki versiya üçün axtarış sözlərini hazırlayırıq
    # Normalize versiyadan qısa sözləri (2 simvoldan az) çıxarırıq
    search_terms = list({query_original, query_normalized})
    # Əgər sorğu çox sözlüdürsə, hər sözü ayrıca da axtarırıq
    individual_words = [w for w in query_normalized.split() if len(w) >= 2]
    
    for file_name in candidate_files[:limit]:
        file_path = os.path.join(DATA_DIR, file_name)
        if not os.path.exists(file_path):
            continue
            
        found_rows = []
        
        def row_matches(row_str: str) -> bool:
            """Sətirin hər hansı axtarış termini ilə uyğun olub-olmadığını yoxlayır."""
            row_norm = normalize_text(row_str)
            row_lower = row_str.lower()
            # Tam sorğu uyğunluğu
            for term in search_terms:
                if term and term in row_lower:
                    return True
                if term and term in row_norm:
                    return True
            # Fərdi söz uyğunluğu (bütün sözlər tapılmalıdır)
            if individual_words:
                if all(w in row_norm for w in individual_words):
                    return True
            return False
        
        try:
            # --- EXCEL ---
            if file_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
                mask = df.apply(
                    lambda row: row_matches(row.astype(str).str.cat(sep=' ')),
                    axis=1
                )
                relevant_df = df[mask]
                if not relevant_df.empty:
                    found_rows = relevant_df.head(row_limit).to_dict(orient='records')

            # --- JSON ---
            elif file_name.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if row_matches(str(item)):
                                found_rows.append(item)
                                if len(found_rows) >= row_limit:
                                    break

            # --- TXT ---
            elif file_name.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if row_matches(line):
                            found_rows.append(line.strip())
                            if len(found_rows) >= row_limit:
                                break

            if found_rows:
                results[file_name] = found_rows
                file_count += 1
                if file_count >= 3:
                    break
                
        except Exception as e:
            print(f"⚠️ '{file_name}' daxili dərin axtarış xətası: {e}")
            
    return results