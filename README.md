# Yerel RAG Asistanı

Microsoft **Foundry Local SDK** kullanılarak geliştirilmiş, tamamen çevrimdışı
çalışan, kendi dokümanlarınız üzerinden soru cevaplayan RAG
(Retrieval-Augmented Generation) tabanlı yapay zekâ asistanı.

Sistem, dil modelinin uydurma cevap üretmesini (halüsinasyon) uygulama
katmanında uygulanan denetimlerle engeller. Sorunun bilgi tabanındaki içeriğe
benzerliği belirlenen eşiğin altında kaldığında dil modeli hiç çalıştırılmadan
cevap verilmesi reddedilir.


---

## Özellikler

- **Tamamen yerel çalışma** — internet bağlantısı, API anahtarı veya bulut
  hesabı gerektirmez; veriler cihazdan çıkmaz
- **Kaynak gösterimi** — her cevap hangi dokümanın hangi bölümünden
  üretildiğini belirtir
- **Çok katmanlı halüsinasyon denetimi** — benzerlik eşiği, varlık doğrulama,
  sayısal değer kontrolü ve tek kaynak yeterliliği
- **Canlı doküman yükleme** — uygulama çalışırken PDF, Word, Markdown ve
  metin dosyası eklenebilir
- **İki arayüz** — komut satırı ve web (Streamlit)
- **Otomatik değerlendirme** — test seti ve metrik raporlama

---

## Mimari

```
Kullanıcı Sorusu
      │
      ▼
[1] Embedding modeli ile vektöre çevrilir
      │
      ▼
[2] SQLite'taki vektörler arasında kosinüs benzerliği araması
      │
      ├──► Benzerlik < 0.35  ══►  REDDET (model çalıştırılmaz)
      │
      ├──► Sorudaki varlık bağlamda yok  ══►  REDDET
      │
      ▼
[3] Bulunan parçalar sistem promptuna bağlam olarak yerleştirilir
      │
      ▼
[4] Yerel dil modeli cevabı üretir (temperature 0.1)
      │
      ▼
[5] Doğrulama: sayısal değer kontrolü, tek kaynak yeterliliği
      │
      ├──► Doğrulanamadı  ══►  Cevap gösterilmez, reddedilir
      │
      ▼
Cevap + Kaynak listesi
```

### Katmanlar

| Katman | Modül | Sorumluluk |
|---|---|---|
| Yapılandırma | `src/config.py` | Tüm parametreler |
| Model | `src/foundry_client.py` | Model yükleme ve yönetimi |
| Veri | `src/db.py` | SQLite işlemleri, vektör saklama |
| Parçalama | `src/chunker.py` | Doküman bölme |
| Okuma | `src/readers.py` | PDF/DOCX/MD/TXT metin çıkarma |
| Yükleme | `src/ingest_service.py` | Tek dosya işleme servisi |
| Getirme | `src/retriever.py` | Vektör arama, eşik denetimi |
| Prompt | `src/prompts.py` | Sistem mesajı şablonları |
| Denetim | `src/guardrails.py` | Halüsinasyon önleme |
| Orkestrasyon | `src/rag_engine.py` | Uçtan uca akış yönetimi |
| Sunum | `app_cli.py`, `app_web.py` | Kullanıcı arayüzleri |

---

## Kurulum

### Gereksinimler

- Windows 10/11 (macOS ve Linux için aşağıdaki nota bakınız)
- Python 3.11 veya üzeri
- En az 8 GB RAM
- Yaklaşık 10 GB boş disk alanı (model dosyaları için)

### Adımlar

```powershell
# 1. Sanal ortam oluştur ve etkinleştir
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\activate

# 2. Bağımlılıkları kur
pip install -r requirements.txt

# 3. Dokümanlarınızı ekleyin
#    data/docs/ klasörüne .md, .txt, .pdf veya .docx dosyalarını kopyalayın

# 4. Bilgi tabanını oluşturun
python ingest.py

# 5. Uygulamayı başlatın
python app_cli.py              # komut satırı
streamlit run app_web.py       # web arayüzü
```

> **macOS / Linux notu:** `requirements.txt` içindeki
> `foundry-local-sdk-winml` yerine `foundry-local-sdk` kullanılmalıdır.
> Python'daki import adı her iki durumda da `foundry_local_sdk` şeklindedir.

