"""
Prompt sablonlari modulu.
RAG sistemi icin sistem mesaji sablonlarini ve baglam
bicimlendirme fonksiyonlarini icerir.
"""
# Bilgi bulunamadiginda kullanilacak standart cevap.
# Tek bir yerde tanimlanir ki hem prompt hem guardrails ayni cumleyi kullansin.
BILGI_YOK_CEVABI = "Bu bilgi dokumanlarimda bulunmuyor."
# ==========================================================
# ANA SABLON (uretimde kullanilan)
# ==========================================================
ANA_SABLON = """Sen bir kurumsal dokuman asistanisin.
GOREVIN:
Asagida verilen dokuman alintilarini kullanarak kullanicinin sorusunu
cevaplamak.
KURALLAR:
1. Cevabindaki her bilgi, asagidaki alintilarda gecen bir ifadeye
   dayanmalidir.
2. Alintilarda bulunmayan hicbir bilgiyi ekleme.
3. Bilgi alintilarda yoksa tam olarak su cumleyi yaz:
   "{bilgi_yok}"
4. Cevabin sonunda kullandigin alinti numaralarini belirt.
   Ornek: (Kaynak: [1], [2])
5. Cevabin EN FAZLA IKI CUMLE olsun. Uzun aciklama yazma.
DOKUMAN ALINTILARI:
{baglam}"""
# ==========================================================
# DENEY SABLONLARI (Gun 11 A/B testi icin)
# ==========================================================
SABLON_A_CIPLAK = """Sen yardimsever bir asistansin. Sorulari cevapla."""
SABLON_B_NAIF = """Asagidaki bilgileri kullanarak soruyu cevapla.
{baglam}"""
SABLON_C_KISITLI = """Sen bir dokuman asistanisin.
Sadece asagidaki alintilarda verilen bilgiyi kullanarak cevap ver.
Kendi genel bilgini kullanma.
ALINTILAR:
{baglam}"""
SABLON_D_KACISLI = ANA_SABLON
def baglam_bicimlendir(parcalar: list, kaynak_goster: bool = True) -> str:
    """
    Getirilen parcalari numaralandirilmis baglam metnine cevirir.
    Args:
        parcalar: retriever.ara() ciktisi
                  [{"metin", "dosya_adi", "sira", "skor"}, ...]
        kaynak_goster: dosya adi eklensin mi
    Returns:
        Numaralandirilmis baglam metni.
    """
    if not parcalar:
        return "(Ilgili alinti bulunamadi.)"
    satirlar = []
    for numara, parca in enumerate(parcalar, start=1):
        metin = parca["metin"].replace("\n", " ").strip()
        if kaynak_goster:
            kaynak = f"({parca['dosya_adi']})"
            satirlar.append(f"[{numara}] {kaynak} {metin}")
        else:
            satirlar.append(f"[{numara}] {metin}")
    return "\n\n".join(satirlar)
def sistem_mesaji_olustur(parcalar: list, sablon: str = None) -> str:
    """
    Getirilen parcalardan tam sistem mesajini olusturur.
    Args:
        parcalar: retriever ciktisi
        sablon  : kullanilacak sablon (varsayilan: ANA_SABLON)
    """
    if sablon is None:
        sablon = ANA_SABLON
    baglam = baglam_bicimlendir(parcalar)
    # Sablonda hangi yer tutucular varsa onlari doldur
    if "{bilgi_yok}" in sablon:
        return sablon.format(baglam=baglam, bilgi_yok=BILGI_YOK_CEVABI)
    if "{baglam}" in sablon:
        return sablon.format(baglam=baglam)
    return sablon
def mesajlari_olustur(soru: str, parcalar: list, sablon: str = None) -> list:
    """
    Modele gonderilecek tam mesaj listesini olusturur.
    Returns:
        [{"role": "system", ...}, {"role": "user", ...}]
    """
    return [
        {"role": "system", "content": sistem_mesaji_olustur(parcalar, sablon)},
        {"role": "user", "content": soru},
    ]
def kaynak_ozeti(parcalar: list) -> str:
    """
    Kullaniciya gosterilecek kaynak listesini olusturur.
    Ayni dosyadan birden fazla parca varsa tekrar etmez.
    """
    if not parcalar:
        return ""
    gorulen = []
    for parca in parcalar:
        etiket = f"{parca['dosya_adi']} (bolum {parca['sira']})"
        if etiket not in gorulen:
            gorulen.append(etiket)
    return " | ".join(gorulen)
