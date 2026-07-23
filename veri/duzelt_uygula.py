#!/usr/bin/env python3
"""duzeltme.py'deki duzeltmeleri tuzla_data.json'a uygular.

NEDEN VAR: tuzla_osm_raw.json ve isletmeler.json diskte yok, yani birlestir.py
bugun calistirilamiyor (Overpass'a yeni sorgu gerekir, o da tek bir duzeltme
icin tum veri setini oynatir). Bu script araya girmeden ayni sozlugu uyguluyor.
Hat geri geldiginde birlestir.py zaten ayni sozlugu okuyor; bu dosya gereksizlesir.

Idempotent: iki kez calistirmak zarar vermez, ayni degerleri yazar.
"""
import json, shutil, sys
import duzeltme

DOSYA = "tuzla_data.json"


def main():
    kayitlar = json.load(open(DOSYA, encoding="utf-8"))
    onceki = {r["id"]: dict(r) for r in kayitlar if r.get("id") in duzeltme.DUZELTME}

    n, eksik = duzeltme.uygula(kayitlar)
    if eksik:
        print(f"UYARI: DUZELTME'deki id veride yok: {eksik}", file=sys.stderr)
    if not n:
        print("Degisen kayit yok.")
        return

    shutil.copy(DOSYA, DOSYA + ".yedek")
    json.dump(kayitlar, open(DOSYA, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # Ne degisti, alan alan. "Duzeltildi" demek yetmez; neyin degistigi gorunmeli.
    for r in kayitlar:
        e = onceki.get(r.get("id"))
        if not e:
            continue
        print(f"\n{r['id']}")
        for k in sorted(set(e) | set(r)):
            if e.get(k) != r.get(k):
                print(f"  {k}:\n    onceki: {e.get(k)!r}\n    simdi : {r.get(k)!r}")
    print(f"\n{n} kayit duzeltildi. Yedek: {DOSYA}.yedek")


if __name__ == "__main__":
    main()
