"""
Embedding üretimi ve vektör benzerliği hesaplama modülü.

Bu modül, metinlerin vektöre çevrilmesi ve vektörler arası
kosinüs benzerliğinin hesaplanmasından sorumludur.
"""

import math
from typing import Sequence

import numpy as np


def cosine_benzerlik(a: Sequence[float], b: Sequence[float]) -> float:
    """
    İki vektör arasındaki kosinüs benzerliğini hesaplar (saf Python).

    Formül: (A · B) / (||A|| * ||B||)

    Returns:
        -1.0 ile 1.0 arasında bir değer. 1.0 = özdeş yön.
    """
    nokta_carpimi = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return nokta_carpimi / (norm_a * norm_b)


def cosine_benzerlik_toplu(sorgu: Sequence[float],
                           vektorler: Sequence[Sequence[float]]) -> np.ndarray:
    """
    Bir sorgu vektörünü çok sayıda vektörle TEK SEFERDE karşılaştırır.

    numpy ile vektörleştirilmiş hesap kullanır; büyük koleksiyonlarda
    saf Python döngüsüne göre çok daha hızlıdır.

    Returns:
        Her vektör için benzerlik skorlarını içeren numpy dizisi.
    """
    matris = np.asarray(vektorler, dtype=np.float32)      # (N, D)
    q = np.asarray(sorgu, dtype=np.float32)               # (D,)

    # Satır normları ve sorgu normu
    matris_normlari = np.linalg.norm(matris, axis=1)
    q_norm = np.linalg.norm(q)

    # Sıfıra bölmeyi engelle
    paydalar = matris_normlari * q_norm
    paydalar[paydalar == 0] = 1e-10

    return (matris @ q) / paydalar


def en_benzer_k(sorgu: Sequence[float],
                vektorler: Sequence[Sequence[float]],
                top_k: int = 3) -> list[tuple[int, float]]:
    """
    Sorguya en benzer K vektörün indeks ve skorlarını döndürür.

    Returns:
        [(indeks, skor), ...] — skora göre azalan sırada.
    """
    skorlar = cosine_benzerlik_toplu(sorgu, vektorler)

    # argsort küçükten büyüğe sıralar; tersine çevirip ilk K'yı alıyoruz
    sirali_indeksler = np.argsort(skorlar)[::-1][:top_k]

    return [(int(i), float(skorlar[i])) for i in sirali_indeksler]


def metinleri_vektore_cevir(client, metinler: list[str],
                            batch_boyutu: int = 32) -> list[list[float]]:
    """
    Metin listesini gruplar hâlinde vektöre çevirir.

    Çok büyük listeleri tek çağrıda göndermek bellek sorunu yaratabilir;
    bu yüzden batch_boyutu kadar parçalara bölünür.
    """
    tum_vektorler = []

    for i in range(0, len(metinler), batch_boyutu):
        grup = metinler[i:i + batch_boyutu]
        response = client.generate_embeddings(grup)
        tum_vektorler.extend(item.embedding for item in response.data)

    return tum_vektorler