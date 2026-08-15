"""
Gun 3 - Akisli (streaming) cok turlu sohbet donguesu.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.foundry_client import sohbet_modeli_al
GECMIS_LIMITI = 6
SISTEM_MESAJI = (
    "Sen yardimsever bir asistansin. Turkce, kisa ve net cevap ver. "
    "Emin olmadigin konularda bunu acikca belirt."
)
def gecmisi_kirp(mesajlar: list) -> list:
    sistem = mesajlar[0]
    kalan = mesajlar[1:]
    if len(kalan) > GECMIS_LIMITI:
        kalan = kalan[-GECMIS_LIMITI:]
    return [sistem] + kalan
def main() -> None:
    print("Model hazirlaniyor...")
    model, client = sohbet_modeli_al()
    mesajlar = [{"role": "system", "content": SISTEM_MESAJI}]
    print("\nSohbet basladi. Cikmak icin 'cikis' yazin.\n")
    while True:
        try:
            soru = input("Siz     : ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not soru:
            continue
        if soru.lower() in ("cikis", "quit", "exit"):
            break
        mesajlar.append({"role": "user", "content": soru})
        mesajlar = gecmisi_kirp(mesajlar)
        print("Asistan : ", end="", flush=True)
        baslangic = time.time()
        parcalar = []
        for chunk in client.complete_streaming_chat(mesajlar):
            if not chunk.choices:
                continue
            icerik = chunk.choices[0].delta.content
            if icerik:
                print(icerik, end="", flush=True)
                parcalar.append(icerik)
        sure = time.time() - baslangic
        tam_cevap = "".join(parcalar)
        print(f"\n          [{sure:.1f} sn, {len(tam_cevap)} karakter]\n")
        mesajlar.append({"role": "assistant", "content": tam_cevap})
    model.unload()
    print("Sohbet sonlandi, model bellekten kaldirildi.")
if __name__ == "__main__":
    main()
