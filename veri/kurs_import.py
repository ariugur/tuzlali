#!/usr/bin/env python3
"""Tuzla surucu kurslari.

DOGRULAMA: 12 kayitta ad VE telefon kaynak sayfada geciyor (kendi sitesi ya da
Yandex org). Siki yontem.

KODLAMA NOTU: enginsurucukursu.com UTF-8 degil (ISO-8859-9). cek() cokuyordu;
siki_dogrula.py'ye charset tespiti eklendi.

Konum: konum.py (paylasilan). Onceden bu mantik bes importer'a kopyalanmisti.
"""
import json, re, unicodedata
import konum

def nrm(s):
    s=str(s or "").lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i"}.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9 ]"," ",s)).strip()
def slugify(s): return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",nrm(s))).strip("-")[:70]

polys, yollar = konum.yukle()

CADDE={
 "Genç Zirve Sürücü Kursu - Tuzla Merkez":"Yavuz Caddesi",
 "Genç Zirve Sürücü Kursu - Aydınlı Şube":"Başkomutan Caddesi",
 "Erdil Sürücü Kursu - Aydıntepe":"Dinçel Sokak",
 "Erdil Sürücü Kursu - Tuzla Şubesi":"Ova Sokak",
 "Yeni Engin Sürücü Kursu":"Tersane Sokak",
 "Test / Gerçek Sürücü Kursu":"100. Yıl Caddesi",
 "İçmeler Sürücü Kursu":"Dr. Sadık Ahmet Caddesi",
 "Tuzla Arslan Sürücü Kursu":"Coşkun Sokak",
 "Toktaş Sürücü Kursu - Tuzla":"Ali İhsan Paşa Caddesi",
 "Tuzla Şifa Sürücü Kursu":"İnönü Caddesi",
 "Özel Uzunyayla Sürücü Kursu":"Mektep Sokak",
 "Tuzla Sürücü Kursu":"Mehir Sokak",
 "Enis İzci Motosiklet Eğitim Alanı":"Fatih Sultan Mehmet Bulvarı",
}
out=[]
for r in json.load(open("kurs_dogrulama.json")):
    if r["ad_dogru"]!="EVET" or r["tel_dogru"]!="ESLESTI": 
        print(f"  ATLANDI: {r['ad'][:38]:38s} ({r['tel_dogru']})"); continue
    k=konum.konumla(polys, yollar, CADDE.get(r["ad"]), r["mahalle"] or None)
    if not k: print(f"  ATLANDI: {r['ad'][:38]:38s} (konumlandirilamadi)"); continue
    lat, lon, notu, kaba = k
    alt = "Motosiklet Eğitim Alanı" if "Motosiklet" in r["ad"] else "Sürücü Kursu"
    kend = "yandex" not in r["url"]
    out.append({"id":"krs-"+slugify(r["ad"]),"slug":slugify(r["ad"]),"ad":r["ad"],
      "kategori":"Servis","alt_kategori":alt,"lat":round(lat,6),"lon":round(lon,6),
      "telefon":r["telefon"],"web":r["url"] if kend else "","instagram":"",
      "adres":r["adres"],"mahalle":"","kaynak":"web-derleme","dogrulandi":False,
      "konum_kalitesi":"yaklasik","konum_notu":notu,
      "kapsam_notu":f"Adi ve telefonu bagimsiz kaynakta dogrulandi: {r['url']}"})
    print(f"  {r['ad'][:38]:38s} {lat:.5f},{lon:.5f} {konum.mahalle_of(polys,lon,lat) or '?':12s}{' KABA' if kaba else ''}")
json.dump(out,open("kurs_tuzla.json","w"),ensure_ascii=False,indent=1)
print(f"\nkurs_tuzla.json: {len(out)} kayit")
