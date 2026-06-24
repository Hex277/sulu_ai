"""
logger.py
---------
Sistemin bütün mərhələlərində toplanan debug məlumatlarını mərkəzi
bir siyahıda (debug_logs) saxlayan modul.

Gələcəkdə bu modul frontend-ə (veb-saytın admin/debug panelinə) JSON
formatında ötürülmək üçün hazır struktur təqdim edir:

    {"step": "...", "label": "...", "data": ...}

Hələlik terminalda oxunaqlı formada çap edir, amma strukturu dəyişdirmədən
sadəcə bu siyahını API cavabı kimi qaytarmaq kifayət edəcək.
"""

import json
from datetime import datetime

from config import VERBOSE_LOGGING

# Bütün sessiyanın debug məlumatlarını saxlayan mərkəzi siyahı.
# main.py hər sorğu əvvəli bunu sıfırlaya bilər (reset_logs()).
debug_logs = []


def log_step(step: str, label: str, data) -> None:
    entry = {
        "step": step,
        "label": label,
        "data": data,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    debug_logs.append(entry)



def _print_pretty(entry: dict) -> None:
    """Terminalda oxunaqlı formada çap edir (yalnız debug məqsədilə)."""
    print(f"\n[{entry['step']}] {entry['label']}")
    data = entry["data"]
    if isinstance(data, (dict, list)):
        try:
            print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])
        except TypeError:
            print(str(data)[:1500])
    else:
        text = str(data)
        # Çox uzun mətnləri terminalda qısaldırıq (loga tam yazılır, çapı qısa)
        print(text[:1500] + ("..." if len(text) > 1500 else ""))


def reset_logs() -> None:
    """Yeni sorğu üçün log siyahısını sıfırlayır."""
    debug_logs.clear()


def export_logs_to_file(path: str = "last_run_debug.json") -> None:
    """
    Cari debug_logs siyahısını JSON faylına yazır.
    Gələcəkdə bunun yerinə birbaşa API endpoint-i debug_logs-u
    return edəcək, amma hələlik fayl şəklində saxlamaq faydalıdır.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(debug_logs, f, ensure_ascii=False, indent=2)