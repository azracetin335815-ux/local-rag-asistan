"""
Gun 19 - Performans olcumu ve darbogaz analizi.
Amac: Sistemin her asamasinda harcanan sureyi ayri ayri olcerek
darbogazi tespit etmek ve optimizasyon onceliklerini belirlemek.
"""
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
PROJE_KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOK))
from src import config, guardrails, prompts
from src.rag_engine import RagEngine
TEKRAR = 3
CEVAPLANABILIR = [
    "Bakim araligi kac saattir?",
    "Urun garantisi kac aydir?",
    "Yillik izin hakki kac gundur?",
]
CEVAPLANAMAZ = [
    "Istanbul'un nufusu kactir?",
    "En iyi pizza tarifi nedir?",
]
def baslik(metin: str) -> None:
    print("\n" + "=" * 66)
    print(f"  {metin}")
    print("=" * 66)
def olc(fonksiyon, tekrar: int = TEKRAR) -> dict:
    """Bir fonksiyonu birkac kez calistirip sure istatistigi dondurur."""
    sureler = []
    for _ in range(tekrar):
        baslangic = time.perf_counter()
        fonksiyon()
        sureler.append(time.perf_counter() - baslangic)
    return {
        "ortalama": statistics.mean(sureler),
        "en_hizli": min(sureler),
        "en_yavas": max(sureler),
    }
