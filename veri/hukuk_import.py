#!/usr/bin/env python3
"""Tuzla hukuk burolari.

DOGRULAMA: 21 kayitta ad VE telefon bagimsiz kaynakta (Yandex org sayfasi ya da
kendi .av.tr sitesi) geciyor. Siki yontem: lookaround'lu regex, gecerli TR onek.

YANDEX'IN "ARTIK FAAL DEGIL" ISARETINE GUVENILMIYOR:
Isletme sahibi uyardi, dogruladik - Yandex, Tuzla Oto Sanayi Sitesi'ni de
"Artik faal degil" gosteriyor. Oysa icinde 21 dukkan var ve 13'unun telefonunu
bugun dogruladik. O yuzden kapali gorunen kayitlar SILINMIYOR, isaretleniyor.

ALINMAYANLAR:
  - Hekim Hukuk        : sitedeki telefon listedekinden FARKLI
  - Safak Hukuk        : telefon sitede gecmiyor
  - Ozgur Onder        : verilen URL bir hukuk burosu YAZILIMI tanitim sayfasi,
                         dizin degil ("Hukuk Burosu Yonetim Programi")
  - telefonsuz satirlar: kaynak sayfada da numara yok
"""
import json, re, sys, unicodedata
sys.path.insert(0,".")
from mahalle_ata import ring_of, icinde, bbox, temiz_ad
from sokak import sokak_nrm, govde

def nrm(s):
    s=str(s or "").lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i"}.items(): s=s.replace(a,b)
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

def cadde_orta(cadde,bek):
    """TUZLA DISI ASLA: mahalle bilinmese bile yol Tuzla poligonlarinin
    icinde olmali. Emlak'ta bu kurali gevsettim ve kayit Pendik'e dustu."""
    if not cadde: return None
    for anahtar in (sokak_nrm, govde):
        h=anahtar(cadde); tut=[]
        for w in yollar:
            if anahtar(w["tags"].get("name"))!=h: continue
            g=w.get("geometry") or []
            if not g: continue
            mlat=sum(p["lat"] for p in g)/len(g); mlon=sum(p["lon"] for p in g)/len(g)
            m=mahalle_of(mlon,mlat)
            if not m: continue
            if bek and m!=bek: continue
            tut.append(g)
        if tut:
            pts=[p for g in tut for p in g]
            return (sum(p["lat"] for p in pts)/len(pts), sum(p["lon"] for p in pts)/len(pts), len(tut))
    return None

CADDE={"2M Hukuk Avukatlık Bürosu":"Seher Sokak","Çelik Hukuk Bürosu":"Tersane Sokak",
 "Özbey Hukuk ve Danışmanlık":"Selvili Sokak","Aydınlı Hukuk":"Gürpınar Caddesi",
 "Avukat Engin Barışık":"Kahraman Sokak","Avukat Anıl Bayram":"Gürpınar Caddesi",
 "Av. Hüsnüye Kırbaş":"İstasyon Caddesi","Arıbaş Hukuk Bürosu":"İstasyon Caddesi",
 "Hukuk Bürosu":"İstasyon Caddesi","Pekdemir Hukuk ve Danışmanlık":"Behram Sokak",
 "Av. Servet Beldağ":"Tok Sokak","Av. Gülden Karagöz":"Araplar Caddesi",
 "Sezgin Akbaba Hukuk Ofisi":"Manastır Yolu","Öz Yiğit Hukuk Bürosu":"Manastır Yolu",
 "AVS Hukuk Bürosu":"Sadık Sokak","International Justice Hukuk Danışmanlık":"Durmaz Sokak",
 "Avukat Pınar Kurt":"Öncü Sokak","Erdil Hukuk ve Danışmanlık Bürosu":"Dinçel Sokak",
 "Tuzla Arabuluculuk Merkezi":"Dr. Sadık Ahmet Caddesi","Rönesans Hukuk Bürosu":"Aydınlı Yolu",
 "Ataman Hukuk Bürosu":"Şehitler Caddesi"}
# Yandex kapali diyor ama guvenilmez -> isaretle, silme
SUPHE={"Öz Yiğit Hukuk Bürosu":"Yandex 'gecici olarak calismiyor' diyor",
       "AVS Hukuk Bürosu":"Yandex 'artik faal degil' diyor"}

out=[]
for r in json.load(open("hukuk_dogrulama.json")):
    if r["ad_dogru"]!="EVET" or r["tel_dogru"]!="ESLESTI": continue
    cad=CADDE.get(r["ad"]); bek=r["mahalle"] or None
    s=cadde_orta(cad,bek)
    if s: lat,lon,n=s; notu=f"{cad}{f' ({bek})' if bek else ''} uzerindeki {n} parcanin ortasi; kapi no OSM'de yok"
    else:
        if not bek: print(f"  ATLANDI: {r['ad'][:36]} - cadde de mahalle de yok"); continue
        p=[q for q in polys if q["ad"]==bek][0]["ring"]
        lat=sum(b for a,b in p)/len(p); lon=sum(a for a,b in p)/len(p)
        notu=f"{bek} merkezi ({cad} OSM'de yok) - KABA"
    alt="Arabuluculuk" if "Arabuluculuk" in r["ad"] else "Hukuk Bürosu"
    kn=f"Adi ve telefonu bagimsiz kaynakta dogrulandi: {r['url']}"
    if r["ad"] in SUPHE:
        kn += (f" | DIKKAT: {SUPHE[r['ad']]} - ama Yandex'in bu isareti guvenilmez "
               "(ayni isareti Tuzla Oto Sanayi Sitesi'ne de koymus, orasi acik). Sahada teyit gerek.")
    out.append({"id":"huk-"+slugify(r["ad"]),"slug":slugify(r["ad"]),"ad":r["ad"],
      "kategori":"Servis","alt_kategori":alt,"lat":round(lat,6),"lon":round(lon,6),
      "telefon":r["telefon"],"web":r["url"] if "yandex" not in r["url"] else "","instagram":"",
      "adres":r["adres"],"mahalle":"","kaynak":"web-derleme","dogrulandi":False,
      "konum_kalitesi":"yaklasik","konum_notu":notu,"kapsam_notu":kn})
    im=" [SUPHE]" if r["ad"] in SUPHE else ""
    print(f"  {r['ad'][:38]:38s} {lat:.5f},{lon:.5f} {mahalle_of(lon,lat) or '?':12s}{im}")
json.dump(out,open("hukuk_tuzla.json","w"),ensure_ascii=False,indent=1)
print(f"\nhukuk_tuzla.json: {len(out)} kayit")
