"""
Dokuman yukleme servisi.
Tek bir dosyanin okunmasi, parcalanmasi, vektorlestirilmesi ve
veritabanina yazilmasi islemlerini kapsuller.
Bu modul hem web arayuzu hem CLI hem de toplu yukleme scripti
tarafindan kullanilir.
"""
import hashlib
import shutil
from pathlib import Path
from src import chunker, db, readers
from src.embeddings import metinleri_vektore_cevir
PROJE_KOK = Path(__file__).resolve().parent.parent
DOCS_KLASORU = PROJE_KOK / "data" / "docs"
BATCH_BOYUTU = 32
def icerik_hash(metin: str) -> str:
    """Metin iceriginin SHA-256 parmak izini hesaplar."""
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()
def mevcut_hash(dosya_adi: str):
    """Veritabanindaki kayitli hash degerini dondurur."""
    with db.baglanti_al() as conn:
        satir = conn.execute(
            "SELECT hash FROM documents WHERE dosya_adi = ?", (dosya_adi,)
        ).fetchone()
    return satir["hash"] if satir else None
def dokumani_sil(dosya_adi: str) -> None:
    """Dokumani ve CASCADE ile tum parcalarini siler."""
    with db.baglanti_al() as conn:
        conn.execute("DELETE FROM documents WHERE dosya_adi = ?", (dosya_adi,))
def dosyayi_kalici_kaydet(kaynak_yol, hedef_ad: str) -> Path:
    """
    Yuklenen dosyayi data/docs/ klasorune kopyalar.
    Boylece dosya kalici olur ve ileride yeniden islenebilir.
    """
    DOCS_KLASORU.mkdir(parents=True, exist_ok=True)
    hedef = DOCS_KLASORU / hedef_ad
    shutil.copy2(kaynak_yol, hedef)
    return hedef
def baytlari_kaydet(veri: bytes, hedef_ad: str) -> Path:
    """
    Bellekteki dosya iceriğini (orn. Streamlit yuklemesi)
    data/docs/ klasorune yazar.
    """
    DOCS_KLASORU.mkdir(parents=True, exist_ok=True)
    hedef = DOCS_KLASORU / hedef_ad
    hedef.write_bytes(veri)
    return hedef
def dosyayi_indeksle(yol, embedding_client, zorla: bool = False) -> dict:
    """
    Tek bir dosyayi okur, parcalar, vektorlestirir ve veritabanina yazar.
    Args:
        yol              : islenecek dosyanin yolu
        embedding_client : Foundry Local embedding istemcisi
        zorla            : True ise degisiklik olmasa da yeniden isle
    Returns:
        {
          "basarili": bool,
          "durum": "eklendi"|"guncellendi"|"atlandi"|"hata",
          "mesaj": str,
          "dosya_adi": str,
          "parca_sayisi": int,
          "karakter_sayisi": int,
        }
    """
    yol = Path(yol)
    dosya_adi = yol.name
    sonuc = {
        "basarili": False,
        "durum": "hata",
        "mesaj": "",
        "dosya_adi": dosya_adi,
        "parca_sayisi": 0,
        "karakter_sayisi": 0,
    }
    # --- 1. Metni cikar ---
    try:
        metin = readers.metni_cikar(yol)
    except readers.OkumaHatasi as hata:
        sonuc["mesaj"] = str(hata)
        return sonuc
    except Exception as hata:
        sonuc["mesaj"] = f"Beklenmeyen okuma hatasi: {hata}"
        return sonuc
    sonuc["karakter_sayisi"] = len(metin)
    # --- 2. Degisiklik kontrolu ---
    yeni_hash = icerik_hash(metin)
    eski_hash = mevcut_hash(dosya_adi)
    if not zorla and eski_hash == yeni_hash:
        sonuc.update({
            "basarili": True,
            "durum": "atlandi",
            "mesaj": "Dosya zaten yuklu ve degismemis",
        })
        return sonuc
    guncelleme = eski_hash is not None
    if guncelleme:
        dokumani_sil(dosya_adi)
    # --- 3. Parcala ---
    parcalar = chunker.parcala(metin)
    if not parcalar:
        sonuc["mesaj"] = "Metinden parca uretilemedi"
        return sonuc
    # --- 4. Veritabanina yaz ---
    try:
        db.veritabanini_kur()
        doc_id = db.dokuman_ekle(dosya_adi, str(yol), yeni_hash)
        for sira, parca in enumerate(parcalar, start=1):
            db.parca_ekle(doc_id, sira, parca)
    except Exception as hata:
        sonuc["mesaj"] = f"Veritabani hatasi: {hata}"
        return sonuc
    # --- 5. Vektorlestir (sadece bu dosyanin parcalari) ---
    try:
        bekleyenler = db.vektorsuz_parcalar()
        if bekleyenler:
            idler = [s["id"] for s in bekleyenler]
            metinler = [s["metin"] for s in bekleyenler]
            vektorler = metinleri_vektore_cevir(
                embedding_client, metinler, batch_boyutu=BATCH_BOYUTU
            )
            db.vektorleri_toplu_guncelle(list(zip(idler, vektorler)))
    except Exception as hata:
        sonuc["mesaj"] = f"Vektorlestirme hatasi: {hata}"
        return sonuc
    sonuc.update({
        "basarili": True,
        "durum": "guncellendi" if guncelleme else "eklendi",
        "mesaj": f"{len(parcalar)} parca islendi",
        "parca_sayisi": len(parcalar),
    })
    return sonuc
