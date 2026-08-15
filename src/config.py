"""
Merkezi yapilandirma.
Projenin tum ayarlanabilir parametreleri burada toplanmistir.
Diger moduller bu degerleri buradan okur.
"""
from pathlib import Path
# ==========================================================
# YOLLAR
# ==========================================================
PROJE_KOK = Path(__file__).resolve().parent.parent
DATA_KLASORU = PROJE_KOK / "data"
DOCS_KLASORU = DATA_KLASORU / "docs"
DB_YOLU = DATA_KLASORU / "knowledge.db"
SONUCLAR_KLASORU = PROJE_KOK / "sonuclar"
LOG_YOLU = SONUCLAR_KLASORU / "sistem.log"
# ==========================================================
# MODELLER
# ==========================================================
# Gelistirme sirasinda kucuk model kullanilir (hiz icin).
# Final demo icin "phi-4-mini" onerilir.
SOHBET_MODELI = "phi-4-mini"
EMBEDDING_MODELI = "qwen3-embedding-0.6b"
UYGULAMA_ADI = "local_rag_asistan"
# ==========================================================
# PARCALAMA (CHUNKING)
# ==========================================================
CHUNK_HEDEF_BOYUT = 500
CHUNK_MAKS_BOYUT = 700
CHUNK_MIN_BOYUT = 120
CHUNK_ORTUSME = 120
# ==========================================================
# GETIRME (RETRIEVAL)
# ==========================================================
# Gun 10 ve Gun 17 olcumlerine gore kalibre edildi.
# Ilgili sorular ~0.50-0.63, ilgisiz sorular ~0.30-0.40 araliginda.
BENZERLIK_ESIGI = 0.35
# Baglama eklenecek en fazla parca sayisi
TOP_K = 3
# Sorgu embedding onbelleginde tutulacak en fazla kayit
SORGU_ONBELLEK_BOYUTU = 128
# ==========================================================
# GUARDRAILS
# ==========================================================
MIN_BAGLAM_UZUNLUGU = 80
MIN_DAYANAK_ORANI = 0.30
# ==========================================================
# VERI YUKLEME
# ==========================================================
EMBEDDING_BATCH_BOYUTU = 32
DESTEKLENEN_UZANTILAR = (".md", ".txt", ".pdf", ".docx")
MAKS_DOSYA_BOYUTU_MB = 20
# ==========================================================
# LOGLAMA
# ==========================================================
LOG_SEVIYESI = "INFO"          # DEBUG, INFO, WARNING, ERROR
LOG_FORMATI = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
def ozet() -> dict:
    """Aktif yapilandirmayi sozluk olarak dondurur (raporlama icin)."""
    return {
        "sohbet_modeli": SOHBET_MODELI,
        "embedding_modeli": EMBEDDING_MODELI,
        "benzerlik_esigi": BENZERLIK_ESIGI,
        "top_k": TOP_K,
        "chunk_hedef": CHUNK_HEDEF_BOYUT,
        "chunk_maks": CHUNK_MAKS_BOYUT,
        "chunk_ortusme": CHUNK_ORTUSME,
        "min_dayanak_orani": MIN_DAYANAK_ORANI,
    }
