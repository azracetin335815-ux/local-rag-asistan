"""
Gun 13 - Halusinasyon karsilastirma testi (RAG SONRASI).
Gun 3'teki kontrol grubu testinin BIREBIR AYNI sorularla,
RAG + guardrails mimarisi uzerinde tekrarlanmasi.
Amac: Mimari degisikligin halusinasyon oranina etkisini olcmek.
"""
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag_engine import RagEngine
PROJE_KOK = Path(__file__).resolve().parent.parent
RAPOR_YOLU = PROJE_KOK / "sonuclar" / "gun13_rag_sonrasi_raporu.md"
ONCEKI_RAPOR = PROJE_KOK / "sonuclar" / "gun03_halusinasyon_raporu.md"
TEKRAR_SAYISI = 3
# Gun 3 ile BIREBIR AYNI sorular - karsilastirma gecerliligi icin sart
TEST_SORULARI = [
    "TX-4400 endustriyel kurutucunun tavsiye edilen bakim araligi kac saattir?",
    "Aselsan KRT-9 modulunun calisma sicaklik araligi nedir?",
    "2023 tarihli Ic Denetim Yonergesi'nin 14. maddesi neyi duzenler?",
    "Vertex-B7 pilinin tam sarj suresi ne kadardir?",
    "Firmamizin 2024 yili personel devir orani yuzde kactir?",
]
# Gun 3 sonuclari (kontrol grubu) - manuel olarak buraya girildi
GUN3_SONUCLARI = {
    "reddetme_orani": 0.0,
    "halusinasyon_orani": 100.0,
    "tutarsizlik_orani": 100.0,
}
def benzersiz_cevap_sayisi(cevaplar: list) -> int:
    normalize = {
        "".join(c.lower() for c in cevap if c.isalnum())
        for cevap in cevaplar
    }
    return len(normalize)
