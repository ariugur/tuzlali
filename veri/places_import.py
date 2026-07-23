#!/usr/bin/env python3
"""Google Places dökümünü (places.json) tuzla_data.json'a ekler.

Operatör kararı: Google engeli bu veri için kaldırıldı, kaynak "google-places"
olarak DÜRÜSTÇE etiketleniyor. dogrulandi=false: telefon/saat yok, konum Google'dan.

PIPELINE:
  1. CLOSED_TEMPORARILY ele
  2. Yemek dışı tipleri ele (gym, playground, home_improvement_store...)
  3. TUZLA POLİGONU: mahalle_ata.ring_of/icinde ile. Tuzla dışı (Pendik/Ataşehir/
     Kocaeli...) DÜŞER. Mahalle poligondan atanır.
  4. Dosya içi tekilleştir: aynı yer iki grid noktasında çıkmış olabilir.
  5. Mevcut 925 ile tekilleştir: 70m içinde aynı isim -> zaten var, ekleme.
  6. Kategori/alt_kategori ata, kayıt kur.

Kuru çalıştırma: python3 places_import.py        (sadece rapor)
Yazma:          python3 places_import.py --yaz
"""
import json, re, sys, math, unicodedata
from mahalle_ata import ring_of, icinde, temiz_ad, bbox
from birlestir import FIELDS, slug, tel_bicim

# --- Google primaryType -> (kategori, alt_kategori) ---
# Alt kategoriler mevcut taksonomiden: Restoran/Fast Food/Kafe/Fırın/Pastane/
# Bar/Kahveci/Dondurmacı/Lokanta/Tatlıcı (Yeme İçme); Kasap/Bakkal (Market).
YEME="Yeme İçme"
MARKET="Market"
TIP = {
    "restaurant":YEME+"|Restoran","turkish_restaurant":YEME+"|Restoran",
    "family_restaurant":YEME+"|Restoran","middle_eastern_restaurant":YEME+"|Restoran",
    "buffet_restaurant":YEME+"|Restoran","fine_dining_restaurant":YEME+"|Restoran",
    "mediterranean_restaurant":YEME+"|Restoran","seafood_restaurant":YEME+"|Restoran",
    "korean_restaurant":YEME+"|Restoran","bistro":YEME+"|Restoran",
    "soup_restaurant":YEME+"|Restoran","barbecue_restaurant":YEME+"|Restoran",
    "steak_house":YEME+"|Restoran","bar_and_grill":YEME+"|Restoran",
    "dumpling_restaurant":YEME+"|Restoran","kebab_shop":YEME+"|Restoran",
    "diner":YEME+"|Restoran",
    "fast_food_restaurant":YEME+"|Fast Food","hamburger_restaurant":YEME+"|Fast Food",
    "pizza_restaurant":YEME+"|Fast Food","chicken_restaurant":YEME+"|Fast Food",
    "sandwich_shop":YEME+"|Fast Food","snack_bar":YEME+"|Fast Food",
    "food_court":YEME+"|Fast Food","meal_delivery":YEME+"|Fast Food",
    "meal_takeaway":YEME+"|Fast Food",
    "cafe":YEME+"|Kafe","coffee_shop":YEME+"|Kafe","cafeteria":YEME+"|Kafe",
    "coffee_roastery":YEME+"|Kafe","tea_house":YEME+"|Kahveci",
    "bakery":YEME+"|Fırın","bagel_shop":YEME+"|Fırın",
    "pastry_shop":YEME+"|Pastane",
    "dessert_shop":YEME+"|Tatlıcı","dessert_restaurant":YEME+"|Tatlıcı",
    "confectionery":YEME+"|Tatlıcı","chocolate_shop":YEME+"|Tatlıcı",
    "candy_store":YEME+"|Tatlıcı",
    "ice_cream_shop":YEME+"|Dondurmacı",
    "bar":YEME+"|Bar","hookah_bar":YEME+"|Bar","sports_bar":YEME+"|Bar",
    "butcher_shop":MARKET+"|Kasap",
    "grocery_store":MARKET+"|Bakkal / Market","food_store":MARKET+"|Bakkal / Market",
    "supermarket":MARKET+"|Süpermarket",
}
# Yemekle ilgisi olmayan, atılacak birincil tipler
ATLA = {"gym","home_improvement_store","home_goods_store","playground","service",
        "banquet_hall","event_venue","live_music_venue","wholesaler","manufacturer",
        "store","point_of_interest","food","tourist_attraction","consultant",
        "catering_service","food_delivery","library","sports_activity_location","health"}

