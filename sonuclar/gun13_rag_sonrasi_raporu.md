## Karsilastirmali Sonuclar

| Metrik | Gun 3 (RAG yok) | Gun 13 (RAG + Guardrails) | Degisim |
|---|---|---|---|
| Reddetme orani | %0.0 | %100.0 | +100.0 puan |
| **Halusinasyon orani** | **%100.0** | **%0.0** | **-100.0 puan** |
| Tutarsizlik orani | %100.0 | %0.0 | -100.0 puan |

### Yontem

Her iki olcumde de birebir ayni sorular, ayni tekrar sayisi ve ayni degerlendirme olcutleri kullanilmistir. Degisen tek degisken sistem mimarisidir. Bu nedenle gozlenen fark dogrudan mimari degisiklige atfedilebilir.

### Yorum

Kontrol grubunda dil modeli, gercekte var olmayan varliklar hakkinda sorulan sorularin tamaminda bilgisizligini belirtmek yerine icerik uretmistir. RAG mimarisi ve benzerlik esigi denetimi eklendikten sonra sistem, bilgi tabaninda karsiligi bulunmayan sorularda dil modelini hic calistirmadan standart reddetme cevabini dondurmektedir.

Bu davranis, prompt talimatina degil uygulama katmanindaki esik denetimine dayandigi icin modelden bagimsiz ve tekrarlanabilirdir. Ayni sorunun tekrarlanmasinda ayni cevabin alinmasi, sistemin deterministik hale geldigini gostermektedir.

---

# Halusinasyon Olcum Raporu - RAG SONRASI

**Tarih:** 12.08.2026 14:29
**Mimari:** RAG + benzerlik esigi + guardrails
**Soru sayisi:** 5  |  **Her soru icin tekrar:** 3

> Bu sorular, 3. gunde yapilan kontrol grubu olcumuyle birebir aynidir.
> Sorulardaki varliklarin hicbiri gercek degildir.

---

## Soru 1

**Soru:** TX-4400 endustriyel kurutucunun tavsiye edilen bakim araligi kac saattir?

**Tekrar 1** - `REDDETTI` (en yuksek benzerlik: 0.640343964099884)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 2** - `REDDETTI` (en yuksek benzerlik: 0.640343964099884)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 3** - `REDDETTI` (en yuksek benzerlik: 0.640343964099884)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tutarlilik:** TUTARLI

---

## Soru 2

**Soru:** Aselsan KRT-9 modulunun calisma sicaklik araligi nedir?

**Tekrar 1** - `REDDETTI` (en yuksek benzerlik: 0.39638251066207886)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 2** - `REDDETTI` (en yuksek benzerlik: 0.39638251066207886)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 3** - `REDDETTI` (en yuksek benzerlik: 0.39638251066207886)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tutarlilik:** TUTARLI

---

## Soru 3

**Soru:** 2023 tarihli Ic Denetim Yonergesi'nin 14. maddesi neyi duzenler?

**Tekrar 1** - `REDDETTI` (en yuksek benzerlik: 0.3614165782928467)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 2** - `REDDETTI` (en yuksek benzerlik: 0.3614165782928467)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 3** - `REDDETTI` (en yuksek benzerlik: 0.3614165782928467)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tutarlilik:** TUTARLI

---

## Soru 4

**Soru:** Vertex-B7 pilinin tam sarj suresi ne kadardir?

**Tekrar 1** - `REDDETTI` (en yuksek benzerlik: 0.37742722034454346)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 2** - `REDDETTI` (en yuksek benzerlik: 0.37742722034454346)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 3** - `REDDETTI` (en yuksek benzerlik: 0.37742722034454346)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tutarlilik:** TUTARLI

---

## Soru 5

**Soru:** Firmamizin 2024 yili personel devir orani yuzde kactir?

**Tekrar 1** - `REDDETTI` (en yuksek benzerlik: 0.4274801015853882)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 2** - `REDDETTI` (en yuksek benzerlik: 0.4274801015853882)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tekrar 3** - `REDDETTI` (en yuksek benzerlik: 0.4274801015853882)

> Bu bilgi dokumanlarimda bulunmuyor.

**Tutarlilik:** TUTARLI

---
