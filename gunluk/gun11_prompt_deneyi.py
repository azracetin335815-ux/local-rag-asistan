"""
Gun 11 - Prompt varyantlarinin karsilastirmali testi.
Amac: Farkli sistem prompt tasarimlarinin, ozellikle bilgi tabaninda
karsiligi olmayan sorularda modelin reddetme davranisina etkisini olcmek.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import prompts
from src.foundry_client import embedding_modeli_al, sohbet_modeli_al
from src.retriever import Retriever
# Bilgi tabaninda karsiligi OLAN soru
CEVAPLANABILIR = "Bakim araligi kac saattir?"
# Bilgi tabaninda karsiligi OLMAYAN sorular
CEVAPLANAMAZ = [
    "Cihazin uretim maliyeti kac liradir?",
    "Sirketin 2025 cirosu ne kadardir?",
]
VARYANTLAR = [
    ("A - Ciplak (baglamsiz)", prompts.SABLON_A_CIPLAK, False),
    ("B - Naif (baglam var, kisit yok)", prompts.SABLON_B_NAIF, True),
    ("C - Kisitli", prompts.SABLON_C_KISITLI, True),
    ("D - Kacis cumleli (ana sablon)", prompts.SABLON_D_KACISLI, True),
]
REDDETME_IFADELERI = [
    "bulunmuyor", "bilmiyorum", "bilgi yok", "yer almamaktadir",
    "bulunmamaktadir", "mevcut degil", "belirtilmemis", "yoktur",
]
def reddetme_mi(cevap: str) -> bool:
    kucuk = cevap.lower()
    return any(ifade in kucuk for ifade in REDDETME_IFADELERI)
def baslik(metin: str) -> None:
    print("\n" + "=" * 64)
    print(f"  {metin}")
    print("=" * 64)
def cevap_uret(client, mesajlar: list) -> str:
    response = client.complete_chat(mesajlar)
    return response.choices[0].message.content.strip()
def main() -> None:
    baslik("HAZIRLIK")
    retriever = Retriever()
    if not retriever.hazir:
        print("HATA: Veritabani bos. Once 'python ingest.py' calistirin.")
        return
    print(f"Retriever hazir: {len(retriever.kayitlar)} parca, "
          f"esik={retriever.esik}")
    emb_model, emb_client = embedding_modeli_al()
    chat_model, chat_client = sohbet_modeli_al()
    def parcalari_getir(soru, esik_uygula=True):
        vektor = emb_client.generate_embedding(soru).data[0].embedding
        return retriever.ara(vektor, top_k=3, esik_uygula=esik_uygula)
    # ==================================================
    # TEST 1: Cevaplanabilir soru
    # ==================================================
    baslik("TEST 1 - CEVAPLANABILIR SORU")
    print(f"Soru: {CEVAPLANABILIR}\n")
    parcalar = parcalari_getir(CEVAPLANABILIR)
    print(f"Getirilen parca sayisi: {len(parcalar)}")
    for p in parcalar:
        print(f"  [{p['skor']:.3f}] {p['dosya_adi']} #{p['sira']}")
    for ad, sablon, baglam_kullan in VARYANTLAR:
        kullanilacak = parcalar if baglam_kullan else []
        mesajlar = prompts.mesajlari_olustur(CEVAPLANABILIR, kullanilacak, sablon)
        baslangic = time.time()
        cevap = cevap_uret(chat_client, mesajlar)
        sure = time.time() - baslangic
        print(f"\n  --- {ad} ({sure:.1f} sn) ---")
        print(f"  {cevap[:300]}")
    # ==================================================
    # TEST 2: Cevaplanamaz sorular (asil test)
    # ==================================================
    baslik("TEST 2 - CEVAPLANAMAZ SORULAR")
    print("Bu sorularin cevabi bilgi tabaninda YOK.")
    print("Dogru davranis: modelin bilgisizligini belirtmesi.\n")
    sonuc_tablosu = {ad: 0 for ad, _, _ in VARYANTLAR}
    for soru in CEVAPLANAMAZ:
        print(f"\n{'-' * 60}")
        print(f"Soru: {soru}")
        # Esik uygulanmadan getir - promptun tek basina etkisini olcmek icin
        zayif_parcalar = parcalari_getir(soru, esik_uygula=False)
        en_yuksek = zayif_parcalar[0]["skor"] if zayif_parcalar else 0.0
        print(f"En yuksek benzerlik: {en_yuksek:.3f} "
              f"(esik {retriever.esik} - {'ALTINDA' if en_yuksek < retriever.esik else 'USTUNDE'})")
        for ad, sablon, baglam_kullan in VARYANTLAR:
            kullanilacak = zayif_parcalar if baglam_kullan else []
            mesajlar = prompts.mesajlari_olustur(soru, kullanilacak, sablon)
            cevap = cevap_uret(chat_client, mesajlar)
            reddetti = reddetme_mi(cevap)
            if reddetti:
                sonuc_tablosu[ad] += 1
            etiket = "REDDETTI" if reddetti else "UYDURDU "
            print(f"\n  [{etiket}] {ad}")
            print(f"    {cevap[:200]}")
    # ==================================================
    # OZET
    # ==================================================
    baslik("OZET - PROMPT VARYANTLARININ REDDETME BASARISI")
    toplam = len(CEVAPLANAMAZ)
    print(f"  {'Varyant':38} {'Reddetme':>12}")
    print("  " + "-" * 52)
    for ad, _, _ in VARYANTLAR:
        basari = sonuc_tablosu[ad]
        oran = basari / toplam * 100
        print(f"  {ad:38} {basari}/{toplam} (%{oran:.0f})")
    print("\n  Yorum:")
    print("  Prompt tasarimi reddetme davranisini belirgin sekilde etkiler.")
    print("  Ancak hicbir prompt %100 garanti vermez. Bu nedenle Gun 13'te")
    print("  kod seviyesinde esik denetimi (guardrails) eklenecektir.")
    emb_model.unload()
    chat_model.unload()
if __name__ == "__main__":
    main()
