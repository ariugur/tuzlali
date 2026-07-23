#!/usr/bin/env python3
"""Tuzla medikal estetik klinikleri.

DOGRULAMA: her biri KENDI SITESINDEN teyit edildi (siki yontem: lookaround'lu
regex + gecerli TR onek suzgeci + script/style temizligi). Dordunde de sayfada
tek gecerli numara var ve iddia edilenle ayni; adres de tutuyor.

ALINMAYANLAR ve sebepleri:
  - Dr. Ismail Sener  : hicbir kaynak yok, ustelik telefonu (0549 124 34 34)
                        Beauty Rise Tuzla'ya ait (Yandex'te dogrulanmisti).
  - Okan Hastanesi    : zaten haritada (3 kaynak). Tablodaki "Tepeoren" YANLIS,
                        hastane Icmeler'de; Tepeoren'de olan kampus.
  - "Seval Ozergin"   : klinik gercek ve dogrulandi ama sitede bu hekim adi
                        gecmiyor. Klinik adiyla giriyor, hekim iddiasi girmiyor.
"""
import json, re, sys, unicodedata
sys.path.insert(0,".")
from mahalle_ata import ring_of, icinde, bbox, temiz_ad

def nrm(s):
    s=str(s or "").lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i","â":"a"}.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9 ]"," ",s)).strip()
def slugify(s): return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",nrm(s))).strip("-")[:70]

polys=[]
for el in json.load(open("mahalle_raw.json")).get("elements",[]):
    ad=(el.get("tags",{}) or {}).get("name")
    if not ad: continue
    r=ring_of(el)
    if len(r)>=4: polys.append({"ad":temiz_ad(ad),"ring":r,"bb":bbox(r)})
def mahalle_of(lon,lat):
    for p in polys:
        x0,y0,x1,y1=p["bb"]
        if x0<=lon<=x1 and y0<=lat<=y1 and icinde((lon,lat),p["ring"]): return p["ad"]
    return ""
yollar=json.load(open("yollar.json"))["elements"]

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

YENI=[
 {"ad":"Estetik Center","alt":"Medikal Estetik","mah":"Postane","cad":"Tarhan Sokak",
  "adres":"Postane Mah. Tarhan Sok. No:3/1","tel":"+90 216 447 47 07","web":"https://estetikcenter.com.tr/",
  "not":"Klinik adi, adresi ve telefonu kendi sitesinden dogrulandi."},
 {"ad":"Dr. Raniya Galifanova Medikal Estetik Merkezi","alt":"Medikal Estetik","mah":"Postane","cad":"Cebeci Sokak",
  "adres":"Postane Mah. Cebeci Sok. No:7 D:2","tel":"+90 543 483 72 00","web":"https://dr-raniyagalifanova.com/",
  "not":"Adi, adresi ve telefonu kendi sitesinden dogrulandi."},
 {"ad":"Uzm. Dr. Kenan Dibek Kliniği","alt":"Dermatoloji","mah":"Postane","cad":"Gülistan Sokak",
  "adres":"Postane Mah. Gülistan Sok. No:10 Villa 4","tel":"+90 544 655 41 34","web":"https://kenandibek.com/",
  "not":"Adi, adresi ve telefonu kendi sitesinden dogrulandi."},
]
out=[]
for y in YENI:
    s=cadde_orta(y["cad"],y["mah"])
    if s: lat,lon,n=s; notu=f"{y['cad']} ({y['mah']}) uzerindeki {n} parcanin ortasi; kapi no OSM'de yok"
    else:
        p=[q for q in polys if q["ad"]==y["mah"]][0]["ring"]
        lat=sum(b for a,b in p)/len(p); lon=sum(a for a,b in p)/len(p)
        notu=f"{y['mah']} merkezi ({y['cad']} OSM'de yok) - KABA"
    out.append({"id":"est-"+slugify(y["ad"]),"slug":slugify(y["ad"]),"ad":y["ad"],
        "kategori":"Sağlık","alt_kategori":y["alt"],"lat":round(lat,6),"lon":round(lon,6),
        "telefon":y["tel"],"web":y["web"],"instagram":"","adres":y["adres"],"mahalle":"",
        "kaynak":"web-derleme","dogrulandi":False,"konum_kalitesi":"yaklasik",
        "konum_notu":notu,"kapsam_notu":y["not"]})
    print(f"  {y['ad'][:42]:42s} {lat:.5f},{lon:.5f}  {mahalle_of(lon,lat)}")
json.dump(out,open("estetik_tuzla.json","w"),ensure_ascii=False,indent=1)
print(f"\nestetik_tuzla.json: {len(out)} kayit")