def main() -> None:
    baslik("PERFORMANS OLCUMU VE DARBOGAZ ANALIZI")
    print("Aktif yapilandirma:")
    for anahtar, deger in config.ozet().items():
        print(f"  {anahtar:20} : {deger}")
    motor = RagEngine()
    if not motor.hazir:
        print("\nHATA: Bilgi tabani bos. Once 'python ingest.py' calistirin.")
        return
    soru = CEVAPLANABILIR[0]
    # ==================================================
    # 1. ASAMA BAZLI OLCUM
    # ==================================================
    baslik("1. ASAMA BAZLI SURE OLCUMU")
    # --- Asama 1: Embedding uretimi ---
    emb = olc(lambda: motor.emb_client.generate_embedding(soru))
    # --- Asama 2: Vektor arama ---
    vektor = motor.emb_client.generate_embedding(soru).data[0].embedding
    arama = olc(lambda: motor.retriever.ara(vektor, top_k=config.TOP_K), tekrar=100)
    # --- Asama 3: Prompt olusturma ---
    parcalar = motor.retriever.ara(vektor, top_k=config.TOP_K)
    prompt_olc = olc(
        lambda: prompts.mesajlari_olustur(soru, parcalar), tekrar=100
    )
    # --- Asama 4: Cevap uretimi ---
    mesajlar = prompts.mesajlari_olustur(soru, parcalar)
    uretim = olc(lambda: motor.chat_client.complete_chat(mesajlar))
    # --- Asama 5: Guardrails ---
    baglam = prompts.baglam_bicimlendir(parcalar)
    ornek_cevap = "Bakim araligi 500 saattir. (Kaynak: [1])"
    guard = olc(
        lambda: guardrails.cevabi_denetle(ornek_cevap, baglam), tekrar=100
    )
    asamalar = [
        ("1. Embedding uretimi", emb["ortalama"]),
        ("2. Vektor arama", arama["ortalama"]),
        ("3. Prompt olusturma", prompt_olc["ortalama"]),
        ("4. Cevap uretimi", uretim["ortalama"]),
        ("5. Guardrails denetimi", guard["ortalama"]),
    ]
    toplam = sum(sure for _, sure in asamalar)
    print(f"\n  {'Asama':26} {'Sure (ms)':>12} {'Pay':>10}  Grafik")
    print("  " + "-" * 62)
    for ad, sure in asamalar:
        pay = sure / toplam * 100
        cubuk = "#" * max(1, int(pay / 2))
        print(f"  {ad:26} {sure*1000:>12.2f} {pay:>9.1f}%  {cubuk}")
    print("  " + "-" * 62)
    print(f"  {'TOPLAM':26} {toplam*1000:>12.2f} {100.0:>9.1f}%")
    # ==================================================
    # 2. DARBOGAZ YORUMU
    # ==================================================
    baslik("2. DARBOGAZ ANALIZI")
    en_yavas = max(asamalar, key=lambda x: x[1])
    model_payi = (emb["ortalama"] + uretim["ortalama"]) / toplam * 100
    kod_payi = 100 - model_payi
    print(f"  En yavas asama       : {en_yavas[0]} "
          f"({en_yavas[1]*1000:.1f} ms)")
    print(f"  Model cagrilarinin payi : %{model_payi:.1f}")
    print(f"  Kendi kodumuzun payi    : %{kod_payi:.1f}")
    print(f"\n  Yorum:")
    print(f"  Toplam surenin buyuk kismi model cikarim asamalarinda")
    print(f"  harcanmaktadir. Kendi kodumuzun (vektor arama, prompt,")
    print(f"  guardrails) toplam icindeki payi %{kod_payi:.1f} seviyesindedir.")
    print(f"  Bu nedenle kod optimizasyonunun toplam sureye etkisi")
    print(f"  Amdahl Yasasi geregi %{kod_payi:.1f} ile sinirlidir.")
    # ==================================================
    # 3. REDDETME KAZANCI
    # ==================================================
    baslik("3. ERKEN DONUS (REDDETME) KAZANCI")
    cevap_sureleri = []
    for s in CEVAPLANABILIR:
        sonuc = motor.answer(s)
        if not sonuc["reddedildi"]:
            cevap_sureleri.append(sonuc["sureler"]["toplam"])
    red_sureleri = []
    for s in CEVAPLANAMAZ:
        sonuc = motor.answer(s)
        if sonuc["reddedildi"]:
            red_sureleri.append(sonuc["sureler"]["toplam"])
    if cevap_sureleri and red_sureleri:
        ort_cevap = statistics.mean(cevap_sureleri)
        ort_red = statistics.mean(red_sureleri)
        kazanc = (1 - ort_red / ort_cevap) * 100
        print(f"  Cevaplanan soru ortalamasi : {ort_cevap:.2f} sn")
        print(f"  Reddedilen soru ortalamasi : {ort_red:.2f} sn")
        print(f"  Zaman kazanci              : %{kazanc:.1f}")
        print(f"\n  Reddedilen sorularda dil modeli hic calistirilmadigi icin")
        print(f"  hem uydurma cevap riski ortadan kalkmakta hem de islem")
        print(f"  suresi belirgin olcude kisalmaktadir.")
    # ==================================================
    # 4. SORGU ONBELLEGI ETKISI
    # ==================================================
    baslik("4. SORGU ONBELLEGI SIMULASYONU")
    onbellek = {}
    def onbellekli_embed(metin):
        if metin in onbellek:
            return onbellek[metin]
        sonuc = motor.emb_client.generate_embedding(metin).data[0].embedding
        onbellek[metin] = sonuc
        return sonuc
    # Ilk cagri (onbellek bos)
    onbellek.clear()
    baslangic = time.perf_counter()
    onbellekli_embed(soru)
    ilk = time.perf_counter() - baslangic
    # Ikinci cagri (onbellekten)
    baslangic = time.perf_counter()
    onbellekli_embed(soru)
    ikinci = time.perf_counter() - baslangic
    print(f"  Ilk cagri (hesaplama)  : {ilk*1000:.2f} ms")
    print(f"  Ikinci cagri (onbellek): {ikinci*1000:.4f} ms")
    if ikinci > 0:
        print(f"  Hizlanma               : {ilk/ikinci:.0f}x")
    print(f"\n  Not: Onbellek yalnizca ayni sorunun tekrarlanmasi durumunda")
    print(f"  fayda saglar. Gercek kullanimda tekrar orani dusuk olabilir,")
    print(f"  ancak degerlendirme ve demo senaryolarinda belirgin katki verir.")
    # ==================================================
    # 5. RAPOR
    # ==================================================
    zaman = datetime.now()
    rapor_yolu = config.SONUCLAR_KLASORU / f"performans_{zaman:%Y%m%d_%H%M}.md"
    satirlar = [
        "# Performans Olcum Raporu",
        "",
        f"**Tarih:** {zaman:%d.%m.%Y %H:%M}",
        "",
        "## Yapilandirma",
        "",
        "| Parametre | Deger |",
        "|---|---|",
    ]
    for anahtar, deger in config.ozet().items():
        satirlar.append(f"| {anahtar} | {deger} |")
    satirlar += [
        "",
        "## Asama Bazli Sure Dagilimi",
        "",
        "| Asama | Sure (ms) | Pay |",
        "|---|---|---|",
    ]
    for ad, sure in asamalar:
        satirlar.append(f"| {ad} | {sure*1000:.2f} | %{sure/toplam*100:.1f} |")
    satirlar += [
        f"| **TOPLAM** | **{toplam*1000:.2f}** | **%100** |",
        "",
        "## Bulgular",
        "",
        f"- Model cikarim asamalarinin toplam sure icindeki payi: **%{model_payi:.1f}**",
        f"- Uygulama kodunun payi: **%{kod_payi:.1f}**",
        f"- En yavas asama: **{en_yavas[0]}** ({en_yavas[1]*1000:.1f} ms)",
        "",
        "Amdahl Yasasi geregi, uygulama kodunda yapilacak "
        f"optimizasyonlarin toplam sureye etkisi %{kod_payi:.1f} ile "
        "sinirlidir. Anlamli hizlanma icin model secimi veya donanim "
        "hizlandirma degerlendirilmelidir.",
        "",
    ]
    if cevap_sureleri and red_sureleri:
        satirlar += [
            "## Erken Donus Kazanci",
            "",
            "| Durum | Ortalama sure |",
            "|---|---|",
            f"| Cevaplanan soru | {ort_cevap:.2f} sn |",
            f"| Reddedilen soru | {ort_red:.2f} sn |",
            f"| **Kazanc** | **%{kazanc:.1f}** |",
            "",
        ]
    config.SONUCLAR_KLASORU.mkdir(parents=True, exist_ok=True)
    rapor_yolu.write_text("\n".join(satirlar), encoding="utf-8")
    print(f"\n  Rapor kaydedildi: {rapor_yolu}")
    motor.kapat()
if __name__ == "__main__":
    main()
