#!/usr/bin/env python3
"""IBB Acik Veri 'Saglik Tesisleri' -> Tuzla kayitlari, temizlenmis.
Kaynak: data.ibb.gov.tr, IBB Acik Veri Lisansi. Anlik goruntu, guncellenmiyor."""
import openpyxl, json, re, unicodedata, math, collections

# ---- Alt Kategori -> (kategori, alt_kategori) ----
MAP = {
    "Eczane":                              ("Sağlık","Eczane"),
    "Aile Sağlığı Merkezi":                ("Sağlık","Aile Sağlığı Merkezi"),
    "Özel Ağız ve Diş Sağlığı Merkezleri": ("Sağlık","Diş Hekimi"),
    "Diş Hekimi":                          ("Sağlık","Diş Hekimi"),
    "Ağız Diş Sağlığı Merkezi":            ("Sağlık","Diş Hekimi"),
    "Doktor/Muayenehane":                  ("Sağlık","Muayenehane"),
    "Psikologlar":                         ("Sağlık","Psikolog"),
    "Psikoteknik Değerlendirme Merkezi":   ("Sağlık","Psikoteknik Merkezi"),
    "Özel Hastane":                        ("Sağlık","Hastane"),
    "Devlet Hastanesi":                    ("Sağlık","Hastane"),
    "Üniversite Hastanesi":                ("Sağlık","Hastane"),
    "Poliklinik Özel":                     ("Sağlık","Poliklinik"),
    "Laboratuvar Özel":                    ("Sağlık","Laboratuvar"),
    "Diyetisyen":                          ("Sağlık","Diyetisyen"),
    "Rehabilitasyon ve Aile Danışma Merkezi": ("Sağlık","Rehabilitasyon"),
    "Verem Savaş Dispanseri":              ("Sağlık","Dispanser"),
    "Belediye Sağlık Merkezi":             ("Sağlık","Belediye Sağlık Merkezi"),
    "Yaşlı Bakım Evi/Huzurevi":            ("Sağlık","Bakım Merkezi"),
    "Sağlık Kabini Özel":                  ("Sağlık","Sağlık Kabini"),
    "İşitme Cihazı Satış ve Uygulama Merkezi": ("Sağlık","İşitme Cihazı"),
    "Veteriner":                           ("Evcil Hayvan","Veteriner"),
    "Gözlükçü/Optik":                      ("Perakende","Optik"),
    "Medikal":                             ("Perakende","Medikal Malzeme"),
}
# tuketiciye donuk olmayan / cop kategoriler
DROP_KAT = {
    "Ecza Deposu",        # B2B toptan
    "Şehir Hastanesi",    # cop: "Tuzla Şehir" x4 ayni noktada, "Has Statik Şehir" hastane degil
}

# "Sağlık Diğer" icinde saklananlar: isimden tespit
DIS_RE  = re.compile(r"diş|dent|aği?z ve diş|ağız diş", re.I)
DROP_RE = re.compile(
    r"osgb|ortak sağlik|ortak sağlık|iş sağliği|iş sağlığı|güvenlik birimi"
    r"|ilaç san|ilaç$|farma|sanofi|biocef|netson|octamed|babytec"
    r"|valiliği|içmeleri|^ibb |plastik", re.I)
# tek kelimeye kesilmis, anlamsiz kayitlar
KESIK_RE = re.compile(r"^\w+ (ortak|sağlik|sağlık)$", re.I)

def slug(s):
    s=s.lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i"}.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",s)).strip("-")[:70]

def norm(s):
    """isim benzerligi icin: kucuk harf, unvan/tur eki atilmis cekirdek"""
    s=slug(s)
    s=re.sub(r"\b(dr|dkt|op|opr|uzm|kl|psk|doc|prof|ozel|tc|ltd|sti|as|san|tic|hiz|hizmetleri|limite|klinigi|klinik|poliklinigi|merkezi|sagligi|saglik|dis|agiz|ve)\b","",s)
    return re.sub(r"-+","-",s).strip("-")

def dist_m(a,b):
    dy=(a[0]-b[0])*110540; dx=(a[1]-b[1])*math.cos(math.radians(a[0]))*111320
    return math.hypot(dx,dy)

def main():
    wb=openpyxl.load_workbook("ibb_saglik.xlsx", read_only=True)
    ws=wb.active; rows=ws.iter_rows(values_only=True); hdr=list(next(rows))
    data=[dict(zip(hdr,r)) for r in rows]
    tz=[r for r in data if str(r.get("İlçe Adı","")).strip().upper()=="TUZLA"]

    out=[]; drop=collections.Counter()
    for r in tz:
        ad=str(r.get("Sağlık Tesisi Adı") or "").strip()
        alt=str(r.get("Alt Kategori") or "").strip()
        if not ad: drop["isimsiz"]+=1; continue
        if alt in DROP_KAT: drop[f"kategori:{alt}"]+=1; continue
        if DROP_RE.search(ad): drop["tuketiciye-donuk-degil"]+=1; continue
        if KESIK_RE.match(ad): drop["kesik-isim"]+=1; continue

        if alt in MAP: kat,altk = MAP[alt]
        elif alt=="Sağlık Diğer" and DIS_RE.search(ad): kat,altk = ("Sağlık","Diş Hekimi")
        else: drop[f"eslesmedi:{alt}"]+=1; continue

        try: lat=float(r["Latitude"]); lon=float(r["Longitude"])
        except (TypeError,ValueError): drop["koordinatsiz"]+=1; continue

        out.append({
            "ad":ad, "kategori":kat, "alt_kategori":altk,
            "lat":round(lat,6), "lon":round(lon,6),
            "adres":str(r.get("ADRES") or "").strip(),
            "mahalle":str(r.get("Mahalle Adı") or "").strip().title(),
            "telefon":"", "calisma_saatleri":"", "web":"", "instagram":"",
            "kaynak":"ibb", "dogrulandi":False,
            "konum_kalitesi":"ibb", "konum_notu":"",
            "kapsam_notu":"",
        })

    # --- IBB ici tekrarlari at: ayni cekirdek isim + 120m icinde ---
    out.sort(key=lambda r:-len(r["ad"]))   # uzun/tam ismi tut
    kept=[]
    for r in out:
        n=norm(r["ad"])
        dup=False
        for k in kept:
            if norm(k["ad"])==n and dist_m((r["lat"],r["lon"]),(k["lat"],k["lon"]))<120:
                dup=True; break
        if dup: drop["ic-tekrar"]+=1
        else: kept.append(r)

    for r in kept: r["slug"]=slug(r["ad"]); r["id"]="i"+slug(r["ad"])[:26]
    kept.sort(key=lambda r:(r["kategori"],r["alt_kategori"],r["ad"]))
    json.dump(kept, open("ibb_tuzla.json","w"), ensure_ascii=False, indent=1)

    print(f"IBB TUZLA ham      : {len(tz)}")
    print(f"ALINAN             : {len(kept)}")
    print(f"ELENEN             : {len(tz)-len(kept)}")
    print()
    print("--- NEDEN ELENDI ---")
    for k,v in drop.most_common(): print(f"  {v:4d}  {k}")
    print()
    c=collections.Counter((r["kategori"],r["alt_kategori"]) for r in kept)
    print("--- ALINAN DAGILIM ---")
    cur=None
    for (k,a),n in sorted(c.items(), key=lambda x:(x[0][0],-x[1])):
        if k!=cur: print(f"\n  ### {k}"); cur=k
        print(f"    {n:3d}  {a}")

main()
