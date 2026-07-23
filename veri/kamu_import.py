#!/usr/bin/env python3
"""Tuzla Belediyesi Acik Veri -> veri/kamu.json

Kamu / yasam noktalari (isletme DEGIL): cami-mescit, muhtarlik, acil durum
toplanma alani, semt pazari, ACEM kurs merkezi. Bunlar tuzla_data.json'a
KARISMIYOR -- "1554 isletme" sayaci ve marka bozulmasin diye ayri dosya.

KAYNAK: https://veri.tuzla.bel.tr (CKAN acik veri portali, CC-BY).
Ham CSV'ler veri/kaynak_acikveri/ altinda; portalin SSL sertifikasi suresi
dolu oldugu icin veriyi bir kez `curl -k` ile cekip commit ettik. Yenilemek
icin ilgili dataset'in "download" linkinden CSV'yi ayni dosya adiyla degistir.

Dataset kaynaklari (portal id):
  camiler.csv     -> ibadethaneler
  muhtarliklar.csv-> mahalle-muhtarliklari
  toplanma.csv    -> acil-durum-toplanma-alanlari
  pazar.csv       -> tuzla-belediyesi-pazar-yerleri
  acem.csv        -> acem-kurs-merkezleri
  parklar.csv     -> tuzla-belediyesinde-bulunan-parklar-ve-imkanlar
"""
import csv, json, os, re, sys

KAYNAK_DIR = os.path.join(os.path.dirname(__file__), "kaynak_acikveri")
CIKTI = os.path.join(os.path.dirname(__file__), "kamu.json")

MAHALLELER = ["Akfırat", "Anadolu", "Aydınlı", "Aydıntepe", "Cami",
              "Evliya Çelebi", "Fatih", "İçmeler", "İstasyon", "Mescit",
              "Mimar Sinan", "Orhanlı", "Orta", "Postane", "Şifa",
              "Tepeören", "Yayla"]


def _norm(s):
    """Turkce duyarsiz eslesme icin sadelestir."""
    tr = str.maketrans("çğıiöşüÇĞİIÖŞÜ", "cgiiosucgiiosu")
    return s.translate(tr).lower()


_MAH_NORM = [(_norm(m), m) for m in MAHALLELER]


def mahalle_bul(*metinler):
    """Adres/ad icinde gecen resmi mahalle adini yakalar (best-effort)."""
    hepsi = _norm(" ".join(m or "" for m in metinler)).replace(
        "mimarsinan", "mimar sinan").replace("postahane", "postane").replace(
        "e.celebi", "evliya celebi")
    for nm, ad in _MAH_NORM:
        if nm in hepsi:
            return ad
    return ""


def slug(s):
    tr = str.maketrans("çğıöşüÇĞİIÖŞÜ", "cgiosucgiiosu")
    s = s.translate(tr).lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def sayi(x):
    """'40,818' ya da '40.818' -> float; bos/gecersiz -> None."""
    if x is None:
        return None
    x = str(x).strip().replace(",", ".")
    try:
        v = float(x)
    except ValueError:
        return None
    return v if v else None


def oku(dosya, ayrac):
    yol = os.path.join(KAYNAK_DIR, dosya)
    with open(yol, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=ayrac))


