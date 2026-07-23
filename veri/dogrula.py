import subprocess, re, io, json, time
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
# Yandex jenerik basligi = org yok. Kontrol deneyiyle bulundu.
JENERIK = "Yandex Maps: Toplu taşıma"

def cek(u):
    r=subprocess.run(["curl","-sSL","--max-time","25","-H",f"User-Agent: {UA}",
                      "-H","Accept-Language: tr-TR,tr;q=0.9","--compressed",u],
                     capture_output=True,text=True,timeout=40)
    return r.stdout

def baslik(s):
    m=re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)',s,re.I)
    if not m: m=re.search(r'<title[^>]*>(.*?)</title>',s,re.S|re.I)
    return re.sub(r"\s+"," ",m.group(1)).strip() if m else ""

son=[]
for l in io.open("guzellik_ham.txt",encoding="utf-8"):
    ad,kat,adr,tel,url=l.rstrip("\n").split("|")
    s=cek(url); t=baslik(s)
    if "yandex.com.tr" in url:
        d = "GERCEK" if (t and JENERIK not in t) else "SAHTE/YOK"
    elif "instagram.com" in url or "facebook.com" in url:
        d = "TEST EDILEMEZ"
    else:
        # kendi sitesi: baslikta isletmenin adindan bir kelime gecmeli
        kok=[w for w in re.split(r"\W+",ad) if len(w)>3]
        d = "GERCEK" if any(w.lower() in t.lower() for w in kok) else "SUPHELI"
    son.append({"ad":ad,"kategori":kat,"adres":adr,"telefon":tel,"url":url,
                "baslik":t[:60],"dogrulama":d})
    print(f"{d:14s} {ad[:32]:32s} {t[:44]}")
    time.sleep(0.4)
json.dump(son,open("guzellik_dogrulama.json","w"),ensure_ascii=False,indent=1)
import collections
print()
for k,v in collections.Counter(x["dogrulama"] for x in son).most_common(): print(f"  {v:3d}  {k}")
