"""
Gün 4 — Embedding üretimi ve vektörlerin incelenmesi.

Amaç: Embedding modelini yüklemek, metinleri vektöre çevirmek,
vektörlerin yapısını (boyut, değer aralığı) gözlemlemek ve
tek çağrı ile toplu çağrının hız farkını ölçmek.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.foundry_client import embedding_modeli_al

ORNEK_CUMLELER = [
    "Foundry Local modelleri cihaz üzerinde çalıştırır.",
    "Yapay zekâ modelleri internet olmadan yerel olarak çalışabilir.",
    "SQLite sunucusuz ve hafif bir veritabanı motorudur.",
    "Kedimiz bütün gün bahçede uyudu.",
    "Enflasyon oranı geçen çeyrekte yükseldi.",
]


def main() -> None:
    print("Embedding modeli hazırlanıyor...")
    model, client = embedding_modeli_al()

    # --- 1. Tek bir metni vektöre çevir ---
    print("\n--- TEK METİN ---")
    response = client.generate_embedding(ORNEK_CUMLELER[0])
    vektor = response.data[0].embedding

    print(f"Metin        : {ORNEK_CUMLELER[0]}")
    print(f"Vektör boyutu: {len(vektor)}")
    print(f"İlk 8 değer  : {[round(d, 4) for d in vektor[:8]]}")
    print(f"En küçük     : {min(vektor):.4f}")
    print(f"En büyük     : {max(vektor):.4f}")

    # --- 2. Determinizm kontrolü: aynı metin, aynı vektör mü? ---
    print("\n--- DETERMİNİZM KONTROLÜ ---")
    tekrar = client.generate_embedding(ORNEK_CUMLELER[0]).data[0].embedding
    ayni = all(abs(a - b) < 1e-6 for a, b in zip(vektor, tekrar))
    print(f"Aynı metin iki kez gömüldü, vektörler özdeş mi? {'EVET' if ayni else 'HAYIR'}")
    print("(Sohbet modelinden farklı olarak embedding modeli deterministiktir.)")

    # --- 3. Tek tek çağrı süresi ---
    print("\n--- HIZ KARŞILAŞTIRMASI ---")
    baslangic = time.time()
    tek_tek = []
    for cumle in ORNEK_CUMLELER:
        tek_tek.append(client.generate_embedding(cumle).data[0].embedding)
    tek_tek_sure = time.time() - baslangic

    # --- 4. Toplu (batch) çağrı süresi ---
    baslangic = time.time()
    toplu_response = client.generate_embeddings(ORNEK_CUMLELER)
    toplu = [item.embedding for item in toplu_response.data]
    toplu_sure = time.time() - baslangic

    print(f"Tek tek ({len(ORNEK_CUMLELER)} çağrı): {tek_tek_sure:.3f} sn")
    print(f"Toplu   (1 çağrı)         : {toplu_sure:.3f} sn")
    if toplu_sure > 0:
        print(f"Hızlanma                  : {tek_tek_sure / toplu_sure:.1f}x")

    # --- 5. Sonuçların aynı olduğunu doğrula ---
    fark = max(
        abs(a - b)
        for v1, v2 in zip(tek_tek, toplu)
        for a, b in zip(v1, v2)
    )
    print(f"İki yöntem arasındaki maksimum fark: {fark:.8f}")

    model.unload()


if __name__ == "__main__":
    main()