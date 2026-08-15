"""
Guardrails - halusinasyon onleme mekanizmalari.
Cevabin baglama dayanip dayanmadigini denetleyen kontrol
fonksiyonlarini icerir.
"""
import re
# --- Ayarlar ---
# Baglamin toplam uzunlugu bu degerin altindaysa cevap uretilmez
MIN_BAGLAM_UZUNLUGU = 80
# Kelime ortusme orani bu degerin altindaysa uyari verilir
MIN_DAYANAK_ORANI = 0.30
# Anlamsiz kabul edilen kisa kelimeler (dayanak hesabina katilmaz)
DURAK_KELIMELER = {
    "ve", "veya", "ile", "bir", "bu", "su", "o", "da", "de", "ki",
    "icin", "gibi", "kadar", "daha", "cok", "az", "en", "ama", "fakat",
    "ancak", "yani", "ise", "the", "and", "for", "with", "that",
}
TURKCE_HARITA = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def kelimeleri_ayikla(metin: str) -> set:
    """
    Metinden anlamli kelimeleri cikarir.

    Turkce karakterler ASCII karsiliklarina cevrilir: dokumanlar
    ASCII-guvenli yazilmis olabilirken model duzgun Turkce uretir
    ("temizligi" vs "temizligi"). Normalizasyon olmadan bu kelimeler
    farkli sayilir ve dayanak orani yanlis dusuk cikar.
    """
    normalize = metin.translate(TURKCE_HARITA).lower()
    kelimeler = re.findall(r"\w+", normalize)
    return {
        k for k in kelimeler
        if len(k) > 2 and k not in DURAK_KELIMELER
    }
def sayilari_ayikla(metin: str) -> set:
    """Metindeki tum sayilari cikarir."""
    return set(re.findall(r"\d+", metin))
def baglam_yeterli_mi(baglam: str) -> tuple:
    """
    Baglamin cevap uretmek icin yeterli uzunlukta olup olmadigini kontrol eder.
    Returns:
        (yeterli_mi, sebep)
    """
    temiz = baglam.strip()
    if len(temiz) < MIN_BAGLAM_UZUNLUGU:
        return False, f"Baglam cok kisa ({len(temiz)} karakter)"
    return True, ""
def dayanak_orani(cevap: str, baglam: str) -> float:
    """
    Cevaptaki kelimelerin ne kadarinin baglamda gectigini olcer.
    Returns:
        0.0 - 1.0 arasi oran. Yuksek = cevap baglama dayaniyor.
    """
    cevap_kelimeleri = kelimeleri_ayikla(cevap)
    if not cevap_kelimeleri:
        return 0.0
    baglam_kelimeleri = kelimeleri_ayikla(baglam)
    ortak = cevap_kelimeleri & baglam_kelimeleri
    return len(ortak) / len(cevap_kelimeleri)
def uydurma_sayilar(cevap: str, baglam: str) -> list:
    """
    Cevapta gecen ama baglamda gecmeyen sayilari dondurur.
    Bu sayilar buyuk olasilikla uydurmadir.
    """
    cevap_sayilari = sayilari_ayikla(cevap)
    baglam_sayilari = sayilari_ayikla(baglam)
    return sorted(cevap_sayilari - baglam_sayilari)
def cevabi_denetle(cevap: str, baglam: str) -> dict:
    """
    Uretilmis bir cevabi tum kontrollerden gecirir.
    Returns:
        {
          "guvenli": bool,           # hicbir uyari yok mu
          "dayanak_orani": float,
          "uydurma_sayilar": list,
          "uyarilar": [str, ...],
        }
    """
    uyarilar = []
    # --- Kontrol 1: Kelime ortusmesi ---
    oran = dayanak_orani(cevap, baglam)
    if oran < MIN_DAYANAK_ORANI:
        uyarilar.append(
            f"Cevabin baglamla kelime ortusmesi dusuk (%{oran*100:.0f})"
        )
    # --- Kontrol 2: Sayi dogrulama ---
    sayilar = uydurma_sayilar(cevap, baglam)
    if sayilar:
        uyarilar.append(
            f"Baglamda bulunmayan sayilar tespit edildi: {', '.join(sayilar)}"
        )
    # --- Kontrol 3: Bos veya cok kisa cevap ---
    if len(cevap.strip()) < 5:
        uyarilar.append("Cevap anlamli icerik tasimiyor")
    return {
        "guvenli": len(uyarilar) == 0,
        "dayanak_orani": round(oran, 3),
        "uydurma_sayilar": sayilar,
        "uyarilar": uyarilar,
    }
def uyari_metni(denetim: dict) -> str:
    """
    Denetim sonucunu kullaniciya gosterilecek metne cevirir.
    Uyari yoksa bos string doner.
    """
    if denetim["guvenli"]:
        return ""
    satirlar = ["[DOGRULAMA UYARISI]"]
    for uyari in denetim["uyarilar"]:
        satirlar.append(f"  - {uyari}")
    satirlar.append("  Lutfen cevabi kaynak dokumandan teyit ediniz.")
    return "\n".join(satirlar)
# ==========================================================
# VARLIK (ENTITY) DOGRULAMA - Halusinasyonu sifira indirmek icin
# ==========================================================
import re as _re
def kodlari_ayikla(metin: str) -> set:
    """
    Metinden model/urun kodu gorunumundeki ifadeleri cikarir.
    Ornek: TX-4400, KRT-9, Vertex-B7 gibi harf+rakam kombinasyonlari.
    """
    return set(_re.findall(r"\b[A-Za-z]+-?\d+[A-Za-z]*\b", metin))
