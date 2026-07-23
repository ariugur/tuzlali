# Yayına alma (deploy) adımları

Faz 2 (nöbetçi eczane cron), Faz 5 (analytics) ve GEO'nun çalışması için site
bir GitHub repo'da + yayında olmalı. Kod hazır; aşağıdakiler senin hesaplarınla
yapılacak tek seferlik adımlar.

## 1. GitHub'a it
Repo lokalde hazır (`git init` + ilk commit yapıldı). Uzak repo ekle ve it:
```bash
git remote add origin https://github.com/<kullanıcı>/tuzla-hali.git
git branch -M main
git push -u origin main
```

## 2. Ücretsiz statik hosting bağla
Önerilen: **Cloudflare Pages** (ücretsiz, hızlı, TR'ye yakın).
- Cloudflare Pages → "Connect to Git" → bu repo → build komutu YOK (statik),
  output dizini kök (`/`).
- Alternatif: GitHub Pages (Settings → Pages → Deploy from branch → main / root).

## 3. Nöbetçi eczane cron'u aç
- `.github/workflows/nobetci.yml` zaten repoda. GitHub → Actions sekmesi →
  workflow'u **Enable** et.
- Günde 2 kez (09:30 ve 18:30 TR) otomatik çalışır, `veri/nobetci.json`'u günceller.
- Hemen test: Actions → "Nöbetçi eczane güncelle" → **Run workflow** (manuel tetik).

## 4. Alan adı — TAMAM ✅
Domain **tuzlali.net** olarak yerleştirildi (`SITE_KOK`, index/nobetci canonical,
robots, sitemap, 27 SEO sayfası, llms.txt). Placeholder kalmadı. Domain değişirse
`sayfa_uret.js` → `SITE_KOK`'u güncelle + `index.html`/`nobetci.html`/`robots.txt`'de
değiştir, sonra `node sayfa_uret.js`.
- DNS: tuzlali.net'i Cloudflare Pages / GitHub Pages hedefine yönlendir (2. adım).

## 5. Analytics (Faz 5 — ücretsiz, KVKK-dostu)
**Cloudflare Web Analytics** (çerezsiz, ücretsiz):
- Cloudflare → Web Analytics → site ekle → verilen `<script>` beacon'ı tüm
  sayfaların `</body>` öncesine koy (veya `ortak.js` üzerinden tek yerden enjekte et).
- Alternatif: GoatCounter (ücretsiz, açık kaynak).

---
Not: Nöbetçi eczane verisi açık kaynaktan (istanbul.eczaneleri.org) derlenir;
sayfa her zaman e-Devlet resmî sorgulamaya da link verir. Kaynağın HTML yapısı
değişirse `veri/nobetci_cek.py` 0 sonuç döndürüp cron'u başarısız yapar ve eldeki
son geçerli `nobetci.json` korunur (boşla ezilmez).
