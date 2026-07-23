#!/usr/bin/env python3
"""Istanbul Noter Odasi 'Bagli Noterlikler' dizini -> Tuzla adresli noterler.

NEDEN ADRESTEN SUZUYORUZ: Tuzla'nin kendi noterligi yok; ilcedeki noterler
Kartal adliyesine bagli oldugu icin "Kartal 20. Noteri" gibi anilirlar.
Adi "Tuzla" diye arasan hicbirini bulamazsin. Tek gercek olcut ADRES.
(OSM'deki tek noter kaydi da tam olarak boyleydi: "Kartal 20. Noteri".)

Kaynak kamuya acik resmi dizin; noterler kamu gorevlisi.
"""
import re, html, json, time, urllib.parse, subprocess

URL = "https://portal.tnb.org.tr/istanbulNoterOdasi/Sayfalar/BagliNoterlikler.aspx"
BASLIK = [
    "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H", "Accept-Language: tr-TR,tr;q=0.9",
    "-H", "Accept-Encoding: gzip, deflate, br",
]

def getir(veri=None):
    cmd = ["curl","-sS","--compressed",*BASLIK]
    if veri:
        cmd += ["-H","Content-Type: application/x-www-form-urlencoded","--data",veri]
    cmd += [URL]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout

def gizli(s):
    d = {}
    for ad in ("__VIEWSTATE","__VIEWSTATEGENERATOR","__EVENTVALIDATION","__REQUESTDIGEST"):
        m = re.search(r'name="%s"[^>]*value="([^"]*)"' % ad, s)
        if m: d[ad] = html.unescape(m.group(1))
    return d

def sayfa_no(s):
    m = re.search(r"Sayfa No\s*/\s*Toplam Sayfa\s*:\s*(\d+)\s*/\s*(\d+)", s)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)

HUCRE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
def satirlar(s):
    m = re.search(r'id="[^"]*gvNoterler"[^>]*>(.*?)</table>', s, re.S | re.I)
    if not m: return []
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S | re.I):
        if "<th" in tr.lower(): continue
        h = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in HUCRE.findall(tr)]
        if len(h) >= 7 and h[0] and "Sayfa No" not in h[0]:
            out.append(h)
    return out

s = getir()
no, top = sayfa_no(s)
print(f"sayfa {no}/{top}")
assert top and top > 1, "sayfalama okunamadi"

HEDEF = "ctl00$ctl36$g_d9367c71_ceed_4bb2_9d5e_64c08632995e$gvNoterler"
tum, gorulen = [], set()
for p in range(1, top + 1):
    if p > 1:
        g = gizli(s)
        veri = urllib.parse.urlencode({
            "__EVENTTARGET": HEDEF, "__EVENTARGUMENT": f"Page${p}", **g})
        s = getir(veri)
        time.sleep(0.7)                       # nazik ol
    n, _ = sayfa_no(s)
    r = satirlar(s)
    yeni = [x for x in r if tuple(x) not in gorulen]
    for x in yeni: gorulen.add(tuple(x))
    tum += yeni
    print(f"  sayfa {n:>2}: {len(r):>2} satir ({len(yeni)} yeni) · toplam {len(tum)}")
    if n != p:
        print(f"  !! sayfa {p} istendi ama {n} geldi - sayfalama kirildi, duruyorum")
        break

json.dump(tum, open("tnb_ham.json","w"), ensure_ascii=False, indent=1)
print(f"\nTOPLAM: {len(tum)} noterlik  (dizin 482 diyor)")
