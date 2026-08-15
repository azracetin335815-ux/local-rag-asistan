"""
Otomatik degerlendirme scripti.
Test soru setini calistirir, sistemin kararlarini olcer ve
metrik raporu uretir.
Kullanim:
    python tests\evaluate.py
    python tests\evaluate.py --detay      # her soru icin cevabi da yazdir
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
def baslik(metin: str) -> None:
    print("\n" + "=" * 66)
    print(f"  {metin}")
    print("=" * 66)
def anahtar_kelime_kontrol(cevap: str, kelimeler: list) -> bool:
    """Anahtar kelimelerden EN AZ BIRI cevapta geciyor mu?"""
    if not kelimeler:
        return True
    kucuk = cevap.lower()
    return any(k.lower() in kucuk for k in kelimeler)
def yasak_kelime_kontrol(cevap: str, kelimeler: list) -> list:
    """Cevapta gecen yasak kelimeleri dondurur."""
    if not kelimeler:
        return []
    kucuk = cevap.lower()
    return [k for k in kelimeler if k.lower() in kucuk]
def kaynak_kontrol(kaynaklar: list, beklenen: str) -> bool:
    """Beklenen kaynak dosyasi getirilen kaynaklar arasinda mi?"""
    if not beklenen:
        return True
    return any(k["dosya_adi"] == beklenen for k in kaynaklar)
def soruyu_degerlendir(motor, test: dict, detay: bool = False) -> dict:
    """Tek bir test sorusunu calistirir ve sonucu degerlendirir."""
    try:
        sonuc = motor.answer(test["soru"])
    except Exception as hata:
        print(f"    [UYARI] {test.get('id', '?')} atlandi: {hata}")
        sonuc = {
            "soru": test["soru"], "cevap": "", "kaynaklar": [],
            "reddedildi": True, "sebep": "hata",
            "en_yuksek_skor": 0.0,
            "sureler": {"getirme": 0.0, "uretim": 0.0, "toplam": 0.0},
        }
    cevap = sonuc["cevap"]
    reddedildi = sonuc["reddedildi"]
    kaynaklar = sonuc["kaynaklar"]
    beklenen = test["beklenen_davranis"]
    # --- Davranis dogrulugu ---
    if beklenen == "cevapla":
        davranis_dogru = not reddedildi
    elif beklenen == "reddet":
        davranis_dogru = reddedildi
    else:                                   # "esnek" - her ikisi de kabul
        davranis_dogru = True
    # --- Icerik kontrolleri ---
    anahtar_ok = True
    yasak_ihlal = []
    kaynak_ok = True
    if not reddedildi:
        anahtar_ok = anahtar_kelime_kontrol(cevap, test.get("anahtar_kelimeler", []))
        yasak_ihlal = yasak_kelime_kontrol(cevap, test.get("yasak_kelimeler", []))
        kaynak_ok = kaynak_kontrol(kaynaklar, test.get("beklenen_kaynak"))
    # --- Genel basari ---
    basarili = davranis_dogru and anahtar_ok and not yasak_ihlal
    return {
        "id": test["id"],
        "kategori": test["kategori"],
        "soru": test["soru"],
        "beklenen": beklenen,
        "gerceklesen": "reddetti" if reddedildi else "cevapladi",
        "cevap": cevap,
        "davranis_dogru": davranis_dogru,
        "anahtar_ok": anahtar_ok,
        "yasak_ihlal": yasak_ihlal,
        "kaynak_ok": kaynak_ok,
        "basarili": basarili,
        "en_yuksek_skor": sonuc.get("en_yuksek_skor", 0.0),
        "kaynaklar": [f"{k['dosya_adi']}#{k['sira']}" for k in kaynaklar],
        "sure": sonuc["sureler"]["toplam"],
    }
def main() -> None:
    detay = "--detay" in sys.argv
    baslik("OTOMATIK DEGERLENDIRME")
    if not TEST_DOSYASI.exists():
        print(f"HATA: Test dosyasi bulunamadi: {TEST_DOSYASI}")
        return
    veri = json.loads(TEST_DOSYASI.read_text(encoding="utf-8-sig"))
    sorular = veri["sorular"]
    print(f"Test seti     : {veri['aciklama']} (surum {veri['surum']})")
    print(f"Soru sayisi   : {len(sorular)}")
    motor = RagEngine(sessiz=True)
    if not motor.hazir:
        print("HATA: Bilgi tabani bos. Once 'python ingest.py' calistirin.")
        return
    durum = motor.retriever.durum()
    print(f"Bilgi tabani  : {durum['parca_sayisi']} parca / "
          f"{durum['dosya_sayisi']} dosya")
    print(f"Benzerlik esigi: {durum['esik']}")
    print(f"Top-k         : {motor.top_k}")
    # ==========================================
    # Testleri calistir
    # ==========================================
    baslik("TEST CALISTIRILIYOR")
    sonuclar = []
    baslangic = time.time()
    for indeks, test in enumerate(sorular, start=1):
        sonuc = soruyu_degerlendir(motor, test, detay)
        sonuclar.append(sonuc)
        isaret = "BASARILI" if sonuc["basarili"] else "BASARISIZ"
        print(f"  [{indeks:2}/{len(sorular)}] {sonuc['id']:4} "
              f"{sonuc['kategori']:15} {isaret:9} "
              f"({sonuc['gerceklesen']:10} skor={sonuc['en_yuksek_skor']})")
        if detay or not sonuc["basarili"]:
            print(f"         Soru : {sonuc['soru']}")
            print(f"         Cevap: {sonuc['cevap'][:120]}")
            if not sonuc["davranis_dogru"]:
                print(f"         >> Beklenen: {sonuc['beklenen']}, "
                      f"gerceklesen: {sonuc['gerceklesen']}")
            if not sonuc["anahtar_ok"]:
                print(f"         >> Anahtar kelime bulunamadi: "
                      f"{test.get('anahtar_kelimeler')}")
            if sonuc["yasak_ihlal"]:
                print(f"         >> Yasak kelime tespit edildi: "
                      f"{sonuc['yasak_ihlal']}")
            if not sonuc["kaynak_ok"]:
                print(f"         >> Beklenen kaynak getirilmedi: "
                      f"{test.get('beklenen_kaynak')}")
    toplam_sure = time.time() - baslangic
    # ==========================================
    # Metrikler
    # ==========================================
    baslik("SONUCLAR")
    toplam = len(sonuclar)
    basarili = sum(1 for s in sonuclar if s["basarili"])
    # Karisiklik matrisi (esnek kategorisi haric)
    tp = sum(1 for s in sonuclar
             if s["beklenen"] == "cevapla" and s["gerceklesen"] == "cevapladi")
    fn = sum(1 for s in sonuclar
             if s["beklenen"] == "cevapla" and s["gerceklesen"] == "reddetti")
    fp = sum(1 for s in sonuclar
             if s["beklenen"] == "reddet" and s["gerceklesen"] == "cevapladi")
    tn = sum(1 for s in sonuclar
             if s["beklenen"] == "reddet" and s["gerceklesen"] == "reddetti")
    kesinlik = tp / (tp + fp) if (tp + fp) else 0.0
    duyarlilik = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * kesinlik * duyarlilik / (kesinlik + duyarlilik) \
        if (kesinlik + duyarlilik) else 0.0
    print(f"  Genel basari      : {basarili}/{toplam} "
          f"(%{basarili/toplam*100:.1f})")
    print(f"  Toplam sure       : {toplam_sure:.1f} sn "
          f"({toplam_sure/toplam:.2f} sn/soru)")
    print(f"\n  KARISIKLIK MATRISI")
    print(f"                        Sistem cevapladi   Sistem reddetti")
    print(f"    Cevaplanmaliydi     {tp:^16}   {fn:^15}")
    print(f"    Reddedilmeliydi     {fp:^16}   {tn:^15}")
    print(f"\n  Kesinlik (Precision): {kesinlik:.3f}  "
          f"(cevapladiklarinin dogruluk orani)")
    print(f"  Duyarlilik (Recall) : {duyarlilik:.3f}  "
          f"(cevaplayabileceklerinin orani)")
    print(f"  F1 skoru            : {f1:.3f}")
    # --- Kategori bazli ---
    print(f"\n  KATEGORI BAZLI BASARI")
    kategoriler = {}
    for s in sonuclar:
        kategoriler.setdefault(s["kategori"], []).append(s)
    for kategori, grup in sorted(kategoriler.items()):
        basari = sum(1 for s in grup if s["basarili"])
        print(f"    {kategori:18} {basari}/{len(grup)} "
              f"(%{basari/len(grup)*100:.0f})")
    # --- Retrieval isabeti ---
    cevaplananlar = [s for s in sonuclar if s["gerceklesen"] == "cevapladi"]
    if cevaplananlar:
        kaynak_isabet = sum(1 for s in cevaplananlar if s["kaynak_ok"])
        print(f"\n  Retrieval isabeti : {kaynak_isabet}/{len(cevaplananlar)} "
              f"(%{kaynak_isabet/len(cevaplananlar)*100:.0f})")
    # --- Basarisizlar ---
    basarisizlar = [s for s in sonuclar if not s["basarili"]]
    if basarisizlar:
        print(f"\n  BASARISIZ TESTLER ({len(basarisizlar)})")
        for s in basarisizlar:
            sebep = []
            if not s["davranis_dogru"]:
                sebep.append("yanlis karar")
            if not s["anahtar_ok"]:
                sebep.append("anahtar kelime yok")
            if s["yasak_ihlal"]:
                sebep.append("yasak kelime")
            print(f"    {s['id']:4} {s['soru'][:45]:47} [{', '.join(sebep)}]")
    # ==========================================
    # Rapor kaydet
    # ==========================================
    SONUC_KLASORU.mkdir(parents=True, exist_ok=True)
    zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
    rapor_yolu = SONUC_KLASORU / f"degerlendirme_{zaman_damgasi}.json"
    rapor = {
        "zaman": datetime.now().isoformat(timespec="seconds"),
        "yapilandirma": {
            "esik": durum["esik"],
            "top_k": motor.top_k,
            "parca_sayisi": durum["parca_sayisi"],
            "dosya_sayisi": durum["dosya_sayisi"],
        },
        "metrikler": {
            "toplam_soru": toplam,
            "basarili": basarili,
            "basari_orani": round(basarili / toplam, 3),
            "kesinlik": round(kesinlik, 3),
            "duyarlilik": round(duyarlilik, 3),
            "f1": round(f1, 3),
            "dogru_kabul": tp,
            "yanlis_red": fn,
            "yanlis_kabul": fp,
            "dogru_red": tn,
            "ortalama_sure": round(toplam_sure / toplam, 3),
        },
        "sonuclar": sonuclar,
    }
    rapor_yolu.write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  Rapor kaydedildi: {rapor_yolu}")
    motor.kapat()
if __name__ == "__main__":
    main()
