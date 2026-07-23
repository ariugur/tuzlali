#!/usr/bin/env python3
"""Tuzla emlak ofisleri.

DOGRULAMA: 10 kayit Yandex org sayfasi / kendi sitesi uzerinden dogrulandi
(siki yontem). Her birinde hem ad hem TELEFON sayfada geciyor.

ALINMAYANLAR:
  - ~20 satir: "kaynak"lari birebir ayni URL (emlakclick.com/emlak-ofisi/
    istanbul/tuzla). Bu bir LISTE sayfasi, isletme sayfasi degil - kaynak sayilmaz.
  - RE/MAX Zeplin, Network Doruk: Yandex KATEGORI sayfasi, org sayfasi degil.
  - 3 hepsiemlak kaydi: Cloudflare "Just a moment..." -> test edilemedi.
  - 3 Instagram kaydi: uydurma hesap da 200 donuyor, ayirt edilemiyor.
  - sahibinden.com: cf-mitigated=challenge, bilincli bot engeli. Asilmadi.
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
    if not cadde: return None
    for anahtar in (sokak_nrm, govde):
        h=anahtar(cadde); tut=[]
        for w in yollar:
            if anahtar(w["tags"].get("name"))!=h: continue
            g=w.get("geometry") or []
            if not g: continue
            mlat=sum(p["lat"] for p in g)/len(g); mlon=sum(p["lon"] for p in g)/len(g)
            m=mahalle_of(mlon,mlat)
            if not m: continue                      # Tuzla disi: asla
            if bek and m!=bek: continue             # mahalle biliniyorsa birebir
            tut.append(g)
        if tut:
            pts=[p for g in tut for p in g]
            return (sum(p["lat"] for p in pts)/len(pts), sum(p["lon"] for p in pts)/len(pts), len(tut))
    return None

CADDE={
 "Concept Gayrimenkul / Tuzla Emlak Ofisi":"İstasyon Caddesi",
 "Nilüfer Emlak":"İstasyon Caddesi", "Tuzla Gayrimenkul":"Şinasi Dural Caddesi",
 "Tuzla Yüksel Gayrimenkul":"Atatürk Caddesi", "Tuzla Yılmaz Emlak":"Atlas Sokak",
 "Tuzla Emlak":"Demirci Sokak", "Tuzla Konut Emlak Gayrimenkul":"Çamlı Belde Yolu",
 "Tuzla Emlak Konutları Site Emlak":"Çamlı Belde Yolu",
 "Tuzla Emlak Konutları Emlak Ofisi":"Çamlı Belde Yolu",
 "TZC Gayrimenkul Otomotiv":"Çiçekçiler Caddesi",
}
out=[]
for r in json.load(open("emlak_dogrulama.json")):
    if r["ad_dogru"]!="EVET" or r["tel_dogru"]!="ESLESTI": continue
    cad=CADDE.get(r["ad"]); bek=r["mahalle"] or None
    s=cadde_orta(cad,bek)
    if s: lat,lon,n=s; notu=f"{cad}{f' ({bek})' if bek else ''} uzerindeki {n} parcanin ortasi; kapi no OSM'de yok"
    else:
        if not bek: print(f"  ATLANDI: {r['ad']} - cadde de mahalle de bulunamadi"); continue
        p=[q for q in polys if q["ad"]==bek][0]["ring"]
        lat=sum(b for a,b in p)/len(p); lon=sum(a for a,b in p)/len(p)
        notu=f"{bek} merkezi ({cad} OSM'de yok) - KABA"
    kend = "yandex" not in r["url"]
    out.append({"id":"eml-"+slugify(r["ad"]),"slug":slugify(r["ad"]),"ad":r["ad"],
      "kategori":"Servis","alt_kategori":"Emlak Ofisi","lat":round(lat,6),"lon":round(lon,6),
      "telefon":r["telefon"],"web":r["url"] if kend else "","instagram":"",
      "adres":r["adres"],"mahalle":"","kaynak":"web-derleme","dogrulandi":False,
      "konum_kalitesi":"yaklasik","konum_notu":notu,
      "kapsam_notu":f"Adi ve telefonu bagimsiz kaynakta dogrulandi: {r['url']}"})
    print(f"  {r['ad'][:40]:40s} {lat:.5f},{lon:.5f}  {mahalle_of(lon,lat) or '?':10s} {r['telefon']}")
json.dump(out,open("emlak_tuzla.json","w"),ensure_ascii=False,indent=1)
print(f"\nemlak_tuzla.json: {len(out)} kayit")
