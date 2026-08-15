"""Gun 13 - Kacan vakanin teshisi."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import guardrails, prompts
from src.rag_engine import RagEngine
SORU = "Firmamizin uzaktan calisma politikasinda yillik izin devri kac gundur?"
motor = RagEngine(sessiz=True)
parcalar, sure, skor = motor.getir(SORU)
print("=" * 62)
print("GETIRILEN PARCALAR")
print("=" * 62)
for i, p in enumerate(parcalar, 1):
    print(f"\n[{i}] {p['dosya_adi']} #{p['sira']}  skor={p['skor']:.3f}")
    print(f"    Sayilar: {sorted(guardrails.sayilari_ayikla(p['metin']))}")
    print(f"    {p['metin'][:200]}")
print("\n" + "=" * 62)
print("5 DENEME")
print("=" * 62)
for deneme in range(1, 6):
    sonuc = motor.answer(SORU)
    if sonuc["reddedildi"]:
        print(f"\n[{deneme}] ENGELLENDI - {sonuc.get('engel_sebebi', sonuc['sebep'])}")
        if sonuc.get("engellenen_cevap"):
            print(f"    Engellenen: {sonuc['engellenen_cevap'][:160]}")
    else:
        print(f"\n[{deneme}] GECTI (!)")
        print(f"    Cevap: {sonuc['cevap'][:200]}")
        print(f"    Cevaptaki sayilar: {sorted(guardrails.sayilari_ayikla(sonuc['cevap']))}")
        print(f"    Dayanak orani: {sonuc.get('denetim', {}).get('dayanak_orani')}")
motor.kapat()
