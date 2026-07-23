#!/usr/bin/env python3
"""Her kayda koordinatindan mahalle atar (nokta-poligon).
Neden: veri alanindaki 'mahalle' %38 dolu ve 37 farkli yazim var
(Aydinli / Aydınlı Mahallesi / Aydınlı ...). Koordinat tek gercek kaynak."""
import json, re, collections

def ring_of(el):
    """OSM relation -> dis halka koordinat listesi. 'outer' way'leri birlestirir."""
    segs=[]
    for m in el.get("members",[]):
        if m.get("type")!="way": continue
        if m.get("role") not in ("outer",""): continue
        g=m.get("geometry")
        if g: segs.append([(p["lon"],p["lat"]) for p in g])
    if not segs: return []
    # segmentleri uc uca ekle
    ring=list(segs.pop(0))
    degisti=True
    while segs and degisti:
        degisti=False
        for i,s in enumerate(segs):
            if   _yakin(ring[-1], s[0]):  ring+=s[1:];            segs.pop(i); degisti=True; break
            elif _yakin(ring[-1], s[-1]): ring+=s[::-1][1:];      segs.pop(i); degisti=True; break
            elif _yakin(ring[0],  s[-1]): ring=s[:-1]+ring;       segs.pop(i); degisti=True; break
            elif _yakin(ring[0],  s[0]):  ring=s[::-1][:-1]+ring; segs.pop(i); degisti=True; break
    return ring

def _yakin(a,b,e=1e-7):
    return abs(a[0]-b[0])<e and abs(a[1]-b[1])<e

def icinde(pt, ring):
    """Isin atma (ray casting). pt=(lon,lat)"""
    x,y=pt; n=len(ring); ic=False
    j=n-1
    for i in range(n):
        xi,yi=ring[i]; xj,yj=ring[j]
        if ((yi>y)!=(yj>y)) and (x < (xj-xi)*(y-yi)/((yj-yi) or 1e-12)+xi):
            ic = not ic
        j=i
    return ic

def bbox(ring):
    xs=[p[0] for p in ring]; ys=[p[1] for p in ring]
    return min(xs),min(ys),max(xs),max(ys)

def temiz_ad(s):
    """'Aydınlı Mahallesi' -> 'Aydınlı'. Tek kanonik ad."""
    s=re.sub(r"\s*(mahallesi|mahalle|mah\.?|mh\.?)\s*$","",str(s).strip(),flags=re.I)
    return s.strip()

def main():
    raw=json.load(open("mahalle_raw.json"))
    polys=[]
    for el in raw.get("elements",[]):
        ad=(el.get("tags",{}) or {}).get("name")
        if not ad: continue
        r=ring_of(el)
        if len(r)<4: continue
        polys.append({"ad":temiz_ad(ad), "ring":r, "bb":bbox(r)})
    print(f"MAHALLE POLIGONU: {len(polys)}")
    for p in sorted(polys, key=lambda x:x["ad"]):
        print(f"  {p['ad'][:26]:26s}  ({len(p['ring'])} nokta)")
    print()

    d=json.load(open("tuzla_data.json"))
    atanan=0; disarida=[]
    for r in d:
        pt=(r["lon"], r["lat"])
        bulundu=None
        for p in polys:
            x0,y0,x1,y1=p["bb"]
            if not (x0<=pt[0]<=x1 and y0<=pt[1]<=y1): continue
            if icinde(pt, p["ring"]): bulundu=p["ad"]; break
        if bulundu:
            r["mahalle"]=bulundu; atanan+=1
        else:
            # poligon disi: eldeki metni koru ama isaretle
            eski=temiz_ad(r.get("mahalle") or "")
            r["mahalle"]=eski
            if eski: disarida.append((r["ad"], eski))
            else: disarida.append((r["ad"], ""))

    json.dump(d, open("tuzla_data.json","w"), ensure_ascii=False, separators=(",",":"))
    print(f"KOORDINATTAN ATANAN : {atanan}/{len(d)}  (%{round(100*atanan/len(d))})")
    print(f"POLIGON DISINDA     : {len(disarida)}")
    print()
    c=collections.Counter(r["mahalle"] for r in d if r["mahalle"])
    print(f"--- KANONIK MAHALLE: {len(c)} ---")
    for k,v in c.most_common(): print(f"  {v:4d}  {k}")
    bos=sum(1 for r in d if not r["mahalle"])
    print(f"\n  {bos} kayitta mahalle yok")

# Guard: main() modul seviyesinde cagriliyordu, yani `import mahalle_ata`
# tuzla_data.json'i sessizce YENIDEN YAZIYORDU. ring_of'u ithal etmek
# isteyen biri veriyi ezerdi.
if __name__ == "__main__":
    main()
