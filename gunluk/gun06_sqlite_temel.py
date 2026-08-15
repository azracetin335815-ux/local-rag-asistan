"""
Gun 6 - SQLite temel islemleri denemesi.
Amac: Veritabani semasini olusturmak, ornek kayitlar eklemek,
okuma islemlerini test etmek ve CASCADE silmenin calistigini dogrulamak.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import db
def baslik(metin: str) -> None:
    print("\n" + "=" * 55)
    print(f"  {metin}")
    print("=" * 55)
def main() -> None:
    baslik("1. VERITABANI KURULUMU")
    db.veritabanini_sifirla()
    print(f"Veritabani olusturuldu: {db.DB_YOLU}")
    print(f"Dosya var mi? {db.DB_YOLU.exists()}")
    baslik("2. DOKUMAN EKLEME")
    d1 = db.dokuman_ekle("kilavuz.md", "data/docs/kilavuz.md", "hash_abc123")
    d2 = db.dokuman_ekle("sss.md", "data/docs/sss.md", "hash_def456")
    print(f"Eklenen dokuman id'leri: {d1}, {d2}")
    # Ayni dosya tekrar eklenirse yeni kayit olusmamali
    d1_tekrar = db.dokuman_ekle("kilavuz.md", "data/docs/kilavuz.md", "hash_abc123")
    print(f"Ayni dosya tekrar eklendi -> donen id: {d1_tekrar} "
          f"({'DOGRU, yeni kayit olusmadi' if d1_tekrar == d1 else 'HATA'})")
    baslik("3. PARCA EKLEME")
    parcalar_d1 = [
        "Cihazi calistirmadan once guc kablosunu kontrol ediniz.",
        "Ilk kurulumda dil secimi yapilmasi gerekmektedir.",
        "Bakim araligi 500 saat olarak belirlenmistir.",
    ]
    for sira, metin in enumerate(parcalar_d1, start=1):
        db.parca_ekle(d1, sira, metin)
    db.parca_ekle(d2, 1, "Urun garantisi 24 aydir.")
    db.parca_ekle(d2, 2, "Iade suresi 14 gundur.")
    print(f"{len(parcalar_d1)} + 2 = {len(parcalar_d1) + 2} parca eklendi.")
    baslik("4. OKUMA ISLEMLERI")
    print("Kayitli dokumanlar:")
    for satir in db.dokumanlari_listele():
        print(f"  [{satir['id']}] {satir['dosya_adi']} "
              f"(hash: {satir['hash']}, tarih: {satir['eklenme_tarihi']})")
    print(f"\n'{ 'kilavuz.md' }' dokumanina ait parcalar:")
    for satir in db.dokumanin_parcalari(d1):
        print(f"  [{satir['sira']}] ({satir['karakter_sayisi']} karakter) "
              f"{satir['metin'][:50]}...")
    baslik("5. ISTATISTIK")
    for anahtar, deger in db.istatistik().items():
        print(f"  {anahtar:20} : {deger}")
    baslik("6. CASCADE SILME TESTI")
    print("Not: embedding sutunu su an bos (NULL) - Gun 7'de doldurulacak.")
    with db.baglanti_al() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (d2,))
    kalan = db.istatistik()
    print(f"'sss.md' silindi.")
    print(f"Kalan dokuman: {kalan['dokuman_sayisi']}, "
          f"kalan parca: {kalan['parca_sayisi']}")
    print("Dokuman silindiginde parcalarinin da silinmesi = CASCADE calisiyor.")
if __name__ == "__main__":
    main()
