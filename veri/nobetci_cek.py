#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tuzla nöbetçi eczaneleri -> veri/nobetci.json

SUNUCU TARAFI çeker (GitHub Actions cron). Tarayıcı değil, o yüzden CORS /
mixed-content / API key derdi yok. Bağımlılık yok: sadece stdlib (urllib),
Actions'ta ekstra kurulum gerekmiyor.

Kaynak: istanbul.eczaneleri.org (sunucu-render, parse edilebilir). Resmî değil,
o yüzden frontend HER ZAMAN resmî kaynağa (e-Devlet / İl Eczacı Odası) fallback
linki de gösterir. Kaynak yapısı değişirse: 0 eczane -> exit 1, böylece cron
BAŞARISIZ olur ve eldeki son geçerli nobetci.json KORUNUR (boşla ezilmez).
"""
import json, re, sys, html as _html, os
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen

KAYNAK_URL = "https://istanbul.eczaneleri.org/tuzla/nobetci-eczaneler.html"
KAYNAK_AD  = "istanbul.eczaneleri.org"
CIKIS      = os.path.join(os.path.dirname(__file__), "nobetci.json")
TR         = timezone(timedelta(hours=3))  # Europe/Istanbul (DST yok, sabit +03)


def getir(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (TuzlaHaritasi nöbetçi botu)"})
    with urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def ayikla(sayfa):
    """<li class="media"> bloklarından ad + adres + detay linki çıkarır."""
    ecz = []
    for blok in re.findall(r'<li class="media">(.*?)</li>', sayfa, re.S):
        ad_m = re.search(r"<h4>(.*?)<span", blok, re.S)
        if not ad_m:
            continue
        ad = _html.unescape(re.sub(r"<[^>]+>", "", ad_m.group(1))).strip()
        if not ad:
            continue
        # detay linki: <a href="/tuzla-...-eczanesi.html">
        det_m = re.search(r'href="(/[^"]*eczanesi\.html)"', blok)
        detay = ("https://istanbul.eczaneleri.org" + det_m.group(1)) if det_m else ""
        # adres: tüm etiketleri sök, adı ve "Tuzla" etiketini at
        metin = _html.unescape(re.sub(r"<[^>]+>", " ", blok))
        metin = re.sub(r"\s+", " ", metin).strip()
        adres = metin.replace(ad, "", 1).strip()
        adres = re.sub(r"^Tuzla\s+", "", adres).strip()          # baştaki ilçe etiketi
        adres = re.sub(r"\s+Tuzla$", "", adres).strip()
        # kaynak mahalle etiketini baş+son tekrarlıyor ("Aydınlı ... Aydınlı")
        parca = adres.split()
        if len(parca) > 2 and parca[-1].lower() == parca[0].lower():
            adres = " ".join(parca[:-1]).strip()
        ecz.append({"ad": ad, "adres": adres, "detay": detay})
    return ecz


def main():
    try:
        sayfa = getir(KAYNAK_URL)
    except Exception as e:
        print(f"HATA: kaynak çekilemedi: {e}", file=sys.stderr)
        sys.exit(1)

    ecz = ayikla(sayfa)
    if not ecz:
        # yapı değişmiş olabilir. Boş yazma -> son geçerli dosya korunsun.
        print("HATA: hiç eczane ayıklanamadı, yapı değişmiş olabilir. Dosya korunuyor.", file=sys.stderr)
        sys.exit(1)

    veri = {
        "ilce": "Tuzla",
        "kaynak": KAYNAK_AD,
        "kaynak_url": KAYNAK_URL,
        "guncelleme": datetime.now(TR).isoformat(timespec="minutes"),
        "eczaneler": ecz,
    }
    with open(CIKIS, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(ecz)} nöbetçi eczane yazıldı -> {CIKIS}")


if __name__ == "__main__":
    main()
