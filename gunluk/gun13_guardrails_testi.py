"""
Gun 13 - Guardrails fonksiyonlarinin birim testi.
Amac: Dayanak kontrolu ve sayi dogrulamanin bilinen ornekler
uzerinde beklenen sonuclari uretip uretmedigini dogrulamak.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import guardrails
BAGLAM = (
    "[1] (cihaz_kilavuzu.md) Cihazin tavsiye edilen bakim araligi 500 "
    "calisma saatidir. Bu sure asilirsa garanti kapsami disinda kalinabilir.\n\n"
    "[2] (sss.md) Urun garantisi 24 aydir. Garanti uretim hatalarini kapsar."
)
TEST_DURUMLARI = [
    ("Bakim araligi 500 saattir.",
     "DOGRU - baglamla uyumlu"),
    ("Bakim araligi 750 saattir.",
     "YANLIS SAYI - baglamda 750 yok"),
    ("Urun garantisi 24 aydir ve uretim hatalarini kapsar.",
     "DOGRU - baglamla uyumlu"),
    ("Cihaz haftada bir kez yaglanmali ve filtresi degistirilmelidir.",
     "ALAKASIZ - baglamda boyle bir bilgi yok"),
    ("Garanti suresi 36 aydir.",
     "YANLIS SAYI - baglamda 24 yaziyor"),
]
def main() -> None:
    print("=" * 62)
    print("  GUARDRAILS BIRIM TESTI")
    print("=" * 62)
    print("\nBAGLAM:")
    print(BAGLAM)
    print("\n" + "=" * 62)
    print("  TEST SONUCLARI")
    print("=" * 62)
    for cevap, beklenen in TEST_DURUMLARI:
        denetim = guardrails.cevabi_denetle(cevap, BAGLAM)
        durum = "GUVENLI" if denetim["guvenli"] else "UYARI VAR"
        print(f"\n  Cevap    : {cevap}")
        print(f"  Beklenen : {beklenen}")
        print(f"  Sonuc    : {durum}")
        print(f"  Dayanak  : {denetim['dayanak_orani']}")
        if denetim["uydurma_sayilar"]:
            print(f"  Supheli sayilar: {denetim['uydurma_sayilar']}")
        for uyari in denetim["uyarilar"]:
            print(f"    -> {uyari}")
    # --- Baglam yeterliligi testi ---
    print("\n" + "=" * 62)
    print("  BAGLAM YETERLILIGI TESTI")
    print("=" * 62)
    for baglam, aciklama in [
        (BAGLAM, "Normal baglam"),
        ("[1] ## Bakim", "Cok kisa baglam (sadece baslik)"),
        ("", "Bos baglam"),
    ]:
        yeterli, sebep = guardrails.baglam_yeterli_mi(baglam)
        print(f"\n  {aciklama}")
        print(f"    Uzunluk : {len(baglam.strip())} karakter")
        print(f"    Yeterli : {'EVET' if yeterli else 'HAYIR'}")
        if sebep:
            print(f"    Sebep   : {sebep}")
if __name__ == "__main__":
    main()
