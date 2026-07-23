import subprocess, re, json, time
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
def cek(u):
    r=subprocess.run(["curl","-sSL","--max-time","25","-H",f"User-Agent: {UA}",
                      "-H","Accept-Language: tr-TR,tr;q=0.9","--compressed",u],
                     capture_output=True,text=True,timeout=40)
    return r.stdout
def rakam(t): return re.sub(r"\D","",t or "")

d=json.load(open("guzellik_dogrulama.json"))
print(f"{'AD':32s} {'LISTEDEKI TEL':16s} {'SAYFADA':16s} SONUC")
print("-"*84)
sonuc=[]
for r in d:
    if r["dogrulama"]!="GERCEK" or "yandex" not in r["url"]:
        r["tel_dogrulama"]="-"; sonuc.append(r); continue
    s=cek(r["url"])
    # sayfadaki tum TR cep/sabit numaralari
    bulunan=set()
    for m in re.finditer(r'(?:\+90[\s\-]?)?(5\d{2}|216|212)[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})', s):
        bulunan.add("0"+m.group(1)+m.group(2)+m.group(3)+m.group(4))
    liste=rakam(r["telefon"])
    if not liste:
        r["tel_dogrulama"]="listede yok"
        if bulunan: r["tel_bulunan"]=sorted(bulunan)[:2]
    elif liste in bulunan: r["tel_dogrulama"]="ESLESTI"
    elif bulunan: r["tel_dogrulama"]="FARKLI"; r["tel_bulunan"]=sorted(bulunan)[:2]
    else: r["tel_dogrulama"]="sayfada tel yok"
    print(f"{r['ad'][:32]:32s} {r['telefon'] or '(yok)':16s} {(r.get('tel_bulunan') or [''])[0] if r.get('tel_bulunan') else '':16s} {r['tel_dogrulama']}")
    sonuc.append(r); time.sleep(0.4)
json.dump(sonuc,open("guzellik_dogrulama.json","w"),ensure_ascii=False,indent=1)
import collections
print()
for k,v in collections.Counter(x.get("tel_dogrulama","-") for x in sonuc).most_common(): print(f"  {v:3d}  {k}")
