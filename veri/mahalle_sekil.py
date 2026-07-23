#!/usr/bin/env python3
"""Her mahallenin GERCEK sinir poligonunu, grid hucresinde cizilebilecek
normalize edilmis SVG path'ine cevirir.
Neden: fotograf-oncelikli grid istendi ama 17 mahallenin 15'inin fotografi yok.
Sahte stok fotograf yerine mahallenin kendi sekli. Fotograf gelince yerini birakir."""
import json, re

def _yakin(a,b,e=1e-7): return abs(a[0]-b[0])<e and abs(a[1]-b[1])<e

def ring_of(el):
    segs=[]
    for m in el.get("members",[]):
        if m.get("type")!="way" or m.get("role") not in ("outer",""): continue
        g=m.get("geometry")
        if g: segs.append([(p["lon"],p["lat"]) for p in g])
    if not segs: return []
    ring=list(segs.pop(0)); degisti=True
    while segs and degisti:
        degisti=False
        for i,s in enumerate(segs):
            if   _yakin(ring[-1],s[0]):  ring+=s[1:];            segs.pop(i); degisti=True; break
            elif _yakin(ring[-1],s[-1]): ring+=s[::-1][1:];      segs.pop(i); degisti=True; break
            elif _yakin(ring[0], s[-1]): ring=s[:-1]+ring;       segs.pop(i); degisti=True; break
            elif _yakin(ring[0], s[0]):  ring=s[::-1][:-1]+ring; segs.pop(i); degisti=True; break
    return ring

def sadelestir(pts, tol):
    """Douglas-Peucker: 400 nokta grid hucresinde gereksiz, ~60'a indir."""
    if len(pts)<3: return pts
    def dik(p,a,b):
        if a==b: return ((p[0]-a[0])**2+(p[1]-a[1])**2)**.5
        t=max(0,min(1,((p[0]-a[0])*(b[0]-a[0])+(p[1]-a[1])*(b[1]-a[1]))/((b[0]-a[0])**2+(b[1]-a[1])**2)))
        px,py=a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])
        return ((p[0]-px)**2+(p[1]-py)**2)**.5
    def dp(p):
        if len(p)<3: return p
        imax,dmax=0,0
        for i in range(1,len(p)-1):
            d=dik(p[i],p[0],p[-1])
            if d>dmax: imax,dmax=i,d
        if dmax>tol: return dp(p[:imax+1])[:-1]+dp(p[imax:])
        return [p[0],p[-1]]
    return dp(pts)

def temiz_ad(s):
    return re.sub(r"\s*(mahallesi|mahalle|mah\.?|mh\.?)\s*$","",str(s).strip(),flags=re.I).strip()

def slug(s):
    import unicodedata
    s=str(s).lower()
    for a,b in {"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c","İ":"i"}.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",s)).strip("-")

W=H=100
out={}
raw=json.load(open("mahalle_raw.json"))
for el in raw.get("elements",[]):
    ad=(el.get("tags") or {}).get("name")
    if not ad: continue
    r=ring_of(el)
    if len(r)<4: continue
    r=sadelestir(r, 0.0002)
    xs=[p[0] for p in r]; ys=[p[1] for p in r]
    x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
    # en-boy oranini koru, kutuya ortala
    import math
    sx=(x1-x0)*math.cos(math.radians((y0+y1)/2)); sy=(y1-y0)
    olcek=min(W/sx, H/sy)*0.86 if sx and sy else 1
    ox=(W-sx*olcek)/2; oy=(H-sy*olcek)/2
    d=[]
    for i,(lon,lat) in enumerate(r):
        X=ox+(lon-x0)*math.cos(math.radians((y0+y1)/2))*olcek
        Y=H-(oy+(lat-y0)*olcek)          # SVG y asagi
        d.append(f"{'M' if i==0 else 'L'}{X:.1f},{Y:.1f}")
    ad_t=temiz_ad(ad)
    out[ad_t]={"slug":slug(ad_t), "path":"".join(d)+"Z", "nokta":len(r)}

json.dump(out, open("mahalle_sekil.json","w"), ensure_ascii=False, separators=(",",":"))
print(f"SEKIL: {len(out)} mahalle")
for k,v in sorted(out.items()):
    print(f"  {k[:20]:20s} {v['nokta']:3d} nokta  path {len(v['path']):5d} kr")
print(f"\ntoplam json: {len(json.dumps(out))} byte")
