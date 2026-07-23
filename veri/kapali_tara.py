#!/usr/bin/env python3
"""Yandex org sayfasi KAPANMIS isletmeyi basligda isaretliyor:
  'Artik faal degil: ...'      -> kapali
  'Gecici olarak calismiyor: ' -> gecici kapali
Bunu simdiye kadar hic kontrol etmedim. Haritaya kapali isletme koymus olabilirim.
"""
import sys, re, json, time
sys.path.insert(0,'.')
from siki_dogrula import cek
KAPALI=[("Artık faal değil","KAPANMIŞ"),("Geçici olarak çalışmıyor","GEÇİCİ KAPALI"),
        ("Artik faal degil","KAPANMIŞ")]
def baslik(s):
    m=re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)',s,re.I) or \
      re.search(r'<title[^>]*>(.*?)</title>',s,re.S|re.I)
    return re.sub(r"\s+"," ",m.group(1)).strip() if m else ""

hedef=[]
for f,alan in [("guzellik_dogrulama.json","url"),("emlak_dogrulama.json","url"),("hukuk_dogrulama.json","url")]:
    try: d=json.load(open(f))
    except FileNotFoundError: continue
    for r in d:
        u=r.get(alan,"")
        if "yandex.com.tr/maps/org" in u: hedef.append((f.split("_")[0], r["ad"], u))
print(f"taranacak Yandex org sayfasi: {len(hedef)}\n")
bulgu=[]
for grup, ad, u in hedef:
    t=baslik(cek(u))
    durum=next((d for k,d in KAPALI if k.lower() in t.lower()), "")
    if durum:
        bulgu.append((grup,ad,durum,t[:56]))
        print(f"  !! {durum:14s} [{grup:9s}] {ad[:34]:34s} {t[:44]}")
    time.sleep(0.35)
print(f"\nKAPALI/GECICI KAPALI BULUNAN: {len(bulgu)} / {len(hedef)}")
json.dump([{"grup":g,"ad":a,"durum":d,"baslik":b} for g,a,d,b in bulgu],
          open("kapali.json","w"), ensure_ascii=False, indent=1)
