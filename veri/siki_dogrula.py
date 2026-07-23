#!/usr/bin/env python3
"""SIKI telefon dogrulama.

ONCEKI HATA: regex ham HTML'de calisiyordu ve WordPress'in CSS zaman
damgalarini (vc_custom_1538478005860) telefon saniyordu. Rakam dizisinin
ortasindan numara cikariyordu.

DUZELTME:
  1. (?<!\d) ve (?!\d) -> eslesme daha uzun bir rakam dizisinin PARCASI olamaz.
  2. Gecerli TR onekleri: 0(53x|54x|55x|50x) cep, 0216/0212 sabit, 0850 kurumsal.
     0518, 0521, 0512 diye bir sey YOK - onceki cikti bunlarla doluydu, alarm buydu.
  3. Ayrica <script>/<style> bloklari atiliyor: numara metinde gecmeli.
"""
import re, sys, json, subprocess, io

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
GECERLI = re.compile(r"^0(5(0[0-9]|3[0-9]|4[0-9]|5[0-9])|216|212|850)")

def cek(u):
    """HTML'i getirir ve DOGRU kodlamayla cozer.

    Turkiye'de cok sayida eski site hala ISO-8859-9 / Windows-1254 kullaniyor.
    text=True ile UTF-8 varsaymak 0xfc ('u') baytinda cokuyordu. Once
    meta charset'e bakiyoruz, yoksa utf-8 deneyip cp1254'e dusuyoruz.
    """
    r=subprocess.run(["curl","-skSL","--max-time","30","-H",f"User-Agent: {UA}",
                      "-H","Accept-Language: tr-TR,tr;q=0.9","--compressed",u],
                     capture_output=True,timeout=45)          # text=True YOK: ham bayt
    b=r.stdout
    m=re.search(rb'charset=["\']?([\w\-]+)', b[:4000], re.I)
    adaylar=[]
    if m:
        try: adaylar.append(m.group(1).decode("ascii").lower())
        except Exception: pass
    adaylar += ["utf-8","cp1254","iso-8859-9","latin-1"]
    for enc in adaylar:
        try: return b.decode(enc)
        except (UnicodeDecodeError, LookupError): continue
    return b.decode("utf-8", errors="replace")

def temiz(s):
    s=re.sub(r"<script[^>]*>.*?</script>","",s,flags=re.S|re.I)
    s=re.sub(r"<style[^>]*>.*?</style>","",s,flags=re.S|re.I)
    return s

# lookaround: daha uzun rakam dizisinin parcasi olamaz
TEL = re.compile(r"(?<!\d)(?:\+?90[\s\-\.\(\)]*)?\(?(0?5\d{2}|0?216|0?212|0?850)\)?[\s\-\.]?(\d{3})[\s\-\.]?(\d{2})[\s\-\.]?(\d{2})(?!\d)")

def telleri(html):
    m=temiz(html)
    b=set()
    for x in TEL.finditer(m):
        g=x.group(1); g=g if g.startswith("0") else "0"+g
        n=g+x.group(2)+x.group(3)+x.group(4)
        if len(n)==11 and GECERLI.match(n): b.add(n)
    for t in re.findall(r'href=["\']tel:([^"\']+)',html,re.I):
        d=re.sub(r"\D","",t)
        if d.startswith("90"): d="0"+d[2:]
        if len(d)==11 and GECERLI.match(d): b.add(d)
    return b

if __name__=="__main__":
    kaynak=json.load(open(sys.argv[1]))
    alan_tel=sys.argv[2]; alan_url=sys.argv[3]
    print(f"{'AD':34s} {'ISTENEN':13s} {'SIKI SONUC':12s} sayfadaki gecerli numaralar")
    print("-"*104)
    degisen=[]
    for r in kaynak:
        url=r.get(alan_url,"")
        if not url or r.get("dogrulama") in ("SUPHELI",) : continue
        eski=r.get("tel_dogrulama") or r.get("tel_dogru") or "-"
        if eski not in ("ESLESTI",): continue
        html=cek(url); b=telleri(html)
        istenen=[re.sub(r"\D","",x) for x in str(r.get(alan_tel,"")).split(";") if x.strip()]
        yeni="ESLESTI" if any(x in b for x in istenen) else ("FARKLI" if b else "SAYFADA YOK")
        isaret="" if yeni==eski else "   <<< DEGISTI"
        print(f"{r['ad'][:34]:34s} {(istenen[0] if istenen else '-'):13s} {yeni:12s} {sorted(b)[:3]}{isaret}")
        if yeni!=eski: degisen.append((r["ad"],eski,yeni))
    print()
    print(f"DEGISEN: {len(degisen)}")
    for a,e,y in degisen: print(f"   {a}: {e} -> {y}")