def kategori_ata(r):
    """primaryType -> (kategori, alt). Bulunamazsa types listesinde ara."""
    pt=r.get("primaryType","")
    if pt in TIP: return TIP[pt].split("|")
    for t in r.get("types",[]):
        if t in TIP: return TIP[t].split("|")
    return None  # yemekle ilgili degil

def ad_norm(s):
    s=unicodedata.normalize("NFKC",str(s or "")).lower()
    s=(s.replace("ı","i").replace("ş","s").replace("ğ","g")
         .replace("ü","u").replace("ö","o").replace("ç","c"))
    return re.sub(r"[^a-z0-9]+"," ",s).strip()

def dist_m(a_lat,a_lon,b_lat,b_lon):
    return math.hypot((a_lat-b_lat)*111320,(a_lon-b_lon)*111320*math.cos(math.radians(a_lat)))

def adres_temizle(s):
    s=re.sub(r",?\s*Türkiye$","",str(s or "").strip())
    return s

# Google periods[].open.day: 0=Pazar. Mevcut sema OSM kisaltmasi kullaniyor.
GUN=["Su","Mo","Tu","We","Th","Fr","Sa"]
SIRA=[1,2,3,4,5,6,0]   # Mo..Su goruntuleme sirasi

def saat_bicim(roh):
    """regularOpeningHours -> 'Mo-Fr 09:00-18:00; Sa 10:00-14:00'.

    MUHAFAZAKAR: yapida en ufak belirsizlik varsa "" doner. Yanlis saat,
    eksik saatten kotudur. Gunde birden fazla vardiya, eksik close, gece
    yarisini asan kapanis -> atla.
    """
    if not isinstance(roh,dict): return ""
    per=roh.get("periods")
    if not isinstance(per,list) or not per: return ""
    # 7 gun x 24 saat acik: Google tek period verir, close yok
    if len(per)==1 and "close" not in per[0]:
        o=(per[0].get("open") or {})
        if o.get("hour")==0 and o.get("minute")==0: return "24/7"
        return ""
    gun_saat={}
    for p in per:
        o,c=p.get("open"),p.get("close")
        if not isinstance(o,dict) or not isinstance(c,dict): return ""
        d=o.get("day")
        if d is None or d!=c.get("day"): return ""      # gece yarisini asiyor
        if d in gun_saat: return ""                      # ayni gun 2. vardiya
        try:
            gun_saat[d]=f"{int(o['hour']):02d}:{int(o['minute']):02d}-{int(c['hour']):02d}:{int(c['minute']):02d}"
        except (KeyError,TypeError,ValueError):
            return ""
    if not gun_saat: return ""
    # ardisik ayni saatli gunleri araliga topla
    bloklar=[]
    for d in SIRA:
        s=gun_saat.get(d)
        if s is None: continue
        if bloklar and bloklar[-1][2]==s and SIRA.index(d)==SIRA.index(bloklar[-1][1])+1:
            bloklar[-1][1]=d
        else:
            bloklar.append([d,d,s])
    parca=[]
    for bas,son,s in bloklar:
        g=GUN[bas] if bas==son else f"{GUN[bas]}-{GUN[son]}"
        parca.append(f"{g} {s}")
    return "; ".join(parca)

