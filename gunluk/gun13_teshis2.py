"""TX-4400 vakasi teshisi."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import guardrails
from src.rag_engine import RagEngine
SORU = "TX-4400 endustriyel kurutucunun tavsiye edilen bakim araligi kac saattir?"
motor = RagEngine(sessiz=True)
parcalar, sure, skor = motor.getir(SORU)
print("GETIRILEN PARCALAR")
print("=" * 62)
for i, p in enumerate(parcalar, 1):
    print(f"\n[{i}] {p['dosya_adi']} #{p['sira']}  skor={p['skor']:.3f}")
    print(f"    Kodlar: {sorted(guardrails.kodlari_ayikla(p['metin']))}")
    print(f"    {p['metin'][:180]}")
print("\n\n5 DENEME")
print("=" * 62)
for d in range(1, 6):
    s = motor.answer(SORU)
    if s["reddedildi"]:
        print(f"\n[{d}] ENGELLENDI - {s.get('engel_sebebi', s['sebep'])}")
    else:
        print(f"\n[{d}] GECTI (!)")
        print(f"    Cevap: {s['cevap'][:200]}")
        print(f"    Cevaptaki kodlar: {sorted(guardrails.kodlari_ayikla(s['cevap']))}")
        print(f"    Dayanak: {s.get('denetim', {}).get('dayanak_orani')}")
motor.kapat()
