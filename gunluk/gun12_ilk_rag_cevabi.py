"""
Gun 12 - RAG motorunun uctan uca testi.
Amac: Motorun cevaplanabilir ve cevaplanamaz sorulardaki davranisini,
kaynak gosterimini, sure olcumlerini ve streaming modunu dogrulamak.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag_engine import RagEngine
CEVAPLANABILIR = [
    "Bakim araligi kac saattir?",
    "Urun garantisi ne kadar surer?",
    "Yillik izin hakki kac gundur?",
    "Uzaktan calisma haftada kac gun yapilabilir?",
]
CEVAPLANAMAZ = [
    "Istanbul'un nufusu kactir?",
    "En iyi pizza tarifi nedir?",
    "Dolar kuru bugun kac lira?",
]
def baslik(metin: str) -> None:
    print("\n" + "=" * 64)
    print(f"  {metin}")
    print("=" * 64)
def sonucu_yazdir(sonuc: dict) -> None:
    """Motor ciktisini okunabilir bicimde ekrana basar."""
    print(f"\n  Soru   : {sonuc['soru']}")
    if sonuc["reddedildi"]:
        print(f"  DURUM  : REDDEDILDI ({sonuc['sebep']})")
        print(f"  Cevap  : {sonuc['cevap']}")
        print(f"  En yuksek skor: {sonuc['en_yuksek_skor']} (esigin altinda)")
    else:
        print(f"  DURUM  : CEVAPLANDI")
        print(f"  Cevap  : {sonuc['cevap'][:250]}")
        print(f"  Kaynak : {sonuc['kaynak_ozeti']}")
        print(f"  Detay  :")
        for k in sonuc["kaynaklar"]:
            print(f"           [{k['skor']}] {k['dosya_adi']} #{k['sira']}")
    s = sonuc["sureler"]
    print(f"  Sure   : getirme={s['getirme']}s, uretim={s['uretim']}s, "
          f"toplam={s['toplam']}s")
def main() -> None:
    baslik("MOTOR BASLATILIYOR")
    motor = RagEngine()
    if not motor.hazir:
        print("HATA: Bilgi tabani bos. Once 'python ingest.py' calistirin.")
        return
    # --- 1. Cevaplanabilir sorular ---
    baslik("1. CEVAPLANABILIR SORULAR")
    cevaplanan = 0
    for soru in CEVAPLANABILIR:
        sonuc = motor.answer(soru)
        sonucu_yazdir(sonuc)
        if not sonuc["reddedildi"]:
            cevaplanan += 1
    print(f"\n  Sonuc: {cevaplanan}/{len(CEVAPLANABILIR)} soru cevaplandi.")
    # --- 2. Cevaplanamaz sorular ---
    baslik("2. CEVAPLANAMAZ SORULAR")
    reddedilen = 0
    for soru in CEVAPLANAMAZ:
        sonuc = motor.answer(soru)
        sonucu_yazdir(sonuc)
        if sonuc["reddedildi"]:
            reddedilen += 1
    print(f"\n  Sonuc: {reddedilen}/{len(CEVAPLANAMAZ)} soru dogru sekilde reddedildi.")
    # --- 3. Streaming testi ---
    baslik("3. STREAMING MODU TESTI")
    soru = CEVAPLANABILIR[0]
    print(f"  Soru: {soru}\n")
    for tur, veri in motor.answer_streaming(soru):
        if tur == "kaynaklar":
            print("  Getirilen kaynaklar:")
            for k in veri:
                print(f"    [{k['skor']}] {k['dosya_adi']} #{k['sira']}")
            print("\n  Cevap: ", end="", flush=True)
        elif tur == "parca":
            print(veri, end="", flush=True)
        elif tur == "red":
            print(f"  REDDEDILDI: {veri['cevap']}")
        elif tur == "bitti":
            s = veri["sureler"]
            print(f"\n\n  [getirme={s['getirme']}s, uretim={s['uretim']}s, "
                  f"toplam={s['toplam']}s]")
    # --- 4. Performans ozeti ---
    baslik("4. GENEL DEGERLENDIRME")
    tum_sorular = CEVAPLANABILIR + CEVAPLANAMAZ
    toplam_sure = 0.0
    red_sayisi = 0
    for soru in tum_sorular:
        sonuc = motor.answer(soru)
        toplam_sure += sonuc["sureler"]["toplam"]
        if sonuc["reddedildi"]:
            red_sayisi += 1
    print(f"  Toplam soru        : {len(tum_sorular)}")
    print(f"  Cevaplanan         : {len(tum_sorular) - red_sayisi}")
    print(f"  Reddedilen         : {red_sayisi}")
    print(f"  Ortalama sure      : {toplam_sure/len(tum_sorular):.2f} sn")
    print(f"\n  Not: Reddedilen sorularda model hic calistirilmadigi icin")
    print(f"  bu sorular cok daha hizli sonuclanir.")
    motor.kapat()
    print("\nTest tamamlandi.")
if __name__ == "__main__":
    main()
