import os
import re
from datetime import datetime
from search_config import SIZE_LIMIT_BYTES, SIBLING_MAX
import docx
import pandas as pd
import json

def normalize_text(text: str) -> str:
    """Azərbaycan + böyük hərf variantlarını latın kiçik hərfə çevirir."""
    chars = {
        'ə': 'e', 'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ə': 'e', 'Ç': 'c', 'Ğ': 'g', 'İ': 'i', 'I': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'
    }
    text = text.lower()
    for az, en in chars.items():
        text = text.replace(az, en)
    return re.sub(r'[^a-z0-9\s]', ' ', text)

def _get_mod_date(full_path: str) -> str:
    """Faylın son dəyişdirilmə tarixini insan dilinə çevirir."""
    try:
        ts = os.path.getmtime(full_path)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "naməlum"
# search_utils.py
def _get_full_content(full_path: str) -> str | None:
    """Mərkəzi oxuyucu funksiya: faylın uzantısına görə oxuyucunu seçir."""
    if not os.path.exists(full_path):
        return None

    try:
        # Fayl ölçüsü yoxlaması
        if os.path.getsize(full_path) > 1024 * 1024: # 1MB limit
            return None

        ext = os.path.splitext(full_path)[1].lower()

        # 1. DOCX Faylları
        if ext == '.docx':
            doc = docx.Document(full_path)
            content = "\n".join([para.text for para in doc.paragraphs])
            return " ".join(content.split())

        # 2. Excel Faylları
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(full_path, sheet_name=0)
            return " ".join(df.to_string().split())

        # 3. XML və ya HTML faylları (tag-lərdən təmizlənir)
        elif ext in ('.xml', '.html'):
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # XML tag-lərini silirik
                clean = re.sub('<.*?>', '', content)
                return " ".join(clean.split())

        # 4. Standart Mətn və JSON faylları
        elif ext in ('.txt', '.json', '.csv', '.log'):
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Əgər JSON-dursa və xüsusi struktur varsa, sadələşdiririk
                if ext == '.json':
                    try:
                        data = json.loads(content)
                        content = json.dumps(data, ensure_ascii=False)
                    except: pass
                return " ".join(content.split())

        return None

    except Exception as e:
        print(f"   ⚠️ '{os.path.basename(full_path)}' oxunarkən xəta: {e}")
        return None
# search_utils.py daxilində bu funksiyanı tamamilə dəyiş:

def _get_sibling_files(full_path: str) -> list:
    """
    Faylın yerləşdiyi qovluqdakı yalnız oxunaqlı və faydalı faylların adlarını qaytarır.
    Sistem fayllarını (.ini, .lnk, .exe, .url) bloklayır.
    """
    try:
        dir_path   = os.path.dirname(full_path)
        base_name  = os.path.basename(full_path)
        all_files  = os.listdir(dir_path)
        
        # Sırf bizim oxuya biləcəyimiz faydalı uzantıların siyahısı
        ALLOWED_EXTENSIONS = {
            'txt', 'json', 'csv', 'xlsx', 'xls', 'doc', 'docx', 
            'pdf', 'md', 'py', 'js', 'html', 'css', 'xml'
        }
        
        siblings = []
        for f in all_files:
            if f == base_name:
                continue
                
            f_path = os.path.join(dir_path, f)
            if os.path.isfile(f_path):
                # Faylın uzantısını yoxlayırıq
                ext = f.split('.')[-1].lower() if '.' in f else ''
                if ext in ALLOWED_EXTENSIONS:
                    siblings.append(f)
                    
        return siblings[:SIBLING_MAX]
    except Exception:
        return []
    
def expand_search_query(user_query: str, formatted_history: str, ai_generator_func) -> str:
    """
    Tarixçəni, Azərbaycan dili şəkilçilərini (Stemming) və fərqli tarix formatlarını 
    analiz edərək AnyTXT üçün universal axtarış sorğusu yaradır.
    """
    # Canlı tarixi dinamik olaraq YYYY-MM-DD formatında alırıq (Məsələn: 2026-05-21)
    current_date = datetime.now().strftime('%Y-%m-%d')

    prompt = f"""Sən bir RAG axtarış optimallaşdırıcısan. 
İstifadəçinin cari sorğusunu, əvvəlki söhbət tarixçəsini və hazırkı canlı tarixi analiz edərək, lokal axtarış mühərrikinin (AnyTXT) doğru sənədləri tapa bilməsi üçün ən uyğun axtarış sorğusunu (Query) yarat.

HAZIRKI CANLI TARİX: {current_date}

QAYDALAR:
1. **Kontekst Bərpası:** Əgər cari sorğuda əvəzliklər ("mənim", "bunu", "o faylı", "bayaq dediyimi") varsa və tarixçədə buna dair ipucu varsa, onları real mövzularla əvəz et. Tarixçə boşdursa, bu addımı keç.
2. **Azərbaycan Dili Şəkilçiləri (Stemming):** AnyTXT dil şəkilçilərini avtomatik anlamır. Əgər sorğuda şəkilçili söz varsa (məsələn: "satışını", "mühasibatlığın"), həmin sözün kökünü və fərqli şəkilçili versiyalarını 'OR' operatoru ilə birləşdir. (Məsələn: satış OR satışı OR satışını).
3. **Ağıllı Tarix Çevrilməsi:** Əgər sorğuda sözlə və ya rəqəmlə qeyri-müəyyən tarix ("mart ayı", "3-cü ay", "bu gün", "ən son") varsa, hazırkı canlı tarixdən ({current_date}) istifadə edərək hədəf ili/ayı tap və fayl adlarında ola biləcək fərqli formatları (nöqtəli, alt xəttli, defisli, boşluqlu) 'OR' operatoru ilə generasiya et. (Məsələn: "mart" üçün: 2026-03 OR 2026_03 OR 2026.03).
4. **Çıxış Formatı:** Heç bir giriş cümləsi, izahat və ya "Axtarış sözü:" yazma. Sadəcə AnyTXT-yə birbaşa göndəriləcək təmiz axtarış ifadəsini qaytar.

ƏVVƏLKİ SÖHBƏT TARİXÇƏSİ:
{formatted_history if formatted_history.strip() else "[Tarixçə boşdur]"}

CARİ SORĞU:
{user_query}

ANYTXT ÜÇÜN OPTİMALLAŞDIRILMIŞ SORĞU:"""

    try:
        optimized_result = ai_generator_func(prompt)
        if optimized_result and len(optimized_result.strip()) > 0:
            return optimized_result.strip()
        return user_query
    except Exception as e:
        print(f"   ⚠️ Query genişləndirmə xətası: {e}")
        return user_query