#!/usr/bin/env python3
"""Kullanicinin derledigi guzellik salonu listesi -> haritaya.

DOGRULAMA ZINCIRI (hicbiri atlanmadi):
  1. Yandex org sayfasinin BASLIGI isletme adini veriyor mu?
     Kontrol deneyi: uydurma org id jenerik "Yandex Maps: Toplu tasima" basligi
     donduruyor. Yani baslik ayirt edici.  -> 20 isletme GERCEK cikti.
  2. Listedeki telefon o sayfada geciyor mu? -> 15/15 ESLESTI.
  3. Instagram/Facebook TEST EDILEMEZ: uydurma hesap da 200 + ayni boyut donuyor.
     Bu kayitlarin TELEFONU ALINMIYOR (uydurma numara gercek birine ait olabilir).

KOORDINAT: adresteki cadde OSM'de bulunup mahalle icindeki parcalarin ortasi.
Kapi numarasi interpolasyonu yok - bu sokaklarda OSM'de kapi numarasi yok.
"""
import json, re, sys, unicodedata
sys.path.insert(0, ".")
from mahalle_ata import ring_of, icinde, bbox, temiz_ad

def nrm(s):
    s = str(s or "").lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i","â":"a"}.items(): s=s.replace(a,b)
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode()
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

def mahalle_merkez(ad):
    for p in polys:
        if p["ad"]==ad:
            r=p["ring"]; return (sum(y for x,y in r)/len(r), sum(x for x,y in r)/len(r))
    return None

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

# (mahalle, cadde) adresten elle cikarildi
ADRES={
 "Aleyna Gülten Beauty":("Postane","İstasyon Caddesi"),
 "Shine Port Beauty Center":("Postane","Cumhuriyet Caddesi"),
 "Gülden Altın Beauty":("Yayla","Vatan Caddesi"),
 "Veine Beauty":("İçmeler",None),
 "Ayşe Muslu Beauty":("Postane","Cumhuriyet Caddesi"),
 "Nif Güzellik ve Bakım Stüdyosu":("Cami","Toros Sokak"),
 "Este Tuzla":("İstasyon","Hacıoğlu Sokak"),
 "Ayfer Tekin Güzellik Merkezi":(None,None),
 "Loresima Beauty":("Postane","İstasyon Caddesi"),
 "SiS Güzellik Salonu":("Aydınlı","Bahçeler Caddesi"),
 "Emine Okur Güzellik Salonu":(None,None),
 "Estevelure Tuzla Beauty Center":("İstasyon","Medrese Sokak"),
 "Emsal Doğan Tuzla":("Postane","Cumhuriyet Caddesi"),
 "Deniz Uysal Beauty & VIP Saloon":("Aydınlı","Kahraman Sokak"),
 "Dermo Estetik ve Güzellik Merkezi Tuzla":("Postane","Yalı Boyu Caddesi"),
 "Gülten Aydın Güzellik Salonu":("Postane","Mühendis Sokak"),
 "Ela Nails":("İçmeler","Yılmaz Sokak"),
 "Star Sun Estetik & Güzellik":("Şifa","Zambak Sokak"),
 "Havva Yıldız Güzellik Salonu":("Şifa","Emiroğlu Caddesi"),
 "Eda Yılan Beauty Center":("Şifa","İnönü Caddesi"),
 "Luana Güzellik Yaşam Merkezi":("Aydınlı","Çamlı Belde Yolu"),
 "Emine Karslıoğlu Güzellik Salonu":("Şifa","Yücelay Sokak"),
 "D&S Beauty":("Postane","Postane Sokak"),
 "My Marvel Beauty":("Yayla","Vatan Caddesi"),
 "Burcu Tekdoğan Güzellik Salonu":("Aydınlı","Gürpınar Caddesi"),
 "Hayal Güzellik Salonu":("Postane","Yalı Boyu Caddesi"),
 "Beauty Rise Tuzla":("Yayla","Şinasi Dural Caddesi"),
 "Selin Beauty Center Tuzla":("Yayla","Vatan Caddesi"),
 "Pınar Beauty & Nails":("Postane","Postane Sokak"),
}
ALT={"Güzellik merkezi":"Güzellik Merkezi","Güzellik salonu":"Güzellik Salonu",
     "Tırnak / güzellik stüdyosu":"Nail Art"}

d=json.load(open("guzellik_dogrulama.json"))
out=[]; atlanan=[]
for r in d:
    if r["dogrulama"]=="SUPHELI":
        atlanan.append((r["ad"],"kaynak sayfasi baska isletmeyi gosteriyor")); continue
    mah,cad=ADRES.get(r["ad"],(None,None))
    if not mah:
        atlanan.append((r["ad"],"adres yok, konumlandirilamaz")); continue
    s=cadde_orta(cad,mah) if cad else None
    if s: lat,lon,n=s; notu=f"{cad} ({mah}) uzerindeki {n} parcanin ortasi; kapi no OSM'de yok"
    else:
        m=mahalle_merkez(mah)
        if not m: atlanan.append((r["ad"],f"{mah} poligonu yok")); continue
        lat,lon=m; notu=f"{mah} mahallesinin merkezi ({cad or 'cadde bilinmiyor'} OSM'de bulunamadi) - KABA"
    # TELEFON KURALI: sadece bagimsiz kaynakta dogrulanmis numara giriyor.
    tel = r["telefon"] if r.get("tel_dogrulama")=="ESLESTI" else ""
    out.append({
        "id":"guz-"+slugify(r["ad"]), "slug":slugify(r["ad"]), "ad":r["ad"],
        "kategori":"Bakım & Güzellik", "alt_kategori":ALT.get(r["kategori"],"Güzellik Salonu"),
        "lat":round(lat,6), "lon":round(lon,6),
        "telefon":tel, "web":r["url"] if not re.search(r"instagram|facebook|yandex",r["url"]) else "",
        "instagram":r["url"] if "instagram" in r["url"] else "",
        "adres":r["adres"], "mahalle":"", "kaynak":"web-derleme", "dogrulandi":False,
        "konum_kalitesi":"yaklasik", "konum_notu":notu,
        "kapsam_notu":("Adi ve telefonu bagimsiz kaynakta dogrulandi." if tel
                       else "Adi dogrulandi, telefon DOGRULANAMADI - bilerek bos."),
    })
json.dump(out,open("guzellik_tuzla.json","w"),ensure_ascii=False,indent=1)
print(f"guzellik_tuzla.json: {len(out)} kayit  ({sum(1 for r in out if r['telefon'])} telefonlu)")
print()
for a,s in atlanan: print(f"  ATLANDI: {a[:34]:34s} {s}")
