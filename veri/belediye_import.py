#!/usr/bin/env python3
"""Tuzla Belediyesi Acik Veri (veri.tuzla.bel.tr, CKAN) -> eczane + saglik kurumu kayitlari.
Eczane CSV'sinde koordinat YOK (telefon+adres var) -> mevcut kayitlarla isimden eslesecek.
Saglik kurumu CSV'sinde ENLEM/BOYLAM VAR -> dogrudan kullanilir."""
import csv, json, re, unicodedata

def tr_title(s):
    """Turkce baslik: Python .title() 'ECZANESI' -> 'Eczanesi̇' (birlesen nokta) uretiyor."""
    s=str(s or "").strip()
    out=[]
    for w in re.split(r"(\s+)", s):
        if not w.strip(): out.append(w); continue
        ilk, kalan = w[0], w[1:]
        ilk = "İ" if ilk=="I" else ("I" if ilk=="ı" else ilk.upper())
        kalan = kalan.replace("I","ı").replace("İ","i").lower()
        out.append(ilk+kalan)
    return "".join(out)

def slug(s):
    s=str(s).lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i"}.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",s)).strip("-")[:70]

def tel_duzelt(t):
    """'216446' gibi kirik, '02164461234' gibi tam. Sadece makul olani kabul et."""
    d=re.sub(r"\D","",str(t or ""))
    if len(d)==10 and d.startswith(("2","5")): return "+90 "+d
    if len(d)==11 and d.startswith("0"):       return "+90 "+d[1:]
    if len(d)==12 and d.startswith("90"):      return "+90 "+d[2:]
    return ""   # kirik/eksik -> uydurma

def oku(path):
    for enc in ("utf-8-sig","cp1254","iso-8859-9"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.reader(f, delimiter=";"))
        except Exception: continue
    return []

# ---------- ECZANELER ----------
rows=oku("bel_eczane.csv")
hdr=[h.strip() for h in rows[0]]
ecz=[]
for r in rows[1:]:
    if len(r)<3: continue
    d=dict(zip(hdr,[x.strip() for x in r]))
    ad=d.get("ECZANE ADI","").strip()
    if not ad: continue
    adres=" ".join(x for x in [d.get("CADDE-SOKAK",""), d.get("NO",""), d.get("MAHALLE","")] if x).strip(" ,")
    ecz.append({"ad":tr_title(ad), "telefon":tel_duzelt(d.get("TELEFON")),
                "adres":adres, "mahalle":tr_title(d.get("MAHALLE") or "")})

# ---------- SAGLIK KURUMLARI (koordinatli) ----------
rows=oku("bel_saglik.csv")
hdr=[h.strip() for h in rows[0]]
kur=[]
for r in rows[1:]:
    if len(r)<4: continue
    d=dict(zip(hdr,[x.strip() for x in r]))
    ad=d.get("SAGLIK KURUMU","").strip()
    if not ad: continue
    try:
        lat=float(str(d.get("ENLEM","")).replace(",","."))
        lon=float(str(d.get("BOYLAM","")).replace(",","."))
    except (TypeError,ValueError):
        lat=lon=None
    if lat is None or not (40.70<=lat<=41.00 and 29.10<=lon<=29.55):
        continue
    if "gisbir" in ad.lower():
        ad="Özel Tusa Hastanesi"   # eski ad: GSM Gisbir. Isletme sahibi dogruladi.
    ad_l=ad.lower()
    alt = ("Hastane" if "hastane" in ad_l
           else "Diş Hekimi" if "diş" in ad_l or "ağız" in ad_l
           else "Aile Sağlığı Merkezi" if "aile sağ" in ad_l or "asm" in ad_l
           else "Poliklinik" if "poliklinik" in ad_l
           else "Sağlık Kurumu")
    kur.append({"ad":ad, "kategori":"Sağlık", "alt_kategori":alt,
                "lat":round(lat,6), "lon":round(lon,6),
                "telefon":tel_duzelt(d.get("TELEFON")),
                "adres":(d.get("ADRES") or "").strip(),
                "mahalle":"", "calisma_saatleri":"", "web":"", "instagram":"",
                "kaynak":"belediye", "dogrulandi":False,
                "konum_kalitesi":"belediye", "konum_notu":"", "kapsam_notu":"",
                "slug":slug(ad), "id":"b"+slug(ad)[:26]})

json.dump(ecz, open("bel_eczane.json","w"), ensure_ascii=False, indent=1)
json.dump(kur, open("bel_kurum.json","w"), ensure_ascii=False, indent=1)

print(f"ECZANE        : {len(ecz)}  (telefonu duzgun olan: {sum(1 for e in ecz if e['telefon'])})")
print(f"SAGLIK KURUMU : {len(kur)}  (koordinatli, telefonu olan: {sum(1 for k in kur if k['telefon'])})")
print()
print("--- saglik kurumu turleri ---")
import collections
for k,v in collections.Counter(x["alt_kategori"] for x in kur).most_common(): print(f"  {v:3d}  {k}")
print()
print("--- eczane ornek ---")
for e in ecz[:4]: print(f"  {e['ad'][:26]:26s} | {e['telefon']:16s} | {e['adres'][:32]}")
print()
print("--- kurum ornek ---")
for k in kur[:6]: print(f"  {k['ad'][:34]:34s} | {k['alt_kategori']:20s} | {k['telefon']}")
