"""
Gün 4 — Semantik benzerlik deneyi.

İki soruyu cevaplıyoruz:
  1. Anlamca benzer cümleler gerçekten yakın vektörler üretiyor mu?
  2. Semantik arama, anahtar kelime aramasının bulamadığını buluyor mu?
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embeddings import (
    cosine_benzerlik,
    en_benzer_k,
    metinleri_vektore_cevir,
)
from src.foundry_client import embedding_modeli_al

# Küçük bir bilgi tabanı — hiçbiri sorgudaki kelimeleri birebir içermiyor
BELGELER = [
    "Aracı durdurmak için fren pedalına kademeli olarak basınız.",
    "Motor yağı her 10.000 kilometrede bir değiştirilmelidir.",
    "Lastik hava basıncı ayda bir kez kontrol edilmelidir.",
    "Klima sistemi filtresi yılda bir defa yenilenir.",
    "Akü bağlantı uçları oksitlenmeye karşı temizlenmelidir.",
    "Far ampulü değişimi için kaput açılarak erişim sağlanır.",
]

# Bilerek dokümanlardaki kelimeleri KULLANMAYAN sorgular
SORGULAR = [
    "vasıtayı nasıl yavaşlatırım",        # "fren" kelimesi yok
    "yağ değişimi ne sıkışıklıkta yapılır",
    "tekerlek basıncı ölçümü",             # "lastik" değil "tekerlek"
]


def anahtar_kelime_ara(sorgu: str, belgeler: list[str]) -> list[int]:
    """
    Basit anahtar kelime araması: sorgudaki kelimelerden herhangi biri
    belgede geçiyorsa eşleşme sayılır. (Karşılaştırma amaçlı.)
    """
    kelimeler = [k.lower() for k in sorgu.split() if len(k) > 3]
    eslesme = []

    for indeks, belge in enumerate(belgeler):
        belge_kucuk = belge.lower()
        if any(kelime in belge_kucuk for kelime in kelimeler):
            eslesme.append(indeks)

    return eslesme


def main() -> None:
    print("Embedding modeli hazırlanıyor...")
    model, client = embedding_modeli_al()

    # --- 1. Belgeleri vektöre çevir ---
    baslangic = time.time()
    belge_vektorleri = metinleri_vektore_cevir(client, BELGELER)
    print(f"{len(BELGELER)} belge {time.time() - baslangic:.2f} sn'de gömüldü.")
    print(f"Vektör boyutu: {len(belge_vektorleri[0])}\n")

    # --- 2. Belgeler arası benzerlik matrisi ---
    print("=" * 60)
    print("BELGELER ARASI BENZERLİK MATRİSİ")
    print("=" * 60)
    print("     " + "".join(f"  B{i}  " for i in range(len(BELGELER))))
    for i, v1 in enumerate(belge_vektorleri):
        satir = f"B{i}   "
        for v2 in belge_vektorleri:
            satir += f"{cosine_benzerlik(v1, v2):5.2f} "
        print(satir)
    print("\n(Köşegen 1.00 olmalı — her belge kendisiyle özdeştir.)\n")

    # --- 3. Semantik arama vs anahtar kelime araması ---
    for sorgu in SORGULAR:
        print("=" * 60)
        print(f"SORGU: {sorgu}")
        print("=" * 60)

        # Anahtar kelime araması
        kelime_sonuc = anahtar_kelime_ara(sorgu, BELGELER)
        print("\n[Anahtar kelime araması]")
        if kelime_sonuc:
            for i in kelime_sonuc:
                print(f"   → {BELGELER[i]}")
        else:
            print("   → SONUÇ BULUNAMADI")

        # Semantik arama
        sorgu_vektoru = client.generate_embedding(sorgu).data[0].embedding
        sonuclar = en_benzer_k(sorgu_vektoru, belge_vektorleri, top_k=2)

        print("\n[Semantik arama]")
        for indeks, skor in sonuclar:
            print(f"   → [{skor:.3f}] {BELGELER[indeks]}")
        print()

    model.unload()


if __name__ == "__main__":
    main()