def main() -> None:
    print("=" * 62)
    print("  HALUSINASYON KARSILASTIRMA TESTI - RAG SONRASI")
    print("=" * 62)
    motor = RagEngine()
    if not motor.hazir:
        print("HATA: Bilgi tabani bos. Once 'python ingest.py' calistirin.")
        return
    satirlar = [
        "# Halusinasyon Olcum Raporu - RAG SONRASI",
        "",
        f"**Tarih:** {datetime.now():%d.%m.%Y %H:%M}",
        f"**Mimari:** RAG + benzerlik esigi + guardrails",
        f"**Soru sayisi:** {len(TEST_SORULARI)}  |  "
        f"**Her soru icin tekrar:** {TEKRAR_SAYISI}",
        "",
        "> Bu sorular, 3. gunde yapilan kontrol grubu olcumuyle birebir aynidir.",
        "> Sorulardaki varliklarin hicbiri gercek degildir.",
        "",
        "---",
        "",
    ]
    toplam_cevap = 0
    toplam_reddetme = 0
    tutarsiz_soru = 0
    for indeks, soru in enumerate(TEST_SORULARI, start=1):
        print(f"\n[{indeks}/{len(TEST_SORULARI)}] {soru[:55]}...")
        satirlar.append(f"## Soru {indeks}")
        satirlar.append("")
        satirlar.append(f"**Soru:** {soru}")
        satirlar.append("")
        cevaplar = []
        for tekrar in range(1, TEKRAR_SAYISI + 1):
            sonuc = motor.answer(soru)
            cevap = sonuc["cevap"]
            cevaplar.append(cevap)
            toplam_cevap += 1
            reddetti = sonuc["reddedildi"]
            if reddetti:
                toplam_reddetme += 1
            etiket = "REDDETTI" if reddetti else "CEVAP URETTI"
            skor = sonuc.get("en_yuksek_skor", 0.0)
            print(f"    Tekrar {tekrar}: {etiket}  (en yuksek skor: {skor})")
            satirlar.append(f"**Tekrar {tekrar}** - `{etiket}` "
                            f"(en yuksek benzerlik: {skor})")
            satirlar.append("")
            satirlar.append("> " + cevap.replace("\n", "\n> "))
            satirlar.append("")
            if not reddetti and sonuc.get("denetim"):
                d = sonuc["denetim"]
                satirlar.append(f"> Dayanak orani: {d['dayanak_orani']}")
                if d["uyarilar"]:
                    for u in d["uyarilar"]:
                        satirlar.append(f"> UYARI: {u}")
                satirlar.append("")
        farkli = benzersiz_cevap_sayisi(cevaplar)
        tutarli = farkli == 1
        if not tutarli:
            tutarsiz_soru += 1
        durum = "TUTARLI" if tutarli else f"TUTARSIZ ({farkli} farkli cevap)"
        print(f"    -> Tutarlilik: {durum}")
        satirlar.append(f"**Tutarlilik:** {durum}")
        satirlar.append("")
        satirlar.append("---")
        satirlar.append("")
    # --- Metrikler ---
    reddetme_orani = toplam_reddetme / toplam_cevap * 100
    halusinasyon_orani = 100 - reddetme_orani
    tutarsizlik_orani = tutarsiz_soru / len(TEST_SORULARI) * 100
    g3 = GUN3_SONUCLARI
    ozet = [
        "## Karsilastirmali Sonuclar",
        "",
        "| Metrik | Gun 3 (RAG yok) | Gun 13 (RAG + Guardrails) | Degisim |",
        "|---|---|---|---|",
        f"| Reddetme orani | %{g3['reddetme_orani']:.1f} | "
        f"%{reddetme_orani:.1f} | "
        f"{reddetme_orani - g3['reddetme_orani']:+.1f} puan |",
        f"| **Halusinasyon orani** | **%{g3['halusinasyon_orani']:.1f}** | "
        f"**%{halusinasyon_orani:.1f}** | "
        f"**{halusinasyon_orani - g3['halusinasyon_orani']:+.1f} puan** |",
        f"| Tutarsizlik orani | %{g3['tutarsizlik_orani']:.1f} | "
        f"%{tutarsizlik_orani:.1f} | "
        f"{tutarsizlik_orani - g3['tutarsizlik_orani']:+.1f} puan |",
        "",
        "### Yontem",
        "",
        "Her iki olcumde de birebir ayni sorular, ayni tekrar sayisi ve ayni "
        "degerlendirme olcutleri kullanilmistir. Degisen tek degisken sistem "
        "mimarisidir. Bu nedenle gozlenen fark dogrudan mimari degisiklige "
        "atfedilebilir.",
        "",
        "### Yorum",
        "",
        "Kontrol grubunda dil modeli, gercekte var olmayan varliklar hakkinda "
        "sorulan sorularin tamaminda bilgisizligini belirtmek yerine icerik "
        "uretmistir. RAG mimarisi ve benzerlik esigi denetimi eklendikten sonra "
        "sistem, bilgi tabaninda karsiligi bulunmayan sorularda dil modelini "
        "hic calistirmadan standart reddetme cevabini dondurmektedir.",
        "",
        "Bu davranis, prompt talimatina degil uygulama katmanindaki esik "
        "denetimine dayandigi icin modelden bagimsiz ve tekrarlanabilirdir. "
        "Ayni sorunun tekrarlanmasinda ayni cevabin alinmasi, sistemin "
        "deterministik hale geldigini gostermektedir.",
        "",
        "---",
        "",
    ]
    RAPOR_YOLU.parent.mkdir(parents=True, exist_ok=True)
    RAPOR_YOLU.write_text("\n".join(ozet + satirlar), encoding="utf-8")
    # --- Ekran ozeti ---
    print("\n" + "=" * 62)
    print("  KARSILASTIRMALI SONUCLAR")
    print("=" * 62)
    print(f"  {'Metrik':22} {'Gun 3':>10} {'Gun 13':>10} {'Degisim':>12}")
    print("  " + "-" * 56)
    print(f"  {'Reddetme orani':22} {g3['reddetme_orani']:>9.1f}% "
          f"{reddetme_orani:>9.1f}% {reddetme_orani - g3['reddetme_orani']:>+11.1f}")
    print(f"  {'Halusinasyon orani':22} {g3['halusinasyon_orani']:>9.1f}% "
          f"{halusinasyon_orani:>9.1f}% "
          f"{halusinasyon_orani - g3['halusinasyon_orani']:>+11.1f}")
    print(f"  {'Tutarsizlik orani':22} {g3['tutarsizlik_orani']:>9.1f}% "
          f"{tutarsizlik_orani:>9.1f}% "
          f"{tutarsizlik_orani - g3['tutarsizlik_orani']:>+11.1f}")
    print("=" * 62)
    print(f"\nRapor kaydedildi: {RAPOR_YOLU}")
    if ONCEKI_RAPOR.exists():
        print(f"Kontrol grubu raporu: {ONCEKI_RAPOR}")
    motor.kapat()
if __name__ == "__main__":
    main()
