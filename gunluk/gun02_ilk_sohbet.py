"""
Gün 2 — İlk yerel model çıkarımı.

Akış: katalogdan model al → indir → belleğe yükle → soru sor → belleği boşalt.
Bu, projenin "model katmanı"nın en yalın hâlidir.
"""

import time
from foundry_local_sdk import Configuration, FoundryLocalManager

# Sohbet modelinin alias'ı. Kendi katalog çıktına göre değiştirebilirsin.
SOHBET_MODELI = "qwen2.5-0.5b"


def indirme_ilerlemesi(yuzde: float) -> None:
    """Model indirilirken ilerlemeyi aynı satırda günceller."""
    print(f"\rModel indiriliyor: {yuzde:.1f}%", end="", flush=True)


def main() -> None:
    # --- 1. SDK'yı başlat ---
    config = Configuration(app_name="local_rag_asistan")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance
    print("SDK başlatıldı.")

    # --- 2. Modeli katalogdan al ---
    model = manager.catalog.get_model(SOHBET_MODELI)
    print(f"Model seçildi: {SOHBET_MODELI}")
    print(f"Önbellekte mi? {'Evet' if model.is_cached else 'Hayır'}")

    # --- 3. İndir (önbellekteyse otomatik atlanır) ---
    baslangic = time.time()
    model.download(indirme_ilerlemesi)
    print()  # ilerleme satırından sonra alt satıra geç
    print(f"İndirme adımı süresi: {time.time() - baslangic:.1f} sn")

    # --- 4. Belleğe yükle ---
    baslangic = time.time()
    model.load()
    yukleme_suresi = time.time() - baslangic
    print(f"Modele RAM'e yüklendi ({yukleme_suresi:.1f} sn)")

    # --- 5. Sohbet istemcisini al ---
    chat_client = model.get_chat_client()

    # --- 6. Mesajları rollere ayırarak hazırla ---
    messages = [
        {
            "role": "system",
            "content": "Sen yardımsever bir asistansın. Kısa ve net cevap ver.",
        },
        {
            "role": "user",
            "content": "Retrieval-Augmented Generation nedir? Tek paragrafta açıkla.",
        },
    ]

    # --- 7. Cevabı üret (tek seferde) ---
    print("\n--- MODELİN CEVABI ---")
    baslangic = time.time()
    response = chat_client.complete_chat(messages)
    cevap_suresi = time.time() - baslangic

    print(response.choices[0].message.content)
    print("----------------------")
    print(f"Cevap üretme süresi: {cevap_suresi:.1f} sn")

    # --- 8. Belleği boşalt ---
    model.unload()
    print("\nModel bellekten kaldırıldı. (Disk önbelleği korunuyor.)")


if __name__ == "__main__":
    main()