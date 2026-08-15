"""
Gun 10 - Getirme modulu testi ve esik kalibrasyonu.
Amac:
  1. Retrieval'in dogru parcalari buldugunu dogrulamak
  2. Ilgili ve ilgisiz sorularin skor dagilimini olcmek
  3. Uygun benzerlik esigini deneysel olarak belirlemek
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.foundry_client import embedding_modeli_al
from src.retriever import Retriever
# Bilgi tabaninda karsiligi OLMASI beklenen sorular
ILGILI_SORULAR = [
    "bakim araligi kac saat",
    "filtre nasil temizlenir",
    "urun garantisi ne kadar",
    "yillik izin kac gun",
    "uzaktan calisma kac gun",
    "E02 hata kodu ne demek",
]
# Bilgi tabaninda karsiligi OLMAMASI beklenen sorular
ILGISIZ_SORULAR = [
    "Istanbul'un nufusu kactir",
    "en iyi pizza tarifi nedir",
    "2024 Nobel edebiyat odulu kime verildi",
    "python'da liste nasil siralanir",
    "dolar kuru bugun kac lira",
]
def baslik(metin: str) -> None:
    print("\n" + "=" * 64)
    print(f"  {metin}")
    print("=" * 64)
def main() -> None:
    baslik("1. RETRIEVER HAZIRLIGI")
    retriever = Retriever()
    if not retriever.hazir:
        print("HATA: Veritabaninda vektorlu parca bulunamadi.")
        print("Once 'python ingest.py' calistirin.")
        return
    for anahtar, deger in retriever.durum().items():
        print(f"  {anahtar:15} : {deger}")
    print("\nEmbedding modeli yukleniyor...")
    model, client = embedding_modeli_al()
    def sorgu_vektoru(metin):
        return client.generate_embedding(metin).data[0].embedding
    # --- 2. Ilgili sorular ---
    baslik("2. ILGILI SORULAR (bilgi tabaninda var)")
    ilgili_skorlar = []
    for soru in ILGILI_SORULAR:
        vektor = sorgu_vektoru(soru)
        sonuclar = retriever.ara(vektor, top_k=2, esik_uygula=False)
        en_yuksek = sonuclar[0]["skor"] if sonuclar else 0.0
        ilgili_skorlar.append(en_yuksek)
        print(f"\n  '{soru}'")
        for sonuc in sonuclar:
            print(f"    [{sonuc['skor']:.3f}] {sonuc['dosya_adi']} #{sonuc['sira']}: "
                  f"{sonuc['metin'][:60].replace(chr(10), ' ')}...")
    # --- 3. Ilgisiz sorular ---
    baslik("3. ILGISIZ SORULAR (bilgi tabaninda yok)")
    ilgisiz_skorlar = []
    for soru in ILGISIZ_SORULAR:
        vektor = sorgu_vektoru(soru)
        sonuclar = retriever.ara(vektor, top_k=1, esik_uygula=False)
        en_yuksek = sonuclar[0]["skor"] if sonuclar else 0.0
        ilgisiz_skorlar.append(en_yuksek)
        kaynak = sonuclar[0]["dosya_adi"] if sonuclar else "-"
        print(f"  [{en_yuksek:.3f}] '{soru}'  (en yakin: {kaynak})")
    # --- 4. Skor dagilimi ---
    baslik("4. SKOR DAGILIMI ANALIZI")
    ilgili_min = min(ilgili_skorlar)
    ilgili_ort = sum(ilgili_skorlar) / len(ilgili_skorlar)
    ilgili_maks = max(ilgili_skorlar)
    ilgisiz_min = min(ilgisiz_skorlar)
    ilgisiz_ort = sum(ilgisiz_skorlar) / len(ilgisiz_skorlar)
    ilgisiz_maks = max(ilgisiz_skorlar)
    print(f"  {'':12} {'En dusuk':>10} {'Ortalama':>10} {'En yuksek':>10}")
    print("  " + "-" * 46)
    print(f"  {'ILGILI':12} {ilgili_min:>10.3f} {ilgili_ort:>10.3f} {ilgili_maks:>10.3f}")
    print(f"  {'ILGISIZ':12} {ilgisiz_min:>10.3f} {ilgisiz_ort:>10.3f} {ilgisiz_maks:>10.3f}")
    bosluk = ilgili_min - ilgisiz_maks
    print(f"\n  Ayirt edici bosluk: {bosluk:.3f}")
    if bosluk > 0:
        onerilen = (ilgili_min + ilgisiz_maks) / 2
        print(f"  Onerilen esik     : {onerilen:.3f}  (bosluk ortasi)")
        print(f"  Mevcut esik       : {retriever.esik:.3f}")
    else:
        print("  UYARI: Bolgeler cakisiyor. Esik secimi kacinilmaz olarak")
        print("  bazi hatalara yol acacak. Chunk boyutu gozden gecirilmeli.")
    # --- 5. Esik simulasyonu ---
    baslik("5. FARKLI ESIK DEGERLERININ SIMULASYONU")
    print(f"  {'Esik':>6} {'Dogru kabul':>13} {'Yanlis kabul':>14} {'Yanlis red':>12}")
    print("  " + "-" * 50)
    for esik in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]:
        dogru_kabul = sum(1 for s in ilgili_skorlar if s >= esik)
        yanlis_kabul = sum(1 for s in ilgisiz_skorlar if s >= esik)
        yanlis_red = sum(1 for s in ilgili_skorlar if s < esik)
        isaret = "  <-- mevcut" if abs(esik - retriever.esik) < 0.001 else ""
        print(f"  {esik:>6.2f} {dogru_kabul:>8}/{len(ILGILI_SORULAR)}"
              f" {yanlis_kabul:>10}/{len(ILGISIZ_SORULAR)}"
              f" {yanlis_red:>9}/{len(ILGILI_SORULAR)}{isaret}")
    print("\n  Hedef: yanlis kabul = 0 (halusinasyon yok),")
    print("         yanlis red mumkun oldugunca dusuk.")
    # --- 6. Esik uygulanmis gercek davranis ---
    baslik("6. ESIK UYGULANMIS DAVRANIS TESTI")
    test_sorulari = [ILGILI_SORULAR[0], ILGISIZ_SORULAR[0]]
    for soru in test_sorulari:
        vektor = sorgu_vektoru(soru)
        sonuclar = retriever.ara(vektor, top_k=3, esik_uygula=True)
        print(f"\n  Soru: '{soru}'")
        if sonuclar:
            print(f"  -> {len(sonuclar)} parca getirildi:")
            for sonuc in sonuclar:
                print(f"       [{sonuc['skor']:.3f}] {sonuc['dosya_adi']} #{sonuc['sira']}")
        else:
            print("  -> HICBIR PARCA ESIGI GECMEDI")
            print("     Sistem cevap uretmeyi reddedecek. (Dogru davranis)")
    # --- 7. Performans ---
    baslik("7. ARAMA PERFORMANSI")
    vektor = sorgu_vektoru(ILGILI_SORULAR[0])
    baslangic = time.time()
    for _ in range(100):
        retriever.ara(vektor, top_k=3)
    sure = time.time() - baslangic
    print(f"  100 arama suresi : {sure*1000:.1f} ms")
    print(f"  Arama basina     : {sure*10:.2f} ms")
    print(f"  Parca sayisi     : {len(retriever.kayitlar)}")
    print("\n  (Embedding uretimi haric - sadece vektor arama maliyeti)")
    model.unload()
if __name__ == "__main__":
    main()
