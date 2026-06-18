# search_local.py
import os
import json
import pandas as pd
from file_manager import DATA_DIR
from search_config import LEXICAL_STOP_WORDS
from search_utils import normalize_text

def python_lexical_search(user_query: str, available_files: list, db_synonyms: list):
    """Fayl adları üzərindən leksikal + sinonim axtarışı aparır."""
    logs = []
    norm_query  = normalize_text(user_query)
    query_words = norm_query.split()
    extensions  = {'xlsx', 'xls', 'json', 'txt', 'csv'}
    results     = {}

    for file_name in available_files:
        norm_file_full = normalize_text(file_name)
        file_parts     = set(norm_file_full.split()) - extensions
        score          = 0

        for word in query_words:
            if word in LEXICAL_STOP_WORDS or len(word) < 2:
                continue

            if word in file_parts:
                score += 25
                logs.append({"type": "info", "label": "Leksikal", "msg": f"'{file_name}' -> '{word}' birbaşa tapıldı (+25 bal)"})

            for group in db_synonyms:
                norm_group = [normalize_text(s) for s in group]
                if word in norm_group:
                    for syn in norm_group:
                        if syn in file_parts:
                            score += 15
                            logs.append({"type": "info", "label": "Sinonim", "msg": f"'{file_name}' -> '{syn}' sinonimi tapıldı (+15 bal)"})

            if score == 0 and any(word in part or part in word for part in file_parts):
                score += 5
                logs.append({"type": "info", "label": "Qismi", "msg": f"'{file_name}' -> '{word}' qismən uyğun gəldi (+5 bal)"})

        if score > 0:
            results[file_name] = score

    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    return sorted_results, logs

def deep_content_search(query: str, candidate_files: list, limit: int = 10, row_limit: int = 20) -> dict:
    """Faylların məzmununda axtarış aparır (Excel, JSON, TXT)."""
    query_original    = str(query).lower().strip()
    query_normalized  = normalize_text(query).strip()
    search_terms      = list({query_original, query_normalized})
    individual_words  = [w for w in query_normalized.split() if len(w) >= 2 and w not in LEXICAL_STOP_WORDS]

    def row_matches(row_str: str) -> bool:
        row_norm  = normalize_text(row_str)
        row_lower = row_str.lower()
        for term in search_terms:
            if term and (term in row_lower or term in row_norm):
                return True
        if len(individual_words) > 1 and all(w in row_norm for w in individual_words):
            return True
        return False

    results    = {}
    file_count = 0

    for file_name in candidate_files[:limit]:
        file_path = os.path.join(DATA_DIR, file_name)
        if not os.path.exists(file_path):
            continue

        found_rows = []
        try:
            if file_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
                mask = df.apply(lambda row: row_matches(row.astype(str).str.cat(sep=' ')), axis=1)
                relevant_df = df[mask]
                if not relevant_df.empty:
                    found_rows = relevant_df.head(row_limit).to_dict(orient='records')

            elif file_name.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if row_matches(str(item)):
                                found_rows.append(item)
                                if len(found_rows) >= row_limit:
                                    break

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
            print(f"   ⚠️ '{file_name}' dərin axtarış xətası: {e}")

    return results