"""
Veri yukleme hatti (ingestion pipeline).
data/docs/ klasorundeki dokumanlari okur, parcalar, vektorlestirir
ve SQLite veritabanina yazar.
Kullanim:
    python ingest.py           # sadece degisenleri isle
    python ingest.py --tumu    # her seyi sifirdan yeniden isle
"""
import hashlib
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import chunker, db
from src.embeddings import metinleri_vektore_cevir
from src.foundry_client import embedding_modeli_al
PROJE_KOK = Path(__file__).resolve().parent
DOCS_KLASORU = PROJE_KOK / "data" / "docs"
# Islenecek dosya uzantilari
DESTEKLENEN = (".md", ".txt", ".pdf", ".docx")
# Embedding icin grup boyutu
BATCH_BOYUTU = 32
def baslik(metin: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {metin}")
    print("=" * 60)
def dosya_hash(icerik: str) -> str:
    """Dosya iceriginin SHA-256 parmak izini hesaplar."""
    return hashlib.sha256(icerik.encode("utf-8")).hexdigest()
def mevcut_hash_al(dosya_adi: str):
    """Veritabanindaki kayitli hash degerini dondurur, yoksa None."""
    with db.baglanti_al() as conn:
        satir = conn.execute(
            "SELECT hash FROM documents WHERE dosya_adi = ?", (dosya_adi,)
        ).fetchone()
    return satir["hash"] if satir else None
def dokumani_sil(dosya_adi: str) -> None:
    """Bir dokumani ve CASCADE ile tum parcalarini siler."""
    with db.baglanti_al() as conn:
        conn.execute("DELETE FROM documents WHERE dosya_adi = ?", (dosya_adi,))
def dosyalari_bul() -> list:
    """data/docs klasorundeki desteklenen dosyalari listeler."""
    if not DOCS_KLASORU.exists():
        return []
    dosyalar = [
        d for d in sorted(DOCS_KLASORU.iterdir())
        if d.is_file() and d.suffix.lower() in DESTEKLENEN
    ]
    return dosyalar
def dosyayi_isle(dosya: Path, zorla: bool = False) -> dict:
    """
    Tek bir dosyayi okur, parcalar ve veritabanina yazar.
    Vektorler bu asamada hesaplanmaz; sonraki adimda toplu yapilir.
    Returns:
        {"durum": "islendi"|"atlandi"|"hata", "parca": int, "mesaj": str}
    """
    try:
        from src.readers import metni_cikar
        icerik = metni_cikar(dosya)
    except Exception as hata:
        return {"durum": "hata", "parca": 0, "mesaj": f"Okunamadi: {hata}"}
        # Bazi dosyalar farkli kodlamada olabilir
        try:
            icerik = dosya.read_text(encoding="latin-1")
        except Exception as hata:
            return {"durum": "hata", "parca": 0, "mesaj": f"Okunamadi: {hata}"}
    except Exception as hata:
        return {"durum": "hata", "parca": 0, "mesaj": f"Okunamadi: {hata}"}
    if not icerik.strip():
        return {"durum": "atlandi", "parca": 0, "mesaj": "Dosya bos"}
    yeni_hash = dosya_hash(icerik)
    eski_hash = mevcut_hash_al(dosya.name)
    # Degisiklik yoksa ve zorlama istenmediyse atla
    if not zorla and eski_hash == yeni_hash:
        return {"durum": "atlandi", "parca": 0, "mesaj": "Degisiklik yok"}
    # Degistiyse veya zorlaniyorsa: eskiyi sil, yeniden yaz
    if eski_hash is not None:
        dokumani_sil(dosya.name)
    parcalar = chunker.parcala(icerik)
    if not parcalar:
        return {"durum": "atlandi", "parca": 0, "mesaj": "Parca uretilemedi"}
    doc_id = db.dokuman_ekle(dosya.name, str(dosya), yeni_hash)
    for sira, parca in enumerate(parcalar, start=1):
        db.parca_ekle(doc_id, sira, parca)
    durum = "islendi" if eski_hash is None else "guncellendi"
    return {"durum": durum, "parca": len(parcalar), "mesaj": ""}
def vektorleri_hesapla() -> int:
    """
    Embedding'i olmayan tum parcalari bulur, toplu olarak vektorlestirir
    ve veritabanini gunceller.
    Returns:
        Islenen parca sayisi.
    """
    bekleyenler = db.vektorsuz_parcalar()
    if not bekleyenler:
        print("  Tum parcalarin vektoru zaten hesaplanmis.")
        return 0
    print(f"  {len(bekleyenler)} parca vektorlestirilecek...")
    model, client = embedding_modeli_al()
    chunk_idler = [satir["id"] for satir in bekleyenler]
    metinler = [satir["metin"] for satir in bekleyenler]
    baslangic = time.time()
    islenen = 0
    tum_vektorler = []
    # Gruplar halinde isle ve ilerleme goster
    for i in range(0, len(metinler), BATCH_BOYUTU):
        grup = metinler[i:i + BATCH_BOYUTU]
        vektorler = metinleri_vektore_cevir(client, grup, batch_boyutu=BATCH_BOYUTU)
        tum_vektorler.extend(vektorler)
        islenen += len(grup)
        yuzde = islenen / len(metinler) * 100
        print(f"\r  Vektorlestiriliyor: {islenen}/{len(metinler)} "
              f"(%{yuzde:.0f})", end="", flush=True)
    print()
    sure = time.time() - baslangic
    # Veritabanina toplu yaz
    db.vektorleri_toplu_guncelle(list(zip(chunk_idler, tum_vektorler)))
    print(f"  Tamamlandi: {len(metinler)} vektor, {sure:.1f} sn "
          f"({sure/len(metinler)*1000:.0f} ms/parca)")
    model.unload()
    return len(metinler)
def main() -> None:
    zorla = "--tumu" in sys.argv
    baslik("VERI YUKLEME HATTI (INGESTION)")
    print(f"Kaynak klasor : {DOCS_KLASORU}")
    print(f"Veritabani    : {db.DB_YOLU}")
    print(f"Mod           : {'TUM DOSYALAR YENIDEN ISLENECEK' if zorla else 'Sadece degisenler'}")
    db.veritabanini_kur()
    # --- 1. Dosyalari bul ---
    baslik("1. DOSYA TARAMA")
    dosyalar = dosyalari_bul()
    if not dosyalar:
        print(f"HATA: {DOCS_KLASORU} icinde islenecek dosya bulunamadi.")
        print(f"Desteklenen uzantilar: {', '.join(DESTEKLENEN)}")
        return
    print(f"{len(dosyalar)} dosya bulundu:")
    for dosya in dosyalar:
        print(f"  - {dosya.name} ({dosya.stat().st_size:,} bayt)")
    # --- 2. Dosyalari isle ---
    baslik("2. OKUMA VE PARCALAMA")
    ozet = {"islendi": 0, "guncellendi": 0, "atlandi": 0, "hata": 0}
    toplam_parca = 0
    for dosya in dosyalar:
        sonuc = dosyayi_isle(dosya, zorla=zorla)
        ozet[sonuc["durum"]] = ozet.get(sonuc["durum"], 0) + 1
        toplam_parca += sonuc["parca"]
        etiket = sonuc["durum"].upper()
        ek = f" - {sonuc['mesaj']}" if sonuc["mesaj"] else ""
        parca_bilgi = f", {sonuc['parca']} parca" if sonuc["parca"] else ""
        print(f"  [{etiket:12}] {dosya.name}{parca_bilgi}{ek}")
    print(f"\n  Yeni islenen: {ozet['islendi']}  |  "
          f"Guncellenen: {ozet['guncellendi']}  |  "
          f"Atlanan: {ozet['atlandi']}  |  "
          f"Hatali: {ozet['hata']}")
    # --- 3. Vektorleri hesapla ---
    baslik("3. VEKTORLESTIRME")
    vektorleri_hesapla()
    # --- 4. Ozet ---
    baslik("4. VERITABANI DURUMU")
    ist = db.istatistik()
    for anahtar, deger in ist.items():
        print(f"  {anahtar:20} : {deger}")
    db_boyut = db.DB_YOLU.stat().st_size
    print(f"  {'veritabani_boyutu':20} : {db_boyut:,} bayt "
          f"({db_boyut/1024:.1f} KB)")
    if ist["parca_sayisi"] != ist["vektorlu_parca"]:
        eksik = ist["parca_sayisi"] - ist["vektorlu_parca"]
        print(f"\n  UYARI: {eksik} parcanin vektoru eksik.")
    else:
        print("\n  Tum parcalarin vektoru hazir. Sistem sorguya hazir.")
if __name__ == "__main__":
    main()
