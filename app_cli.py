"""
Yerel RAG Asistani - Komut Satiri Uygulamasi.
Kullanim:
    python app_cli.py
    python app_cli.py --renksiz     # ANSI renklerini kapat
"""
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import guardrails, prompts
from src.rag_engine import RagEngine
PROJE_KOK = Path(__file__).resolve().parent
LOG_YOLU = PROJE_KOK / "sonuclar" / "sohbet_log.jsonl"
# Takip sorusu tespiti icin ipuclari
TAKIP_IPUCLARI = ("peki", "ya ", "onun", "bunun", "o zaman", "peki ya")
class Renk:
    """ANSI renk kodlari. aktif=False ise tum kodlar bos string olur."""
    def __init__(self, aktif: bool = True):
        self.BASLIK = "\033[95m" if aktif else ""
        self.MAVI = "\033[94m" if aktif else ""
        self.YESIL = "\033[92m" if aktif else ""
        self.SARI = "\033[93m" if aktif else ""
        self.KIRMIZI = "\033[91m" if aktif else ""
        self.GRI = "\033[90m" if aktif else ""
        self.KALIN = "\033[1m" if aktif else ""
        self.SIFIR = "\033[0m" if aktif else ""
class Uygulama:
    """CLI uygulama durumu ve komut yonetimi."""
    def __init__(self, renkli: bool = True):
        self.r = Renk(renkli)
        self.motor = None
        self.son_sonuc = None
        self.gecmis = []          # [(soru, cevap, reddedildi), ...]
        self.oturum_baslangic = datetime.now()
    # --------------------------------------------------
    # Ekran yardimcilari
    # --------------------------------------------------
    def banner(self) -> None:
        r = self.r
        print(f"\n{r.BASLIK}{r.KALIN}" + "=" * 60)
        print("  YEREL RAG ASISTANI")
        print("  Foundry Local SDK ile cevrimdisi dokuman asistani")
        print("=" * 60 + f"{r.SIFIR}\n")
    def yardim(self) -> None:
        r = self.r
        print(f"\n{r.MAVI}KOMUTLAR{r.SIFIR}")
        komutlar = [
            ("/yukle <yol>", "Dosya yukle ve indeksle (md/txt/pdf/docx)"),
            ("/dokumanlar", "Yuklu dokumanlari listele"),
            ("/yardim", "Bu listeyi goster"),
            ("/kaynak", "Son cevabin kaynaklarini detayli goster"),
            ("/durum", "Bilgi tabani durumunu goster"),
            ("/yenile", "Veritabanini yeniden yukle (ingest sonrasi)"),
            ("/gecmis", "Bu oturumdaki sorulari listele"),
            ("/temizle", "Ekrani temizle"),
            ("/cikis", "Uygulamadan cik"),
        ]
        for komut, aciklama in komutlar:
            print(f"  {r.SARI}{komut:12}{r.SIFIR} {aciklama}")
        print()
    def durum_goster(self) -> None:
        r = self.r
        durum = self.motor.retriever.durum()
        gecen = (datetime.now() - self.oturum_baslangic).total_seconds()
        print(f"\n{r.MAVI}BILGI TABANI DURUMU{r.SIFIR}")
        print(f"  Parca sayisi    : {durum['parca_sayisi']}")
        print(f"  Dosya sayisi    : {durum['dosya_sayisi']}")
        print(f"  Vektor boyutu   : {durum['vektor_boyutu']}")
        print(f"  Benzerlik esigi : {durum['esik']}")
        print(f"  Getirilen parca : {self.motor.top_k} (top-k)")
        print(f"\n{r.MAVI}OTURUM{r.SIFIR}")
        print(f"  Sorulan soru    : {len(self.gecmis)}")
        print(f"  Gecen sure      : {gecen/60:.1f} dakika")
        print()
    def kaynak_goster(self) -> None:
        r = self.r
        if not self.son_sonuc:
            print(f"{r.GRI}  Henuz bir soru sorulmadi.{r.SIFIR}\n")
            return
        if self.son_sonuc["reddedildi"]:
            print(f"{r.GRI}  Son soru reddedildigi icin kaynak yok.")
            print(f"  Sebep: {self.son_sonuc['sebep']}{r.SIFIR}\n")
            return
        print(f"\n{r.MAVI}KAYNAKLAR{r.SIFIR}")
        for numara, k in enumerate(self.son_sonuc["kaynaklar"], start=1):
            print(f"\n  {r.SARI}[{numara}]{r.SIFIR} {k['dosya_adi']} "
                  f"(bolum {k['sira']}) - benzerlik: {k['skor']}")
            print(f"      {r.GRI}{k['onizleme']}...{r.SIFIR}")
        print()
    def gecmis_goster(self) -> None:
        r = self.r
        if not self.gecmis:
            print(f"{r.GRI}  Bu oturumda henuz soru sorulmadi.{r.SIFIR}\n")
            return
        print(f"\n{r.MAVI}OTURUM GECMISI{r.SIFIR}")
        for numara, (soru, _, reddedildi) in enumerate(self.gecmis, start=1):
            isaret = f"{r.KIRMIZI}[RED]{r.SIFIR}" if reddedildi else f"{r.YESIL}[OK] {r.SIFIR}"
            print(f"  {numara:2}. {isaret} {soru[:60]}")
        print()
    # --------------------------------------------------
    # Islevsel yardimcilar
    # --------------------------------------------------
    def takip_sorusu_mu(self, soru: str) -> bool:
        """
        Kisa ve baglama bagimli bir takip sorusu mu?
        Basit sezgisel: kisa + takip ipucu iceriyor + gecmis var.
        """
        if not self.gecmis:
            return False
        kucuk = soru.lower()
        return len(soru) < 35 and any(ip in kucuk for ip in TAKIP_IPUCLARI)
    def arama_sorgusu(self, soru: str) -> str:
        """
        Takip sorularinda onceki soruyla birlestirerek arama sorgusu uretir.
        Boylece 'peki garantisi?' gibi sorular baglamini kaybetmez.
        """
        if self.takip_sorusu_mu(soru):
            onceki = self.gecmis[-1][0]
            return f"{onceki} {soru}"
        return soru
    def logla(self, sonuc: dict) -> None:
        """Soru-cevap kaydini JSONL formatinda dosyaya ekler."""
        kayit = {
            "zaman": datetime.now().isoformat(timespec="seconds"),
            "soru": sonuc["soru"],
            "cevap": sonuc["cevap"],
            "reddedildi": sonuc["reddedildi"],
            "sebep": sonuc.get("sebep"),
            "en_yuksek_skor": sonuc.get("en_yuksek_skor"),
            "kaynaklar": [
                f"{k['dosya_adi']}#{k['sira']}" for k in sonuc["kaynaklar"]
            ],
            "sureler": sonuc["sureler"],
        }
        try:
            LOG_YOLU.parent.mkdir(parents=True, exist_ok=True)
            with LOG_YOLU.open("a", encoding="utf-8") as dosya:
                dosya.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        except Exception:
            pass          # loglama basarisiz olsa da uygulama devam etmeli
    # --------------------------------------------------
    # Soru isleme
    # --------------------------------------------------
    def soruyu_isle(self, soru: str) -> None:
        r = self.r
        sorgu = self.arama_sorgusu(soru)
        if sorgu != soru:
            print(f"{r.GRI}  (takip sorusu - arama: '{sorgu[:50]}...'){r.SIFIR}")
        kaynaklar_gosterildi = False
        son_sonuc = None
        for tur, veri in self.motor.answer_streaming(sorgu):
            if tur == "red":
                print(f"\n  {r.KIRMIZI}{veri['cevap']}{r.SIFIR}")
                print(f"  {r.GRI}(en yuksek benzerlik: {veri['en_yuksek_skor']}, "
                      f"esik: {self.motor.retriever.esik}){r.SIFIR}\n")
                son_sonuc = veri
                # Reddedilen soruda gercek soruyu kaydet
                son_sonuc["soru"] = soru
                break
            if tur == "kaynaklar":
                ozet = ", ".join(
                    f"{k['dosya_adi']}#{k['sira']} ({k['skor']})" for k in veri
                )
                print(f"  {r.GRI}Kaynaklar: {ozet}{r.SIFIR}")
                print(f"\n  {r.YESIL}Cevap:{r.SIFIR} ", end="", flush=True)
                kaynaklar_gosterildi = True
            elif tur == "parca":
                print(veri, end="", flush=True)
            elif tur == "bitti":
                son_sonuc = veri
                son_sonuc["soru"] = soru
                # Guardrails denetimi
                # Motor zaten tam baglamla denetim yapti; onu kullan.
                # (Burada tekrar hesaplamak, kisaltilmis onizleme metni
                #  kullanildigi icin yanlis uyari uretiyordu.)
                denetim = veri.get("denetim") or {
                    "guvenli": True, "dayanak_orani": 0.0,
                    "uydurma_sayilar": [], "uyarilar": []
                }
                son_sonuc["denetim"] = denetim
                print()
                if not denetim["guvenli"]:
                    print(f"\n  {r.SARI}{guardrails.uyari_metni(denetim)}{r.SIFIR}")
                s = veri["sureler"]
                print(f"\n  {r.GRI}[getirme: {s['getirme']}s | "
                      f"uretim: {s['uretim']}s | toplam: {s['toplam']}s | "
                      f"dayanak: {denetim['dayanak_orani']}]{r.SIFIR}\n")
        if son_sonuc:
            self.son_sonuc = son_sonuc
            self.gecmis.append((soru, son_sonuc["cevap"], son_sonuc["reddedildi"]))
            self.logla(son_sonuc)
    # --------------------------------------------------
    # Ana dongu
    # --------------------------------------------------
    def calistir(self) -> None:
        r = self.r
        self.banner()
        print("Sistem baslatiliyor...")
        self.motor = RagEngine(sessiz=True)
        if not self.motor.hazir:
            print(f"{r.KIRMIZI}HATA: Bilgi tabani bos.{r.SIFIR}")
            print("Once 'python ingest.py' komutunu calistirin.\n")
            return
        durum = self.motor.retriever.durum()
        print(f"{r.YESIL}Hazir.{r.SIFIR} "
              f"{durum['parca_sayisi']} parca / {durum['dosya_sayisi']} dosya "
              f"yuklendi. Esik: {durum['esik']}")
        print(f"{r.GRI}Komutlar icin /yardim yazin.{r.SIFIR}\n")
        while True:
            try:
                girdi = input(f"{r.KALIN}Soru >{r.SIFIR} ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if not girdi:
                continue
            # --- Komut mu? ---
            if girdi.startswith("/"):
                komut = girdi.lower().split()[0]
                if komut in ("/cikis", "/exit", "/quit"):
                    break
                elif komut in ("/yardim", "/help", "/?"):
                    self.yardim()
                elif komut == "/kaynak":
                    self.kaynak_goster()
                elif komut == "/durum":
                    self.durum_goster()
                elif komut == "/gecmis":
                    self.gecmis_goster()
                elif komut == "/temizle":
                    print("\033[2J\033[H", end="")
                    self.banner()
                elif komut == "/yukle":
                    parcalar = girdi.split(maxsplit=1)
                    if len(parcalar) < 2:
                        print(f"  {r.KIRMIZI}Kullanim: /yukle <dosya_yolu>{r.SIFIR}")
                        print(f"  {r.GRI}Ornek: /yukle C:\\Belgeler\\rapor.pdf{r.SIFIR}\n")
                    else:
                        from src import ingest_service

                        hedef = parcalar[1].strip().strip('"').strip("'")
                        print(f"  Isleniyor: {hedef}")

                        rapor = ingest_service.yoldan_isle(
                            hedef, self.motor.emb_client
                        )

                        if rapor["basarili"]:
                            if rapor["durum"] == "atlandi":
                                print(f"  {r.SARI}{rapor['mesaj']}{r.SIFIR}\n")
                            else:
                                print(f"  {r.YESIL}Basarili:{r.SIFIR} "
                                      f"{rapor['dosya_adi']} - "
                                      f"{rapor['parca_sayisi']} parca "
                                      f"({rapor['karakter_sayisi']:,} karakter)")
                                adet = self.motor.yenile()
                                print(f"  Bilgi tabani guncellendi: "
                                      f"{adet} parca\n")
                        else:
                            print(f"  {r.KIRMIZI}Hata:{r.SIFIR} "
                                  f"{rapor['mesaj']}\n")

                elif komut == "/dokumanlar":
                    from src import ingest_service

                    dokumanlar = ingest_service.yuklu_dokumanlar()
                    if not dokumanlar:
                        print(f"  {r.GRI}Yuklu dokuman yok.{r.SIFIR}\n")
                    else:
                        print(f"\n{r.MAVI}YUKLU DOKUMANLAR{r.SIFIR}")
                        for d in dokumanlar:
                            print(f"  {d['dosya_adi']:34} "
                                  f"{d['parca_sayisi']:>3} parca  {d['tarih']}")
                        print()
                elif komut == "/yenile":
                    print("  Bilgi tabani yeniden yukleniyor...")
                    adet = self.motor.yenile()
                    print(f"  {r.YESIL}Tamamlandi.{r.SIFIR} {adet} parca yuklendi.\n")
                else:
                    print(f"  {r.KIRMIZI}Bilinmeyen komut: {komut}{r.SIFIR}")
                    print(f"  {r.GRI}/yardim ile komut listesini gorebilirsiniz.{r.SIFIR}\n")
                continue
            # --- Normal soru ---
            self.soruyu_isle(girdi)
        # --- Kapanis ---
        print(f"\n{r.MAVI}Oturum ozeti{r.SIFIR}")
        print(f"  Sorulan soru : {len(self.gecmis)}")
        reddedilen = sum(1 for _, _, red in self.gecmis if red)
        print(f"  Cevaplanan   : {len(self.gecmis) - reddedilen}")
        print(f"  Reddedilen   : {reddedilen}")
        if LOG_YOLU.exists():
            print(f"  Log dosyasi  : {LOG_YOLU}")
        self.motor.kapat()
        print(f"\n{r.GRI}Modeller bellekten kaldirildi. Gorusmek uzere.{r.SIFIR}\n")
def main() -> None:
    renkli = "--renksiz" not in sys.argv
    Uygulama(renkli=renkli).calistir()
if __name__ == "__main__":
    main()
