"""
Gun 17 - Parametre optimizasyonu ve hata analizi.
Farkli esik ve top_k degerleriyle test setini calistirir,
metrikleri karsilastirir ve en iyi yapilandirmayi belirler.
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag_engine import RagEngine
PROJE_KOK = Path(__file__).resolve().parent.parent
TEST_DOSYASI = PROJE_KOK / "tests" / "test_sorulari.json"
SONUC_KLASORU = PROJE_KOK / "sonuclar"
# Denenecek parametre degerleri
ESIK_DEGERLERI = [0.30, 0.35, 0.40, 0.45, 0.50]
TOPK_DEGERLERI = [1, 2, 3, 4]
def baslik(metin: str) -> None:
    print("\n" + "=" * 68)
    print(f"  {metin}")
    print("=" * 68)
def anahtar_kontrol(cevap: str, kelimeler: list) -> bool:
    if not kelimeler:
        return True
    kucuk = cevap.lower()
    return any(k.lower() in kucuk for k in kelimeler)
def yasak_kontrol(cevap: str, kelimeler: list) -> list:
    if not kelimeler:
        return []
    kucuk = cevap.lower()
    return [k for k in kelimeler if k.lower() in kucuk]
def testi_calistir(motor, sorular: list) -> dict:
    """
    Test setini mevcut yapilandirmayla calistirir ve metrikleri dondurur.
    """
    tp = fn = fp = tn = 0
    basarili = 0
    detaylar = []
    for test in sorular:
        try:
            sonuc = motor.answer(test["soru"])
        except Exception as hata:
            # SDK bazen "Operation was cancelled" dondurebilir.
            # Tarama kesilmesin: bu soruyu reddedilmis say ve devam et.
            print(f"    [UYARI] {test.get('id', '?')} atlandi: {hata}")
            sonuc = {
                "soru": test["soru"], "cevap": "", "kaynaklar": [],
                "reddedildi": True, "sebep": "hata",
                "en_yuksek_skor": 0.0,
                "sureler": {"getirme": 0.0, "uretim": 0.0, "toplam": 0.0},
            }
        reddedildi = sonuc["reddedildi"]
        beklenen = test["beklenen_davranis"]
        cevap = sonuc["cevap"]
        # Karisiklik matrisi
        if beklenen == "cevapla":
            if reddedildi:
                fn += 1
            else:
                tp += 1
        elif beklenen == "reddet":
            if reddedildi:
                tn += 1
            else:
                fp += 1
        # Basari degerlendirmesi
        if beklenen == "cevapla":
            davranis_ok = not reddedildi
        elif beklenen == "reddet":
            davranis_ok = reddedildi
        else:
            davranis_ok = True
        anahtar_ok = True
        yasak_ihlal = []
        kaynak_ok = True
        if not reddedildi:
            anahtar_ok = anahtar_kontrol(cevap, test.get("anahtar_kelimeler", []))
            yasak_ihlal = yasak_kontrol(cevap, test.get("yasak_kelimeler", []))
            beklenen_kaynak = test.get("beklenen_kaynak")
            if beklenen_kaynak:
                kaynak_ok = any(
                    k["dosya_adi"] == beklenen_kaynak
                    for k in sonuc["kaynaklar"]
                )
        test_basarili = davranis_ok and anahtar_ok and not yasak_ihlal
        if test_basarili:
            basarili += 1
        detaylar.append({
            "id": test["id"],
            "kategori": test["kategori"],
            "soru": test["soru"],
            "beklenen": beklenen,
            "reddedildi": reddedildi,
            "cevap": cevap[:200],
            "basarili": test_basarili,
            "davranis_ok": davranis_ok,
            "anahtar_ok": anahtar_ok,
            "yasak_ihlal": yasak_ihlal,
            "kaynak_ok": kaynak_ok,
            "skor": sonuc.get("en_yuksek_skor", 0.0),
            "kaynaklar": [k["dosya_adi"] for k in sonuc["kaynaklar"]],
        })
    kesinlik = tp / (tp + fp) if (tp + fp) else 0.0
    duyarlilik = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * kesinlik * duyarlilik / (kesinlik + duyarlilik) \
        if (kesinlik + duyarlilik) else 0.0
    return {
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "kesinlik": kesinlik,
        "duyarlilik": duyarlilik,
        "f1": f1,
        "basari_orani": basarili / len(sorular),
        "basarili": basarili,
        "toplam": len(sorular),
        "detaylar": detaylar,
    }
def main() -> None:
    baslik("PARAMETRE OPTIMIZASYONU")
    if not TEST_DOSYASI.exists():
        print(f"HATA: {TEST_DOSYASI} bulunamadi.")
        return
    veri = json.loads(TEST_DOSYASI.read_text(encoding="utf-8-sig"))
    sorular = veri["sorular"]
    motor = RagEngine(sessiz=True)
    if not motor.hazir:
        print("HATA: Bilgi tabani bos. Once 'python ingest.py' calistirin.")
        return
    orijinal_esik = motor.retriever.esik
    orijinal_topk = motor.top_k
    print(f"Test soru sayisi : {len(sorular)}")
    print(f"Mevcut esik      : {orijinal_esik}")
    print(f"Mevcut top_k     : {orijinal_topk}")
    print(f"\nToplam {len(ESIK_DEGERLERI) + len(TOPK_DEGERLERI)} yapilandirma "
          f"denenecek. Bu birkac dakika surebilir.")
    tum_sonuclar = []
    # ==========================================
    # ADIM 1: Esik optimizasyonu (top_k sabit)
    # ==========================================
    baslik("ADIM 1 - BENZERLIK ESIGI OPTIMIZASYONU")
    print(f"  (top_k = {orijinal_topk} sabit tutuluyor)\n")
    print(f"  {'Esik':>6} {'Basari':>9} {'Kesinlik':>10} {'Duyarlilik':>12} "
          f"{'F1':>7} {'YK':>4} {'YR':>4}")
    print("  " + "-" * 58)
    esik_sonuclari = []
    for esik in ESIK_DEGERLERI:
        motor.retriever.esik = esik
        baslangic = time.time()
        m = testi_calistir(motor, sorular)
        sure = time.time() - baslangic
        m["esik"] = esik
        m["top_k"] = orijinal_topk
        m["sure"] = sure
        esik_sonuclari.append(m)
        tum_sonuclar.append(m)
        print(f"  {esik:>6.2f} {m['basarili']:>4}/{m['toplam']:<4} "
              f"{m['kesinlik']:>10.3f} {m['duyarlilik']:>12.3f} "
              f"{m['f1']:>7.3f} {m['fp']:>4} {m['fn']:>4}")
    print("\n  YK = Yanlis Kabul (halusinasyon)  |  YR = Yanlis Red")
    # En iyi esik: yanlis kabul = 0 kisiti altinda en yuksek duyarlilik
    guvenli_olanlar = [m for m in esik_sonuclari if m["fp"] == 0]
    if guvenli_olanlar:
        en_iyi_esik_m = max(guvenli_olanlar, key=lambda m: m["duyarlilik"])
        print(f"\n  Secilen esik: {en_iyi_esik_m['esik']}")
        print(f"  Gerekce: yanlis kabul = 0 kisiti altinda en yuksek "
              f"duyarlilik ({en_iyi_esik_m['duyarlilik']:.3f})")
    else:
        en_iyi_esik_m = max(esik_sonuclari, key=lambda m: m["f1"])
        print(f"\n  UYARI: Hicbir esik degeri yanlis kabulu sifira indiremedi.")
        print(f"  En yuksek F1 skoruna gore secildi: {en_iyi_esik_m['esik']}")
    en_iyi_esik = en_iyi_esik_m["esik"]
    # ==========================================
    # ADIM 2: top_k optimizasyonu (esik sabit)
    # ==========================================
    baslik("ADIM 2 - TOP-K OPTIMIZASYONU")
    print(f"  (esik = {en_iyi_esik} sabit tutuluyor)\n")
    motor.retriever.esik = en_iyi_esik
    print(f"  {'top_k':>6} {'Basari':>9} {'Kesinlik':>10} {'Duyarlilik':>12} "
          f"{'F1':>7} {'Sure':>8}")
    print("  " + "-" * 58)
    topk_sonuclari = []
    for topk in TOPK_DEGERLERI:
        motor.top_k = topk
        baslangic = time.time()
        m = testi_calistir(motor, sorular)
        sure = time.time() - baslangic
        m["esik"] = en_iyi_esik
        m["top_k"] = topk
        m["sure"] = sure
        topk_sonuclari.append(m)
        tum_sonuclar.append(m)
        print(f"  {topk:>6} {m['basarili']:>4}/{m['toplam']:<4} "
              f"{m['kesinlik']:>10.3f} {m['duyarlilik']:>12.3f} "
              f"{m['f1']:>7.3f} {sure:>7.1f}s")
    guvenli_topk = [m for m in topk_sonuclari if m["fp"] == 0]
    if guvenli_topk:
        en_iyi_topk_m = max(guvenli_topk, key=lambda m: m["basari_orani"])
    else:
        en_iyi_topk_m = max(topk_sonuclari, key=lambda m: m["f1"])
    en_iyi_topk = en_iyi_topk_m["top_k"]
    print(f"\n  Secilen top_k: {en_iyi_topk}")
    print(f"  Gerekce: en yuksek genel basari orani "
          f"({en_iyi_topk_m['basari_orani']*100:.1f}%)")
    # ==========================================
    # ADIM 3: Hata analizi (en iyi yapilandirmayla)
    # ==========================================
    baslik("ADIM 3 - HATA ANALIZI")
    print(f"  Yapilandirma: esik={en_iyi_esik}, top_k={en_iyi_topk}\n")
    motor.retriever.esik = en_iyi_esik
    motor.top_k = en_iyi_topk
    final = testi_calistir(motor, sorular)
    basarisizlar = [d for d in final["detaylar"] if not d["basarili"]]
    if not basarisizlar:
        print("  Tum testler basarili. Hata analizi gerekmiyor.")
    else:
        print(f"  {len(basarisizlar)} test basarisiz. Kok neden siniflandirmasi:\n")
        hata_tipleri = {
            "retrieval": [],
            "esik": [],
            "uretim": [],
            "belirsiz": [],
        }
        for d in basarisizlar:
            # Siniflandirma mantigi
            if d["beklenen"] == "cevapla" and d["reddedildi"]:
                # Cevaplanmasi gerekirken reddedildi
                if d["skor"] < en_iyi_esik:
                    hata_tipleri["esik"].append(d)
                else:
                    hata_tipleri["belirsiz"].append(d)
            elif not d["kaynak_ok"]:
                hata_tipleri["retrieval"].append(d)
            elif not d["anahtar_ok"] or d["yasak_ihlal"]:
                hata_tipleri["uretim"].append(d)
            else:
                hata_tipleri["belirsiz"].append(d)
        aciklamalar = {
            "retrieval": "Yanlis kaynak getirildi - chunking/embedding sorunu",
            "esik": "Dogru bilgi var ama esigi gecemedi - esik cok yuksek",
            "uretim": "Dogru baglam var ama cevap hatali - model kapasitesi",
            "belirsiz": "Siniflandirilamadi - manuel inceleme gerekli",
        }
        for tip, liste in hata_tipleri.items():
            if not liste:
                continue
            print(f"  [{tip.upper()}] {len(liste)} adet - {aciklamalar[tip]}")
            for d in liste:
                print(f"      {d['id']:4} ({d['kategori']:14}) "
                      f"skor={d['skor']:.3f}  {d['soru'][:42]}")
                print(f"           Cevap: {d['cevap'][:90]}")
            print()
    # ==========================================
    # ADIM 4: Ozet ve oneri
    # ==========================================
    baslik("ADIM 4 - SONUC VE ONERILER")
    mevcut = next(
        (m for m in esik_sonuclari if abs(m["esik"] - orijinal_esik) < 0.001),
        None
    )
    print(f"  {'':22} {'Mevcut':>12} {'Onerilen':>12}")
    print("  " + "-" * 48)
    print(f"  {'Benzerlik esigi':22} {orijinal_esik:>12.2f} {en_iyi_esik:>12.2f}")
    print(f"  {'top_k':22} {orijinal_topk:>12} {en_iyi_topk:>12}")
    if mevcut:
        print(f"  {'Basari orani':22} "
              f"{mevcut['basari_orani']*100:>11.1f}% "
              f"{final['basari_orani']*100:>11.1f}%")
        print(f"  {'Kesinlik':22} {mevcut['kesinlik']:>12.3f} "
              f"{final['kesinlik']:>12.3f}")
        print(f"  {'Duyarlilik':22} {mevcut['duyarlilik']:>12.3f} "
              f"{final['duyarlilik']:>12.3f}")
        print(f"  {'F1 skoru':22} {mevcut['f1']:>12.3f} {final['f1']:>12.3f}")
    print(f"\n  Kategori bazli final basari:")
    kategoriler = {}
    for d in final["detaylar"]:
        kategoriler.setdefault(d["kategori"], []).append(d)
    for kategori, grup in sorted(kategoriler.items()):
        basari = sum(1 for d in grup if d["basarili"])
        print(f"    {kategori:18} {basari}/{len(grup)} "
              f"(%{basari/len(grup)*100:.0f})")
    if en_iyi_esik != orijinal_esik or en_iyi_topk != orijinal_topk:
        print(f"\n  UYGULAMAK ICIN:")
        if en_iyi_esik != orijinal_esik:
            print(f"    src/retriever.py -> BENZERLIK_ESIGI = {en_iyi_esik}")
        if en_iyi_topk != orijinal_topk:
            print(f"    src/rag_engine.py -> VARSAYILAN_TOP_K = {en_iyi_topk}")
    else:
        print(f"\n  Mevcut yapilandirma zaten optimal. Degisiklik gerekmiyor.")
    # --- Rapor kaydet ---
    SONUC_KLASORU.mkdir(parents=True, exist_ok=True)
    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
    rapor_yolu = SONUC_KLASORU / f"optimizasyon_{zaman}.json"
    # detaylar cok yer kapladigi icin sadece ozet metrikleri kaydet
    ozet_sonuclar = [
        {k: v for k, v in m.items() if k != "detaylar"}
        for m in tum_sonuclar
    ]
    rapor_yolu.write_text(json.dumps({
        "zaman": datetime.now().isoformat(timespec="seconds"),
        "test_soru_sayisi": len(sorular),
        "onerilen": {"esik": en_iyi_esik, "top_k": en_iyi_topk},
        "onceki": {"esik": orijinal_esik, "top_k": orijinal_topk},
        "final_metrikler": {
            k: v for k, v in final.items() if k != "detaylar"
        },
        "tum_denemeler": ozet_sonuclar,
        "hatalar": basarisizlar,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Rapor kaydedildi: {rapor_yolu}")
    # Ayarlari geri yukle
    motor.retriever.esik = orijinal_esik
    motor.top_k = orijinal_topk
    motor.kapat()
if __name__ == "__main__":
    main()
