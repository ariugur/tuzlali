#!/usr/bin/env python3
"""Tersane firmalarini kapi numarasina gore cadde boyunca dagitir.
DIKKAT: sonuc YAKLASIK konumdur, dogrulanmis degildir. konum_kalitesi='yaklasik' olarak isaretlenir."""
import json, re, math

def load_streets():
    d = json.load(open("streets_raw.json"))
    by = {}
    for e in d["elements"]:
        n = e.get("tags", {}).get("name", "")
        g = e.get("geometry") or []
        if not g: continue
        key = None
        nl = n.lower()
        if "tersaneler caddesi" in nl: key = "tersaneler"
        elif "güzin" in nl or "guzin" in nl: key = "guzin"
        elif "sinem" in nl: key = "sinem"
        elif "kızılçam" in nl or "kizilcam" in nl: key = "kizilcam"
        elif "rauf orbay" in nl: key = "rauforbay"
        if key: by.setdefault(key, []).extend([(p["lon"], p["lat"]) for p in g])
    # her sokagi tek bir polyline'a indir: baslangictan uca dogru sirala
    out = {}
    for k, pts in by.items():
        pts = list(dict.fromkeys(pts))
        # ana ekseni bul (lon mu lat mi daha cok degisiyor)
        lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
        if (max(lons)-min(lons)) >= (max(lats)-min(lats)):
            pts.sort(key=lambda p: p[0])
        else:
            pts.sort(key=lambda p: p[1])
        out[k] = pts
    return out

def cum_len(pts):
    d = [0.0]
    for i in range(1, len(pts)):
        dx = (pts[i][0]-pts[i-1][0]) * math.cos(math.radians(pts[i][1])) * 111320
        dy = (pts[i][1]-pts[i-1][1]) * 110540
        d.append(d[-1] + math.hypot(dx, dy))
    return d

def at_frac(pts, f):
    d = cum_len(pts); total = d[-1]
    if total == 0: return pts[0][1], pts[0][0]
    target = f * total
    for i in range(1, len(d)):
        if d[i] >= target:
            seg = d[i]-d[i-1]
            t = 0 if seg == 0 else (target-d[i-1])/seg
            lon = pts[i-1][0] + (pts[i][0]-pts[i-1][0])*t
            lat = pts[i-1][1] + (pts[i][1]-pts[i-1][1])*t
            return lat, lon
    return pts[-1][1], pts[-1][0]

STREET_PAT = [
    (re.compile(r"Tersaneler\s+Cad", re.I), "tersaneler"),
    (re.compile(r"Güzin\s+So?k", re.I), "guzin"),
    (re.compile(r"Sinem\s+Sk?", re.I), "sinem"),
    (re.compile(r"Kızılçam\s+So?k", re.I), "kizilcam"),
    (re.compile(r"Rauf\s+Orbay", re.I), "rauforbay"),
]

def parse(rec):
    a = rec["adres"]
    for pat, key in STREET_PAT:
        if pat.search(a):
            m = re.search(r"No[:.]?\s*(\d+)", a, re.I)
            if m: return key, int(m.group(1))
            return key, None
    return None, None

def main():
    streets = load_streets()
    recs = json.load(open("gisbir_tuzla.json"))

    # her sokak icin numara araligi
    nums = {}
    for r in recs:
        k, n = parse(r)
        if k and n is not None: nums.setdefault(k, []).append(n)
    rng = {k: (min(v), max(v)) for k, v in nums.items()}

    ok = 0
    for r in recs:
        k, n = parse(r)
        if k and k in streets and n is not None and k in rng:
            lo, hi = rng[k]
            f = 0.5 if hi == lo else (n-lo)/(hi-lo)
            f = 0.05 + f*0.90   # uclardan biraz iceri al
            lat, lon = at_frac(streets[k], f)
            r["lat"], r["lon"] = round(lat, 6), round(lon, 6)
            r["konum_kalitesi"] = "yaklasik"
            r["konum_notu"] = f"{k} caddesi uzerinde No:{n} interpolasyonu - DOGRULANMADI"
            ok += 1
        else:
            r["lat"] = r["lon"] = None
            r["konum_kalitesi"] = "yok"
            r["konum_notu"] = "adresten cikarilamadi - elle konulmali"
        r["kategori"] = "Marina & Denizcilik"
        r["kaynak"] = "gisbir"
        r["dogrulandi"] = False
        r["instagram"] = ""
        r["calisma_saatleri"] = ""
        r["mahalle"] = "Tersaneler Bölgesi"
        r["slug"] = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-",
            r["ad"].lower().translate(str.maketrans("ığüşöç", "igusoc")))).strip("-")[:70]
        r["id"] = "g" + r["slug"][:24]

    json.dump(recs, open("gisbir_tuzla_geo.json", "w"), ensure_ascii=False, indent=1)
    print(f"YAKLASIK KONUM ATANDI : {ok}/{len(recs)}")
    print(f"ELLE KONULACAK        : {len(recs)-ok}")
    print()
    for r in recs:
        if r["lat"] is None:
            print(f"  [elle] {r['ad'][:52]}")
    print("\n--- ornek yaklasik konumlar ---")
    for r in recs[:5]:
        if r["lat"]: print(f"  {r['ad'][:40]:40s} {r['lat']},{r['lon']}")

main()
