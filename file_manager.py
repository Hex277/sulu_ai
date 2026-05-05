import os
import json
import pandas as pd
from config import DATA_DIR, CURRENT_AI_MODE

# Word fayllarını oxumaq üçün kitabxananı yoxlayırıq
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def get_file_list() -> list:
    """Data qovluğundakı bütün faylların adlarını qaytarır."""
    if not os.path.exists(DATA_DIR):
        return []
    return os.listdir(DATA_DIR)

def read_file_content(filename: str) -> str:
    """Seçilmiş faylın məzmununu oxuyur və AI-ın növünə uyğun mətnə çevirir."""
    file_path = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(file_path):
        return "Fayl tapılmadı."

    try:
        # 1. EXCEL FAYLLARI (.xlsx, .xls)
        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path).fillna('')
            if CURRENT_AI_MODE == "openai":
                # OpenAI üçün ən dəqiq format: JSON records (Sətir-sətir məlumat)
                return df.to_json(orient="records", force_ascii=False)
            else:
                # Local AI üçün ənənəvi cədvəl görünüşü
                return df.to_string(index=False)

        # 2. CSV FAYLLARI (.csv)
        elif filename.endswith('.csv'):
            df = pd.read_csv(file_path).fillna('')
            if CURRENT_AI_MODE == "openai":
                return df.to_json(orient="records", force_ascii=False)
            else:
                return df.to_string(index=False)

        # 3. WORD FAYLLARI (.docx)
        elif filename.endswith('.docx'):
            if not DOCX_AVAILABLE:
                return "XƏTA: Word fayllarını oxumaq üçün terminalda 'pip install python-docx' işlədin."
            
            doc = docx.Document(file_path)
            # Yalnız boş olmayan abzasları götürürük
            text = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
            
            if CURRENT_AI_MODE == "openai":
                # OpenAI üçün kontekst sərhədlərini dəqiqləşdiririk
                return f"[SƏNƏD BAŞLANĞICI]\n{text}\n[SƏNƏD SONU]"
            else:
                return text

        # 4. JSON FAYLLARI (.json)
        elif filename.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if CURRENT_AI_MODE == "openai":
                    # Tokenə qənaət etmək üçün sıxlaşdırılmış (indent=None) format
                    return json.dumps(data, ensure_ascii=False)
                else:
                    # Local AI boşluqları oxumağı sevir
                    return json.dumps(data, ensure_ascii=False, indent=2)

        # 5. MARKDOWN VƏ DİGƏR MƏTN FAYLLARI (.md, .txt)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

    except Exception as e:
        return f"Xəta baş verdi ({filename}): {str(e)}"