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

## 3. Otomatik deploy + nöbetçi cron — TEK EKSİK: 1 secret
Repo GitHub'da (github.com/ariugur/tuzlali), site Cloudflare Pages'te
(tuzlali.pages.dev) CANLI. `.github/workflows/nobetci.yml` şunu yapar:
her push + günde 2x (09:30/18:30 TR) → siteyi Pages'e deploy + nöbetçi güncelle.

**Çalışması için 1 secret gerekli (bunu ekleyene kadar Actions deploy adımı hata verir):**
1. Cloudflare → My Profile → API Tokens → Create Token → **"Cloudflare Pages: Edit"** şablonu.
2. GitHub repo → Settings → Secrets and variables → Actions → New repository secret:
   isim `CLOUDFLARE_API_TOKEN`, değer = oluşturduğun token.
   (veya: `gh secret set CLOUDFLARE_API_TOKEN` ile.)
- Account ID workflow'da gömülü (gizli değil): `97bd8b6f36fadffcf529f0d9bf105e68`.
- Secret eklenince: her push otomatik yayınlanır; nöbetçi günde 2x tazelenir.
- Not: Otopark canlı Function'dan (`/api/otopark`) geldiği için cron gerektirmez.

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

## 6. Marka varlıkları — TAMAM ✅
Logo, favicon, PWA ikonları, OG/sosyal görseller yerleştirildi ve bağlandı:
- Favicon seti + `site.webmanifest` + `theme-color` tüm sayfaların `<head>`'inde
  (root: favicon.ico/.svg, apple-touch-icon, icon-192/512, manifest).
- OG/Twitter kartı: `https://tuzlali.net/gorseller/marka/og-1200x630.png` (her sayfada).
- Nav + footer logosu: `gorseller/marka/logo-horizontal(-white).svg`.
- Kalan sosyal görseller `gorseller/marka/` içinde hazır (fb-cover, ig-post,
  ig-story, x-cover, avatar) — sosyal hesap açınca yükle.
- PWA "ana ekrana ekle" manifest + ikonlarla hazır; HTTPS'te deploy olunca çalışır.

---
Not: Nöbetçi eczane verisi açık kaynaktan (istanbul.eczaneleri.org) derlenir;
sayfa her zaman e-Devlet resmî sorgulamaya da link verir. Kaynağın HTML yapısı
değişirse `veri/nobetci_cek.py` 0 sonuç döndürüp cron'u başarısız yapar ve eldeki
son geçerli `nobetci.json` korunur (boşla ezilmez).
