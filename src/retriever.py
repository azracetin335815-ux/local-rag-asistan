"""
Getirme (retrieval) modulu.
Veritabanindaki vektorler uzerinde kosinus benzerligi aramasi yapar
ve sorguya en alakali dokuman parcalarini dondurur.
"""
from src import config
import numpy as np
from src import db
# Varsayilan ayarlar
BENZERLIK_ESIGI = config.BENZERLIK_ESIGI
VARSAYILAN_TOP_K = 3
# Benzerlik esigi.
# Gun 5 olcumlerine gore: ilgili sorular 0.48-0.73, ilgisizler 0.20-0.24.
# Esik bu iki bolge arasindaki bosluga yerlestirildi.

class Retriever:
    """
    Vektor arama motoru.
    Vektorler bellekte tutulur; veritabani degistiginde yenile()
    cagrilarak guncellenir.
    """
    def __init__(self, esik: float = BENZERLIK_ESIGI):
        self.esik = esik
        self.kayitlar = []
        self.matris = None          # normalize edilmis vektor matrisi
        self.yenile()
    def yenile(self) -> int:
        """
        Veritabanindan tum vektorleri yukler ve normalize eder.
        Normalizasyon sayesinde sorgu aninda bolme islemi gerekmez.
        Returns:
            Yuklenen parca sayisi.
        """
        self.kayitlar, ham_matris = db.tum_vektorleri_yukle()
        if len(self.kayitlar) == 0:
            self.matris = None
            return 0
        # Birim uzunluga normalize et (satir bazinda)
        normlar = np.linalg.norm(ham_matris, axis=1, keepdims=True)
        normlar[normlar == 0] = 1e-10          # sifira bolmeyi engelle
        self.matris = (ham_matris / normlar).astype(np.float32)
        return len(self.kayitlar)
    @property
    def hazir(self) -> bool:
        """Arama yapilabilir durumda mi?"""
        return self.matris is not None and len(self.kayitlar) > 0
    def ara(self, sorgu_vektoru, top_k: int = VARSAYILAN_TOP_K,
            esik_uygula: bool = True) -> list:
        """
        Sorgu vektorune en benzer parcalari dondurur.
        Args:
            sorgu_vektoru : sorgunun embedding vektoru
            top_k         : en fazla kac parca dondurulecek
            esik_uygula   : True ise esigin altindaki sonuclar elenir
        Returns:
            [{"metin", "skor", "dosya_adi", "sira", "id"}, ...]
            Skora gore azalan sirada. Esik uygulaniyorsa bos liste donebilir.
        """
        if not self.hazir:
            return []
        q = np.asarray(sorgu_vektoru, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm
        # Normalize vektorlerde kosinus benzerligi = nokta carpimi
        skorlar = self.matris @ q
        # En yuksek skorlu top_k indeksi bul
        adet = min(top_k, len(skorlar))
        adaylar = np.argpartition(skorlar, -adet)[-adet:]
        adaylar = adaylar[np.argsort(skorlar[adaylar])[::-1]]
        sonuclar = []
        for indeks in adaylar:
            skor = float(skorlar[indeks])
            if esik_uygula and skor < self.esik:
                continue
            kayit = self.kayitlar[int(indeks)]
            sonuclar.append({
                "id": kayit["id"],
                "metin": kayit["metin"],
                "dosya_adi": kayit["dosya_adi"],
                "sira": kayit["sira"],
                "skor": skor,
            })
        return sonuclar
    def en_yuksek_skor(self, sorgu_vektoru) -> float:
        """
        Esikten bagimsiz olarak en yuksek benzerlik skorunu dondurur.
        Esik ayarlamasi ve hata ayiklama icin kullanilir.
        """
        if not self.hazir:
            return 0.0
        q = np.asarray(sorgu_vektoru, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return 0.0
        return float(np.max(self.matris @ (q / q_norm)))
    def durum(self) -> dict:
        """Retriever'in mevcut durumunu ozetler."""
        dosyalar = {k["dosya_adi"] for k in self.kayitlar}
        return {
            "parca_sayisi": len(self.kayitlar),
            "dosya_sayisi": len(dosyalar),
            "vektor_boyutu": int(self.matris.shape[1]) if self.hazir else 0,
            "esik": self.esik,
        }
