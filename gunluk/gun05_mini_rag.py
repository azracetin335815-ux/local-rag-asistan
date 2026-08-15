"""
Gun 5 - Bellek ici mini RAG uygulamasi.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.embeddings import en_benzer_k, metinleri_vektore_cevir
from src.foundry_client import embedding_modeli_al, sohbet_modeli_al
TOP_K = 2
BELGELER = [
    "Foundry Local, yapay zeka modellerini bulut baglantisi olmadan "
    "dogrudan kullanicinin cihazinda calistiran bir yerel calisma zamanidir.",
    "Foundry Local SDK Python, C#, JavaScript ve Rust dillerini destekler.",
    "Embedding modelleri metinleri sayisal vektorlere donusturerek "
    "anlamsal benzerlik aramasini mumkun kilar.",
    "Foundry Local, islemci ve grafik birimleri uzerinde verimli cikarim "
    "icin ONNX Runtime kullanir.",
    "Model katalogu, indirilip yerel olarak calistirilabilen onceden "
    "optimize edilmis modelleri sunar.",
    "Retrieval-Augmented Generation, model cevaplarini kullanicinin kendi "
    "verisine dayandirarak halusinasyon riskini azaltir.",
    "Vektor benzerlik aramasi, bir sorguya anlamca yakin olan dokumanlari "
    "kelime eslesmesine bakmaksizin bulur.",
    "SQLite, ayri bir sunucu gerektirmeyen, tek dosyada saklanan hafif bir "
    "iliskisel veritabani motorudur.",
]
SISTEM_SABLONU = """Sen bir dokuman asistanisin.
Asagidaki baglami kullanarak kullanicinin sorusunu cevapla.
Kurallar:
- SADECE asagidaki baglamda verilen bilgiyi kullan.
- Baglamda cevap yoksa "Bu bilgi dokumanlarimda bulunmuyor." de.
- Kendi genel bilgini kullanma, tahmin yurutme.
- Kisa ve net cevap ver.
Baglam:
{baglam}"""
def baglam_olustur(secilen: list) -> str:
    satirlar = []
    for sira, (indeks, _skor) in enumerate(secilen, start=1):
        satirlar.append(f"[{sira}] {BELGELER[indeks]}")
    return "\n".join(satirlar)
def main() -> None:
    print("=" * 60)
    print("  MINI RAG - Yerel Dokuman Asistani (Bellek Ici Surum)")
    print("=" * 60)
    print("\n[1/3] Embedding modeli yukleniyor...")
    embedding_model, embedding_client = embedding_modeli_al()
    print("[2/3] Sohbet modeli yukleniyor...")
    sohbet_model, sohbet_client = sohbet_modeli_al()
    print(f"[3/3] {len(BELGELER)} belge indeksleniyor...")
    baslangic = time.time()
    belge_vektorleri = metinleri_vektore_cevir(embedding_client, BELGELER)
    indeksleme_suresi = time.time() - baslangic
    print(f"\nHazir. {len(BELGELER)} belge {indeksleme_suresi:.2f} sn'de "
          f"indekslendi (vektor boyutu: {len(belge_vektorleri[0])}).")
    print("\nBilgi tabani su konulari iceriyor:")
    print("  - Foundry Local mimarisi ve desteklenen diller")
    print("  - Embedding modelleri ve vektor aramasi")
    print("  - ONNX Runtime ve model katalogu")
    print("  - RAG mimarisi ve SQLite")
    print("\nOrnek sorular:")
    print('  "Foundry Local hangi programlama dillerini destekler?"')
    print('  "Halusinasyon nasil azaltilir?"')
    print('  "Istanbul nufusu kactir?"   <- bilgi tabaninda YOK, ne diyecek?')
    print("\nCikmak icin 'cikis' yazin.\n")
    while True:
        try:
            soru = input("Soru    : ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not soru:
            continue
        if soru.lower() in ("cikis", "quit", "exit"):
            break
        toplam_baslangic = time.time()
        retrieval_baslangic = time.time()
        soru_vektoru = embedding_client.generate_embedding(soru).data[0].embedding
        secilen = en_benzer_k(soru_vektoru, belge_vektorleri, top_k=TOP_K)
        retrieval_suresi = time.time() - retrieval_baslangic
        print(f"\n  [Getirilen baglam - {retrieval_suresi:.2f} sn]")
        for sira, (indeks, skor) in enumerate(secilen, start=1):
            onizleme = BELGELER[indeks][:70]
            print(f"    [{sira}] benzerlik={skor:.3f} -> {onizleme}...")
        mesajlar = [
            {
                "role": "system",
                "content": SISTEM_SABLONU.format(baglam=baglam_olustur(secilen)),
            },
            {"role": "user", "content": soru},
        ]
        print("\n  Cevap   : ", end="", flush=True)
        uretim_baslangic = time.time()
        for chunk in sohbet_client.complete_streaming_chat(mesajlar):
            if not chunk.choices:
                continue
            icerik = chunk.choices[0].delta.content
            if icerik:
                print(icerik, end="", flush=True)
        uretim_suresi = time.time() - uretim_baslangic
        toplam_sure = time.time() - toplam_baslangic
        print(f"\n\n  [Getirme: {retrieval_suresi:.2f} sn | "
              f"Uretim: {uretim_suresi:.2f} sn | "
              f"Toplam: {toplam_sure:.2f} sn]\n")
    embedding_model.unload()
    sohbet_model.unload()
    print("Modeller bellekten kaldirildi. Gorusmek uzere.")
if __name__ == "__main__":
    main()