İlk çalıştırmada modeller otomatik indirilir. Bu işlem bağlantı hızına göre
birkaç dakika sürebilir ve yalnızca bir kez yapılır.

---

## Kullanım

### Komut satırı

```powershell
python app_cli.py
```

| Komut | İşlev |
|---|---|
| `/yardim` | Komut listesi |
| `/kaynak` | Son cevabın kaynaklarını detaylı göster |
| `/durum` | Bilgi tabanı istatistikleri |
| `/yukle <dosya>` | Yeni doküman ekle |
| `/yenile` | Bilgi tabanını yeniden yükle |
| `/gecmis` | Oturum geçmişi |
| `/cikis` | Çıkış |

### Web arayüzü

```powershell
streamlit run app_web.py
```

Tarayıcıda `http://localhost:8501` adresi açılır. Kenar çubuğundan dosya
yükleyebilir, sistem durumunu izleyebilirsiniz.

### Veri yükleme

```powershell
python ingest.py           # sadece değişen dosyaları işle
python ingest.py --tumu    # tüm dosyaları yeniden işle
```

### Değerlendirme

```powershell
python tests\evaluate.py           # metrikleri hesapla
python tests\evaluate.py --detay   # cevapları da göster
```

---

## Proje Yapısı

```
local-rag-asistan/
├─ data/
│  ├─ docs/                  Bilgi tabanı dokümanları
│  └─ knowledge.db           SQLite veritabanı
├─ src/                      Uygulama modülleri
│  ├─ config.py              Merkezi yapılandırma
│  ├─ foundry_client.py      Model yönetimi
│  ├─ db.py                  Veritabanı katmanı
│  ├─ chunker.py             Doküman parçalama
│  ├─ readers.py             Dosya okuma (PDF/DOCX/MD/TXT)
│  ├─ ingest_service.py      Tek dosya işleme
│  ├─ embeddings.py          Vektör üretimi ve benzerlik
│  ├─ retriever.py           Vektör arama
│  ├─ prompts.py             Prompt şablonları
│  ├─ guardrails.py          Halüsinasyon önleme
│  └─ rag_engine.py          Orkestrasyon motoru
├─ gunluk/                   Günlük öğrenme ve deneme scriptleri
├─ tests/
│  ├─ test_sorulari.json     Değerlendirme test seti
│  └─ evaluate.py            Otomatik değerlendirme
├─ sonuclar/                 Ölçüm raporları ve loglar
├─ ingest.py                 Veri yükleme hattı
├─ app_cli.py                Komut satırı uygulaması
├─ app_web.py                Web arayüzü
└─ requirements.txt
```

---

## Yapılandırma

Tüm parametreler `src/config.py` dosyasındadır.

| Parametre | Değer | Açıklama |
|---|---|---|
| `BENZERLIK_ESIGI` | 0.35 | Bu değerin altında cevap reddedilir |
| `TOP_K` | 3 | Bağlama eklenecek en fazla parça sayısı |
| `CHUNK_HEDEF_BOYUT` | 500 | Hedeflenen parça uzunluğu (karakter) |
| `CHUNK_MAKS_BOYUT` | 700 | Maksimum parça uzunluğu |
| `CHUNK_ORTUSME` | 120 | Ardışık parçalar arası tekrar |
| `SOHBET_MODELI` | phi-4-mini | Cevap üreten model |
| `EMBEDDING_MODELI` | qwen3-embedding-0.6b | Vektörleştirme modeli |

Cevap üretiminde `temperature=0.1` ve `max_tokens=200` kullanılır. Bu
değerler `src/rag_engine.py` içinde tanımlıdır.

Parametreleri değiştirdikten sonra `python tests\evaluate.py` çalıştırarak
etkisini ölçmeniz önerilir.

---

## Ölçüm Sonuçları

### Halüsinasyon Karşılaştırması

Aynı sorular, aynı model, farklı mimari ile yapılan kontrollü deney:

| Metrik | RAG öncesi | RAG + Guardrails |
|---|---|---|
| Reddetme oranı | %0 | %100 |
| **Halüsinasyon oranı** | **%100** | **%0** |
| Tutarsızlık oranı | %100 | %0 |

Gerçekte var olmayan beş varlık hakkında, her biri üç kez sorularak toplam
15 soru sorulmuştur.

### Otomatik Değerlendirme (19 soruluk test seti)

