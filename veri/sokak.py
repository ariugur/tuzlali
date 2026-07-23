#!/usr/bin/env python3
"""Turkce sokak adi normallestirme.

SORUN: ayni sokak OSM'de "Tarhan Sokagi", adreste "Tarhan Sok." yaziyor.
Tam eslesme arayinca ıskalanıyor ve kayit mahalle merkezine dusuyor (8 kayit
boyle dustu). Ek olarak "Gulistan Sokak" ve "Gulistan Sokagi" AYNI ANDA var.

COZUM: son ekleri tek bicime indir, govdeyi karsilastir.
"""
import re, unicodedata

def _sadele(s):
    s=str(s or "").lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i","â":"a","î":"i"}.items():
        s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9 ]"," ",s)).strip()

# uzun olan once: "sokagi" once eslesmeli, yoksa "sok" onu kirpar
EKLER=[(r"\b(sokagi|sokak|sokk|sok|sk)\b","sk"),
       (r"\b(caddesi|cadde|cad|cd)\b","cd"),
       (r"\b(bulvari|bulvar|bulv|blv)\b","bl"),
       (r"\b(yolu|yol)\b","yol"),
       (r"\b(mahallesi|mahalle|mah|mh)\b","")]

def sokak_nrm(s):
    t=_sadele(s)
    for pat,yeni in EKLER:
        t=re.sub(pat,yeni,t)
    return re.sub(r"\s+"," ",t).strip()

def govde(s):
    """Son eki tamamen at: 'tarhan sk' -> 'tarhan'. Tur farkini yok sayar."""
    t=sokak_nrm(s)
    return re.sub(r"\b(sk|cd|bl|yol)\b","",t).strip()

if __name__=="__main__":
    testler=[("Tarhan Sokak","Tarhan Sokağı"),("Cebeci Sok.","Cebeci Sokak"),
             ("Gülistan Sokak","Gülistan Sokağı"),("Manastır Yolu Cad.","Manastır Yolu"),
             ("Yalı Boyu Cad.","Yalı Boyu Caddesi"),("İnönü Cad.","İnönü Caddesi"),
             ("Hüdai Sokak","Hüdai Sokağı"),("Şinasi Dural Cad.","Şinasi Dural Caddesi")]
    print("govde esitligi testi:")
    for a,b in testler:
        e=govde(a)==govde(b)
        print(f"   {a:22s} <-> {b:22s} {'OK' if e else 'HATA'}  ({govde(a)!r})")
    # yanlis pozitif olmamali
    print()
    print("FARKLI olmali:")
    for a,b in [("Yavuz Caddesi","Yavuz Selim Caddesi"),("Cebeci Sokak","Cebeci Caddesi")]:
        print(f"   {a:22s} <-> {b:22s} govde: {govde(a)!r} vs {govde(b)!r} -> {'AYNI (dikkat)' if govde(a)==govde(b) else 'farkli'}")
