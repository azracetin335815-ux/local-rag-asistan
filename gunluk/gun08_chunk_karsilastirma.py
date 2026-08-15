"""
Gun 8 - Parcalama stratejilerinin karsilastirilmasi.
Amac: Farkli parca boyutlarinin ve stratejilerin sonuca etkisini
olcmek; hangi ayarlarin bizim dokumanlarimiz icin uygun oldugunu
deneysel olarak belirlemek.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import chunker
PROJE_KOK = Path(__file__).resolve().parent.parent
DOCS_KLASORU = PROJE_KOK / "data" / "docs"
def baslik(metin: str) -> None:
    print("\n" + "=" * 62)
    print(f"  {metin}")
    print("=" * 62)
def sabit_boyut_bol(metin: str, boyut: int) -> list:
    """Karsilastirma icin: naif sabit boyutlu bolme."""
    return [metin[i:i + boyut] for i in range(0, len(metin), boyut)]
def main() -> None:
    dosyalar = sorted(DOCS_KLASORU.glob("*.md")) + sorted(DOCS_KLASORU.glob("*.txt"))
    if not dosyalar:
        print(f"HATA: {DOCS_KLASORU} klasorunde dokuman bulunamadi.")
        print("Once ornek dokumanlari olusturun.")
        return
    baslik("1. BULUNAN DOKUMANLAR")
    for dosya in dosyalar:
        boyut = dosya.stat().st_size
        print(f"  {dosya.name:30} {boyut:>7,} bayt")
    # Tum dokumanlari birlestirmeden, ilk dosyayi ornek olarak kullan
    ornek_dosya = dosyalar[0]
    metin = ornek_dosya.read_text(encoding="utf-8")
    baslik(f"2. NAIF SABIT BOYUTLU BOLME  ({ornek_dosya.name})")
    sabit = sabit_boyut_bol(metin, 700)
    print(f"Parca sayisi: {len(sabit)}")
    print("\nIlk iki parcanin SINIRLARI:")
    for i, parca in enumerate(sabit[:2], start=1):
        print(f"\n  Parca {i} sonu   : ...{parca[-60:]!r}")
        if i < len(sabit):
            print(f"  Parca {i+1} basi   : {sabit[i][:60]!r}...")
    print("\n  -> Dikkat: kesme noktalari cumle ortasina denk gelebiliyor.")
    baslik(f"3. HIBRIT STRATEJI  ({ornek_dosya.name})")
    hibrit = chunker.parcala(metin)
    print(f"Parca sayisi: {len(hibrit)}")
    print("\nParcalar:")
    for i, parca in enumerate(hibrit, start=1):
        ilk_satir = parca.split("\n")[0][:55]
        print(f"  [{i}] ({len(parca):>4} kr) {ilk_satir}...")
    baslik("4. FARKLI HEDEF BOYUTLARIN KARSILASTIRMASI")
    print(f"{'Hedef':>7} {'Maks':>7} {'Parca':>7} {'Ortalama':>10} "
          f"{'En kisa':>9} {'En uzun':>9} {'Std':>8}")
    print("-" * 62)
    for hedef, maks in [(300, 450), (500, 750), (700, 1000), (1200, 1600)]:
        parcalar = chunker.parcala(metin, hedef=hedef, maks=maks)
        ist = chunker.parcalama_istatistigi(parcalar)
        print(f"{hedef:>7} {maks:>7} {ist['parca_sayisi']:>7} "
              f"{ist['ortalama']:>10.1f} {ist['en_kisa']:>9} "
              f"{ist['en_uzun']:>9} {ist['std_sapma']:>8.1f}")
    print("\nYorum: Hedef boyut kucultuldukce parca sayisi artar ve her parca")
    print("daha spesifik olur, ancak baglam butunlugu zayiflar.")
    baslik("5. TUM DOKUMANLARIN PARCALANMASI")
    toplam_parca = 0
    toplam_karakter = 0
    for dosya in dosyalar:
        icerik = dosya.read_text(encoding="utf-8")
        parcalar = chunker.parcala(icerik)
        ist = chunker.parcalama_istatistigi(parcalar)
        toplam_parca += ist["parca_sayisi"]
        toplam_karakter += ist["toplam_karakter"]
        print(f"\n  {dosya.name}")
        print(f"    Parca sayisi   : {ist['parca_sayisi']}")
        print(f"    Ortalama boyut : {ist['ortalama']} karakter")
        print(f"    Aralik         : {ist['en_kisa']} - {ist['en_uzun']}")
        print(f"    Std sapma      : {ist['std_sapma']}")
        print(f"    Cok kisa parca : {ist['cok_kisa_sayisi']}")
    baslik("6. GENEL OZET")
    print(f"  Toplam dokuman : {len(dosyalar)}")
    print(f"  Toplam parca   : {toplam_parca}")
    print(f"  Toplam karakter: {toplam_karakter:,}")
    print(f"  Tahmini vektor boyutu: {toplam_parca * 4096:,} bayt "
          f"({toplam_parca * 4096 / 1024:.1f} KB)")
    print("\n  (Her parca 1024 boyutlu float32 vektor = 4096 bayt)")
if __name__ == "__main__":
    main()
