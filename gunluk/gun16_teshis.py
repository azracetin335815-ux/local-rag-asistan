import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag_engine import RagEngine
for SORU in ["Filtre nasil temizlenir?", "Iade suresi ne kadardir?"]:
    motor = RagEngine(sessiz=True) if 'motor' not in dir() else motor
    print("=" * 62)
    print("SORU:", SORU)
    parcalar, sure, skor = motor.getir(SORU)
    print(f"En yuksek skor: {skor:.3f}  |  Getirilen parca: {len(parcalar)}")
    for p in parcalar:
        print(f"  [{p['skor']:.3f}] {p['dosya_adi']}#{p['sira']}: {p['metin'][:110]}")
    s = motor.answer(SORU)
    print("SONUC:", "REDDEDILDI" if s["reddedildi"] else "CEVAPLANDI")
    print("Sebep:", s.get("engel_sebebi") or s.get("sebep"))
    if s.get("engellenen_cevap"):
        print("Engellenen cevap:", s["engellenen_cevap"][:180])
    print()
motor.kapat()
