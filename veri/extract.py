#!/usr/bin/env python3
"""OSM ham verisini temiz isletme kaydina cevirir. E-5 altini D100 geometrisiyle filtreler."""
import json, csv, unicodedata, re, sys, bisect

# --- OSM etiketi -> (ana kategori, alt kategori) ---
CATS = {
    "shop=supermarket":    ("Market", "Süpermarket"),
    "shop=convenience":    ("Market", "Bakkal / Market"),
    "shop=greengrocer":    ("Market", "Manav"),
    "shop=butcher":        ("Market", "Kasap"),
    "amenity=pharmacy":    ("Sağlık", "Eczane"),
    "amenity=hospital":    ("Sağlık", "Hastane"),
    "healthcare=hospital": ("Sağlık", "Hastane"),
    "healthcare=centre":   ("Sağlık", "Aile Sağlığı Merkezi"),
    "healthcare=rehabilitation": ("Sağlık", "Rehabilitasyon"),
    "amenity=nursing_home":("Sağlık", "Bakım Merkezi"),
    "healthcare=nurse":    ("Sağlık", "Bakım Merkezi"),
    "amenity=clinic":      ("Sağlık", "Poliklinik"),
    "amenity=doctors":     ("Sağlık", "Muayenehane"),
    "amenity=dentist":     ("Sağlık", "Diş Kliniği"),
    "amenity=veterinary":  ("Evcil Hayvan", "Veteriner"),
    "healthcare=veterinary": ("Evcil Hayvan", "Veteriner"),
    "shop=pet":            ("Evcil Hayvan", "Petshop"),
    "shop=pet_grooming":   ("Evcil Hayvan", "Pet Kuaför"),
    "amenity=restaurant":  ("Yeme İçme", "Restoran"),
    "amenity=fast_food":   ("Yeme İçme", "Fast Food"),
    "amenity=cafe":        ("Yeme İçme", "Kafe"),
    "amenity=bar":         ("Yeme İçme", "Bar"),
    "amenity=pub":         ("Yeme İçme", "Pub"),
    "shop=bakery":         ("Yeme İçme", "Fırın"),
    "shop=pastry":         ("Yeme İçme", "Pastane"),
    "shop=hairdresser":    ("Bakım & Güzellik", "Kuaför / Berber"),
    "shop=beauty":         ("Bakım & Güzellik", "Güzellik Merkezi"),
    "shop=massage":        ("Bakım & Güzellik", "Masaj / Bakım"),
    "shop=mobile_phone":   ("Perakende", "Telefoncu"),
    "shop=optician":       ("Perakende", "Optik"),
    "shop=florist":        ("Perakende", "Çiçekçi"),
    "shop=stationery":     ("Perakende", "Kırtasiye"),
    "shop=clothes":        ("Perakende", "Giyim"),
    "shop=jewelry":        ("Perakende", "Kuyumcu"),
    "shop=hardware":       ("Perakende", "Hırdavat"),
    "shop=doityourself":   ("Perakende", "Yapı Market"),
    "shop=electronics":    ("Perakende", "Elektronik"),
    "shop=furniture":      ("Perakende", "Mobilya"),
    "shop=department_store": ("Perakende", "Mağaza"),
    "shop=car_repair":     ("Servis", "Oto Servis"),
    "shop=car":            ("Servis", "Oto Galeri"),
    "shop=laundry":        ("Servis", "Çamaşırhane"),
    "shop=dry_cleaning":   ("Servis", "Kuru Temizleme"),
    "amenity=bank":        ("Servis", "Banka"),
    "office=notary":       ("Servis", "Noter"),
    "office=estate_agent": ("Servis", "Emlak Ofisi"),
    "office=lawyer":       ("Servis", "Hukuk Bürosu"),
    "amenity=driving_school": ("Servis", "Sürücü Kursu"),
    "shop=estate_agent":   ("Servis", "Emlak Ofisi"),
    "amenity=notary":      ("Servis", "Noter"),
    "amenity=fuel":        ("Servis", "Akaryakıt"),
    "tourism=hotel":       ("Konaklama", "Otel"),
    "tourism=guest_house": ("Konaklama", "Pansiyon"),
    "leisure=marina":      ("Marina & Denizcilik", "Marina"),
    "shop=boat":           ("Marina & Denizcilik", "Tekne / Ekipman"),
    "craft=boatbuilder":   ("Marina & Denizcilik", "Tekne Yapım / Bakım"),
    "shop=fishing":        ("Marina & Denizcilik", "Balıkçı Malzemesi"),
    "amenity=bureau_de_change": ("Servis", "Döviz Bürosu"),
    "shop=travel_agency":  ("Servis", "Seyahat Acentesi"),
    "shop=copyshop":       ("Servis", "Kırtasiye / Fotokopi"),
    "amenity=veterinary_pharmacy": ("Evcil Hayvan", "Veteriner Eczanesi"),
    "healthcare=dentist":  ("Sağlık", "Diş Kliniği"),
    "healthcare=doctor":   ("Sağlık", "Muayenehane"),
    "healthcare=clinic":   ("Sağlık", "Poliklinik"),
    "healthcare=physiotherapist": ("Sağlık", "Fizyoterapi"),
    "healthcare=laboratory": ("Sağlık", "Laboratuvar"),
    "shop=tattoo":         ("Bakım & Güzellik", "Dövme"),
    "shop=cosmetics":      ("Bakım & Güzellik", "Kozmetik"),
    "shop=perfumery":      ("Bakım & Güzellik", "Parfümeri"),
    "shop=nails":          ("Bakım & Güzellik", "Nail Art"),
    "leisure=spa":         ("Bakım & Güzellik", "Spa"),
    "amenity=spa":         ("Bakım & Güzellik", "Spa"),
    "leisure=sauna":       ("Bakım & Güzellik", "Sauna"),
    "shop=nutrition_supplements": ("Bakım & Güzellik", "Takviye / Sporcu Gıdası"),
    "leisure=fitness_centre": ("Bakım & Güzellik", "Spor Salonu"),
    "shop=shoes":          ("Perakende", "Ayakkabı"),
    "shop=bag":            ("Perakende", "Çanta"),
    "shop=books":          ("Perakende", "Kitapçı"),
    "shop=toys":           ("Perakende", "Oyuncakçı"),
    "shop=sports":         ("Perakende", "Spor Malzemesi"),
    "shop=computer":       ("Perakende", "Bilgisayar"),
    "shop=tyres":          ("Servis", "Lastikçi"),
    "shop=car_parts":      ("Servis", "Oto Yedek Parça"),
    "shop=car_wash":       ("Servis", "Oto Yıkama"),
    "amenity=car_wash":    ("Servis", "Oto Yıkama"),
    "amenity=vehicle_inspection": ("Servis", "Araç Muayene"),
    "amenity=car_rental":  ("Servis", "Oto Kiralama"),
    "shop=motorcycle":     ("Servis", "Motosiklet"),
    "shop=motorcycle_repair": ("Servis", "Motosiklet Servisi"),
    "craft=electrician":   ("Servis", "Elektrikçi"),
    "craft=plumber":       ("Servis", "Tesisatçı"),
    "craft=carpenter":     ("Servis", "Marangoz"),
    "shop=locksmith":      ("Servis", "Çilingir"),
    "shop=tailor":         ("Servis", "Terzi"),
    "shop=alcohol":        ("Market", "Tekel Bayi"),
    "shop=seafood":        ("Market", "Balıkçı"),
    "shop=deli":           ("Market", "Şarküteri"),
    "shop=confectionery":  ("Yeme İçme", "Tatlıcı"),
    "shop=ice_cream":      ("Yeme İçme", "Dondurmacı"),
    "shop=coffee":         ("Yeme İçme", "Kahveci"),
    "shop=tea":            ("Yeme İçme", "Çaycı"),
    "amenity=ice_cream":   ("Yeme İçme", "Dondurmacı"),
    "amenity=food_court":  ("Yeme İçme", "Yemek Katı"),
    "tourism=apartment":   ("Konaklama", "Apart"),
    "tourism=hostel":      ("Konaklama", "Hostel"),
    "tourism=motel":       ("Konaklama", "Motel"),
}
# ticari olmayan / istemedigimiz
SKIP_KEYS = {"amenity=school","amenity=place_of_worship","amenity=parking","leisure=park",
             "leisure=garden","office=government","amenity=kindergarten",
             "amenity=university","amenity=college","leisure=pitch","leisure=playground"}

