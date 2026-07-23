#!/usr/bin/env python3
"""GISBIR Tuzla firmalarini Nominatim ile geocode eder. Politika: 1 req/sn, gercek User-Agent."""
import json, time, urllib.parse, urllib.request, re, sys

UA = "TuzlaHaritasi/0.1 (yerel isletme haritasi; iletisim: uguraripro@gmail.com)"
TUZLA_BB = (40.79, 40.87, 29.25, 29.37)  # lat_min, lat_max, lon_min, lon_max

def nominatim(q, structured=None):
    base = "https://nominatim.openstreetmap.org/search?"
    p = {"format": "json", "limit": "3", "countrycodes": "tr",
         "viewbox": "29.25,40.87,29.37,40.79", "bounded": "1"}
    if structured:
        p.update(structured)
    else:
        p["q"] = q
    url = base + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        print(f"  !! {e}", file=sys.stderr)
        return []

def in_tuzla(lat, lon):
    return TUZLA_BB[0] <= lat <= TUZLA_BB[1] and TUZLA_BB[2] <= lon <= TUZLA_BB[3]

def strategies(rec):
    """Genisten dara dogru arama denemeleri."""
    adres = rec["adres"]
    # sokak + no cikar
    m = re.search(r"(Tersaneler Cad\w*|Güzin Sok\w*|Sinem Sk\w*|Kızılçam Sok\w*|Rauf Orbay Cad\w*)\s*No[:.]?\s*(\d+)", adres, re.I)
    out = []
    if m:
        sokak = m.group(1).replace("Cad", "Caddesi").replace("Sok", "Sokak").replace("Sk", "Sokak")
        sokak = re.sub(r"(Caddesii|Sokakak|Sokaki)", lambda x: x.group(0)[:-2], sokak)
        out.append({"street": f"{m.group(2)} {sokak}", "city": "Tuzla", "state": "İstanbul"})
    out.append({"q": f"{adres}, İstanbul, Türkiye"})
    # sadece sokak adi
    if m:
        out.append({"q": f"{m.group(1)}, Tuzla, İstanbul"})
    return out

def main():
    recs = json.load(open("gisbir_tuzla.json"))
    done = []
    for i, r in enumerate(recs, 1):
        hit = None
        for s in strategies(r):
            res = nominatim(None, s) if "q" not in s else nominatim(s["q"])
            time.sleep(1.1)  # Nominatim politikasi
            for x in res:
                lat, lon = float(x["lat"]), float(x["lon"])
                if in_tuzla(lat, lon):
                    hit = (lat, lon, x.get("display_name", "")[:60])
                    break
            if hit: break
        r["lat"] = hit[0] if hit else None
        r["lon"] = hit[1] if hit else None
        r["geocode_kaynak"] = hit[2] if hit else ""
        status = f"{hit[0]:.5f},{hit[1]:.5f}" if hit else "BULUNAMADI"
        print(f"{i:2d}/{len(recs)}  {r['ad'][:44]:44s} -> {status}")
        done.append(r)

    json.dump(done, open("gisbir_tuzla_geo.json", "w"), ensure_ascii=False, indent=1)
    ok = sum(1 for r in done if r["lat"])
    print(f"\n=== GEOCODE: {ok}/{len(done)} basarili ===")

main()
