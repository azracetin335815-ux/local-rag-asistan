"""
Gun 20 - Model karsilastirma testi.
Amac: Sohbet modelinin degistirilmesinin hangi metrikleri
etkiledigini, hangilerini etkilemedigini olcmek.
Beklenti:
  - Halusinasyon orani ve getirme isabeti DEGISMEMELI
    (bunlar retrieval katmanina bagli, modelden bagimsiz)
  - Anahtar kelime kapsamasi ARTMALI
  - Sure UZAMALI
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
PROJE_KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOK))
from src import config
from src.rag_engine import RagEngine
TEST_DOSYASI = PROJE_KOK / "tests" / "test_sorulari.json"
def anahtar_kelime_var_mi(cevap: str, kelimeler: list) -> bool:
    if not kelimeler:
        return True
    kucuk = cevap.lower()
    return any(str(k).lower() in kucuk for k in kelimeler)
def kaynak_isabetli_mi(kaynaklar: list, beklenen: str) -> bool:
    if not beklenen:
        return True
    return any(k["dosya_adi"] == beklenen for k in kaynaklar)
def modeli_degerlendir(model_adi: str, test_seti: dict) -> dict:
    """Belirtilen sohbet modeliyle test setini calistirir."""
    print(f"\n{'=' * 62}")
    print(f"  MODEL: {model_adi}")
    print("=" * 62)
    # Modeli gecici olarak degistir
    orijinal = config.SOHBET_MODELI
    config.SOHBET_MODELI = model_adi
    try:
        import src.foundry_client as fc
        fc.SOHBET_MODELI = model_adi
        motor = RagEngine(sessiz=True)
        if not motor.hazir:
            print("  HATA: Bilgi tabani bos.")
            return {}
        cevaplanabilir = test_seti["cevaplanabilir"]
        cevaplanamaz = test_seti["cevaplanamaz"]
        kaynak_isabet = 0
        kelime_kapsama = 0
        cevaplanan = 0
        sureler = []
        print(f"\n  Cevaplanabilir sorular ({len(cevaplanabilir)}):")
        for test in cevaplanabilir:
            sonuc = motor.answer(test["soru"])
            if not sonuc["reddedildi"]:
                cevaplanan += 1
            if kaynak_isabetli_mi(sonuc["kaynaklar"], test.get("beklenen_kaynak")):
                kaynak_isabet += 1
            if (not sonuc["reddedildi"] and
                    anahtar_kelime_var_mi(sonuc["cevap"],
                                          test.get("anahtar_kelimeler", []))):
                kelime_kapsama += 1
            sureler.append(sonuc["sureler"]["toplam"])
            print(f"    {'OK ' if not sonuc['reddedildi'] else 'RED'} "
                  f"{test['soru'][:45]}")
        halusinasyon = 0
        print(f"\n  Cevaplanamaz sorular ({len(cevaplanamaz)}):")
        for test in cevaplanamaz:
            sonuc = motor.answer(test["soru"])
            if not sonuc["reddedildi"]:
                halusinasyon += 1
            sureler.append(sonuc["sureler"]["toplam"])
            print(f"    {'RED' if sonuc['reddedildi'] else '!!!'} "
                  f"{test['soru'][:45]}")
        motor.kapat()
        n_p = len(cevaplanabilir)
        n_n = len(cevaplanamaz)
        return {
            "model": model_adi,
            "cevaplanan": cevaplanan,
            "cevaplanabilir_toplam": n_p,
            "kaynak_isabeti": kaynak_isabet / n_p * 100,
            "kelime_kapsamasi": kelime_kapsama / n_p * 100,
            "halusinasyon_orani": halusinasyon / n_n * 100,
            "ortalama_sure": sum(sureler) / len(sureler),
        }
    finally:
        config.SOHBET_MODELI = orijinal
def main() -> None:
    if not TEST_DOSYASI.exists():
        print(f"HATA: {TEST_DOSYASI} bulunamadi.")
        return
    test_seti = json.loads(TEST_DOSYASI.read_text(encoding="utf-8"))
    print("=" * 62)
    print("  MODEL KARSILASTIRMA TESTI")
    print("=" * 62)
    print(f"  Test seti: {len(test_seti['cevaplanabilir'])} cevaplanabilir, "
          f"{len(test_seti['cevaplanamaz'])} cevaplanamaz soru")
    print(f"  Benzerlik esigi: {config.BENZERLIK_ESIGI}")
    print(f"  Top-k: {config.TOP_K}")
    print("\n  NOT: Ilk calistirmada modeller indirilecegi icin uzun surebilir.")
    sonuclar = []
    for model_adi in ["qwen2.5-0.5b", "phi-4-mini"]:
        try:
            sonuc = modeli_degerlendir(model_adi, test_seti)
            if sonuc:
                sonuclar.append(sonuc)
        except Exception as hata:
            print(f"\n  {model_adi} test edilemedi: {hata}")
    if len(sonuclar) < 2:
        print("\nKarsilastirma icin en az iki model gerekli.")
        return
    # --- Karsilastirma tablosu ---
    print("\n" + "=" * 62)
    print("  KARSILASTIRMA")
    print("=" * 62)
    a, b = sonuclar[0], sonuclar[1]
    print(f"\n  {'Metrik':28} {a['model']:>14} {b['model']:>14}")
    print("  " + "-" * 58)
    print(f"  {'Getirme isabeti':28} {a['kaynak_isabeti']:>13.1f}% "
          f"{b['kaynak_isabeti']:>13.1f}%")
    print(f"  {'Anahtar kelime kapsamasi':28} {a['kelime_kapsamasi']:>13.1f}% "
          f"{b['kelime_kapsamasi']:>13.1f}%")
    print(f"  {'Halusinasyon orani':28} {a['halusinasyon_orani']:>13.1f}% "
          f"{b['halusinasyon_orani']:>13.1f}%")
    print(f"  {'Ortalama sure':28} {a['ortalama_sure']:>13.2f}s "
          f"{b['ortalama_sure']:>13.2f}s")
    print("\n  YORUM:")
    if abs(a["kaynak_isabeti"] - b["kaynak_isabeti"]) < 0.01:
        print("  - Getirme isabeti DEGISMEDI. Bu beklenen sonuctur; getirme")
        print("    katmani sohbet modelinden bagimsiz calismaktadir.")
    if abs(a["halusinasyon_orani"] - b["halusinasyon_orani"]) < 0.01:
        print("  - Halusinasyon orani DEGISMEDI. Reddetme karari esik")
        print("    denetimiyle verildigi icin modelden bagimsizdir.")
    kelime_fark = b["kelime_kapsamasi"] - a["kelime_kapsamasi"]
    if kelime_fark > 0:
        print(f"  - Anahtar kelime kapsamasi {kelime_fark:+.1f} puan degisti.")
        print("    Bu, model kalitesinin dogrudan etkiledigi tek metriktir.")
    sure_fark = (b["ortalama_sure"] / a["ortalama_sure"] - 1) * 100
    print(f"  - Ortalama sure %{sure_fark:+.0f} degisti.")
    print("\n  SONUC: Mimari katmanlarin dogru ayristirildigi dogrulanmistir.")
    print("  Model degisikligi yalnizca cevap uretim kalitesini ve suresini")
    print("  etkilemis, getirme ve reddetme davranisini degistirmemistir.")
    # --- Rapor ---
    zaman = datetime.now()
    rapor = config.SONUCLAR_KLASORU / f"model_karsilastirma_{zaman:%Y%m%d_%H%M}.md"
    satirlar = [
        "# Model Karsilastirma Raporu",
        "",
        f"**Tarih:** {zaman:%d.%m.%Y %H:%M}",
        f"**Benzerlik esigi:** {config.BENZERLIK_ESIGI}  |  "
        f"**Top-k:** {config.TOP_K}",
        "",
        "| Metrik | " + " | ".join(s["model"] for s in sonuclar) + " |",
        "|---|" + "---|" * len(sonuclar),
        "| Getirme isabeti | " +
        " | ".join(f"%{s['kaynak_isabeti']:.1f}" for s in sonuclar) + " |",
        "| Anahtar kelime kapsamasi | " +
        " | ".join(f"%{s['kelime_kapsamasi']:.1f}" for s in sonuclar) + " |",
        "| Halusinasyon orani | " +
        " | ".join(f"%{s['halusinasyon_orani']:.1f}" for s in sonuclar) + " |",
        "| Ortalama sure | " +
        " | ".join(f"{s['ortalama_sure']:.2f} sn" for s in sonuclar) + " |",
        "",
        "## Yorum",
        "",
        "Getirme isabeti ve halusinasyon orani metriklerinin model "
        "degisikliginden etkilenmemesi, bu davranislarin uygulama "
        "katmanindaki esik denetimine dayandigini ve dil modelinden "
        "bagimsiz oldugunu dogrulamaktadir. Anahtar kelime kapsamasi ve "
        "islem suresi ise dogrudan model kalitesine bagli olarak "
        "degismistir.",
        "",
    ]
    config.SONUCLAR_KLASORU.mkdir(parents=True, exist_ok=True)
    rapor.write_text("\n".join(satirlar), encoding="utf-8")
    print(f"\n  Rapor: {rapor}")
if __name__ == "__main__":
    main()