def uydurma_kodlar(cevap: str, baglam: str) -> list:
    """
    Cevapta gecen ama baglamda birebir gecmeyen kod/model isimlerini dondurur.
    """
    cevap_kodlari = kodlari_ayikla(cevap)
    baglam_kodlari = kodlari_ayikla(baglam)
    return sorted(cevap_kodlari - baglam_kodlari)
def cevap_guvenilir_mi(cevap: str, baglam: str, soru: str = "") -> tuple:
    """
    Cevabin KULLANICIYA GOSTERILMEYE uygun olup olmadigina karar verir.
    Bu fonksiyon uyari degil, ENGELLEME icin kullanilir.
    Returns:
        (guvenilir_mi, sebep)
    """
    # Sayisal uydurma varsa engelle
    _temiz = _re.sub(r"\(?\s*Kaynak\s*:?[^)]*\)?", "", cevap, flags=_re.IGNORECASE)
    _temiz = _re.sub(r"\[\d+\]", "", _temiz)
    # Sorudaki sayilar da mesru kabul edilir: sistem yanlis oncul
    # duzeltirken ("36 ay degil, 24 ay") soruyu tekrarlamak zorundadir.
    # Sorudaki sayilar yalnizca RED baglaminda ("degil", "hayir") mesrudur.
    # Aksi halde model yanlis onculu kabul etmis olabilir.
    _reddedici = any(k in cevap.lower() for k in ("hayir", "değil", "degil", "yanlis"))
    _ek = (" " + soru) if _reddedici else ""
    sayilar = uydurma_sayilar(_temiz, baglam + _ek)
    if sayilar:
        return False, f"Baglamda olmayan sayisal deger: {', '.join(sayilar)}"
    # Model/urun kodu uydurma varsa engelle
    kodlar = uydurma_kodlar(cevap, baglam)
    if kodlar:
        return False, f"Baglamda olmayan kod/model adi: {', '.join(kodlar)}"
    # Kelime ortusmesi cok dusukse engelle (once sadece uyariydi, artik engel)
    oran = dayanak_orani(cevap, baglam)
    if oran < MIN_DAYANAK_ORANI:
        return False, f"Cevap baglamla yeterince ortusmuyor (%{oran*100:.0f})"
    return True, ""
# ==========================================================
# TEK KAYNAK YETERLILIGI - capraz-parca birlestirme hatasini onler
# ==========================================================
def tek_kaynakla_destekleniyor_mu(cevap: str, parca_metinleri: list,
                                  soru: str = "") -> tuple:
    """
    Cevaptaki sayisal/kod bilgilerinin TEK BIR parca icinde birlikte
    gecip gecmedigini kontrol eder. Birden fazla gercek bilginin
    farkli parcalardan birlestirilerek yanlis bir iddia olusturulmasini
    (cross-chunk fact stitching) yakalamak icin kullanilir.
    Returns:
        (destekleniyor_mu, sebep)
    """
    # Kaynak referanslarini ("(Kaynak: [1], [2])") sayi analizinden cikar
    temiz_cevap = _re.sub(r"\(?\s*Kaynak\s*:?[^)]*\)?", "", cevap, flags=_re.IGNORECASE)
    temiz_cevap = _re.sub(r"\[\d+\]", "", temiz_cevap)
    cevap_sayilari = sayilari_ayikla(temiz_cevap)
    # Sorudan gelen sayilar mesrudur (yanlis oncul duzeltme)
    cevap_sayilari -= sayilari_ayikla(soru)
    cevap_kodlari = kodlari_ayikla(cevap)
    onemli_ogeler = cevap_sayilari | cevap_kodlari
    if not onemli_ogeler:
        return True, ""
    # En az bir parca, cevaptaki TUM onemli ogeleri tek basina icermeli
    for parca in parca_metinleri:
        parca_sayilari = sayilari_ayikla(parca)
        parca_kodlari = kodlari_ayikla(parca)
        parca_ogeleri = parca_sayilari | parca_kodlari
        if onemli_ogeler.issubset(parca_ogeleri):
            return True, ""
    return False, (
        f"Cevaptaki bilgiler ({', '.join(sorted(onemli_ogeler))}) "
        f"tek bir kaynak parcasinda birlikte gecmiyor - "
        f"farkli parcalardan birlestirilmis olabilir"
    )
# ==========================================================
# SORU VARLIK DENETIMI - soruda gecen entity baglamda var mi?
# ==========================================================
def soru_varliklari_baglamda_mi(soru: str, baglam: str) -> tuple:
    """
    Sorudaki model/urun kodu gorunumundeki varliklarin baglamda
    gecip gecmedigini kontrol eder.
    Ornek: Kullanici "TX-4400" soruyor ancak baglamda yalnizca
    "TX-2000" var. Bu durumda model, farkli bir cihazin verisini
    sorulan cihaza mal edebilir. Bu tur capraz-varlik atfini
    onlemek icin cevap uretimi engellenir.
    Returns:
        (uygun_mu, sebep)
    """
    soru_kodlari = kodlari_ayikla(soru)
    if not soru_kodlari:
        return True, ""
    baglam_kodlari = {k.lower() for k in kodlari_ayikla(baglam)}
    eksik = [k for k in soru_kodlari if k.lower() not in baglam_kodlari]
    if eksik:
        return False, (
            f"Soruda gecen '{', '.join(eksik)}' ifadesi dokumanlarda "
            f"bulunmuyor"
        )
    return True, ""
