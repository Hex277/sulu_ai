# search_anytxt.py
import os
import time
import requests
from search_config import ANYTXT_URL, ANYTXT_DELAY, ANYTXT_STOP_WORDS, SIZE_LIMIT_BYTES
from search_utils import normalize_text, _get_mod_date, _get_full_content, _get_sibling_files

_anytxt_cache: dict = {}

def anytxt_rpc_call(method: str, params: dict) -> dict:
    payload = {
        "id": 1,
        "jsonrpc": "2.0",
        "method": method,
        "params": {"input": params}
    }
    try:
        response = requests.post(ANYTXT_URL, json=payload, timeout=5)
        if response.status_code == 200:
            res_json = response.json()
            data_obj = res_json.get("result", {}).get("data", {})
            return data_obj.get("output", {})
    except Exception as e:
        print(f"   ⚠️ AnyTXT RPC xətası: {e}")
    return {}

def process_word(word: str) -> dict:
    if word in _anytxt_cache:
        return _anytxt_cache[word]

    output = anytxt_rpc_call("ATRpcServer.Searcher.V1.GetResult", {"pattern": word, "filterDir": "", "filterExt": "*", "limit": "100", "offset": 0, "order": 0})    
    files_list = output.get("files", [])
    word_results = {}

    for f_data in files_list:
        try:
            fid       = f_data[0]
            full_path = f_data[3]
            
            # --- 1. DESKTOP SÜZGƏCİ ---
            # Faylın yolunda '\desktop\' və ya '/desktop/' yoxdursa, onu dərhal ötürürük
            if "\\desktop\\" not in full_path.lower() and "/desktop/" not in full_path.lower():
                continue
                
            f_name    = os.path.basename(full_path)

            # --- 2. DDOS QORUMASI (0.15 saniyəlik gecikmə) ---
            # AnyTXT RPC serverinə ard-arda çox sürətli sorğu getməsinin qarşısını alır
            time.sleep(0.15)

            frag_output = anytxt_rpc_call("ATRpcServer.Searcher.V1.GetFragment", {"fid": fid, "pattern": word})
            snippet = frag_output.get("text") or "Məlumat tapıldı."

            full_content = _get_full_content(full_path)
            if full_content is not None:
                size_kb = os.path.getsize(full_path) / 1024
                print(f"      📄 '{f_name}' kiçikdir ({size_kb:.1f} KB) → tam mətn oxundu.")
            else:
                print(f"      📦 '{f_name}' böyükdür (>{SIZE_LIMIT_BYTES//1024} KB) → yalnız snippet.")

            mod_date = _get_mod_date(full_path)
            siblings = _get_sibling_files(full_path)

            word_results[f_name] = {
                "snippet"       : snippet,
                "full_content"  : full_content,
                "mod_date"      : mod_date,
                "path"          : full_path,
                "sibling_files" : siblings
            }
        except Exception as e:
            continue

    _anytxt_cache[word] = word_results
    return word_results

def _filter_query_words(query: str) -> list:
    norm = normalize_text(query)
    seen = set()
    filtered = []
    for w in norm.split():
        if w in ANYTXT_STOP_WORDS or len(w) < 3 or w in seen:
            continue
        seen.add(w)
        filtered.append(w)
    return filtered

def anytxt_search(query: str) -> dict:
    words = _filter_query_words(query)
    if not words: return {}

    final_results = {}
    for i, word in enumerate(words):
        if i > 0: time.sleep(ANYTXT_DELAY)
        word_results = process_word(word)

        for f_name, data in word_results.items():
            if f_name not in final_results:
                final_results[f_name] = {
                    "snippets"      : [],
                    "full_content"  : data["full_content"],
                    "mod_date"      : data["mod_date"],
                    "path"          : data["path"],
                    "sibling_files" : data["sibling_files"]
                }
            if data["snippet"] not in final_results[f_name]["snippets"]:
                final_results[f_name]["snippets"].append(data["snippet"])
            if final_results[f_name]["full_content"] is None and data["full_content"]:
                final_results[f_name]["full_content"] = data["full_content"]

    return final_results

def clear_anytxt_cache():
    global _anytxt_cache
    _anytxt_cache = {}

# Legacy funksiyalar (digər fayllar istifadə edirsə qorunur)
def fetch_word_score(word, url): pass
def fetch_from_anytxt(word): pass