"""
Gün 1 — Geliştirme ortamı doğrulama scripti.

Amaç: Projeye başlamadan önce Python sürümü, sanal ortam durumu,
proje klasör yapısı ve sistem kaynaklarının uygunluğunu kontrol etmek.
"""

import sys
import os
import platform
from pathlib import Path

# Proje kök dizini: bu dosya gunluk/ içinde olduğu için bir üst klasör
PROJE_KOK = Path(__file__).resolve().parent.parent

# Projenin çalışması için gerekli minimum şartlar
MIN_PYTHON = (3, 11)
GEREKLI_KLASORLER = ["data/docs", "src", "gunluk", "tests"]


def baslik(metin: str) -> None:
    """Terminal çıktısını okunabilir kılmak için başlık basar."""
    print("\n" + "=" * 55)
    print(f"  {metin}")
    print("=" * 55)


def python_surumu_kontrol() -> bool:
    """Python sürümünün SDK için yeterli olup olmadığını kontrol eder."""
    surum = sys.version_info
    uygun = (surum.major, surum.minor) >= MIN_PYTHON

    print(f"Python sürümü      : {surum.major}.{surum.minor}.{surum.micro}")
    print(f"Gerekli minimum    : {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
    print(f"Durum              : {'UYGUN' if uygun else 'YETERSIZ'}")
    return uygun


def sanal_ortam_kontrol() -> bool:
    """
    Sanal ortamın aktif olup olmadığını kontrol eder.
    sys.prefix ile sys.base_prefix farklıysa venv aktiftir.
    """
    aktif = sys.prefix != sys.base_prefix

    print(f"Yorumlayıcı yolu   : {sys.executable}")
    print(f"Sanal ortam aktif  : {'EVET' if aktif else 'HAYIR'}")

    if not aktif:
        print("  UYARI: .\\.venv\\Scripts\\Activate.ps1 komutunu çalıştırın.")
    return aktif


def klasor_yapisi_kontrol() -> bool:
    """Proje için gerekli klasörlerin var olup olmadığını kontrol eder."""
    tamam = True
    for klasor in GEREKLI_KLASORLER:
        yol = PROJE_KOK / klasor
        var = yol.is_dir()
        print(f"  {'[+]' if var else '[-]'} {klasor}")
        if not var:
            tamam = False
    return tamam


def sistem_bilgisi() -> None:
    """Donanım ve işletim sistemi bilgilerini yazdırır."""
    print(f"İşletim sistemi    : {platform.system()} {platform.release()}")
    print(f"Mimari             : {platform.machine()}")
    print(f"İşlemci çekirdeği  : {os.cpu_count()}")

    # RAM bilgisi (Windows'ta ek kütüphane olmadan alınabilir)
    try:
        if platform.system() == "Windows":
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MemoryStatusEx()
            stat.dwLength = ctypes.sizeof(MemoryStatusEx)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

            toplam_gb = stat.ullTotalPhys / (1024 ** 3)
            bos_gb = stat.ullAvailPhys / (1024 ** 3)
            print(f"Toplam RAM         : {toplam_gb:.1f} GB")
            print(f"Boş RAM            : {bos_gb:.1f} GB")

            if toplam_gb < 8:
                print("  UYARI: Foundry Local için en az 8 GB RAM önerilir.")
    except Exception as hata:
        print(f"RAM bilgisi okunamadı: {hata}")


def paket_kontrol() -> None:
    """Kurulu olması beklenen paketleri kontrol eder."""
    paketler = {
        "numpy": "Vektör hesaplamaları",
        "foundry_local_sdk": "Yerel model çalıştırma (Gün 2'de kurulacak)",
        "streamlit": "Web arayüzü (Gün 15'te kullanılacak)",
    }

    for paket, aciklama in paketler.items():
        try:
            __import__(paket)
            print(f"  [+] {paket:22} — {aciklama}")
        except ImportError:
            print(f"  [ ] {paket:22} — henüz kurulu değil ({aciklama})")


def main() -> None:
    baslik("PROJE ORTAM KONTROLÜ")
    print(f"Proje kök dizini   : {PROJE_KOK}")

    baslik("1. PYTHON SÜRÜMÜ")
    python_ok = python_surumu_kontrol()

    baslik("2. SANAL ORTAM")
    venv_ok = sanal_ortam_kontrol()

    baslik("3. KLASÖR YAPISI")
    klasor_ok = klasor_yapisi_kontrol()

    baslik("4. SİSTEM BİLGİSİ")
    sistem_bilgisi()

    baslik("5. PAKET DURUMU")
    paket_kontrol()

    baslik("SONUÇ")
    if python_ok and venv_ok and klasor_ok:
        print("Ortam hazır. Gün 2'ye geçebilirsiniz.")
    else:
        print("Eksikler var. Yukarıdaki uyarıları giderin.")


if __name__ == "__main__":
    main()