def ad_temizle(s):
    """OSM'de bozuk yazilmis Turkce adlari duzeltir.

    Sorun: birileri veriyi girmeden once Python/Excel'de .title() veya .lower()
    calistirmis. Turkce'de "İ".lower() -> "i" + U+0307 (birlesim noktasi) verir,
    yani 'i' zaten noktaliyken ustune BIR NOKTA DAHA biniyor.
    Sonuc haritada "Köri̇ veteri̇ner poli̇kli̇ni̇ği̇" gibi gorunuyor.

    Turkce'de 'i' + U+0307 HER ZAMAN bu hatadir (i'nin noktasi zaten var),
    o yuzden guvenle silinebilir. Baska harflerdeki birlesim isaretlerine
    dokunmuyoruz.
    """
    s = unicodedata.normalize("NFC", str(s or ""))
    # NFC "I"+U+0307 -> "İ" birlestirmesini zaten yapiyor (U+0130'un
    # kanonik ayrisimi bu). Elde kalan tek sorun "i"+U+0307: Unicode'da
    # "noktali i ustune nokta" diye bir harf yok, o yuzden birlesmiyor.
    return s.replace("i\u0307", "i")

def slugify(s):
    s = s.lower()
    tr = {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i"}
    for a,b in tr.items(): s = s.replace(a,b)
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode()
    s = re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return re.sub(r"-+","-",s)[:70]

# isimden tespit: OSM etiketi yanlis/eksik oldugunda isim gercegi soyler
ASM_PAT   = __import__("re").compile(r"aile sağ|aile sag|a\.?s\.?m\b|verem savaş|dispanser", __import__("re").I)
COP_PAT   = __import__("re").compile(r"^(acıl girişi|acil girişi|revir)$|termal tesis", __import__("re").I)
DIS_PAT   = __import__("re").compile(r"diş|dent|ağız ve diş", __import__("re").I)
# OSM'de lastikci cogu zaman car_parts/car_repair olarak etiketlenmis.
# Tabelasinda "Lastik" yaziyorsa lastikcidir; etiket degil isim gercegi soyluyor.
LASTIK_PAT = __import__("re").compile(r"lastik|tyre|pirelli|michelin|bridgestone", __import__("re").I)

def cat_of(tags):
    ad = (tags.get("name") or "")
    if COP_PAT.search(ad): return None          # bina parcasi / yanlis etiket
    if ASM_PAT.search(ad): return ("Sağlık", "Aile Sağlığı Merkezi")
    if DIS_PAT.search(ad) and (tags.get("amenity") in ("hospital","clinic","dentist")
                               or tags.get("healthcare")):
        return ("Sağlık", "Diş Kliniği")
    # sadece oto etiketliyse devreye giriyor: "Lastik Cafe" diye bir yer
    # kategorisini degistirmesin.
    if LASTIK_PAT.search(ad) and tags.get("shop") in ("car_parts","car_repair","tyres"):
        return ("Servis", "Lastikçi")
    for k in ("amenity","shop","craft","healthcare","leisure","office","tourism"):
        if k in tags:
            key = f"{k}={tags[k]}"
            if key in SKIP_KEYS: return None
            if key in CATS: return CATS[key]
    return None

def phone(tags):
    for k in ("phone","contact:phone","contact:mobile"):
        if tags.get(k): return tags[k].split(";")[0].strip()
    return ""

def website(tags):
    for k in ("website","contact:website","url"):
        if tags.get(k): return tags[k].split(";")[0].strip()
    return ""

def insta(tags):
    for k in ("contact:instagram","instagram"):
        if tags.get(k): return tags[k].strip()
    return ""

# --- D100 hattini yukle: her boylam icin yolun enlemi ---
def load_d100(path="d100_raw.json"):
    try:
        d = json.load(open(path))
    except Exception:
        return None
    pts = []
    for el in d.get("elements", []):
        for p in el.get("geometry", []) or []:
            pts.append((p["lon"], p["lat"]))
    if len(pts) < 2: return None
    pts.sort()
    lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
    def lat_at(lon):
        i = bisect.bisect_left(lons, lon)
        i = max(1, min(i, len(lons)-1))
        x0,x1 = lons[i-1], lons[i]; y0,y1 = lats[i-1], lats[i]
        if x1 == x0: return y0
        return y0 + (y1-y0)*(lon-x0)/(x1-x0)
    return lat_at

# ---- E-5 KUZEYI ISTISNALARI ----
# Kural E-5 alti, ama bazi kurumlar cizginin metrelerce kuzeyinde kaliyor ve
# ilce icin belirleyici. Kapsam kuzeye acildikca bu liste kisalir/kalkar.
ISTISNA = {
    "Okan Üniversitesi Hastanesi":      "ilcenin en buyuk hastanesi, D100'un 17m kuzeyinde",
    "Okan Üniversitesi Diş Hastanesi":  "Okan kampusu dis hastanesi",
}

def main():
    raw = json.load(open("tuzla_osm_raw.json"))
    lat_at = load_d100()
    if lat_at is None:
        print("!! D100 geometrisi yok - E-5 filtresi UYGULANMADI", file=sys.stderr)

    out, skipped_north, yabanci_tuzla = [], 0, 0
    seen = set()
    for e in raw.get("elements", []):
        t = e.get("tags", {})
        name = ad_temizle(t.get("name")).strip()
        if not name: continue
        c = cat_of(t)
        if not c: continue
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None or lon is None: continue

        # DUNYADA 3 TUZLA VAR: Istanbul, Romanya (44.0N 28.6E), Kibris (35.1N 33.9E).
        # Overpass area["name"="Tuzla"] ucunu birden getiriyor. Istanbul disini ele.
        if not (40.70 <= lat <= 41.00 and 29.10 <= lon <= 29.55):
            yabanci_tuzla += 1
            continue

        # KAPSAM: tum Tuzla. E-5 filtresi kapatildi (isletme sahibi karari).
        # lat_at hala yukleniyor; ileride bolge etiketi icin kullanilabilir.
        istisna = name in ISTISNA

        key = (slugify(name), round(lat,4), round(lon,4))
        if key in seen: continue
        seen.add(key)

        out.append({
            "id": f"{e['type'][0]}{e['id']}",
            "slug": slugify(name),
            "ad": name,
            "kategori": c[0],
            "alt_kategori": c[1],
            "lat": round(lat,6),
            "lon": round(lon,6),
            "telefon": phone(t),
            "calisma_saatleri": t.get("opening_hours",""),
            "web": website(t),
            "instagram": insta(t),
            "adres": " ".join(x for x in [t.get("addr:street",""), t.get("addr:housenumber","")] if x).strip(),
            "mahalle": t.get("addr:suburb","") or t.get("addr:neighbourhood",""),
            "kaynak": "osm",
            "dogrulandi": False,
            "kapsam_notu": f"E-5 kuzeyi istisnasi: {ISTISNA[name]}" if istisna else "",
        })

    out.sort(key=lambda r:(r["kategori"], r["alt_kategori"], r["ad"]))
    json.dump(out, open("isletmeler.json","w"), ensure_ascii=False, indent=1)
    with open("isletmeler.csv","w",newline="",encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)

    import collections
    print(f"YABANCI TUZLA ELENEN : {yabanci_tuzla}  (Romanya/Kibris)")
    print(f"(E-5 filtresi KAPALI - tum Tuzla)")
    print(f"TICARI KAYIT (tum Tuzla): {len(out)}\n")
    cc = collections.Counter((r["kategori"], r["alt_kategori"]) for r in out)
    cur = None
    for (k, a), n in sorted(cc.items(), key=lambda x:(x[0][0], -x[1])):
        if k != cur: print(f"\n### {k}"); cur = k
        print(f"  {n:3d}  {a}")
    tel = sum(1 for r in out if r["telefon"]); sa = sum(1 for r in out if r["calisma_saatleri"])
    print(f"\n--- DOLULUK ---\ntelefon: {tel}/{len(out)} (%{100*tel/len(out):.0f})")
    print(f"saat   : {sa}/{len(out)} (%{100*sa/len(out):.0f})")

main()