def yuklenen_dosyayi_isle(veri: bytes, orijinal_ad: str,
                          embedding_client) -> dict:
    """
    Web arayuzunden gelen bellek ici dosyayi isler.
    Args:
        veri             : dosyanin bayt icerigi
        orijinal_ad      : kullanicinin dosya adi
        embedding_client : embedding istemcisi
    """
    # Guvenlik: uzanti kontrolu
    if not readers.uzanti_gecerli_mi(orijinal_ad):
        return {
            "basarili": False,
            "durum": "hata",
            "mesaj": f"Desteklenmeyen format. Kabul edilenler: "
                     f"{', '.join(sorted(readers.DESTEKLENEN_UZANTILAR))}",
            "dosya_adi": orijinal_ad,
            "parca_sayisi": 0,
            "karakter_sayisi": 0,
        }
    # Guvenlik: boyut kontrolu
    if len(veri) > readers.MAKS_DOSYA_BOYUTU:
        return {
            "basarili": False,
            "durum": "hata",
            "mesaj": f"Dosya cok buyuk ({len(veri)/1024/1024:.1f} MB). "
                     f"Sinir: {readers.MAKS_DOSYA_BOYUTU/1024/1024:.0f} MB",
            "dosya_adi": orijinal_ad,
            "parca_sayisi": 0,
            "karakter_sayisi": 0,
        }
    # Guvenlik: dosya adi temizleme
    guvenli_ad = readers.dosya_adini_temizle(orijinal_ad)
    try:
        yol = baytlari_kaydet(veri, guvenli_ad)
    except Exception as hata:
        return {
            "basarili": False,
            "durum": "hata",
            "mesaj": f"Dosya kaydedilemedi: {hata}",
            "dosya_adi": guvenli_ad,
            "parca_sayisi": 0,
            "karakter_sayisi": 0,
        }
    return dosyayi_indeksle(yol, embedding_client)
def yoldan_isle(kaynak_yol: str, embedding_client) -> dict:
    """
    CLI icin: diskteki bir dosyayi data/docs'a kopyalayip indeksler.
    """
    kaynak = Path(kaynak_yol).expanduser()
    if not kaynak.exists():
        return {
            "basarili": False, "durum": "hata",
            "mesaj": f"Dosya bulunamadi: {kaynak}",
            "dosya_adi": kaynak.name,
            "parca_sayisi": 0, "karakter_sayisi": 0,
        }
    if not readers.uzanti_gecerli_mi(kaynak.name):
        return {
            "basarili": False, "durum": "hata",
            "mesaj": f"Desteklenmeyen format: {kaynak.suffix}",
            "dosya_adi": kaynak.name,
            "parca_sayisi": 0, "karakter_sayisi": 0,
        }
    guvenli_ad = readers.dosya_adini_temizle(kaynak.name)
    # Dosya zaten data/docs icindeyse kopyalama
    try:
        if kaynak.resolve().parent == DOCS_KLASORU.resolve():
            hedef = kaynak
        else:
            hedef = dosyayi_kalici_kaydet(kaynak, guvenli_ad)
    except Exception as hata:
        return {
            "basarili": False, "durum": "hata",
            "mesaj": f"Dosya kopyalanamadi: {hata}",
            "dosya_adi": guvenli_ad,
            "parca_sayisi": 0, "karakter_sayisi": 0,
        }
    return dosyayi_indeksle(hedef, embedding_client)
def yuklu_dokumanlar() -> list:
    """Veritabanindaki dokumanlarin ozet listesini dondurur."""
    with db.baglanti_al() as conn:
        satirlar = conn.execute(
            "SELECT d.id, d.dosya_adi, d.eklenme_tarihi, "
            "COUNT(c.id) AS parca_sayisi "
            "FROM documents d LEFT JOIN chunks c ON c.document_id = d.id "
            "GROUP BY d.id ORDER BY d.eklenme_tarihi DESC"
        ).fetchall()
    return [
        {
            "id": s["id"],
            "dosya_adi": s["dosya_adi"],
            "tarih": s["eklenme_tarihi"],
            "parca_sayisi": s["parca_sayisi"],
        }
        for s in satirlar
    ]
def dokumani_kaldir(dosya_adi: str, dosyayi_da_sil: bool = False) -> bool:
    """
    Bir dokumani bilgi tabanindan kaldirir.
    Args:
        dosyayi_da_sil: True ise diskteki dosya da silinir
    """
    try:
        dokumani_sil(dosya_adi)
        if dosyayi_da_sil:
            yol = DOCS_KLASORU / dosya_adi
            if yol.exists():
                yol.unlink()
        return True
    except Exception:
        return False
