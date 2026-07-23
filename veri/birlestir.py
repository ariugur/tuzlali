#!/usr/bin/env python3
"""Uc kaynagi birlestirir: OSM (isletmeler.json) + IBB (ibb_tuzla.json) + GISBIR (gisbir_tuzla_geo.json).
Ayni yeri iki kaynak da biliyorsa KAYITLARI BIRLESTIRIR (OSM'de telefon, IBB'de adres var)."""
import json, re, math, unicodedata, collections
import duzeltme   # kayit duzeltmeleri: TEK kaynak (duzeltme.py)

# CIKTI SEMASI: modul seviyesinde, cunku elle_uygula.py da bunu kullaniyor.
# main() icinde kalsaydi ikinci bir kopya yazmak gerekirdi.
FIELDS=["id","slug","ad","diger_ad","kategori","alt_kategori","lat","lon","telefon",
        "calisma_saatleri","web","instagram","adres","mahalle","kaynak","dogrulandi",
        "konum_kalitesi","konum_notu","kapsam_notu","ad_celiskisi","olasi_tekrar",
        "tekrar_notu","baro_sicil"]

def slug(s):
    s=s.lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i"}.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",s)).strip("-")[:70]

STOP=r"\b(dr|dkt|op|opr|uzm|kl|psk|doc|prof|ozel|tc|ltd|sti|as|san|tic|hiz|hizmetleri|limite|klinigi|klinik|poliklinigi|merkezi|sagligi|saglik|eczanesi|eczane|hastanesi|hastane|hastahanesi|veteriner|dis|agiz|ve|the)\b"
def norm(s):
    s=re.sub(STOP,"",slug(s))
    return re.sub(r"-+","-",s).strip("-")

ASM_NO=re.compile(r"\b(\d{1,2})\s*(?:nolu|no'lu|no\.?lu)\b", re.I)
def asm_no(ad):
    """ASM'lerin iki adi var: numara (7 Nolu) ve sehit adi. Numara varsa kesin anahtar."""
    m=ASM_NO.search(str(ad or ""))
    return m.group(1) if m else None

def dist_m(a,b):
    dy=(a[0]-b[0])*110540
    dx=(a[1]-b[1])*math.cos(math.radians(a[0]))*111320
    return math.hypot(dx,dy)

def tel_bicim(t):
    """Telefonu TEK bicime indirir. Kaynaklar 9 ayri bicimde veriyordu:
    '+90 2163944200', '0216 394 42 00', '+902163944200'...

    444'LU HATLAR AYRI: '444 0 704' 7 hanelidir, alan kodu yoktur, kurumsal
    hattir. Normal telefon gibi bicimlendirmek onu bozar.
    """
    ham=str(t or "").strip()
    if not ham: return ""
    d=re.sub(r"\D","",ham)
    if d.startswith("90") and len(d)==12: d="0"+d[2:]
    elif len(d)==10 and not d.startswith("0"): d="0"+d
    if len(d)==7 and d.startswith("444"):          # 444 X XXX
        return f"{d[:3]} {d[3]} {d[4:]}"
    if len(d)==11 and d.startswith("0"):
        return f"+90 {d[1:4]} {d[4:7]} {d[7:9]} {d[9:]}"
    return ham                                      # taninmadi: elleme, bozma

def pick(*vals):
    for v in vals:
        if v: return v
    return ""

