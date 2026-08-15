"""
Gun 7 - Vektor saklama ve geri okuma testi.
Amac: Serilestirme yontemlerinin boyutlarini karsilastirmak,
gidis-donus (round-trip) dogrulugunu test etmek ve gercek
embedding vektorlerinin veritabanina yazilip okunabildigini kanitlamak.
"""
import json
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import db
from src.foundry_client import embedding_modeli_al
def baslik(metin: str) -> None:
    print("\n" + "=" * 55)
    print(f"  {metin}")
    print("=" * 55)
def main() -> None:
    baslik("1. VERITABANI HAZIRLIGI")
    db.veritabanini_sifirla()
    print("Veritabani sifirlandi ve yeniden olusturuldu.")
    baslik("2. EMBEDDING URETIMI")
    model, client = embedding_modeli_al()
    metinler = [
        "Cihazi calistirmadan once guc kablosunu kontrol ediniz.",
        "Bakim araligi 500 saat olarak belirlenmistir.",
        "Urun garantisi 24 aydir ve kullanici hatalarini kapsamaz.",
    ]
    response = client.generate_embeddings(metinler)
    vektorler = [item.embedding for item in response.data]
    print(f"{len(vektorler)} vektor uretildi (boyut: {len(vektorler[0])})")
    baslik("3. SERILESTIRME BOYUT KARSILASTIRMASI")
    ornek = vektorler[0]
    json_boyut = len(json.dumps(ornek).encode("utf-8"))
    f64_boyut = len(np.asarray(ornek, dtype=np.float64).tobytes())
    f32_boyut = len(db.vektoru_bayta_cevir(ornek))
    print(f"JSON metin      : {json_boyut:>7,} bayt")
    print(f"numpy float64   : {f64_boyut:>7,} bayt")
    print(f"numpy float32   : {f32_boyut:>7,} bayt   <- secilen yontem")
    print(f"\nJSON'a gore tasarruf : %{(1 - f32_boyut/json_boyut)*100:.1f}")
    print(f"float64'e gore tasarruf: %{(1 - f32_boyut/f64_boyut)*100:.1f}")
    baslik("4. GIDIS-DONUS (ROUND-TRIP) TESTI")
    bayt = db.vektoru_bayta_cevir(ornek)
    geri = db.bayti_vektore_cevir(bayt)
    print(f"Orijinal boyut : {len(ornek)}")
    print(f"Geri okunan    : {len(geri)}")
    print(f"Ilk 5 orijinal : {[round(x, 6) for x in ornek[:5]]}")
    print(f"Ilk 5 geri     : {[round(float(x), 6) for x in geri[:5]]}")
    esit = np.allclose(np.asarray(ornek, dtype=np.float32), geri, atol=1e-6)
    print(f"\nVeriler ayni mi? {'EVET - kayipsiz' if esit else 'HAYIR - BOZULMA VAR'}")
    maks_fark = float(np.max(np.abs(np.asarray(ornek) - geri)))
    print(f"Maksimum fark  : {maks_fark:.10f}")
    print("(float64 -> float32 donusumunden kaynaklanan, beklenen hassasiyet kaybi)")
    baslik("5. YANLIS TIP UYARISI")
    yanlis = np.frombuffer(bayt, dtype=np.float64)
    print(f"float32 yazilip float64 okunursa:")
    print(f"  Beklenen boyut : {len(ornek)}")
    print(f"  Gercek boyut   : {len(yanlis)}   <- YANLIS")
    print(f"  Ilk deger      : {yanlis[0]:.6e}  <- anlamsiz")
    print("Ders: yazma ve okuma tipleri MUTLAKA ayni olmali.")
    baslik("6. VERITABANINA YAZMA")
    doc_id = db.dokuman_ekle("test_kilavuz.md", "data/docs/test_kilavuz.md", "hash_test")
    baslangic = time.time()
    for sira, (metin, vektor) in enumerate(zip(metinler, vektorler), start=1):
        db.parca_ekle_vektorlu(doc_id, sira, metin, vektor)
    yazma_suresi = time.time() - baslangic
    print(f"{len(metinler)} parca vektoruyle birlikte yazildi "
          f"({yazma_suresi:.3f} sn)")
    for anahtar, deger in db.istatistik().items():
        print(f"  {anahtar:20} : {deger}")
    baslik("7. VERITABANINDAN OKUMA VE DOGRULAMA")
    kayitlar, matris = db.tum_vektorleri_yukle()
    print(f"Yuklenen parca sayisi : {len(kayitlar)}")
    print(f"Matris boyutu         : {matris.shape}  (parca x vektor_boyutu)")
    print(f"Matris tipi           : {matris.dtype}")
    print("\nParcalar:")
    for kayit in kayitlar:
        print(f"  [{kayit['id']}] {kayit['dosya_adi']} #{kayit['sira']}: "
              f"{kayit['metin'][:45]}...")
    # Yazilan ile okunan vektorler ayni mi?
    orijinal_matris = np.asarray(vektorler, dtype=np.float32)
    dogru = np.allclose(orijinal_matris, matris, atol=1e-6)
    print(f"\nYazilan ve okunan vektorler ayni mi? "
          f"{'EVET - veri butunlugu saglandi' if dogru else 'HAYIR - SORUN VAR'}")
    baslik("8. DISK KULLANIMI")
    boyut = db.DB_YOLU.stat().st_size
    print(f"Veritabani dosya boyutu: {boyut:,} bayt ({boyut/1024:.1f} KB)")
    print(f"Parca basina ortalama  : {boyut/len(kayitlar):,.0f} bayt")
    model.unload()
    print("\nTest tamamlandi.")
if __name__ == "__main__":
    main()
