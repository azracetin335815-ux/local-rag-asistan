"""Gün 2 — src/foundry_client.py modülünün doğrulanması."""

import sys
from pathlib import Path

# Proje kökünü Python yoluna ekle ki 'src' paketini bulabilelim
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.foundry_client import sohbet_modeli_al


def main() -> None:
    model, client = sohbet_modeli_al()

    messages = [
        {"role": "system", "content": "Tek cümleyle cevap ver."},
        {"role": "user", "content": "SQLite nedir?"},
    ]

    response = client.complete_chat(messages)
    print("\nCevap:", response.choices[0].message.content)

    model.unload()


if __name__ == "__main__":
    main()