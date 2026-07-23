#!/usr/bin/env python3
"""Istanbul Noter Odasi resmi dizini -> Tuzla noterleri.

NEDEN ADRESTEN SUZUYORUZ: Tuzla'nin kendi noterligi yok. Ilcedeki noterler
Kartal adliyesine bagli, o yuzden "Kartal 6. Noteri" gibi anilirlar.
Adi "Tuzla" diye arasan sifir sonuc alirsin. Tek gecerli olcut ADRES.

KOORDINAT: dizin koordinat vermiyor, adres veriyor. Adresteki caddeyi OSM'de
bulup o caddenin Tuzla icindeki parcalarinin ortasini aliyoruz -> "yaklasik".
Kapi numarasi interpolasyonu yapmiyoruz cunku bu caddelerde OSM'de kapi
numarasi yok (GISBIR'de ayni duvara carpmistik).
"""
import json, re, sys, unicodedata
sys.path.insert(0, ".")
from mahalle_ata import ring_of, icinde, bbox, temiz_ad

def nrm(s):
    s = str(s or "").lower()
    for a, b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i","â":"a"}.items():
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()

def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", nrm(s))).strip("-")[:70]

def tr_title(s):
    """Python'un .title()'i Turkce'de bozuk: "GENİŞLER".title() -> "Geni\u0307şler"
    ("i" + U+0307). Once I/İ'yi yerine koyup sonra baslik yapiyoruz.
    Ayni hatayi belediye_import.py'de de yasamistik."""
    s = str(s or "").strip()
    out = []
    for kelime in s.split():
        k = kelime.replace("I", "ı").replace("İ", "i").lower()
        out.append((k[0].replace("i", "İ").replace("ı", "I").upper() + k[1:]) if k else k)
    return " ".join(out).replace("i\u0307", "i")

def tel_duzelt(t):
    """Dizin '216 3945454' ve '216 394 06 14' diye iki bicimde veriyor. Tekilestir."""
    d = re.sub(r"\D", "", str(t or ""))
    if len(d) == 10 and d[0] != "0": d = "0" + d
    if len(d) != 11: return re.sub(r"\s+", " ", str(t or "")).strip()
    return f"+90 {d[1:4]} {d[4:7]} {d[7:9]} {d[9:]}"

polys = []
for el in json.load(open("mahalle_raw.json")).get("elements", []):
    ad = (el.get("tags", {}) or {}).get("name")
    if not ad: continue
    r = ring_of(el)
    if len(r) >= 4: polys.append({"ad": temiz_ad(ad), "ring": r, "bb": bbox(r)})

def mahalle_of(lon, lat):
    for p in polys:
        x0, y0, x1, y1 = p["bb"]
        if x0 <= lon <= x1 and y0 <= lat <= y1 and icinde((lon, lat), p["ring"]):
            return p["ad"]
    return ""

yollar = json.load(open("yollar.json"))["elements"]


from sokak import sokak_nrm, govde

def cadde_orta(cadde, bek_mah):
    """Cadde adi + MAHALLE.
    IKI ASAMA:
      1) Turu koruyarak: "Tarhan Sok." == "Tarhan Sokagi"  (tarhan sk)
      2) Tutmazsa govde: "Manastir Yolu Cad." == "Manastir Yolu"
    Govde tek basina riskli - "Cebeci Sokak" ile "Cebeci Caddesi" ayni govdeye
    duser ama FARKLI sokaklar. O yuzden once tur korunuyor.
    Mahalle suzgeci sart: ayni cadde adi Istanbul'da onlarca yerde var.
    """
    if not cadde: return None
    for asama, anahtar in ((1, sokak_nrm), (2, govde)):
        h = anahtar(cadde); tut = []
        for w in yollar:
            if anahtar(w["tags"].get("name")) != h: continue
            g = w.get("geometry") or []
            if not g: continue
            mlat = sum(p["lat"] for p in g)/len(g); mlon = sum(p["lon"] for p in g)/len(g)
            if mahalle_of(mlon, mlat) == bek_mah: tut.append(g)
        if tut:
            pts = [p for g in tut for p in g]
            return (sum(p["lat"] for p in pts)/len(pts), sum(p["lon"] for p in pts)/len(pts), len(tut))
    return None

# noter no -> (koordinat kaynagi, deger, mahalle)
KONUM = {
    "6":  ("osb",    (40.88143, 29.38157), "Aydınlı"),    # Anadolu Yakasi OSB poligon merkezi
    "10": ("cadde",  "Yavuz Caddesi",      "Aydıntepe"),
    "12": ("cadde",  "Mimar Sinan Caddesi","Cami"),
    "19": ("cadde",  "Fevzi Çakmak Caddesi","Postane"),   # adresteki Hudai Sokak OSM'de yok
    "20": ("osm",    (40.87929, 29.35249), "Aydınlı"),    # OSM'de kayitli, TNB adresiyle uyusuyor
    "30": ("cadde",  "Fettah Başaran Caddesi","Mescit"),
    "31": ("cadde",  "İnönü Caddesi",      "Şifa"),
}

ham = [r for r in json.load(open("tnb_ham.json")) if len(r) == 8]
tz  = [r for r in ham if re.search(r"\bTUZLA\b", r[7], re.I)]
print(f"dizin: {len(ham)} noterlik · Tuzla adresli: {len(tz)}\n")

out = []
for r in tz:
    no = re.search(r"(\d+)", r[0]).group(1)
    tur, deger, bek = KONUM[no]
    if tur == "cadde":
        s = cadde_orta(deger, bek)
        if not s:
            print(f"  !! KARTAL {no}: '{deger}' {bek}'de bulunamadi - ATLANDI")
            continue
        lat, lon, n = s
        kalite, notu = "yaklasik", f"{deger} ({bek}) uzerindeki {n} parcanin ortasi; kapi no OSM'de yok"
    else:
        lat, lon = deger
        kalite = "" if tur == "osm" else "yaklasik"
        notu = ("OSM'de kayitli, TNB adresiyle dogrulandi" if tur == "osm"
                else "Anadolu Yakasi OSB alaninin merkezi; Gazi Bulvari OSM'de yok")
    ger = mahalle_of(lon, lat)
    ad = f"Kartal {no}. Noteri"
    tel = tel_duzelt(r[5])
    out.append({
        "id": "tnb-kartal-" + no, "slug": slugify(ad), "ad": ad,
        "kategori": "Servis", "alt_kategori": "Noter",
        "lat": round(lat, 6), "lon": round(lon, 6),
        "telefon": tel, "web": "", "instagram": "",
        "adres": re.sub(r"\s+", " ", r[7]).strip(),
        "mahalle": ger,
        "kaynak": "tnb", "dogrulandi": False,
        "konum_kalitesi": kalite, "konum_notu": notu,
        "kapsam_notu": f"Noter: {tr_title(r[1])}. Kaynak: Istanbul Noter Odasi resmi dizini.",
        "diger_ad": tr_title(r[1]),
    })
    u = "OK " if ger == bek else f"!! {ger or 'DISARIDA'}"
    print(f"  Kartal {no:>2}. Noteri  {lat:.5f},{lon:.5f}  bek:{bek:10s} {u:12s} {kalite or 'kesin'}")

json.dump(out, open("noter_tuzla.json", "w"), ensure_ascii=False, indent=1)
print(f"\nnoter_tuzla.json: {len(out)} kayit")
