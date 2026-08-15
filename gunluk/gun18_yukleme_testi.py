"""
Gun 18 - Dokuman okuyucu ve yukleme servisi testi.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import ingest_service, readers
from src.foundry_client import embedding_modeli_al
PROJE_KOK = Path(__file__).resolve().parent.parent
DOCS = PROJE_KOK / "data" / "docs"
def baslik(metin: str) -> None:
    print("\n" + "=" * 62)
    print(f"  {metin}")
    print("=" * 62)
def main() -> None:
    baslik("1. DESTEKLENEN FORMATLAR")
    print(f"  Uzantilar    : {', '.join(sorted(readers.DESTEKLENEN_UZANTILAR))}")
    print(f"  Boyut siniri : {readers.MAKS_DOSYA_BOYUTU/1024/1024:.0f} MB")
    baslik("2. DOSYA ADI TEMIZLEME TESTI")
    tehlikeli_adlar = [
        "normal_dosya.pdf",
        "../../../etc/passwd",
        "rapor 2026 (son).docx",
        "dosya<>:|?.txt",
        "..\\..\\windows\\system32\\config.md",
    ]
    for ad in tehlikeli_adlar:
        temiz = readers.dosya_adini_temizle(ad)
        gecerli = readers.uzanti_gecerli_mi(temiz)
        print(f"  {ad:45} -> {temiz:30} "
              f"[{'gecerli' if gecerli else 'reddedildi'}]")
    baslik("3. MEVCUT DOSYALARIN OKUNMASI")
    dosyalar = sorted(DOCS.glob("*")) if DOCS.exists() else []
    if not dosyalar:
        print("  data/docs klasorunde dosya yok.")
    else:
        for dosya in dosyalar:
            if not dosya.is_file():
                continue
            try:
                metin = readers.metni_cikar(dosya)
                print(f"  [OK]    {dosya.name:32} {len(metin):>7,} karakter")
            except readers.OkumaHatasi as hata:
                print(f"  [HATA]  {dosya.name:32} {hata}")
    baslik("4. YUKLU DOKUMANLAR (veritabani)")
    dokumanlar = ingest_service.yuklu_dokumanlar()
    if not dokumanlar:
        print("  Veritabaninda dokuman yok.")
    else:
        print(f"  {'Dosya':32} {'Parca':>7}  Tarih")
        print("  " + "-" * 58)
        for d in dokumanlar:
            print(f"  {d['dosya_adi']:32} {d['parca_sayisi']:>7}  {d['tarih']}")
    baslik("5. CANLI INDEKSLEME TESTI")
    print("  Test dosyasi olusturuluyor...")
    test_icerik = (
        "# Test Dokumani\n\n"
        "Bu dosya canli yukleme ozelligini test etmek icin olusturulmustur.\n\n"
        "## Ozel Bilgi\n\n"
        "Test kodu ZZ-9999 olarak belirlenmistir. Bu kod yalnizca bu "
        "dokumanda gecmektedir ve sistemin yeni yuklenen dokumani "
        "bulabildigini dogrulamak icin kullanilir.\n\n"
        "## Ikinci Bolum\n\n"
        "Test parametresi 42 birim olarak ayarlanmistir. Bu deger "
        "sistemin dogru calistigini gostermek amaciyla secilmistir."
    )
    test_yol = DOCS / "gun18_test_dokumani.md"
    test_yol.parent.mkdir(parents=True, exist_ok=True)
    test_yol.write_text(test_icerik, encoding="utf-8")
    print(f"  Olusturuldu: {test_yol.name}")
    print("\n  Embedding modeli yukleniyor...")
    model, client = embedding_modeli_al()
    print("  Indeksleniyor...")
    sonuc = ingest_service.dosyayi_indeksle(test_yol, client)
    print(f"\n  Durum        : {sonuc['durum']}")
    print(f"  Basarili     : {sonuc['basarili']}")
    print(f"  Mesaj        : {sonuc['mesaj']}")
    print(f"  Parca sayisi : {sonuc['parca_sayisi']}")
    print(f"  Karakter     : {sonuc['karakter_sayisi']:,}")
    # Ayni dosya tekrar - atlanmali
    print("\n  Ayni dosya tekrar indeksleniyor (idempotency testi)...")
    sonuc2 = ingest_service.dosyayi_indeksle(test_yol, client)
    print(f"  Durum: {sonuc2['durum']} - {sonuc2['mesaj']}")
    baslik("6. YENI DOKUMANIN SORGULANABILIRLIGI")
    from src.retriever import Retriever
    retriever = Retriever()
    print(f"  Retriever yenilendi: {len(retriever.kayitlar)} parca")
    test_sorusu = "ZZ-9999 kodu nedir?"
    vektor = client.generate_embedding(test_sorusu).data[0].embedding
    sonuclar = retriever.ara(vektor, top_k=2, esik_uygula=False)
    print(f"\n  Test sorusu: '{test_sorusu}'")
    for s in sonuclar:
        print(f"    [{s['skor']:.3f}] {s['dosya_adi']} #{s['sira']}: "
              f"{s['metin'][:60]}...")
    if sonuclar and sonuclar[0]["dosya_adi"] == "gun18_test_dokumani.md":
        print("\n  BASARILI: Yeni yuklenen dokuman aramada bulundu.")
    else:
        print("\n  UYARI: Yeni dokuman en ust sirada cikmadi.")
    model.unload()
    print("\n  Not: Test dokumanini kaldirmak icin:")
    print("    python -c \"import sys; sys.path.insert(0,'.'); "
          "from src import ingest_service; "
          "ingest_service.dokumani_kaldir('gun18_test_dokumani.md', True)\"")
if __name__ == "__main__":
    main()