def main():
    yaz = "--yaz" in sys.argv
    ham=json.load(open("../places.json"))
    mevcut=json.load(open("tuzla_data.json",encoding="utf-8"))

    # Tuzla poligonları
    raw=json.load(open("mahalle_raw.json"))
    polys=[]
    for el in raw.get("elements",[]):
        ad=temiz_ad((el.get("tags",{}) or {}).get("name",""))
        if not ad: continue
        rng=ring_of(el)
        if len(rng)>=4: polys.append({"ad":ad,"ring":rng,"bb":bbox(rng)})

    def mahalle_of(lon,lat):
        for p in polys:
            x0,y0,x1,y1=p["bb"]
            if x0<=lon<=x1 and y0<=lat<=y1 and icinde((lon,lat),p["ring"]):
                return p["ad"]
        return None

    sayac={"kapali":0,"yemek_disi":0,"tuzla_disi":0,"dosya_ici_tekrar":0,"mevcutta_var":0,"eklendi":0}
    dosya_gorulen={}   # (ad_norm, yuvarlak konum) -> ilk
    yeni=[]

    for r in ham:
        if r.get("businessStatus")=="CLOSED_TEMPORARILY": sayac["kapali"]+=1; continue
        kat=kategori_ata(r)
        if not kat: sayac["yemek_disi"]+=1; continue
        loc=r.get("location") or {}
        lat,lon=loc.get("latitude"),loc.get("longitude")
        if lat is None or lon is None: sayac["yemek_disi"]+=1; continue
        mah=mahalle_of(lon,lat)
        if not mah: sayac["tuzla_disi"]+=1; continue

        ad=str(r.get("displayName",{}).get("text","")).strip()
        an=ad_norm(ad)
        anahtar=(an, round(lat,4), round(lon,4))
        if anahtar in dosya_gorulen: sayac["dosya_ici_tekrar"]+=1; continue
        dosya_gorulen[anahtar]=True

        # mevcut 925 ile: 70m icinde ayni isim -> zaten var
        varmi=False
        for m in mevcut:
            if dist_m(lat,lon,m["lat"],m["lon"])<=70 and ad_norm(m["ad"])==an:
                varmi=True; break
        if varmi: sayac["mevcutta_var"]+=1; continue

        # --details ile cekilen kayitlarda telefon/web/saat var; yoksa "" kalir
        tel=tel_bicim(r.get("nationalPhoneNumber") or r.get("internationalPhoneNumber"))
        web=str(r.get("websiteUri") or "").strip()
        saat=saat_bicim(r.get("regularOpeningHours"))
        if tel or saat:
            not_=("Google Places kaydından; telefon/saat Google'dan, konum Google'dan. "
                  "Doğrulanmadı.")
        else:
            not_="Google Places kaydından; telefon/saat yok, konum Google'dan. Doğrulanmadı."

        kayit={k:"" for k in FIELDS}
        kayit.update({
            "id":"gp-"+r["id"],
            "slug":slug(ad),
            "ad":ad,
            "kategori":kat[0],
            "alt_kategori":kat[1],
            "lat":round(lat,6),"lon":round(lon,6),
            "telefon":tel,
            "calisma_saatleri":saat,
            "web":web,
            "adres":adres_temizle(r.get("formattedAddress")),
            "mahalle":mah,
            "kaynak":"google-places",
            "dogrulandi":False,
            "konum_kalitesi":"",
            "kapsam_notu":not_,
        })
        yeni.append(kayit)
        sayac["eklendi"]+=1

    print("=== PIPELINE RAPORU ===")
    print(f"  ham kayit          : {len(ham)}")
    print(f"  CLOSED_TEMPORARILY : -{sayac['kapali']}")
    print(f"  yemek disi (gym vs): -{sayac['yemek_disi']}")
    print(f"  TUZLA DISI         : -{sayac['tuzla_disi']}")
    print(f"  dosya ici tekrar   : -{sayac['dosya_ici_tekrar']}")
    print(f"  mevcutta zaten var : -{sayac['mevcutta_var']}")
    print(f"  --> EKLENECEK      : {sayac['eklendi']}")

    import collections
    print("\n--- eklenecekler: mahalle ---")
    for k,v in collections.Counter(x["mahalle"] for x in yeni).most_common():
        print(f"  {v:4}  {k}")
    print("\n--- eklenecekler: alt kategori ---")
    for k,v in collections.Counter(x["alt_kategori"] for x in yeni).most_common():
        print(f"  {v:4}  {k}")

    if not yaz:
        print("\n(KURU calisma. Yazmak icin: python3 places_import.py --yaz)")
        return

    import shutil
    shutil.copy("tuzla_data.json","tuzla_data.json.yedek")
    mevcut+=yeni
    json.dump(mevcut,open("tuzla_data.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print(f"\n{len(yeni)} kayit eklendi. Toplam: {len(mevcut)}. Yedek: tuzla_data.json.yedek")

if __name__=="__main__":
    main()
