"""
Foundry Local model katmanı.

Bu modül, SDK'nın başlatılmasını ve model yükleme işlemlerini tek yerde toplar.
Projenin diğer tüm modülleri modeli buradan alır.
"""

from foundry_local_sdk import Configuration, FoundryLocalManager
from src import config

SOHBET_MODELI = config.SOHBET_MODELI
EMBEDDING_MODELI = config.EMBEDDING_MODELI

# Manager'ın iki kez başlatılmasını önlemek için bayrak
_baslatildi = False


def manager_al():
    """
    Foundry Local yöneticisini döndürür.
    İlk çağrıda SDK'yı başlatır, sonraki çağrılarda mevcut örneği verir.
    """
    global _baslatildi

    if not _baslatildi:
        config = Configuration(app_name="local_rag_asistan")
        FoundryLocalManager.initialize(config)
        _baslatildi = True

    return FoundryLocalManager.instance


def model_hazirla(alias: str, sessiz: bool = False):
    """
    Verilen alias'a sahip modeli indirir (gerekirse) ve belleğe yükler.

    Args:
        alias: Model kısa adı (ör. "qwen2.5-0.5b")
        sessiz: True ise indirme ilerlemesi yazdırılmaz

    Returns:
        Yüklenmiş model nesnesi
    """
    manager = manager_al()
    model = manager.catalog.get_model(alias)

    if not model.is_cached:
        if not sessiz:
            model.download(
                lambda p: print(f"\r[{alias}] indiriliyor: {p:.1f}%",
                                end="", flush=True)
            )
            print()
        else:
            model.download(lambda p: None)

    if not model.is_loaded:
        model.load()
        if not sessiz:
            print(f"[{alias}] belleğe yüklendi.")

    return model


def sohbet_modeli_al():
    """Sohbet modelini hazırlar ve chat istemcisiyle birlikte döndürür."""
    model = model_hazirla(SOHBET_MODELI)
    return model, model.get_chat_client()


def embedding_modeli_al():
    """Embedding modelini hazırlar ve embedding istemcisiyle birlikte döndürür."""
    model = model_hazirla(EMBEDDING_MODELI)
    return model, model.get_embedding_client()


def openai_istemcisi_al():
    """
    Foundry Local'i sunucu modunda baslatir ve OpenAI uyumlu istemci dondurur.
    Bu yontem temperature ve max_tokens gibi uretim parametrelerinin
    ayarlanmasina imkan verir (complete_chat bunu desteklemiyor).
    """
    import openai
    manager = manager_al()
    try:
        manager.start_web_service()
    except Exception:
        pass
    return openai.OpenAI(base_url=f"{manager.urls[0]}/v1", api_key="local-key")