def temiz(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def _tr_upper(c):
    return {"i": "İ", "ı": "I"}.get(c, c.upper())


def _tr_lower(c):
    return {"I": "ı", "İ": "i"}.get(c, c.lower())


def tr_baslik(s):
    """Turkce-duyarli baslik bicimi: ALL CAPS kamu adlarini okunur yapar."""
    kelimeler = []
    for w in temiz(s).split(" "):
        if not w:
            continue
        kelimeler.append(_tr_upper(w[0]) + "".join(_tr_lower(c) for c in w[1:]))
    return " ".join(kelimeler)


def bosluk_ekle(s):
    """'Mah.şifa' -> 'Mah. şifa'; noktadan sonra bitisik harfi ayirir."""
    return re.sub(r"\.([A-Za-zÇĞİıÖŞÜçğöşü])", r". \1", s or "")


def cami_adi(s):
    """CAPS cami adi -> baslik; nokta-bosluk + kisaltma + mahalle duzeltir.
    Cami CSV'si dogru Turkce buyuk harf (İ/Ş) tuttugu icin baslik bicimi temiz."""
    s = tr_baslik(bosluk_ekle(s))
    s = re.sub(r"\bMh\.", "Mah.", s)
    s = s.replace("Mimarsinan", "Mimar Sinan")
    s = re.sub(r"\bC\.$", "Camii", s)          # "... Çizmeci C." -> "Camii"
    s = re.sub(r"\bCami$", "Camii", s)
    return s


# ACEM CSV'si ASCII-only CAPS ("MIMARSINAN","SIFA") -- İ/ı/Ş mekanik geri
# gelmiyor. 9 kayit oldugu icin bariz-amaclanan dogru Turkce yazim elle verildi.
# Anahtar = slug (İ/I ayrimindan bagimsiz eslessin).
ACEM_DUZELT = {
    "aydinli-acem-merkezi": "Aydınlı AÇEM Merkezi",
    "tuzla-belediyesi-ek-hizmet-binasi-orhanli": "Tuzla Belediyesi Ek Hizmet Binası / Orhanlı",
    "emlak-konutlari-1-etap": "Emlak Konutları 1. Etap AÇEM Merkezi",
    "yayla-mah-acem-merkezi": "Yayla Mah. AÇEM Merkezi",
    "sifa-park-avm-acem-merkezi": "Şifa Park AVM AÇEM Merkezi",
    "sifa-kultur-merkezi-acem-merk": "Şifa Kültür Merkezi AÇEM Merkezi",
    "icmeler-mh-acem-merkezi": "İçmeler AÇEM Merkezi",
    "mimarsinan-acem-merkezi-ahmet-yesevi-semt-konagi": "Mimar Sinan AÇEM Merkezi (Ahmet Yesevi Semt Konağı)",
    "kadin-koordinasyon-merkezi": "Kadın Koordinasyon Merkezi (AÇEM)",
}


def acem_adi(s):
    ham = temiz(s)
    return ACEM_DUZELT.get(slug(ham), tr_baslik(ham))


def kayit(tur, ad, adres, lat, lon, mah, note):
    ad = temiz(ad)
    return {
        "id": slug(tur) + "-" + slug(ad),
        "tur": tur,
        "ad": ad,
        "adres": temiz(adres),
        "mahalle": mah or mahalle_bul(adres, ad),
        "lat": lat,
        "lon": lon,
        "not": temiz(note),
    }


def main():
    out = []

    # --- Cami & Mescit --- "CAMI ADI;ADRES;ENLEM;BOYLAM"
    for r in oku("camiler.csv", ";"):
        out.append(kayit("Cami & Mescit", cami_adi(r["CAMI ADI"]), r["ADRES"],
                         sayi(r["ENLEM"]), sayi(r["BOYLAM"]), "", ""))

    # --- Muhtarlik --- "MUHTARLIK ADI,ADRES,ENLEM,BOYLAM"
    for r in oku("muhtarliklar.csv", ","):
        out.append(kayit("Muhtarlık", r["MUHTARLIK ADI"], r["ADRES"],
                         sayi(r["ENLEM"]), sayi(r["BOYLAM"]), "", ""))

    # --- Toplanma Alani --- basliklar: AD, MAHALLE ADI, ENLEM, BOYLAM, TOPLAM ALAN
    for r in oku("toplanma.csv", ","):
        alan = temiz(r.get("TOPLAM ALAN") or r.get("KULLANIM ALANI") or "")
        mah = temiz(r.get("MAHALLE ADI", "")).replace("Mh.", "").replace(
            "Mah.", "").strip()
        note = f"≈{alan} m² toplanma alanı" if alan else "Acil durum toplanma alanı"
        out.append(kayit("Toplanma Alanı", r["AD"], "",
                         sayi(r["ENLEM"]), sayi(r["BOYLAM"]),
                         mahalle_bul(mah, r["AD"]), note))

    # --- Semt Pazari (KOORDINAT YOK) --- "PAZAR ADI;ESNAF SAYISI;KURULUS GUNU;KURULDUGU YER"
    for r in oku("pazar.csv", ";"):
        gun = temiz(r["KURULUS GUNU"])
        esnaf = temiz(r["ESNAF SAYISI"])
        note = f"Kuruluş günü: {gun}"
        if esnaf:
            note += f" · {esnaf} esnaf"
        out.append(kayit("Pazar Yeri", r["PAZAR ADI"], r["KURULDUGU YER"],
                         None, None, mahalle_bul(r["PAZAR ADI"], r["KURULDUGU YER"]),
                         note))

    # --- ACEM Kurs Merkezi --- basliklar: ANNE VE COCUK EGITIM MERKEZLERI, ADRES, ENLEM, BOYLAM, BASLANGIC SAATI, BITIS SAATI
    for r in oku("acem.csv", ","):
        bas = temiz(r.get("BASLANGIC SAATI", ""))[:5]
        bit = temiz(r.get("BITIS SAATI", ""))[:5]
        note = f"Kurs saati {bas}–{bit}" if bas and bit else ""
        out.append(kayit("AÇEM Kurs Merkezi", acem_adi(r["ANNE VE COCUK EGITIM MERKEZLERI"]),
                         r["ADRES"], sayi(r["ENLEM"]), sayi(r["BOYLAM"]), "", note))

    # --- Parklar --- MAHALLE,ADRES,PARKLARIMIZ,ENLEM,BOYLAM,...,saha/oyun sayilari
    IMKAN = [("HALI SAHA", "Halı saha"), ("FUTBOL SAHASI", "Futbol sahası"),
             ("BASKETBOL SAHASI", "Basketbol"), ("TENIS KORTU", "Tenis kortu"),
             ("ÇOK AMACLI SAHA", "Çok amaçlı saha"),
             ("COCUK OYUN GRUBU SAYISI", "Çocuk oyun grubu"),
             ("FITNESS GRUBU SAYISI", "Fitness")]

    def poz(v):
        try:
            return int(float(str(v).replace(",", ".").strip() or 0)) > 0
        except ValueError:
            return False

    for r in oku("parklar.csv", ","):
        var = [ad for kol, ad in IMKAN if poz(r.get(kol))]
        note = " · ".join(var) if var else "Park"
        out.append(kayit("Park", tr_baslik(r["PARKLARIMIZ"]), tr_baslik(r.get("ADRES", "")),
                         sayi(r["ENLEM"]), sayi(r["BOYLAM"]),
                         mahalle_bul(r.get("MAHALLE", "")), note))

    json.dump(out, open(CIKTI, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    ozet = {}
    kord = 0
    for k in out:
        ozet[k["tur"]] = ozet.get(k["tur"], 0) + 1
        if k["lat"]:
            kord += 1
    print(f"{len(out)} kayıt -> {CIKTI}")
    for t, n in ozet.items():
        print(f"  {t:22} {n}")
    print(f"Koordinatlı: {kord}/{len(out)}")


if __name__ == "__main__":
    main()
