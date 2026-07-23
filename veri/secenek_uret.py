#!/usr/bin/env python3
"""tuzla_data.json -> secenekler.json (kategori + mahalle listesi).

NEDEN: ekle.html yalnizca iki acilir menuyu doldurmak icin 963 KB'lik
tuzla_data.json'u indiriyordu. Gereken veri ~1 KB.

Kategoriler ve mahalleler UYDURULMUYOR, veriden turetiliyor: tek kaynak
hala tuzla_data.json. Veri degisince bu script yeniden calistirilir.

Kullanim: python3 secenek_uret.py
"""
import json
import pathlib

KAYNAK = pathlib.Path(__file__).parent / "tuzla_data.json"
HEDEF = pathlib.Path(__file__).parent / "secenekler.json"


def tr_sirala(degerler):
    # Turkce siralama: 'i' ve 'I' ayrimi icin basit normalizasyon
    duzen = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return sorted(degerler, key=lambda s: s.translate(duzen).casefold())


def main():
    kayitlar = json.loads(KAYNAK.read_text(encoding="utf-8"))

    kategoriler = tr_sirala({r["kategori"] for r in kayitlar if r.get("kategori")})
    mahalleler = tr_sirala({r["mahalle"] for r in kayitlar if r.get("mahalle")})

    cikti = {
        "_uretildi": "veri/secenek_uret.py ile tuzla_data.json'dan turetildi",
        "_kayit_sayisi": len(kayitlar),
        "kategoriler": kategoriler,
        "mahalleler": mahalleler,
    }
    HEDEF.write_text(
        json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    kaynak_kb = KAYNAK.stat().st_size // 1024
    hedef_kb = max(1, HEDEF.stat().st_size // 1024)
    print(f"{len(kategoriler)} kategori, {len(mahalleler)} mahalle yazildi.")
    print(f"{HEDEF.name}: {hedef_kb} KB  (kaynak {kaynak_kb} KB)")


if __name__ == "__main__":
    main()
