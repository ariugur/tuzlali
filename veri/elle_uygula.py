#!/usr/bin/env python3
"""elle.json'daki kayitlardan tuzla_data.json'da OLMAYANLARI ekler.

NEDEN VAR: birlestir.py bugun calistirilamiyor -- tuzla_osm_raw.json ve
isletmeler.json diskte yok, hat ancak Overpass'a yeni sorgu atarak calisir, o da
tek bir kayit icin tum veri setine bugunku OSM degisikliklerini sokar.
Bu script sadece elle.json'daki eksikleri ekliyor, baska hicbir seye dokunmuyor.
Hat geri geldiginde birlestir.py zaten elle.json'u okuyor; bu dosya gereksizlesir.

birlestir.py'nin elle blogunun AYNISINI yapiyor (slug, FIELDS, tel_bicim) ve
bunlari oradan ITHAL ediyor -- ikinci kopya sema tutmuyoruz.

Idempotent: iki kez calistirmak kayit tekrarlamaz (id kontrolu var).
"""
import json, shutil, sys
from birlestir import FIELDS, slug, tel_bicim

DOSYA = "tuzla_data.json"


def main():
    kayitlar = json.load(open(DOSYA, encoding="utf-8"))
    mevcut = {r.get("id") for r in kayitlar}

    elle = [r for r in json.load(open("elle.json", encoding="utf-8"))
            if not any(k.startswith("_") for k in r)]

    yeni = []
    for r in elle:
        if r.get("id") in mevcut:
            continue
        if not r.get("lat"):
            print(f"ATLANDI (lat yok): {r.get('ad')}", file=sys.stderr)
            continue
        r.setdefault("slug", slug(r["ad"]))
        kayit = {k: r.get(k, "") for k in FIELDS}
        kayit["telefon"] = tel_bicim(kayit.get("telefon"))
        yeni.append(kayit)

    if not yeni:
        print("Eklenecek yeni kayit yok.")
        return

    shutil.copy(DOSYA, DOSYA + ".yedek")
    kayitlar += yeni
    json.dump(kayitlar, open(DOSYA, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    for k in yeni:
        print(f"\n+ {k['id']}")
        for a in ("ad", "kategori", "alt_kategori", "mahalle", "adres",
                  "telefon", "calisma_saatleri", "lat", "lon", "kaynak"):
            print(f"    {a:18} {k[a]!r}")
    print(f"\n{len(yeni)} kayit eklendi. Toplam: {len(kayitlar)}. Yedek: {DOSYA}.yedek")


if __name__ == "__main__":
    main()
