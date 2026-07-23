#!/usr/bin/env python3
"""Adresten koordinat: TEK KAYNAK.

Bu dosya once bes ayri importer'a KOPYALANMISTI (noter/guzellik/estetik/emlak/
hukuk). "Tuzla disi asla" kuralini sadece ikisine eklemistim; digerleri sansa
kaldi. Kopya kod = yarisi duzeltilmis hata. O yuzden tek yere alindi.

KURALLAR (her biri bir hatadan ogrenildi):
  1. TUZLA DISI ASLA. Mahalle bilinmese bile yol Tuzla poligonlarinin icinde
     olmali. Gevsettigimde "Tuzla Yuksel Gayrimenkul" Pendik'e dustu.
  2. IKI ASAMALI AD ESLESTIRME. Adres "Tarhan Sok.", OSM "Tarhan Sokagi" yaziyor.
     Once turu koruyarak (tarhan sk == tarhan sk), tutmazsa govdeyle. Govde tek
     basina riskli: "Cebeci Sokak" ile "Cebeci Caddesi" ayni govdeye duser ama
     FARKLI sokaklardir.
  3. KAPI NO INTERPOLASYONU YOK. Bu sokaklarda OSM'de kapi numarasi yok;
     interpolasyon sahte hassasiyet olurdu. Konum "yaklasik" isaretlenir.
"""
import json, re, unicodedata
from mahalle_ata import ring_of, icinde, bbox, temiz_ad
from sokak import sokak_nrm, govde

def yukle(mahalle_raw="mahalle_raw.json", yollar_json="yollar.json"):
    polys=[]
    for el in json.load(open(mahalle_raw)).get("elements",[]):
        ad=(el.get("tags",{}) or {}).get("name")
        if not ad: continue
        r=ring_of(el)
        if len(r)>=4: polys.append({"ad":temiz_ad(ad),"ring":r,"bb":bbox(r)})
    yollar=json.load(open(yollar_json))["elements"]
    return polys, yollar

def mahalle_of(polys, lon, lat):
    for p in polys:
        x0,y0,x1,y1=p["bb"]
        if x0<=lon<=x1 and y0<=lat<=y1 and icinde((lon,lat),p["ring"]): return p["ad"]
    return ""

def mahalle_merkez(polys, ad):
    for p in polys:
        if p["ad"]==ad:
            r=p["ring"]
            return (sum(y for x,y in r)/len(r), sum(x for x,y in r)/len(r))
    return None

def cadde_orta(polys, yollar, cadde, bek_mah):
    """-> (lat, lon, parca_sayisi) ya da None."""
    if not cadde: return None
    for anahtar in (sokak_nrm, govde):
        h=anahtar(cadde); tut=[]
        for w in yollar:
            if anahtar(w["tags"].get("name"))!=h: continue
            g=w.get("geometry") or []
            if not g: continue
            mlat=sum(p["lat"] for p in g)/len(g); mlon=sum(p["lon"] for p in g)/len(g)
            m=mahalle_of(polys, mlon, mlat)
            if not m: continue                    # KURAL 1: Tuzla disi asla
            if bek_mah and m!=bek_mah: continue
            tut.append(g)
        if tut:
            pts=[p for g in tut for p in g]
            return (sum(p["lat"] for p in pts)/len(pts),
                    sum(p["lon"] for p in pts)/len(pts), len(tut))
    return None

def konumla(polys, yollar, cadde, mah):
    """-> (lat, lon, not, kaba_mi). Cadde bulunamazsa mahalle merkezine duser."""
    s=cadde_orta(polys, yollar, cadde, mah)
    if s:
        lat, lon, n = s
        return lat, lon, f"{cadde}{f' ({mah})' if mah else ''} uzerindeki {n} parcanin ortasi; kapi no OSM'de yok", False
    if not mah: return None
    m=mahalle_merkez(polys, mah)
    if not m: return None
    return m[0], m[1], f"{mah} merkezi ({cadde or 'cadde bilinmiyor'} OSM'de yok) - KABA", True
