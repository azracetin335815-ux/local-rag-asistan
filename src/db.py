"""
SQLite veritabani katmani (v1).
Dokuman ve parca (chunk) tablolarinin olusturulmasi ve temel
ekleme/okuma islemlerinden sorumludur.
"""
import sqlite3
from pathlib import Path
PROJE_KOK = Path(__file__).resolve().parent.parent
DB_YOLU = PROJE_KOK / "data" / "knowledge.db"
SEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dosya_adi       TEXT    NOT NULL UNIQUE,
    yol             TEXT    NOT NULL,
    hash            TEXT    NOT NULL,
    eklenme_tarihi  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     INTEGER NOT NULL,
    sira            INTEGER NOT NULL,
    metin           TEXT    NOT NULL,
    embedding       BLOB,
    karakter_sayisi INTEGER NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
"""
def baglanti_al() -> sqlite3.Connection:
    """
    Veritabani baglantisi acar ve gerekli ayarlari yapar.
    Yabanci anahtar kontrolu SQLite'ta varsayilan kapali oldugu icin
    her baglantida acilmalidir.
    """
    DB_YOLU.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_YOLU)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
def veritabanini_kur() -> None:
    """Tablolari ve indeksleri olusturur. Zaten varsa hicbir sey yapmaz."""
    with baglanti_al() as conn:
        conn.executescript(SEMA)
def dokuman_ekle(dosya_adi: str, yol: str, hash_degeri: str) -> int:
    """
    Yeni bir dokuman kaydi ekler ve id'sini dondurur.
    Dosya adi zaten varsa mevcut kaydin id'sini dondurur.
    """
    with baglanti_al() as conn:
        mevcut = conn.execute(
            "SELECT id FROM documents WHERE dosya_adi = ?", (dosya_adi,)
        ).fetchone()
        if mevcut:
            return mevcut["id"]
        imlec = conn.execute(
            "INSERT INTO documents (dosya_adi, yol, hash) VALUES (?, ?, ?)",
            (dosya_adi, yol, hash_degeri),
        )
        return imlec.lastrowid
def parca_ekle(document_id: int, sira: int, metin: str) -> int:
    """Bir dokumana ait metin parcasi ekler. Embedding Gun 7'de eklenecek."""
    with baglanti_al() as conn:
        imlec = conn.execute(
            "INSERT INTO chunks (document_id, sira, metin, karakter_sayisi) "
            "VALUES (?, ?, ?, ?)",
            (document_id, sira, metin, len(metin)),
        )
        return imlec.lastrowid
def dokumanlari_listele() -> list:
    """Tum dokuman kayitlarini dondurur."""
    with baglanti_al() as conn:
        return conn.execute(
            "SELECT * FROM documents ORDER BY id"
        ).fetchall()
def dokumanin_parcalari(document_id: int) -> list:
    """Belirli bir dokumana ait tum parcalari sirali dondurur."""
    with baglanti_al() as conn:
        return conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY sira",
            (document_id,),
        ).fetchall()
def istatistik() -> dict:
    """Veritabanindaki kayit sayilarini dondurur."""
    with baglanti_al() as conn:
        dokuman = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
        parca = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
        vektorlu = conn.execute(
            "SELECT COUNT(*) AS n FROM chunks WHERE embedding IS NOT NULL"
        ).fetchone()["n"]
    return {
        "dokuman_sayisi": dokuman,
        "parca_sayisi": parca,
        "vektorlu_parca": vektorlu,
    }
def veritabanini_sifirla() -> None:
    """Tum tablolari siler ve yeniden olusturur. Dikkatli kullan."""
    with baglanti_al() as conn:
        conn.executescript("DROP TABLE IF EXISTS chunks; DROP TABLE IF EXISTS documents;")
    veritabanini_kur()
