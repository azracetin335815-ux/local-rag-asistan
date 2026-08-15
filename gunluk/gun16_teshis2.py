import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import guardrails, prompts
from src.rag_engine import RagEngine
SORULAR = [
    "Filtre nasil temizlenir?",
    "Teknik destek hangi saatlerde calisir?",
    "Garanti suresi 36 ay mi?",
    "Uzaktan calisma haftada 5 gun yapilabiliyor degil mi?",
]
motor = RagEngine(sessiz=True)
for soru in SORULAR:
    print("=" * 66)
    print("SORU:", soru)
    parcalar, sure, skor = motor.getir(soru)
    print(f"skor={skor:.3f}  parca={len(parcalar)}")
    for p in parcalar:
        print(f"  [{p['skor']:.3f}] {p['dosya_adi']}#{p['sira']}: {p['metin'][:90]}")
    s = motor.answer(soru)
    if s["reddedildi"]:
        print("ENGELLENDI:", s.get("engel_sebebi") or s.get("sebep"))
        ec = s.get("engellenen_cevap")
        if ec:
            print("Model cevabi:", ec[:180])
            baglam = prompts.baglam_bicimlendir(parcalar)
            print("  dayanak_orani:", guardrails.dayanak_orani(ec, baglam))
            print("  uydurma_sayilar:", guardrails.uydurma_sayilar(ec, baglam + " " + soru))
    else:
        print("CEVAPLANDI:", s["cevap"][:150])
    print()
motor.kapat()
