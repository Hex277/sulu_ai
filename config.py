"""
config.py
---------
Layihənin bütün konfiqurasiya parametrlərini mərkəzləşdirən modul.
Bütün digər modullar parametrləri bu fayldan idxal etməlidir ki,
gələcəkdə (Flask/FastAPI inteqrasiyasında) tək yerdən idarə oluna bilsin.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# ----------------------------------------------------------------------
# VERİLƏNLƏR BAZASI (POSTGRESQL)
# ----------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")  # Supabase hostunu .env-dən çəkə bilərsən
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sulu_db")
DB_USER = os.getenv("DB_USER", "sulu_admin")
DB_PASS = os.getenv("DB_PASS", "123")

def get_db_connection():
    """Postgres bazasına yeni qoşulma yaradır."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        cursor_factory=RealDictCursor
    )
# .env faylını yüklə (OPENAI_API_KEY və s. üçün)
load_dotenv()

# ----------------------------------------------------------------------
# YOLLAR (PATHS)
# ----------------------------------------------------------------------
# Layihənin kök qovluğu (bu faylın yerləşdiyi qovluq)
BASE_DIR = Path(__file__).resolve().parent

# Sənədlərin oxunacağı YEGANƏ qovluq. Sistem bundan kənara ƏSLA çıxmamalıdır.
DATA_DIR = BASE_DIR / "data"

# Lazımı qovluqları avtomatik yarat (yoxdursa)
DATA_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------
# OPENAI API
# ----------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Sorğu optimizasiyası üçün sürətli/ucuz model
OPTIMIZER_MODEL = os.getenv("OPTIMIZER_MODEL", "gpt-4o-mini")

# Əsas cavab generasiyası üçün model
MAIN_MODEL = os.getenv("MAIN_MODEL", "gpt-4o")

# ----------------------------------------------------------------------
# DƏSTƏKLƏNƏN FAYL FORMATLARI
# ----------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".txt", ".json", ".docx", ".xlsx", ".csv", ".pdf"}

# ----------------------------------------------------------------------
# AZƏRBAYCAN DİLİ ÜÇÜN STOP-WORD SİYAHISI
# ----------------------------------------------------------------------
AZ_STOPWORDS = {
    "və", "ki", "bu", "bir", "olan", "üçün", "ilə", "də", "da",
    "nə", "necə", "hansı", "haqqında", "amma", "lakin", "ya", "isə",
    "ən", "çox", "az", "kimi", "görə", "sonra", "əvvəl", "indi", "hər",
    "bütün", "deyil", "var", "yox", "olur", "oldu", "edir", "etdi",
}

# ----------------------------------------------------------------------
# BM25 AXTARIŞ PARAMETRLƏRİ
# ----------------------------------------------------------------------
# Axtarışda nəzərə alınacaq maksimal nəticə (fayl) sayı
TOP_K_RESULTS = 5

# ----------------------------------------------------------------------
# KONTEKST ÇIXARMA (SNIPPET) PARAMETRLƏRİ
# ----------------------------------------------------------------------
# Faylın TAM mətninin göndərilməsi üçün maksimal simvol limiti.
# Bundan kiçik fayllar tam, böyük fayllar isə "snippet" şəklində göndərilir.
FULL_TEXT_CHAR_LIMIT = 3000

# Snippet çıxarılarkən, tapılan açar sözün ətrafından nə qədər simvol götürülsün
SNIPPET_WINDOW = 250

# Bir fayldan çıxarılacaq maksimal snippet sayı (çox təkrarlanan sözlər üçün limit)
MAX_SNIPPETS_PER_FILE = 6

# ----------------------------------------------------------------------
# PROMPT / TOKEN LİMİTLƏRİ
# ----------------------------------------------------------------------
# AI-a göndəriləcək YEKUN promptun (kontekst + sual) maksimal simvol sayı.
# Bu limit aşıldıqda, ən az uyğun (relevansı aşağı) sənədlərdən kəsilməyə başlanır.
MAX_PROMPT_CHARS = 12000

# ----------------------------------------------------------------------
# DEBUG / LOG PARAMETRLƏRİ
# ----------------------------------------------------------------------
# True olduqda, debug_logs terminalda da oxunaqlı formada çap olunur.
VERBOSE_LOGGING = True