# ==========================================================
# VEKTOR (EMBEDDING) ISLEMLERI - Gun 7
# ==========================================================
import numpy as np
# Vektorlerin saklanacagi sayisal tip.
# float32 secildi: float64'un yarisi kadar yer kaplar,
# kosinus benzerligi icin hassasiyeti fazlasiyla yeterlidir.
VEKTOR_TIPI = np.float32
def vektoru_bayta_cevir(vektor) -> bytes:
    """
    Float listesini kompakt bayt dizisine cevirir (serilestirme).
    1024 boyutlu bir vektor 4096 bayt yer kaplar.
    """
    return np.asarray(vektor, dtype=VEKTOR_TIPI).tobytes()
def bayti_vektore_cevir(veri: bytes) -> np.ndarray:
    """
    Bayt dizisini numpy vektorune geri cevirir (deserilestirme).
    NOT: Donen dizi salt okunurdur (frombuffer kopyalama yapmaz).
    Degistirmek gerekirse .copy() cagrilmalidir.
    """
    return np.frombuffer(veri, dtype=VEKTOR_TIPI)
def parca_ekle_vektorlu(document_id: int, sira: int, metin: str,
                        vektor=None) -> int:
    """Metin parcasini embedding vektoruyle birlikte ekler."""
    veri = vektoru_bayta_cevir(vektor) if vektor is not None else None
    with baglanti_al() as conn:
        imlec = conn.execute(
            "INSERT INTO chunks (document_id, sira, metin, embedding, "
            "karakter_sayisi) VALUES (?, ?, ?, ?, ?)",
            (document_id, sira, metin, veri, len(metin)),
        )
        return imlec.lastrowid
def vektor_guncelle(chunk_id: int, vektor) -> None:
    """Mevcut bir parcanin embedding vektorunu gunceller."""
    with baglanti_al() as conn:
        conn.execute(
            "UPDATE chunks SET embedding = ? WHERE id = ?",
            (vektoru_bayta_cevir(vektor), chunk_id),
        )
def vektorleri_toplu_guncelle(kayitlar: list) -> None:
    """
    Cok sayida parcanin vektorunu tek islemde gunceller.
    kayitlar: [(chunk_id, vektor), ...]
    Tek tek UPDATE yerine executemany kullanmak cok daha hizlidir.
    """
    veri = [(vektoru_bayta_cevir(v), cid) for cid, v in kayitlar]
    with baglanti_al() as conn:
        conn.executemany(
            "UPDATE chunks SET embedding = ? WHERE id = ?", veri
        )
def vektorsuz_parcalar() -> list:
    """
    Henuz embedding'i hesaplanmamis parcalari dondurur.
    Ingestion sirasinda cache mantigi icin kullanilir.
    """
    with baglanti_al() as conn:
        return conn.execute(
            "SELECT id, metin FROM chunks WHERE embedding IS NULL ORDER BY id"
        ).fetchall()
def tum_vektorleri_yukle() -> tuple:
    """
    Retrieval icin tum parcalari ve vektorlerini belleğe yukler.
    Returns:
        (kayitlar, matris)
        kayitlar : her parca icin id, metin, dosya adi bilgisi
        matris   : (N, D) boyutlu numpy dizisi - tum vektorler
    """
    with baglanti_al() as conn:
        satirlar = conn.execute(
            "SELECT c.id, c.metin, c.sira, d.dosya_adi, c.embedding "
            "FROM chunks c "
            "JOIN documents d ON d.id = c.document_id "
            "WHERE c.embedding IS NOT NULL "
            "ORDER BY c.id"
        ).fetchall()
    if not satirlar:
        return [], np.empty((0, 0), dtype=VEKTOR_TIPI)
    kayitlar = [
        {
            "id": s["id"],
            "metin": s["metin"],
            "sira": s["sira"],
            "dosya_adi": s["dosya_adi"],
        }
        for s in satirlar
    ]
    matris = np.vstack([bayti_vektore_cevir(s["embedding"]) for s in satirlar])
    return kayitlar, matris
