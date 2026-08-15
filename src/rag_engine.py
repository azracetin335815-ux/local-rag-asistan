"""
RAG orkestrasyon motoru.
Getirme, prompt olusturma ve cevap uretme adimlarini birlestirerek
uctan uca soru-cevap islevi saglar.
"""
import time
from src import config
from src import guardrails, prompts
from src.foundry_client import embedding_modeli_al, sohbet_modeli_al
from src.retriever import Retriever
VARSAYILAN_TOP_K = config.TOP_K
class RagEngine:
    """
    RAG sistemi ana motoru.
    Kullanim:
        motor = RagEngine()
        sonuc = motor.answer("bakim araligi kac saat?")
        print(sonuc["cevap"])
        motor.kapat()
    """
    def __init__(self, top_k: int = VARSAYILAN_TOP_K, sessiz: bool = False):
        self.top_k = top_k
        self.sessiz = sessiz
        if not sessiz:
            print("Embedding modeli yukleniyor...")
        self.emb_model, self.emb_client = embedding_modeli_al()
        if not sessiz:
            print("Sohbet modeli yukleniyor...")
        self.chat_model, self.chat_client = sohbet_modeli_al()

        # OpenAI uyumlu istemci (temperature ve max_tokens destegi icin)
        from src.foundry_client import openai_istemcisi_al, SOHBET_MODELI
        try:
            self.openai_client = openai_istemcisi_al()
            self.model_alias = SOHBET_MODELI
            if not sessiz:
                print("Sunucu modu hazir (temperature destegi aktif).")
        except Exception as hata:
            self.openai_client = None
            if not sessiz:
                print(f"Sunucu modu baslatilamadi, standart mod kullanilacak: {hata}")

        if not sessiz:
            print("Bilgi tabani yukleniyor...")
        self.retriever = Retriever()
        if not sessiz:
            durum = self.retriever.durum()
            print(f"Hazir: {durum['parca_sayisi']} parca, "
                  f"{durum['dosya_sayisi']} dosya, esik={durum['esik']}")
    # ------------------------------------------------------
    # Yardimci metotlar
    # ------------------------------------------------------
    @property
    def hazir(self) -> bool:
        """Bilgi tabani sorgulanabilir durumda mi?"""
        return self.retriever.hazir
    def yenile(self) -> int:
        """
        Bilgi tabanini veritabanindan yeniden yukler.
        ingest.py calistirildiktan sonra cagrilmalidir.
        """
        return self.retriever.yenile()
    def _soruyu_vektorlestir(self, soru: str):
        return self.emb_client.generate_embedding(soru).data[0].embedding
    def _bos_sonuc(self, soru: str, sebep: str, getirme_suresi: float,
                   en_yuksek_skor: float = 0.0) -> dict:
        """Reddetme durumunda dondurulecek standart sonuc yapisi."""
        return {
            "soru": soru,
            "cevap": prompts.BILGI_YOK_CEVABI,
            "kaynaklar": [],
            "kaynak_ozeti": "",
            "reddedildi": True,
            "sebep": sebep,
            "en_yuksek_skor": en_yuksek_skor,
            "sureler": {
                "getirme": round(getirme_suresi, 3),
                "uretim": 0.0,
                "toplam": round(getirme_suresi, 3),
            },
        }
    def _kaynak_listesi(self, parcalar: list) -> list:
        """Getirilen parcalari kullaniciya gosterilecek bicime cevirir."""
        return [
            {
                "dosya_adi": p["dosya_adi"],
                "sira": p["sira"],
                "skor": round(p["skor"], 3),
                "onizleme": p["metin"].replace("\n", " ")[:120],
            }
            for p in parcalar
        ]
    # ------------------------------------------------------
    # Ana metotlar
    # ------------------------------------------------------
    def getir(self, soru: str) -> tuple:
        """
        Sadece getirme adimini calistirir (cevap uretmez).
        Returns:
            (parcalar, getirme_suresi, en_yuksek_skor)
        """
        baslangic = time.time()
        vektor = self._soruyu_vektorlestir(soru)
        parcalar = self.retriever.ara(vektor, top_k=self.top_k)
        en_yuksek = self.retriever.en_yuksek_skor(vektor)
        sure = time.time() - baslangic
        return parcalar, sure, en_yuksek
    def answer(self, soru: str) -> dict:
        """
        Soruyu uctan uca cevaplar (bloklayan mod).
        Returns:
            Yapilandirilmis sonuc sozlugu.
        """
        toplam_baslangic = time.time()
        if not soru or not soru.strip():
            return self._bos_sonuc(soru, "bos_soru", 0.0)
        if not self.hazir:
            return self._bos_sonuc(soru, "bos_bilgi_tabani", 0.0)
        # --- 1. GETIRME ---
        parcalar, getirme_suresi, en_yuksek = self.getir(soru)
        # --- 2. ESIK DENETIMI (erken donus) ---
        if not parcalar:
            return self._bos_sonuc(soru, "benzerlik_esigi",
                                   getirme_suresi, en_yuksek)
        # --- 2b. SORU VARLIK DENETIMI ---
        # Soruda gecen bir varlik baglamda yoksa, model baska bir
        # varligin verisini sorulana mal edebilir. Uretim yapilmaz.
        baglam_on = prompts.baglam_bicimlendir(parcalar)
        varlik_ok, varlik_sebep = guardrails.soru_varliklari_baglamda_mi(
            soru, baglam_on
        )
        if not varlik_ok:
            sonuc = self._bos_sonuc(soru, "varlik_bulunamadi",
                                    getirme_suresi, en_yuksek)
            sonuc["engel_sebebi"] = varlik_sebep
            return sonuc

        # --- 3. PROMPT OLUSTURMA ---
        mesajlar = prompts.mesajlari_olustur(soru, parcalar)
        # --- 4. CEVAP URETIMI ---
       
        uretim_baslangic = time.time()
        if self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=self.model_alias,
                messages=mesajlar,
                temperature=0.1,
                max_tokens=200,
            )
        else:
            response = self.chat_client.complete_chat(mesajlar)
        cevap = response.choices[0].message.content.strip()
        uretim_suresi = time.time() - uretim_baslangic
        # --- 5. DOGRULAMA (ENGELLEYICI) ---
        baglam_metni = prompts.baglam_bicimlendir(parcalar)
        guvenilir, engel_sebebi = guardrails.cevap_guvenilir_mi(
            cevap, baglam_metni, soru
        )
        if guvenilir:
            parca_metinleri = [p["metin"] for p in parcalar]
            guvenilir, engel_sebebi = guardrails.tek_kaynakla_destekleniyor_mu(
                cevap, parca_metinleri, soru
            )

        if not guvenilir:
            sonuc = self._bos_sonuc(soru, "dogrulama_basarisiz",
                                    getirme_suresi, en_yuksek)
            sonuc["engellenen_cevap"] = cevap
            sonuc["engel_sebebi"] = engel_sebebi
            return sonuc

        # Ekstra bilgi: uyari niteliginde denetim raporu (engellemeyen, bilgilendiren)
        denetim = guardrails.cevabi_denetle(cevap, baglam_metni)

        toplam_sure = time.time() - toplam_baslangic

        return {
            "soru": soru,
            "cevap": cevap,
            "kaynaklar": self._kaynak_listesi(parcalar),
            "kaynak_ozeti": prompts.kaynak_ozeti(parcalar),
            "reddedildi": False,
            "sebep": None,
            "denetim": denetim,
            "en_yuksek_skor": round(en_yuksek, 3),
            "sureler": {
                "getirme": round(getirme_suresi, 3),
                "uretim": round(uretim_suresi, 3),
                "toplam": round(toplam_sure, 3),
            },
        }
    def answer_streaming(self, soru: str):
        """
        Soruyu cevaplar ve cevabi parca parca akitir (generator).
        Kullanim:
            for tur, veri in motor.answer_streaming(soru):
                if tur == "kaynaklar": ...
                elif tur == "parca":   print(veri, end="")
                elif tur == "bitti":   print(veri["sureler"])
        Yayin turleri:
            ("kaynaklar", [...])  - getirme tamamlandi
            ("red", sonuc)        - esik gecilmedi, uretim yapilmayacak
            ("parca", metin)      - cevap parcasi
            ("bitti", sonuc)      - tamamlandi, ozet bilgi
        """
        toplam_baslangic = time.time()
        if not soru or not soru.strip():
            yield ("red", self._bos_sonuc(soru, "bos_soru", 0.0))
            return
        if not self.hazir:
            yield ("red", self._bos_sonuc(soru, "bos_bilgi_tabani", 0.0))
            return
        parcalar, getirme_suresi, en_yuksek = self.getir(soru)
        if not parcalar:
            yield ("red", self._bos_sonuc(soru, "benzerlik_esigi",
                                          getirme_suresi, en_yuksek))
            return
        yield ("kaynaklar", self._kaynak_listesi(parcalar))
        mesajlar = prompts.mesajlari_olustur(soru, parcalar)
        uretim_baslangic = time.time()
        parcacikar = []
        for chunk in self.chat_client.complete_streaming_chat(mesajlar):
            # SDK bazen bos choices listesi donebilir - atla
            if not chunk.choices:
                continue
            icerik = chunk.choices[0].delta.content
            if icerik:
                parcacikar.append(icerik)
                yield ("parca", icerik)
        uretim_suresi = time.time() - uretim_baslangic
        toplam_sure = time.time() - toplam_baslangic
        yield ("bitti", {
            "denetim": guardrails.cevabi_denetle(
                "".join(parcacikar).strip(),
                prompts.baglam_bicimlendir(parcalar)
            ),
            "soru": soru,
            "cevap": "".join(parcacikar).strip(),
            "kaynaklar": self._kaynak_listesi(parcalar),
            "kaynak_ozeti": prompts.kaynak_ozeti(parcalar),
            "reddedildi": False,
            "sebep": None,
            "en_yuksek_skor": round(en_yuksek, 3),
            "sureler": {
                "getirme": round(getirme_suresi, 3),
                "uretim": round(uretim_suresi, 3),
                "toplam": round(toplam_sure, 3),
            },
        })
    def kapat(self) -> None:
        """Modelleri bellekten kaldirir."""
        try:
            self.emb_model.unload()
            self.chat_model.unload()
        except Exception:
            pass
