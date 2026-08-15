"""
Yerel RAG Asistani - Streamlit Web Arayuzu.
Calistirma:
    streamlit run app_web.py
"""
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import guardrails, prompts
from src.rag_engine import RagEngine
# ==========================================================
# SAYFA AYARLARI
# ==========================================================
st.set_page_config(
    page_title="Yerel RAG Asistani",
    page_icon="::",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ==========================================================
# MOTOR YUKLEME (onbellekli)
# ==========================================================
@st.cache_resource(show_spinner="Modeller yukleniyor, lutfen bekleyin...")
def motoru_yukle():
    """
    RAG motorunu bir kez yukler ve onbellekte tutar.
    Streamlit her etkilesimde scripti bastan calistirdigi icin
    bu dekorator olmadan modeller surekli yeniden yuklenirdi.
    """
    return RagEngine(sessiz=True)
# ==========================================================
# OTURUM DURUMU
# ==========================================================
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []
if "istatistik" not in st.session_state:
    st.session_state.istatistik = {"toplam": 0, "cevaplanan": 0, "reddedilen": 0}
# ==========================================================
# ANA GOVDE
# ==========================================================
st.title("Yerel RAG Asistani")
st.caption("Foundry Local SDK ile cevrimdisi calisan dokuman asistani - "
           "cevaplar yalnizca yuklenen dokumanlara dayanir")
motor = motoru_yukle()
if not motor.hazir:
    st.error(
        "Bilgi tabani bos gorunuyor. Terminalde `python ingest.py` "
        "komutunu calistirdiktan sonra kenar cubugundaki "
        "**Bilgi tabanini yenile** butonuna basin."
    )
    st.stop()
# ==========================================================
# KENAR CUBUGU
# ==========================================================
with st.sidebar:
    st.header("Sistem Durumu")
    durum = motor.retriever.durum()
    sutun1, sutun2 = st.columns(2)
    sutun1.metric("Parca", durum["parca_sayisi"])
    sutun2.metric("Dosya", durum["dosya_sayisi"])
    st.metric("Benzerlik esigi", durum["esik"])
    st.caption(f"Vektor boyutu: {durum['vektor_boyutu']}")
    st.divider()
    st.header("Oturum")
    ist = st.session_state.istatistik
    sutun1, sutun2, sutun3 = st.columns(3)
    sutun1.metric("Soru", ist["toplam"])
    sutun2.metric("Cevap", ist["cevaplanan"])
    sutun3.metric("Red", ist["reddedilen"])
    st.divider()
    st.header("Dokuman Yukle")

    yuklenen = st.file_uploader(
        "Dosya secin",
        type=["md", "txt", "pdf", "docx"],
        accept_multiple_files=True,
        help="PDF, Word, Markdown veya duz metin. En fazla 10 MB.",
    )

    if yuklenen and st.button("Yukle ve indeksle", type="primary",
                              use_container_width=True):
        from src import ingest_service

        ilerleme = st.progress(0.0)
        durum_kutusu = st.empty()
        raporlar = []

        for indeks, dosya in enumerate(yuklenen, start=1):
            durum_kutusu.info(f"Isleniyor: {dosya.name}")

            rapor = ingest_service.yuklenen_dosyayi_isle(
                dosya.getvalue(), dosya.name, motor.emb_client
            )
            raporlar.append(rapor)
            ilerleme.progress(indeks / len(yuklenen))

        durum_kutusu.empty()
        ilerleme.empty()

        for rapor in raporlar:
            if rapor["basarili"] and rapor["durum"] != "atlandi":
                st.success(
                    f"{rapor['dosya_adi']}: {rapor['parca_sayisi']} parca "
                    f"({rapor['durum']})"
                )
            elif rapor["durum"] == "atlandi":
                st.info(f"{rapor['dosya_adi']}: {rapor['mesaj']}")
            else:
                st.error(f"{rapor['dosya_adi']}: {rapor['mesaj']}")

        adet = motor.yenile()
        st.success(f"Bilgi tabani guncellendi: {adet} parca")
        st.rerun()

    # Yuklu dokumanlar listesi
    with st.expander("Yuklu dokumanlar"):
        from src import ingest_service as _svc

        dokumanlar = _svc.yuklu_dokumanlar()
        if not dokumanlar:
            st.caption("Henuz dokuman yok.")
        else:
            for d in dokumanlar:
                sutun_a, sutun_b = st.columns([3, 1])
                sutun_a.write(f"**{d['dosya_adi']}**")
                sutun_a.caption(f"{d['parca_sayisi']} parca - {d['tarih']}")
                if sutun_b.button("Sil", key=f"sil_{d['id']}"):
                    _svc.dokumani_kaldir(d["dosya_adi"], dosyayi_da_sil=True)
                    motor.yenile()
                    st.rerun()
    st.divider()
    st.header("Islemler")
    if st.button("Bilgi tabanini yenile", use_container_width=True):
        adet = motor.yenile()
        st.success(f"{adet} parca yeniden yuklendi.")
        st.rerun()
    if st.button("Sohbeti temizle", use_container_width=True):
        st.session_state.mesajlar = []
        st.session_state.istatistik = {
            "toplam": 0, "cevaplanan": 0, "reddedilen": 0
        }
        st.rerun()
    st.divider()
    st.caption(
        "Sistem, sorunun bilgi tabanindaki icerige benzerligi esigin "
        "altinda kaldiginda dil modelini hic calistirmadan cevap "
        "vermeyi reddeder."
    )
# ==========================================================
# SOHBET GECMISI
# ==========================================================
for mesaj in st.session_state.mesajlar:
    with st.chat_message(mesaj["rol"]):
        st.markdown(mesaj["icerik"])
        # Reddedilen cevaplarda bilgi kutusu
        if mesaj.get("reddedildi"):
            st.info(
                f"Benzerlik skoru {mesaj.get('skor', 0)} olup "
                f"{durum['esik']} esiginin altinda kaldigi icin cevap "
                f"uretilmedi."
            )
        # Guardrails uyarilari
        if mesaj.get("uyarilar"):
            for uyari in mesaj["uyarilar"]:
                st.warning(uyari)
        # Kaynak paneli
        if mesaj.get("kaynaklar"):
            with st.expander(f"Kaynaklar ({len(mesaj['kaynaklar'])} alinti)"):
                for numara, k in enumerate(mesaj["kaynaklar"], start=1):
                    st.markdown(
                        f"**[{numara}] {k['dosya_adi']}** "
                        f"(bolum {k['sira']}) - benzerlik: `{k['skor']}`"
                    )
                    st.caption(k["onizleme"] + "...")
        # Sure bilgisi
        if mesaj.get("sureler"):
            s = mesaj["sureler"]
            st.caption(
                f"Getirme: {s['getirme']} sn | Uretim: {s['uretim']} sn | "
                f"Toplam: {s['toplam']} sn"
            )
# ==========================================================
# SORU GIRISI VE CEVAP URETIMI
# ==========================================================
soru = st.chat_input("Dokumanlar hakkinda bir soru sorun...")
if soru:
    # --- Kullanici mesajini goster ve kaydet ---
    st.session_state.mesajlar.append({"rol": "user", "icerik": soru})
    with st.chat_message("user"):
        st.markdown(soru)
    # --- Cevap uret ---
    with st.chat_message("assistant"):
        # Generator'i sararak metin disi bilgileri yakala
        yakalanan = {"kaynaklar": [], "sonuc": None, "red": None}
        def metin_akisi():
            for tur, veri in motor.answer_streaming(soru):
                if tur == "kaynaklar":
                    yakalanan["kaynaklar"] = veri
                elif tur == "parca":
                    yield veri
                elif tur == "bitti":
                    yakalanan["sonuc"] = veri
                elif tur == "red":
                    yakalanan["red"] = veri
        with st.spinner("Dokumanlar taraniyor..."):
            cevap_metni = st.write_stream(metin_akisi())
        # --- REDDEDILDI ---
        if yakalanan["red"]:
            red = yakalanan["red"]
            st.markdown(red["cevap"])
            st.info(
                f"Benzerlik skoru {red['en_yuksek_skor']} olup "
                f"{durum['esik']} esiginin altinda kaldigi icin cevap "
                f"uretilmedi."
            )
            st.session_state.mesajlar.append({
                "rol": "assistant",
                "icerik": red["cevap"],
                "reddedildi": True,
                "skor": red["en_yuksek_skor"],
                "kaynaklar": [],
                "sureler": red["sureler"],
            })
            st.session_state.istatistik["toplam"] += 1
            st.session_state.istatistik["reddedilen"] += 1
        # --- CEVAPLANDI ---
        elif yakalanan["sonuc"]:
            sonuc = yakalanan["sonuc"]
            kaynaklar = yakalanan["kaynaklar"]
            # Motor zaten tam baglamla denetim yapti; onu kullan.
            # (Kisaltilmis onizleme metniyle yeniden hesaplamak yanlis
            #  uyari uretiyordu.)
            denetim = sonuc.get("denetim") or {
                "guvenli": True, "dayanak_orani": 0.0,
                "uydurma_sayilar": [], "uyarilar": []
            }

            uyarilar = []
            if not denetim["guvenli"]:
                for uyari in denetim["uyarilar"]:
                    st.warning(uyari)
                    uyarilar.append(uyari)
            # Kaynak paneli
            if kaynaklar:
                with st.expander(f"Kaynaklar ({len(kaynaklar)} alinti)"):
                    for numara, k in enumerate(kaynaklar, start=1):
                        st.markdown(
                            f"**[{numara}] {k['dosya_adi']}** "
                            f"(bolum {k['sira']}) - benzerlik: `{k['skor']}`"
                        )
                        st.caption(k["onizleme"] + "...")
            s = sonuc["sureler"]
            st.caption(
                f"Getirme: {s['getirme']} sn | Uretim: {s['uretim']} sn | "
                f"Toplam: {s['toplam']} sn | "
                f"Dayanak orani: {denetim['dayanak_orani']}"
            )
            st.session_state.mesajlar.append({
                "rol": "assistant",
                "icerik": cevap_metni,
                "reddedildi": False,
                "kaynaklar": kaynaklar,
                "uyarilar": uyarilar,
                "sureler": sonuc["sureler"],
            })
            st.session_state.istatistik["toplam"] += 1
            st.session_state.istatistik["cevaplanan"] += 1
