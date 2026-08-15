# Yerel RAG Asistani
## Foundry Local SDK ile Cevrimdisi Dokuman Asistani
**Staj Projesi Sunumu**
Sure: 20 is gunu
---
## 1. Problem
Buyuk dil modelleri, egitim verisinde bulunmayan bilgiler soruldugunda
"bilmiyorum" demek yerine **inandirici ama uydurma** cevaplar uretir.
Buna **halusinasyon** denir.
### Olculen Durum (Gun 3 - Kontrol Grubu)
Gercekte var olmayan 5 varlik hakkinda, her biri 3 kez sorularak
toplam 15 soru soruldu:
| Metrik | Deger |
|---|---|
| Bilgisizligini belirten cevap | 0 / 15 |
| **Halusinasyon orani** | **%100** |
| Tutarsizlik orani (ayni soruya farkli cevap) | %100 |
**Bulgu:** Model hicbir soruda bilmedigini soylemedi. Ayni sorunun
tekrarinda farkli cevaplar vermesi, bilginin modelde bulunmadigini
ve uretilen metnin hatirlama degil olasiliksal tamamlama oldugunu
kanitlamaktadir.
---
## 2. Cozum Yaklasimi
### Neden RAG?
| Yontem | Artilari | Eksileri |
|---|---|---|
| Fine-tuning | Bilgi modele islenir | Pahali, GPU gerekir, veri degisince tekrar egitim |
| Baglam enjeksiyonu | Basit | Baglam penceresi sinirli |
| **RAG** | Anlik guncelleme, kaynak gosterimi, olceklenebilir | Getirme kalitesi kritik |
### Neden Foundry Local?
- Modeller **cihaz uzerinde** calisir, veri disari cikmaz
- Internet, API anahtari, bulut hesabi gerektirmez
- Donanim (CPU/GPU/NPU) otomatik optimize edilir
- SDK bagimsiz calisir, CLI kurulumu gerektirmez
---
## 3. Mimari
### Katmanli Tasarim
Her katman bagimsiz test edilebilir ve degistirilebilir.
Gun 20'de sohbet modeli degistirildiginde yalnizca **tek bir
yapilandirma satiri** guncellendi; diger katmanlarda degisiklik
gerekmedi.
---
## 4. Halusinasyonu Sifira Indirme
Tek bir onlem yerine **cok katmanli savunma** uygulandi:
| Katman | Mekanizma | Aksiyon |
|---|---|---|
| 1 | Benzerlik esigi (0.40) | REDDET - model hic calismaz |
| 2 | Baglam yeterliligi | REDDET |
| 3 | Dayanak orani (kelime ortusmesi) | UYAR |
| 4 | Sayisal deger dogrulamasi | UYAR |
| 5 | Kaynak gosterimi | Her cevapta zorunlu |
### Kritik Bulgu
Gun 11'de yapilan A/B testinde, sistem promptuna acik talimat
eklenmesinin reddetme davranisini iyilestirdigi ancak **tam
guvenilirlik saglamadigi** olculdu. Bu nedenle denetim, prompt
seviyesinden **uygulama koduna** tasindi.
**Prompt olasiliksaldir, kod deterministiktir.**
---
## 5. Sonuclar
### Halusinasyon Karsilastirmasi
| Metrik | Gun 3 (RAG yok) | Gun 13 (RAG + Guardrails) |
|---|---|---|
| Reddetme orani | %0 | %100 |
| **Halusinasyon orani** | **%100** | **%0** |
| Tutarsizlik orani | %100 | %0 |
*Her iki olcumde birebir ayni sorular ve olcutler kullanildi.
Degisen tek degisken sistem mimarisidir.*
### Sistem Basarimi (Gun 16 - Otomatik Degerlendirme)
| Metrik | Deger |
|---|---|
| Karar dogrulugu | (evaluate.py ciktisi) |
| Getirme isabeti | (evaluate.py ciktisi) |
| Halusinasyon orani | (evaluate.py ciktisi) |
### Esik Kalibrasyonu (Gun 10)
| Soru turu | Benzerlik skoru araligi |
|---|---|
| Bilgi tabaninda var | 0.50 - 0.63 |
| Bilgi tabaninda yok | 0.30 - 0.40 |
Esik, iki bolge arasindaki bosluga (0.40) yerlestirildi.
Yanlis kabul orani sifira indirilirken hicbir gecerli soru
reddedilmedi.
---
## 6. Teknik Kararlar ve Gerekceleri
| Karar | Gerekce |
|---|---|
| float32 vektor saklama | JSON'a gore %82, float64'e gore %50 tasarruf |
| Hibrit parcalama | Sabit boyut cumleyi boluyor, paragraf dengesiz |
| Brute-force arama | 0.04 ms/sorgu; ANN karmasikligi gereksiz |
| SQLite | Sunucusuz, tek dosya, cevrimdisi calisma ile uyumlu |
| Uyari / reddetme ayrimi | Kelime ortusmesi yanlis alarm verebilir |
| Erken donus | Reddedilen sorularda model calismaz - hem guvenli hem hizli |
---
## 7. Performans
Asama bazli olcumde toplam surenin buyuk bolumunun **dil modeli
cikarim** asamalarinda harcandigi tespit edildi. Uygulama kodunun
(vektor arama, prompt olusturma, guardrails) payi sinirli kaldi.
**Amdahl Yasasi:** Kod optimizasyonunun toplam sureye etkisi,
kodun toplam icindeki payiyla sinirlidir. Bu nedenle optimizasyon
onceligi model secimine ve gereksiz model cagrilarinin
onlenmesine verildi.
---
## 8. Bilinen Sinirlar
- Taranmis (goruntu tabanli) PDF dosyalarindan metin cikarilamaz
- Brute-force arama ~100.000 parcanin uzerinde yetersiz kalir
- Cok turlu takip sorulari sezgisel yontemle islenir
- Dayanak denetimi kelime ortusmesine dayandigi icin yeniden
  ifade durumlarinda yanlis uyari uretebilir
- Tek kullanicili senaryo icin tasarlanmistir
---
## 9. Gelecek Gelistirmeler
**Kisa vadeli:** OCR destegi, hibrit arama (embedding + BM25),
sorgu yeniden yazma
**Orta vadeli:** ANN indeksi (FAISS/HNSW), yeniden siralama modeli,
cok dilli destek
**Uzun vadeli:** Cok kullanicili mimari, rol tabanli erisim kontrolu,
insan geri bildirim dongusu
---
## 10. Ozet
20 is gununde, tamamen cevrimdisi calisan, kendi dokumanlari
uzerinden soru cevaplayan ve halusinasyonu olculebilir bicimde
ortadan kaldiran bir RAG sistemi gelistirildi.
**Temel bulgu:** Halusinasyon, dil modelinin egitimiyle degil,
**uygulama mimarisiyle** cozulebilir bir problemdir. Getirme
asamasinda uygulanan esik denetimi, modelden bagimsiz ve
tekrarlanabilir bir garanti saglar.