def main():
    osm=json.load(open("isletmeler.json"))
    ibb=json.load(open("ibb_tuzla.json"))
    gis=json.load(open("gisbir_tuzla_geo.json"))
    try:
        bel_kurum=json.load(open("bel_kurum.json"))
        bel_ecz=json.load(open("bel_eczane.json"))
    except FileNotFoundError:
        bel_kurum, bel_ecz = [], []
    gis=[r for r in gis if r.get("lat")]

    for r in osm: r.setdefault("kapsam_notu","")
    for r in gis:
        r.setdefault("kapsam_notu","")
        r.setdefault("konum_kalitesi","yaklasik")

    merged=list(osm)
    idx=collections.defaultdict(list)
    for i,r in enumerate(merged):
        if r.get("lat"): idx[norm(r["ad"])].append(i)

    birlesen=0; yeni=0
    for r in ibb:
        n=norm(r["ad"])
        hit=None
        # 1) isim + 180m
        for i in idx.get(n,[]):
            if dist_m((r["lat"],r["lon"]),(merged[i]["lat"],merged[i]["lon"]))<180:
                hit=i; break
        # 2) isim tutmasa da: AYNI ALT KATEGORI + 30m => fiziksel olarak ayni yer.
        #    (eczane devri: OSM eski adi, IBB yeni adi tutuyor. 3m'de iki eczane olamaz.)
        if hit is None:
            for i,m in enumerate(merged):
                if not m.get("lat"): continue
                if m.get("alt_kategori")!=r["alt_kategori"]: continue
                if dist_m((r["lat"],r["lon"]),(m["lat"],m["lon"]))<30:
                    hit=i; break
        if hit is None:
            merged.append(r); idx[n].append(len(merged)-1); yeni+=1
        else:
            m=merged[hit]
            if norm(m["ad"])!=norm(r["ad"]):
                # iki kaynak ayni noktada FARKLI isim veriyor: hangisi guncel bilinmiyor.
                m["diger_ad"]=m["ad"]; m["ad"]=r["ad"]      # IBB resmi kayit, birincil
                m["ad_celiskisi"]=True
            # BIRLESTIR: her alanda dolu olani tut
            m["adres"]   = pick(m.get("adres"), r.get("adres"))
            m["mahalle"] = pick(m.get("mahalle"), r.get("mahalle"))
            m["telefon"] = pick(m.get("telefon"), r.get("telefon"))
            m["web"]     = pick(m.get("web"), r.get("web"))
            # IBB alt kategorisi daha spesifik (Dis Hekimi / Psikolog / Muayenehane)
            if r["alt_kategori"] not in ("Eczane",) and r["kategori"]=="Sağlık":
                m["kategori"], m["alt_kategori"] = r["kategori"], r["alt_kategori"]
            m["kaynak"] = "osm+ibb"
            birlesen+=1

    # --- BELEDIYE KURUMLARI: koordinatli, resmi. IBB gibi birlestir. ---
    bel_birlesen=bel_yeni=0
    for r in bel_kurum:
        n=norm(r["ad"]); hit=None
        rno=asm_no(r["ad"])
        for i,m in enumerate(merged):
            if not m.get("lat"): continue
            d=dist_m((r["lat"],r["lon"]),(m["lat"],m["lon"]))
            # ASM numarasi eslesiyorsa kesin ayni kurum (300m tolerans: kaynaklar
            # binayi farkli noktalara koyuyor)
            if rno and asm_no(m["ad"])==rno and d<400: hit=i; break
            if norm(m["ad"])==n and d<250: hit=i; break
            if m.get("alt_kategori")==r["alt_kategori"] and d<60: hit=i; break
        if hit is None:
            merged.append(r); bel_yeni+=1
        else:
            m=merged[hit]
            m["telefon"]=pick(m.get("telefon"), r.get("telefon"))
            m["adres"]=pick(m.get("adres"), r.get("adres"))
            if norm(m["ad"])!=n and not m.get("diger_ad"):
                m["diger_ad"]=r["ad"]; m["ad_celiskisi"]=True
            m["kaynak"]=(m.get("kaynak","")+"+belediye")
            bel_birlesen+=1

    # --- BELEDIYE ECZANELERI: koordinat YOK. isimle eslesip TELEFON doldur. ---
    ecz_idx=collections.defaultdict(list)
    for i,m in enumerate(merged):
        if m.get("alt_kategori")=="Eczane": ecz_idx[norm(m["ad"])].append(i)
    tel_dolan=0; ecz_eslesmeyen=0
    for e in bel_ecz:
        hits=ecz_idx.get(norm(e["ad"]),[])
        if not hits: ecz_eslesmeyen+=1; continue
        for i in hits:
            m=merged[i]
            if not m.get("telefon") and e.get("telefon"):
                m["telefon"]=e["telefon"]; tel_dolan+=1
            m["adres"]=pick(m.get("adres"), e.get("adres"))
            m["mahalle"]=pick(m.get("mahalle"), e.get("mahalle"))
            if "belediye" not in m.get("kaynak",""): m["kaynak"]=m.get("kaynak","")+"+belediye"

    merged += gis

    # TNB: Istanbul Noter Odasi resmi dizini -> Tuzla adresli noterler.
    # OSM'deki "Kartal 20. Noteri" ile ayni ada sahip; asagidaki isim
    # eslestirmesi ikisini birlestirir (OSM kesin koordinat, TNB telefon+adres).
    try:
        noter=json.load(open("noter_tuzla.json"))
    except FileNotFoundError:
        noter=[]
    merged += noter

    # Kullanicinin derledigi guzellik salonlari. Adlar Yandex org sayfasinin
    # basligiyla, telefonlar ayni sayfadaki numarayla dogrulandi.
    # Dogrulanamayan telefon GIRMIYOR (guzellik_import.py'deki kural).
    try:
        guz=json.load(open("guzellik_tuzla.json"))
    except FileNotFoundError:
        guz=[]
    merged += guz

    # Medikal estetik klinikleri. Her biri KENDI SITESINDEN dogrulandi
    # (siki yontem: lookaround'lu regex, gecerli TR onek suzgeci).
    try:
        est=json.load(open("estetik_tuzla.json"))
    except FileNotFoundError:
        est=[]
    merged += est

    # Emlak ofisleri. 10 kayit; her birinde ad VE telefon bagimsiz kaynakta
    # dogrulandi. Kaynagi liste sayfasi olan ~20 satir alinmadi.
    try:
        eml=json.load(open("emlak_tuzla.json"))
    except FileNotFoundError:
        eml=[]
    merged += eml

    # Hukuk burolari. 21 kayit; ad ve telefon bagimsiz kaynakta dogrulandi.
    try:
        huk=json.load(open("hukuk_tuzla.json"))
    except FileNotFoundError:
        huk=[]
    merged += huk

    # Surucu kurslari. 12 kayit; ad ve telefon kaynak sayfada dogrulandi.
    try:
        krs=json.load(open("kurs_tuzla.json"))
    except FileNotFoundError:
        krs=[]
    merged += krs

    # IBB kaydinda olup telefonu olmayan hekimlere, KENDI SITESINDEN dogrulanmis
    # numarayi ekle. Yeni kayit acmiyoruz - kayit zaten resmi listeden geldi,
    # eksigi sadece telefonu. Anahtar: isim + IBB'nin verdigi mahalle.
    TEL_EK = {
        ("ozlem-cemboluk","İçmeler"): {
            "telefon": "+90 555 088 17 17",
            "web": "https://ozlemcemboluk.com/",
            "not": "Telefon ve adres hekimin kendi sitesinden dogrulandi.",
        },
    }
    tel_eklenen=0
    for r in merged:
        if not r.get("lat"): continue
        k=(slug(r["ad"]).replace("op-dr-","").replace("uzm-dr-","").replace("dr-",""), r.get("mahalle",""))
        if k in TEL_EK and not r.get("telefon"):
            e=TEL_EK[k]
            r["telefon"]=e["telefon"]; r["web"]=r.get("web") or e["web"]
            r["kapsam_notu"]=e["not"]
            r["kaynak"]=r.get("kaynak","")+"+web"
            tel_eklenen+=1
    print(f"TELEFON EKLENEN  : {tel_eklenen}")

    # ELLE GIRILEN: acik kaynakta olmayan, sahada dogrulanan kayitlar.
    # En sona ekleniyor ve HICBIR eslestirmeye girmiyor: elle girilmisse
    # zaten "bunu ben gordum" demektir, algoritmanin duzeltecegi bir sey yok.
    # _ ile baslayan anahtarlar dosyanin basindaki aciklama blogu, kayit degil.
    try:
        elle=[r for r in json.load(open("elle.json")) if not any(k.startswith("_") for k in r)]
    except FileNotFoundError:
        elle=[]
    for r in elle:
        r.setdefault("slug", slug(r["ad"]))
        r.setdefault("kapsam_notu","")
        r.setdefault("konum_kalitesi","")
    merged += elle

    out=[]
    for r in merged:
        if not r.get("lat"): continue
        out.append({k:r.get(k,"") for k in FIELDS})
    for r in out:
        if r["alt_kategori"]=="Diş Kliniği": r["alt_kategori"]="Diş Hekimi"
    for r in out: r["telefon"]=tel_bicim(r.get("telefon"))

    # OLASI TEKRAR: ayni alt kategori + 250m icinde baska kayit.
    # Ozellikle ASM'lerde kaynaklar farkli isim konvansiyonu kullaniyor
    # (belediye "7 Nolu", OSM/IBB sehit adi) -> otomatik eslestirilemiyor.
    # Sessizce birlestirmek de saklamak da yanlis olurdu: isaretleyip sahaya birakiyoruz.
    # SADECE ASM: market/restoran/banka gercekten kumelenir (BIM ile A101 100m arayla
    # acilir), onlari isaretlemek anlamsiz. ASM'de ise uc kaynak uc farkli isim
    # konvansiyonu kullandigi icin otomatik eslestirme yapilamiyor.
    for r in out: r["olasi_tekrar"]=False
    asm=[r for r in out if r["alt_kategori"]=="Aile Sağlığı Merkezi"]
    for i,a in enumerate(asm):
        for b in asm[i+1:]:
            if dist_m((a["lat"],a["lon"]),(b["lat"],b["lon"]))<250:
                a["olasi_tekrar"]=b["olasi_tekrar"]=True

    # ---- TELEFONDAN BIRLESTIRME ----
    # Iki isletme ayni sabit hatti paylasmaz. Ayni telefon + ayni kategori +
    # BENZER isim => tek isletme, iki kayit. Kaynaklar onu farkli yerlere
    # koymus ("Orhanli Eczanesi" iki kayitta, arada 1110m).
    # Isimler FARKLI ise birlestirmiyoruz: devir olabilir (Alaaddin/Ihlamur)
    # ya da kardes sirket (Desan/KPT). Korlemesine silmek veri kaybettirir;
    # onlar sadece isaretleniyor.
    TEL_STOP=r"\b(eczanesi|eczane|aile|sagligi|saglik|merkezi|merkez|nolu|no|semt|restaurant|restoran|san|tic|as|a-s|ltd|sti|deniz|insaat|isletmeciligi)\b"
    def tel_norm(x):
        return re.sub(r"-+","-",re.sub(TEL_STOP,"",slug(x).replace("-"," "))).strip("- ").replace(" ","-")
    def kaynak_puan(r): return r.get("kaynak","").count("+")+1
    def doluluk(r): return sum(1 for k in ("telefon","adres","web","calisma_saatleri") if r.get(k))

    tel_g=collections.defaultdict(list)
    for r in out:
        t=re.sub(r"\D","",r.get("telefon") or "")
        if len(t)>=10: tel_g[t[-10:]].append(r)

    silinecek=set(); tel_birlesen=0
    for t,v in tel_g.items():
        if len(v)<2 or len({r["alt_kategori"] for r in v})!=1: continue
        n=[tel_norm(r["ad"]) for r in v]
        benzer = len(set(n))==1 or any(a and b and (a in b or b in a)
                                       for i,a in enumerate(n) for b in n[i+1:])
        if not benzer: continue
        # TUTULAN: once kaynak sayisi, sonra doluluk, sonra kesin konum
        v=sorted(v, key=lambda r:(-kaynak_puan(r), -doluluk(r), r.get("konum_kalitesi")=="yaklasik"))
        tut=v[0]
        for x in v[1:]:
            for k in ("adres","web","instagram","calisma_saatleri","mahalle"):
                if not tut.get(k) and x.get(k): tut[k]=x[k]
            if slug(tut["ad"])!=slug(x["ad"]) and not tut.get("diger_ad"):
                tut["diger_ad"]=x["ad"]; tut["ad_celiskisi"]=True
            for kk in x.get("kaynak","").split("+"):
                if kk and kk not in tut.get("kaynak",""):
                    tut["kaynak"]=tut.get("kaynak","")+"+"+kk
            silinecek.add(id(x)); tel_birlesen+=1
    out=[r for r in out if id(r) not in silinecek]
    print(f"TELEFONDAN BIRLESEN: {tel_birlesen} kayit silindi")

    # ---- KAYIT DUZELTMESI (id bazli) ----
    # Sozluk duzeltme.py'de: hat bugun yeniden calistirilamadigi icin ayni
    # duzeltme tuzla_data.json'a duzelt_uygula.py ile de basiliyor. Iki kopya
    # sozluk tutmuyoruz.
    duzeltilen, eksik_id = duzeltme.uygula(out)
    print(f"KAYIT DUZELTILEN : {duzeltilen}")
    if eksik_id: print(f"  UYARI: DUZELTME'deki id veride yok: {eksik_id}")

    # ---- SAHA DUZELTMESI (isletme sahibinin yerel bilgisi) ----
    # Ucunde de ayni desen: numara BIRINE ait, kaynak onu digerine de yazmis.
    # Kayitlar duruyor (uc isletme de gercek), sadece yanlis numara siliniyor.
    # Bunu hicbir kaynaktan cikaramazdim - Beauty Rise devri gibi, yerel bilgi.
    YANLIS_TEL = {
        # (ad parcasi, dogru sahibi) -> numarayi bu kayittan SIL
        "ihlamur":  "Alaaddin Eczanesi",
        "4-nolu":   "Aydınlı TOKİ Şehit Hüsmaettin Ürün Aile Sağlığı Merkezi",
        "kpt":      "Desan Deniz İnşaat San. A.Ş.",
    }
    tel_silinen=0
    for r in out:
        k=slug(r["ad"])
        for parca, sahibi in YANLIS_TEL.items():
            if k.startswith(parca) and r.get("telefon"):
                r["telefon"]=""
                r["kapsam_notu"]=((r.get("kapsam_notu","")+" ") if r.get("kapsam_notu") else "") + \
                    f"Kaynaktaki telefon yanlisti ({sahibi} numarasi), silindi. Isletme gercek."
                tel_silinen+=1
                break
    print(f"YANLIS TELEFON SILINEN: {tel_silinen}")

    # TELEFON ANAHTARI: mesafeden cok daha guclu. Iki isletme ayni sabit hatti
    # paylasmaz. Yukaridaki 250m kurali "Orhanli Eczanesi"nin 1110m arayla iki
    # kez girdigini kaciriyordu - ayni telefonla. Yani iki kaynak AYNI eczaneyi
    # farkli yerlere koymus; iki isletme degil, bir isletme + hatali koordinat.
    # Ayni kategori sarti zincir merkez numarasi yanlis pozitiflerini kirpiyor.
    tel_g=collections.defaultdict(list)
    for r in out:
        t=re.sub(r"\D","",r.get("telefon") or "")
        if len(t)>=10: tel_g[t[-10:]].append(r)
    tel_tekrar=0
    for t,v in tel_g.items():
        if len(v)<2: continue
        if len({r["alt_kategori"] for r in v})!=1: continue
        for r in v:
            if not r["olasi_tekrar"]: tel_tekrar+=1
            r["olasi_tekrar"]=True
            r["tekrar_notu"]=("Ayni telefon baska bir kayitta da var: "
                              + ", ".join(x["ad"] for x in v if x is not r))
    print(f"TELEFONDAN TEKRAR : {tel_tekrar} kayit isaretlendi")
    out.sort(key=lambda r:(r["kategori"],r["alt_kategori"],r["ad"]))
    json.dump(out, open("tuzla_data.json","w"), ensure_ascii=False, separators=(",",":"))

    print(f"OSM         : {len(osm)}")
    print(f"IBB         : {len(ibb)}   -> birlesen {birlesen}, yeni {yeni}")
    print(f"GISBIR      : {len(gis)}")
    print(f"BELEDIYE    : kurum {len(bel_kurum)} -> birlesen {bel_birlesen}, yeni {bel_yeni}")
    print(f"              eczane {len(bel_ecz)} -> telefon dolan {tel_dolan}, eslesmeyen {ecz_eslesmeyen}")
    print(f"TOPLAM      : {len(out)}")
    print()
    c=collections.Counter(r["kategori"] for r in out)
    for k,v in c.most_common(): print(f"  {v:4d}  {k}")
    print()
    print("--- SAGLIK DETAY ---")
    s=collections.Counter(r["alt_kategori"] for r in out if r["kategori"]=="Sağlık")
    for k,v in s.most_common(): print(f"  {v:4d}  {k}")
    print()
    ks=collections.Counter(r["kaynak"] for r in out)
    print("--- KAYNAK ---")
    for k,v in ks.most_common(): print(f"  {v:4d}  {k}")
    tel=sum(1 for r in out if r["telefon"]); adr=sum(1 for r in out if r["adres"])
    print()
    print(f"telefonu olan : {tel}/{len(out)} = %{round(100*tel/len(out))}")
    print(f"adresi olan   : {adr}/{len(out)} = %{round(100*adr/len(out))}")
    tk=[r for r in out if r.get("olasi_tekrar")]
    print(f"OLASI TEKRAR  : {len(tk)}  (ayni tur, 250m icinde -> sahada dogrulanmali)")
    import collections as _c
    for k,v in _c.Counter(r["alt_kategori"] for r in tk).most_common(6):
        print(f"    {v:3d}  {k}")
    cel=[r for r in out if r.get("ad_celiskisi")]
    print(f"AD CELISKISI  : {len(cel)}  (ayni noktada iki kaynak farkli isim veriyor)")
    for r in cel[:12]:
        print(f'    "{r["ad"][:26]:26s}" <-> "{r["diger_ad"][:26]:26s}" | {r["alt_kategori"]}')


# Guard: bu dosya modul seviyesinde main() cagiriyordu, yani `import birlestir`
# tum hatti calistiriyordu (ve isletmeler.json olmadigi icin cokuyordu).
if __name__ == "__main__":
    main()
