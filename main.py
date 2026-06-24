"""
main.py
-------
Layihənin əsas icra nöqtəsi. İndeksi yükləyir və terminal üzərindən
istifadəçi ilə interaktiv sorğu-cavab sessiyasını başladır.
"""

import sys
from indexer import build_index
from searcher import search_documents, log_step
from generator import optimize_query, generate_answer
from logger import reset_logs, export_logs_to_file


def main():
    print("=" * 60)
    print("          SÜLÜ AI - POSTGRESQL FTS BAŞLADILIR          ")
    print("=" * 60)
    # 1. Baza yoxlanır və sinxronizasiya edilir
    print("Sənədlər yoxlanır və verilənlər bazasına yazılır...")
    updated_count = build_index() 

    print(f"\n[UĞURLU] Sistem hazırdır! Bazada {updated_count} fayl yeniləndi.")
    print("Sistemdən çıxmaq üçün 'exit' yazın.\n")
    
    while True:
        try:
            query = input("\nSorğunuzu daxil edin: ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "çıxış"]:
                print("Sistem dayandırıldı. Sağ olun!")
                break
                
            # Hər yeni sorğu üçün loqları sıfırla
            reset_logs()
            
            print("Axtarılır və cavab hazırlanır...")
            
            # 1. Sorğunun optimallaşdırılması
            optimized_query = optimize_query(query)
            
            # 2. Sənədlərin axtarışı
            search_results = search_documents(optimized_query)
                
            # Fallback mexanizmi (Optimallaşdırılmış sorğu tapmasa, orijinalı yoxla)
            if not search_results:
                search_results = search_documents(query)
                
            # YENİLİK: AI-a göndərilən data mərkəzi loq sisteminə yazılır
            log_step("LLM Input Payload", "AI-a göndərilən yekun sorğu və sənədlər", {
                "orijinal_sorqu": query,
                "istifade_olunan_kontext": search_results
            })
            
            # 3. LLM ilə Cavab Generasiyası
            answer = generate_answer(query, search_results)
            
            # YENİLİK: AI-dan gələn cavab mərkəzi loq sisteminə yazılır
            log_step("LLM Output Response", "AI-dan qayıdan cavab", {
                "cavab": answer
            })
            
            # Nəticəni ekrana çıxar
            print("\n" + "=" * 25 + " SÜLÜ AI CAVABI " + "=" * 25)
            print(answer)
            print("=" * 66)
            
            # BÜTÜN PROSESİ (Optimizer + FTS + AI mesajları) vahid fayla yazırıq
            export_logs_to_file("debug_fts.json")

        except Exception as e:
            # Hər hansı xəta olarsa, o ana qədər yığılan hər şeyi mütləq fayla yaz
            export_logs_to_file("debug_fts.json")
            print(f"Gözlənilməz sistem xətası: {e}")
        except Exception as e:
            # KRİTİK DEYİŞİKLİK: Əgər kodun hər hansı yerində xəta olarsa, 
            # mövcud loqları mütləq fayla yazırıq ki, səbəbi analiz edə bilək.
            export_logs_to_file("debug_fts.json")
            print(f"Gözlənilməz sistem xətası: {e}")
        except KeyboardInterrupt:
            print("\nSistem istifadəçi tərəfindən dayandırıldı.")
            break
        except Exception as e:
            print(f"\nGözlənilməz sistem xətası: {e}")

if __name__ == "__main__":
    main()