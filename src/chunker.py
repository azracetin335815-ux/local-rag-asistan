"""
Dokuman parcalama (chunking) modulu.
Uzun metinleri, anlamsal butunlugu koruyacak sekilde
belirli boyut araliginda parcalara boler.
"""
import re
from src import config
# Varsayilan ayarlar
HEDEF_BOYUT = config.CHUNK_HEDEF_BOYUT
MAKS_BOYUT = config.CHUNK_MAKS_BOYUT
MIN_BOYUT = 120         # karakter - bundan kisa parcalar birlestirilir
ORTUSME = 120           # karakter - ardisik parcalar arasi tekrar
def paragraflara_bol(metin: str) -> list:
    """
    Metni bos satirlardan paragraflara boler.
    Fazla bosluklari temizler, bos paragraflari atar.
    """
    ham = re.split(r"\n\s*\n", metin)
    return [p.strip() for p in ham if p.strip()]
def cumlelere_bol(metin: str) -> list:
    """
    Metni cumle sinirlarindan boler.
    Basit yaklasim: nokta, unlem veya soru isaretinden sonra
    bosluk gelen yerler cumle sonu kabul edilir.
    Kisaltmalarda ("Dr.", "vb.") hatali bolme yapabilir; bu
    kabul edilebilir bir sapmadir.
    """
    parcalar = re.split(r"(?<=[.!?])\s+", metin)
    return [c.strip() for c in parcalar if c.strip()]
def buyuk_parcayi_bol(metin: str, maks: int, ortusme: int) -> list:
    """
    Maksimum boyutu asan bir metni cumle sinirlarindan boler.
    Cumleler tek tek eklenir, sinir asilinca yeni parca baslatilir.
    """
    cumleler = cumlelere_bol(metin)
    parcalar = []
    aktif = ""
    for cumle in cumleler:
        # Cumle tek basina bile cok uzunsa, zorla karakter bazli bol
        if len(cumle) > maks:
            if aktif:
                parcalar.append(aktif.strip())
                aktif = ""
            for i in range(0, len(cumle), maks):
                parcalar.append(cumle[i:i + maks].strip())
            continue
        if len(aktif) + len(cumle) + 1 <= maks:
            aktif = f"{aktif} {cumle}".strip()
        else:
            parcalar.append(aktif.strip())
            # Ortusme: onceki parcanin sonundan bir miktar tasi
            kuyruk = aktif[-ortusme:] if ortusme > 0 else ""
            aktif = f"{kuyruk} {cumle}".strip()
    if aktif.strip():
        parcalar.append(aktif.strip())
    return parcalar
def parcala(metin: str,
            hedef: int = HEDEF_BOYUT,
            maks: int = MAKS_BOYUT,
            minimum: int = MIN_BOYUT,
            ortusme: int = ORTUSME) -> list:
    """
    Bir dokumani parcalara boler (hibrit strateji).
    Adimlar:
      1. Paragraflara bol
      2. Cok buyuk paragraflari cumle sinirlarindan bol
      3. Cok kucuk paragraflari hedef boyuta ulasana kadar birlestir
    Returns:
        Parca metinlerinin listesi.
    """
    if not metin or not metin.strip():
        return []
    paragraflar = paragraflara_bol(metin)
    # Adim 1-2: buyuk paragraflari boler, digerlerini oldugu gibi birakir
    ara_parcalar = []
    for paragraf in paragraflar:
        if len(paragraf) > maks:
            ara_parcalar.extend(buyuk_parcayi_bol(paragraf, maks, ortusme))
        else:
            ara_parcalar.append(paragraf)
    # Adim 3: kucuk parcalari birlestir
    sonuc = []
    aktif = ""
    for parca in ara_parcalar:
        if not aktif:
            aktif = parca
            continue
        birlesik_uzunluk = len(aktif) + len(parca) + 2
        # Aktif parca hala kucukse ve birlestirince hedefi asmiyorsa birlestir
        if len(aktif) < minimum or birlesik_uzunluk <= hedef:
            aktif = f"{aktif}\n\n{parca}"
        else:
            sonuc.append(aktif.strip())
            aktif = parca
    if aktif.strip():
        sonuc.append(aktif.strip())
    return sonuc
def parcalama_istatistigi(parcalar: list) -> dict:
    """Parcalama kalitesini olcen metrikleri hesaplar."""
    if not parcalar:
        return {
            "parca_sayisi": 0, "toplam_karakter": 0, "ortalama": 0,
            "en_kisa": 0, "en_uzun": 0, "std_sapma": 0, "cok_kisa_sayisi": 0,
        }
    boyutlar = [len(p) for p in parcalar]
    ortalama = sum(boyutlar) / len(boyutlar)
    varyans = sum((b - ortalama) ** 2 for b in boyutlar) / len(boyutlar)
    return {
        "parca_sayisi": len(parcalar),
        "toplam_karakter": sum(boyutlar),
        "ortalama": round(ortalama, 1),
        "en_kisa": min(boyutlar),
        "en_uzun": max(boyutlar),
        "std_sapma": round(varyans ** 0.5, 1),
        "cok_kisa_sayisi": sum(1 for b in boyutlar if b < MIN_BOYUT),
    }
