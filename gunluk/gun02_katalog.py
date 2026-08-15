"""
Gun 2 - Foundry Local model katalogunu listeleme.
"""
from foundry_local_sdk import Configuration, FoundryLocalManager
def main() -> None:
    config = Configuration(
        app_name="local_rag_asistan",
        log_level="info",
    )
    print("Foundry Local baslatiliyor...")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance
    print("SDK baslatildi.\n")
    modeller = manager.catalog.list_models()
    print(f"Donaniminiz icin uygun {len(modeller)} model bulundu:\n")
    for model in modeller:
        print(f"  - {model.alias}")
    print("\nOnbellekteki (indirilmis) modeller:")
    onbellek = manager.catalog.get_cached_models()
    if onbellek:
        for model in onbellek:
            print(f"  - {model.alias}")
    else:
        print("  (henuz indirilmis model yok)")
    print("\nBellege yuklu modeller:")
    yuklu = manager.catalog.get_loaded_models()
    if yuklu:
        for model in yuklu:
            print(f"  - {model.alias}")
    else:
        print("  (yuklu model yok)")
if __name__ == "__main__":
    main()
