"""
Merkezi loglama yapilandirmasi.
Kullanim:
    from src.log_ayari import logger_al
    logger = logger_al(__name__)
    logger.info("Mesaj")
"""
import logging
from logging.handlers import RotatingFileHandler
from src import config
_yapilandirildi = False
def _yapilandir() -> None:
    """Kok logger'i bir kez yapilandirir."""
    global _yapilandirildi
    if _yapilandirildi:
        return
    config.SONUCLAR_KLASORU.mkdir(parents=True, exist_ok=True)
    kok = logging.getLogger("rag")
    kok.setLevel(getattr(logging, config.LOG_SEVIYESI, logging.INFO))
    # Ayni handler'in tekrar eklenmesini engelle
    if kok.handlers:
        _yapilandirildi = True
        return
    # Dosyaya yazma - boyut sinirli, donen dosya
    dosya_handler = RotatingFileHandler(
        config.LOG_YOLU,
        maxBytes=1_000_000,      # 1 MB
        backupCount=3,
        encoding="utf-8",
    )
    dosya_handler.setFormatter(logging.Formatter(config.LOG_FORMATI))
    kok.addHandler(dosya_handler)
    # Konsola sadece uyari ve uzerini yaz (CLI ciktisini kirletmemek icin)
    konsol_handler = logging.StreamHandler()
    konsol_handler.setLevel(logging.WARNING)
    konsol_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    kok.addHandler(konsol_handler)
    _yapilandirildi = True
def logger_al(ad: str) -> logging.Logger:
    """Modul icin logger dondurur."""
    _yapilandir()
    return logging.getLogger(f"rag.{ad}")
