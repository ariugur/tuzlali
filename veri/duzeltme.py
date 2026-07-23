"""Kayit duzeltmeleri: TEK KAYNAK.

NEDEN AYRI DOSYA:
  Bugun tuzla_data.json'i yeniden uretemiyoruz -- tuzla_osm_raw.json ve
  isletmeler.json diskte yok, hat ancak Overpass'a yeni sorgu atarak calisir.
  O yuzden duzeltme dogrudan tuzla_data.json'a uygulaniyor (duzelt_uygula.py).
  Ama hat bir gun tekrar calistiginda duzeltmenin KAYBOLMAMASI lazim; bu yuzden
  birlestir.py de ayni dosyadan okuyup uyguluyor.
  Sozluk burada, uygulayan iki yerde. Kopya sozluk = yarisi guncellenmis duzeltme.

ANAHTAR NEDEN OSM ID:
  Ada gore eslestirseydik iki "Little Caesars" var (Mescit n5942892973,
  Aydintepe n13763417401); duzeltme ikisine birden vururdu.

NEDEN KONUM YOK:
  Konum bilerek duzeltilmiyor. Bkz. n13763417401 notu.

TEYIT KAYNAGI (operator karari):
  Yandex teyit zinciri DISINDA. Sebebi somut: bu projede Tuzla Oto Sanayi
  Sitesi'ni -- icinde 21 faal isletme olan koca siteyi -- "artik faal degil"
  gosterdi. Guvenilir degil.
  Google Maps ve Apple Maps duz HTTP ile teyide UYGUN DEGIL: ikisi de veriyi
  JS ile yukluyor, uydurma bir isletme sorgusu gercek isletmeyle ayni cevabi
  donuyor (Google ~179 KB "Google Haritalar" kabugu, Apple ~12 KB "Search"
  kabugu -- her iki durumda da ayni). Yani onlari cekmek teyit SAYILMAZ.
  Pratik zincir: (1) markanin/isletmenin KENDI sitesi -- test edilebiliyorsa,
  (2) operatorun kendi gozuyle Google/Apple'da gordugu ve bildirdigi bilgi.
  Ikisi de kayitta boyle etiketlenir; "bagimsiz dogrulandi" denmez.
"""

DUZELTME = {
    "n13763417401": {   # Little Caesars, Aydintepe
        "ad": "Little Caesars Tuzla Aydıntepe Şubesi",
        "telefon": "+90 216 266 22 52",
        "adres": "Aydıntepe Mah., Prof. Dr. Necmettin Erbakan Cad. No:7",
        "calisma_saatleri": "Her gün 10:00-02:00",
        "not": "Ad, telefon, adres ve saat operator bildirimi (Google Maps kaydi). "
               "Little Caesars'in kendi sitesi bakim modunda -- her yol ayni 16 KB "
               "sayfayi donduruyor, kaynak olarak kullanilamadi. KONUM "
               "DEGISTIRILMEDI: kayit zaten OSM dugumu (n13763417401) ve bildirilen "
               "koordinat ona ~37m uzakti; ayni bina. Taban veri ODbL, OSM'in kendi "
               "noktasini bir harita servisinin noktasiyla degistirmek icin sebep yok.",
    },
}

# Kullanicinin bildirdigi ama DOGRULANMAYIP alinmayan degerler.
# Burada duruyorlar ki ileride biri "bunu soylemistik" dediginde cevabi olsun.
REDDEDILEN = {
    "n13763417401": {
        "lat/lon": "40.85915697916251, 29.298295419728074 -- alinmadi: Google "
                   "kaynakli ve OSM/Yandex ikilisine gore aykiri (~37m). Ayrica "
                   "14 ondalik hane = nanometre hassasiyeti, sahte kesinlik.",
    },
}


def uygula(kayitlar):
    """DUZELTME'yi yerinde uygular. (duzeltilen, veride_olmayan_idler) doner."""
    n = 0
    for r in kayitlar:
        d = DUZELTME.get(r.get("id"))
        if not d:
            continue
        for alan in ("ad", "telefon", "adres", "calisma_saatleri"):
            if d.get(alan):
                r[alan] = d[alan]
        r["kapsam_notu"] = d["not"]
        r["dogrulandi"] = True
        if "+web" not in (r.get("kaynak") or ""):
            r["kaynak"] = (r.get("kaynak") or "") + "+web"
        n += 1
    idler = {r.get("id") for r in kayitlar}
    return n, [k for k in DUZELTME if k not in idler]