| Metrik | Değer |
|---|---|
| Genel başarı | %89.5 |
| **Kesinlik (Precision)** | **1.000** |
| Duyarlılık (Recall) | 0.818 |
| F1 skoru | 0.900 |
| Retrieval isabeti | %100 |

Kesinlik değerinin 1.000 olması, sistemin cevap verdiği hiçbir soruda
yanlış bilgi üretmediğini gösterir.

### Performans

| Aşama | Pay |
|---|---|
| Cevap üretimi | %93.7 |
| Embedding üretimi | %6.3 |
| Vektör arama + prompt + guardrails | %0.1 |

Reddedilen sorularda dil modeli çalıştırılmadığı için işlem süresi %95.8
kısalmaktadır (ortalama 23.4 saniye yerine 1 saniye).

---

## Halüsinasyon Önleme Yaklaşımı

Sistem, prompt talimatlarına güvenmek yerine uygulama katmanında dört
bağımsız denetim uygular:

**1. Benzerlik eşiği** — Sorunun bilgi tabanındaki içeriğe benzerliği 0.35'in
altındaysa dil modeli hiç çalıştırılmaz.

**2. Soru varlık denetimi** — Soruda geçen ürün/model kodu dokümanlarda
bulunmuyorsa cevap üretimine başlanmaz. Bu, modelin başka bir varlığın
verisini sorulan varlığa mal etmesini engeller.

**3. Sayısal değer doğrulaması** — Cevapta geçen sayılar bağlamda yoksa cevap
kullanıcıya gösterilmez.

**4. Tek kaynak yeterliliği** — Cevaptaki bilgiler farklı doküman
parçalarından birleştirilmişse engellenir. Bu, gerçek bilgilerin yanlış
bir iddia oluşturacak şekilde harmanlanmasını önler.

Bu denetimler kod seviyesinde çalıştığı için model davranışından bağımsız
ve tekrarlanabilirdir.

---

## Bilinen Sınırlar

- **Retrieval hassasiyeti:** Kısa ve tekil bilgi cümleleri embedding'de zayıf
  eşleşebilir; benzerlik skoru eşiğin altında kalabilir.
- **Konu çeşitliliği:** Bilgi tabanına konu dışı dokümanlar eklendikçe bazı
  sorularda yanlış doküman öne çıkabilir.
- **Cümle içi seçim:** Model doğru dokümandan yanlış cümleyi seçebilir. Sayısal
  doğrulama bunu yakalayamaz çünkü değer bağlamda gerçekten mevcuttur.
- **Yanlış öncüllü sorular:** Sistem düzeltme yapmak yerine reddetmeyi tercih
  edebilir. Prompt'a düzeltme yönergesi eklendiğinde modelin genel olarak
  aşırı temkinli davrandığı ölçülmüştür.
- **Taranmış PDF:** Görüntü tabanlı PDF dosyalarından metin çıkarılamaz;
  OCR desteği bulunmamaktadır.
- **Cevap süresi:** Soru başına 15-25 saniye. Sürenin %93.7'si model
  çıkarımında geçtiği için kod optimizasyonuyla iyileştirilemez.
- **Ölçek:** Brute-force vektör araması kullanılmaktadır. Yaklaşık 100.000
  parçanın üzerinde ANN (FAISS, HNSW) tabanlı bir çözüme geçilmesi gerekir.
- **Tek kullanıcı:** SQLite ve bellek içi vektör matrisi tek kullanıcılı
  senaryo için tasarlanmıştır.

---

## Gelecek Geliştirmeler

- Taranmış PDF'ler için OCR desteği
- Embedding ile anahtar kelime aramasını birleştiren hibrit arama
- Takip sorularını dil modeli yardımıyla yeniden yazma
- Yaklaşık en yakın komşu (ANN) indeksi ile ölçeklenebilirlik
- Çok kullanıcılı mimari ve rol tabanlı erişim kontrolü

---

## Kaynaklar

- [Foundry Local dokümantasyonu](https://learn.microsoft.com/en-us/azure/foundry-local/)
- [Foundry Local RAG örneği](https://learn.microsoft.com/en-us/azure/foundry-local/tutorials/tutorial-build-rag-app)
- [Foundry Local SDK referansı](https://learn.microsoft.com/en-us/azure/foundry-local/reference/reference-sdk-current)
- [Building Your First Local RAG Application with Foundry Local](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968)
