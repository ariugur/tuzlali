#!/usr/bin/env node
/* SEO STATIK SAYFA URETICI
 *
 * NEDEN: 1554 isletme JS ile JSON'dan basiliyordu; Google hicbirini
 * indeksleyemiyordu. Bu script her KATEGORI ve her MAHALLE icin taranabilir
 * statik HTML uretir: gercek isletme listesi + JSON-LD + canonical + ic link.
 *
 * TAKSONOMI TEK KAYNAK: gruplar.js Function ile yuklenir, grupBul aynen
 * kullanilir. Burada kopyalanmaz (CLAUDE.md §6).
 *
 * Kullanim: node sayfa_uret.js
 * Cikti   : kategori/<slug>.html, mahalle/<slug>.html, sitemap.xml
 *
 * ALAN ADI: SITE_KOK sabiti. Alan adi belli olunca burayi degistir, yeniden
 * calistir. canonical ve sitemap mutlak URL ister.
 */
"use strict";
const fs = require("fs");
const path = require("path");

const SITE_KOK = "https://ORNEK-ALAN-ADI"; // TODO: gercek alan adi
const KOK = __dirname;

// --- taksonomi: gruplar.js'ten, kopyasiz ---
const src = fs.readFileSync(path.join(KOK, "gruplar.js"), "utf8");
const { GRUPLAR, grupBul } = new Function(src + "; return {GRUPLAR, grupBul};")();

const DATA = JSON.parse(fs.readFileSync(path.join(KOK, "veri/tuzla_data.json"), "utf8"));
const SEKIL = JSON.parse(fs.readFileSync(path.join(KOK, "veri/mahalle_sekil.json"), "utf8"));

// --- yardimcilar ---
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
// "<Null>", "null" gibi placeholder cop degerleri bos say (veri katmani
// temizliyor ama kaynak yine bozuk gelirse kartta gorunmesin)
const COP = new Set(["<null>", "null", "none", "nan", "n/a"]);
function temiz(v) {
  return typeof v === "string" && COP.has(v.trim().toLowerCase()) ? "" : v;
}
function slug(s) {
  const tr = { ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u", İ: "i" };
  return String(s).replace(/[çğıöşüİ]/g, (c) => tr[c] || c)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}
function css(v) {
  // gruplar.js renkleri --c-* degiskeni; JSON-LD/harici renk gerekmiyor,
  // sadece sinif adi olarak kullanacagiz, gercek renk ortak.css'te.
  return v;
}

// --- her kayda grup ata ---
DATA.forEach((r) => { r._grup = grupBul(r).ad; });

// grup sayilari (ic link cipleri icin)
const grupSay = {};
GRUPLAR.forEach((g) => { grupSay[g.ad] = DATA.filter((r) => r._grup === g.ad).length; });

// mahalle sayilari
const mahSay = {};
DATA.forEach((r) => { const m = (r.mahalle || "").trim(); if (m) mahSay[m] = (mahSay[m] || 0) + 1; });
const mahListe = Object.keys(mahSay).sort((a, b) => mahSay[b] - mahSay[a]);

// --- ortak sayfa iskeleti ---
function nav() {
  return `<nav class="nav">
  <div class="wrap">
    <a href="../index.html" class="logo"><i class="ph-fill ph-map-pin-area"></i> Tuzla Haritası</a>
    <div class="nav-links">
      <a href="../kesfet.html">İşletmeler</a>
      <a href="../nobetci.html">Nöbetçi eczane</a>
      <a href="../index.html#mahalleler">Mahalleler</a>
      <a href="../index.html#veri">Veri kaynağı</a>
    </div>
    <div class="nav-sag">
      <a href="../kesfet.html" class="btn btn-primary"><i class="ph ph-map-trifold"></i> <span class="nav-cta-yazi">Haritayı aç</span></a>
      <button class="nav-burger" type="button" aria-label="Menüyü aç" aria-expanded="false" aria-controls="navPanel">
        <i class="ph ph-list" aria-hidden="true"></i>
      </button>
    </div>
  </div>
  <div class="nav-panel" id="navPanel">
    <a href="../index.html"><i class="ph ph-house" aria-hidden="true"></i> Ana sayfa</a>
    <a href="../kesfet.html"><i class="ph ph-storefront" aria-hidden="true"></i> İşletmeler</a>
    <a href="../nobetci.html"><i class="ph ph-first-aid-kit" aria-hidden="true"></i> Nöbetçi eczane</a>
    <a href="../index.html#mahalleler"><i class="ph ph-map-pin-area" aria-hidden="true"></i> Mahalleler</a>
    <a href="../index.html#veri"><i class="ph ph-info" aria-hidden="true"></i> Veri kaynağı</a>
  </div>
</nav>`;
}
function foot() {
  return `<footer class="foot">
  <div class="wrap">
    <span>Tuzla İşletme Haritası</span>
    <span>Harita verisi © OpenStreetMap katkıcıları (ODbL) · Sağlık verisi: İBB Açık Veri · Firma verisi: GİSBİR</span>
  </div>
</footer>`;
}

// tek isletme karti
function kart(r) {
  const rows = [];
  const adres = temiz(r.adres), tel = temiz(r.telefon), saat = temiz(r.calisma_saatleri);
  if (adres) rows.push(`<div class="r"><i class="ph ph-map-pin" aria-hidden="true"></i><span>${esc(adres)}</span></div>`);
  if (tel) rows.push(`<div class="r"><i class="ph ph-phone" aria-hidden="true"></i><a href="tel:${esc(String(tel).replace(/\s/g, ""))}">${esc(tel)}</a></div>`);
  if (saat) rows.push(`<div class="r"><i class="ph ph-clock" aria-hidden="true"></i><span>${esc(saat)}</span></div>`);
  const badge = !r.dogrulandi ? ` <span class="seo-badge">doğrulanmadı</span>` : "";
  const grup = GRUPLAR.find((g) => g.ad === r._grup) || GRUPLAR[5];
  // baslik h3: sayfa h1 > bolum h2 (mahalle) veya sr-only h2 (kategori) > h3
  return `<li class="seo-card">
    <h3>${esc(r.ad)}${badge}</h3>
    <div class="sub"><span class="cdot" style="background:var(${esc(grup.renk)})"></span>${esc(r.alt_kategori || r.kategori || "")}${r.mahalle ? ` · ${esc(r.mahalle)}` : ""}</div>
    ${rows.length ? `<div class="seo-rows">${rows.join("")}</div>` : ""}
  </li>`;
}

// Liste govdesi. bolumlu=true (mahalle): kategoriye gore boler, her genel
// kategori bir h2 bolum. bolumlu=false (kategori): tek duz liste + sr-only h2.
function listeGovde(kayitlar, bolumlu, aktifAd) {
  const sirali = kayitlar.slice().sort((a, b) => (a.ad || "").localeCompare(b.ad || "", "tr"));
  if (!bolumlu) {
    return `<h2 class="sr-only">${esc(aktifAd)} işletmeleri</h2>
    <ol class="seo-list">
      ${sirali.map(kart).join("\n      ")}
    </ol>`;
  }
  // GRUPLAR sirasinda kategori bolumleri; bos grup atlanir
  let html = "";
  GRUPLAR.forEach((g) => {
    const grubun = sirali.filter((r) => r._grup === g.ad);
    if (!grubun.length) return;
    html += `<section class="seo-bolum">
      <h2 class="seo-bolum-bas"><span class="cdot" style="background:var(${g.renk})"></span>${esc(g.ad)} <span class="say">${grubun.length}</span></h2>
      <ol class="seo-list">
        ${grubun.map(kart).join("\n        ")}
      </ol>
    </section>`;
  });
  return html;
}

// FAQ uretimi: VERIDEN, spesifik sayilarla. Jenerik degil -> alintilanabilir.
// Kaynak cumlesi ortak. Her sayfaya 3 soru: boguculuk yapmaz.
const KAYNAK_CEVAP =
  "Kayıtlar OpenStreetMap (ODbL), İBB Açık Veri ve GİSBİR üye dizininden derlendi; " +
  "her işletme kaynağıyla listeli. Telefon ve çalışma saati bazı kayıtlarda eksik olabilir, " +
  "işletmelere sorularak tamamlanıyor.";

function dokum(kayitlar, anahtar, kac) {
  const c = {};
  kayitlar.forEach((r) => { const v = (r[anahtar] || "").trim(); if (v) c[v] = (c[v] || 0) + 1; });
  return Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, kac);
}

function sssKategori(ad, kayitlar) {
  const alt = dokum(kayitlar, "alt_kategori", 3).map(([a, n]) => `${a} (${n})`).join(", ");
  const mah = dokum(kayitlar, "mahalle", 3).map(([a, n]) => `${a} (${n})`).join(", ");
  return [
    [`Tuzla'da kaç ${ad.toLowerCase()} işletmesi var?`,
     `Bu rehberde ${kayitlar.length} ${ad.toLowerCase()} işletmesi listeli. En yaygın türler: ${alt}.`],
    [`Tuzla'da ${ad.toLowerCase()} en çok hangi mahallede?`,
     `En yoğun mahalleler: ${mah}. Her mahallenin kendi sayfasından tam listeye ulaşabilirsiniz.`],
    ["Bu bilgiler nereden geliyor?", KAYNAK_CEVAP],
  ];
}

function sssMahalle(ad, kayitlar) {
  const kat = GRUPLAR.map((g) => [g.ad, kayitlar.filter((r) => r._grup === g.ad).length])
    .filter(([, n]) => n).sort((a, b) => b[1] - a[1]);
  const ilk3 = kat.slice(0, 3).map(([a, n]) => `${a} (${n})`).join(", ");
  const hepsi = kat.map(([a, n]) => `${a} (${n})`).join(", ");
  return [
    [`${ad} Mahallesi'nde kaç işletme var?`,
     `Tuzla ${ad} Mahallesi'nde ${kayitlar.length} işletme listeli. En çok: ${ilk3}.`],
    [`${ad} Mahallesi'nde hangi kategoriler var?`,
     `${ad} Mahallesi'ndeki işletmeler şu kategorilerde: ${hepsi}.`],
    ["Bu bilgiler nereden geliyor?", KAYNAK_CEVAP],
  ];
}

// Gorunur FAQ: <details> ile KATLANABILIR, varsayilan kapali. Insan icin 3
// kapali satir (bogmaz), acan okur; LLM/Google DOM'dan okur.
function sssHtml(sss) {
  return `<section class="seo-sss" aria-label="Sık sorulanlar">
    <h2 class="seo-sss-bas">Sık sorulanlar</h2>
    ${sss.map(([s, c]) => `<details class="sss-q">
      <summary>${esc(s)}</summary>
      <p>${esc(c)}</p>
    </details>`).join("\n    ")}
  </section>`;
}

// Gorunmez FAQPage schema (ayni sorular): insan yuku sifir, LLM tam fayda.
function sssSchema(sss) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: sss.map(([s, c]) => ({
      "@type": "Question", name: s,
      acceptedAnswer: { "@type": "Answer", text: c },
    })),
  };
}

// Site kimligi: her sayfada publisher. Insan gormez.
function orgSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Tuzla İşletme Haritası",
    url: SITE_KOK + "/",
    description: "Tuzla'daki yerel işletmelerin adres, telefon ve harita rehberi. " +
      "Açık kaynaklı verilerden derlendi.",
    publisher: {
      "@type": "Organization",
      name: "Tuzla İşletme Haritası",
      url: SITE_KOK + "/",
    },
  };
}

// JSON-LD: BreadcrumbList + ItemList + FAQPage + WebSite
function jsonLd(baslik, url, kayitlar, sss) {
  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Tuzla İşletme Haritası", item: SITE_KOK + "/" },
      { "@type": "ListItem", position: 2, name: baslik, item: url },
    ],
  };
  const itemList = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: baslik,
    numberOfItems: kayitlar.length,
    itemListElement: kayitlar.slice(0, 100).map((r, i) => {
      const biz = {
        "@type": "LocalBusiness",
        name: r.ad,
        address: { "@type": "PostalAddress", streetAddress: r.adres || "", addressLocality: "Tuzla", addressRegion: "İstanbul", addressCountry: "TR" },
        geo: { "@type": "GeoCoordinates", latitude: r.lat, longitude: r.lon },
      };
      if (r.telefon) biz.telephone = r.telefon;
      return { "@type": "ListItem", position: i + 1, item: biz };
    }),
  };
  const bloklar = [breadcrumb, itemList, orgSchema()];
  if (sss) bloklar.push(sssSchema(sss));
  return bloklar
    .map((b) => `<script type="application/ld+json">${JSON.stringify(b)}</script>`)
    .join("\n");
}

function sayfa({ baslik, aciklama, url, aktifTip, aktifAd, kayitlar, canliLink, lede, bolumlu, sss }) {
  const sirali = kayitlar.slice().sort((a, b) => (a.ad || "").localeCompare(b.ad || "", "tr"));
  // ic link cipleri: kategoriler (bu sayfa mahalle ise) + mahalleler (bu sayfa kategori ise)
  let kategoriChips = GRUPLAR.filter((g) => grupSay[g.ad] > 0).map((g) =>
    `<a class="seo-chip${aktifTip === "kategori" && aktifAd === g.ad ? " aktif" : ""}" href="../kategori/${slug(g.ad)}.html">
      <span class="cdot" style="background:var(${g.renk})"></span>${esc(g.ad)}<span class="n">${grupSay[g.ad]}</span></a>`).join("");
  let mahalleChips = mahListe.map((m) =>
    `<a class="seo-chip${aktifTip === "mahalle" && aktifAd === m ? " aktif" : ""}" href="../mahalle/${slug(m)}.html">${esc(m)}<span class="n">${mahSay[m]}</span></a>`).join("");

  return `<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(baslik)}</title>
<meta name="description" content="${esc(aciklama)}">
<link rel="canonical" href="${esc(url)}">
<meta property="og:title" content="${esc(baslik)}">
<meta property="og:description" content="${esc(aciklama)}">
<meta property="og:type" content="website">
<meta property="og:url" content="${esc(url)}">
<link rel="stylesheet" href="../ortak.css">
<link rel="stylesheet" href="../ikonlar/regular.css">
<link rel="stylesheet" href="../ikonlar/fill.css">
<link rel="stylesheet" href="../seo.css">
<script src="../ortak.js"></script>
${jsonLd(baslik, url, sirali, sss)}
</head>
<body>
${nav()}
<main>
  <div class="wrap seo-head">
    <nav class="seo-crumb" aria-label="Konum">
      <a href="../index.html" class="crumb-home"><i class="ph ph-house" aria-hidden="true"></i> Ana sayfa</a><i class="ph ph-caret-right" aria-hidden="true"></i>
      <span>${esc(aktifAd)}</span>
    </nav>
    <h1>${esc(lede.h1)}</h1>
    <p class="lede">${esc(lede.p)}</p>
    <div class="seo-actions">
      <a href="${canliLink}" class="btn btn-primary"><i class="ph ph-map-trifold"></i> Haritada gör</a>
    </div>
  </div>

  <div class="wrap">
    ${listeGovde(kayitlar, bolumlu, aktifAd)}
  </div>

  <div class="wrap">
    ${sss ? sssHtml(sss) : ""}
  </div>

  <div class="wrap seo-links">
    <h2>Kategoriler</h2>
    <div class="seo-chips">${kategoriChips}</div>
  </div>
  <div class="wrap seo-links" style="border-top:none;padding-top:8px">
    <h2>Mahalleler</h2>
    <div class="seo-chips">${mahalleChips}</div>
  </div>
</main>
${foot()}
</body>
</html>`;
}

// --- uret ---
let uretilen = 0;
const sitemapUrls = [`${SITE_KOK}/`, `${SITE_KOK}/kesfet.html`, `${SITE_KOK}/nobetci.html`];

fs.mkdirSync(path.join(KOK, "kategori"), { recursive: true });
fs.mkdirSync(path.join(KOK, "mahalle"), { recursive: true });

// kategori sayfalari
GRUPLAR.forEach((g) => {
  const kayitlar = DATA.filter((r) => r._grup === g.ad);
  if (!kayitlar.length) return;
  const s = slug(g.ad);
  const url = `${SITE_KOK}/kategori/${s}.html`;
  const html = sayfa({
    baslik: `Tuzla ${g.ad} | ${kayitlar.length} İşletme`,
    aciklama: `Tuzla'daki ${kayitlar.length} ${g.ad.toLowerCase()} işletmesi. Adres, telefon, çalışma saati ve haritada konum.`,
    url,
    aktifTip: "kategori", aktifAd: g.ad, kayitlar,
    canliLink: `../kesfet.html?k=${encodeURIComponent(g.ad)}`,
    lede: { h1: `Tuzla ${g.ad}`, p: `Tuzla genelinde ${kayitlar.length} ${g.ad.toLowerCase()} kaydı. Aşağıdan listeleyin, haritada konumunu görün, yol tarifi alın.` },
    sss: sssKategori(g.ad, kayitlar),
  });
  fs.writeFileSync(path.join(KOK, "kategori", `${s}.html`), html);
  sitemapUrls.push(url); uretilen++;
});

// mahalle sayfalari
mahListe.forEach((m) => {
  const kayitlar = DATA.filter((r) => (r.mahalle || "").trim() === m);
  if (!kayitlar.length) return;
  const s = (SEKIL[m] && SEKIL[m].slug) || slug(m);
  const url = `${SITE_KOK}/mahalle/${s}.html`;
  const html = sayfa({
    baslik: `${m} Mahallesi İşletmeleri, Tuzla | ${kayitlar.length} Yer`,
    aciklama: `Tuzla ${m} Mahallesi'ndeki ${kayitlar.length} işletme: eczane, market, kafe, sağlık ve daha fazlası. Adres, telefon, harita.`,
    url,
    aktifTip: "mahalle", aktifAd: m, kayitlar, bolumlu: true,
    canliLink: `../kesfet.html?mahalle=${encodeURIComponent(m)}`,
    lede: { h1: `${m} Mahallesi, Tuzla`, p: `${m} Mahallesi'nde ${kayitlar.length} işletme. Kategorilere göz atın, haritada konumu görün.` },
    sss: sssMahalle(m, kayitlar),
  });
  fs.writeFileSync(path.join(KOK, "mahalle", `${s}.html`), html);
  sitemapUrls.push(url); uretilen++;
});

// sitemap
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<!-- sayfa_uret.js ile uretildi. Alan adi ${SITE_KOK} (sabitten). -->
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapUrls.map((u) => `  <url><loc>${u}</loc></url>`).join("\n")}
</urlset>
`;
fs.writeFileSync(path.join(KOK, "sitemap.xml"), sitemap);

// llms.txt: AI crawler'lari icin site ozeti. Insan gormez, LLM'e yol haritasi.
const katSat = GRUPLAR.filter((g) => grupSay[g.ad] > 0)
  .map((g) => `- [Tuzla ${g.ad}](${SITE_KOK}/kategori/${slug(g.ad)}.html): ${grupSay[g.ad]} işletme`);
const mahSat = mahListe
  .map((m) => `- [${m} Mahallesi](${SITE_KOK}/mahalle/${(SEKIL[m] && SEKIL[m].slug) || slug(m)}.html): ${mahSay[m]} işletme`);
const llms = `# Tuzla İşletme Haritası

> Tuzla'daki ${DATA.length} yerel işletmenin adres, telefon, çalışma saati ve harita rehberi. Sağlık, yeme-içme, market, otomotiv, tersane ve daha fazlası kategori ve mahalleye göre listeli.

Veri kaynağı: OpenStreetMap (ODbL), İBB Açık Veri, GİSBİR üye dizini. Kayıtların bir kısmında telefon/çalışma saati eksik olabilir.

## Kategoriler
${katSat.join("\n")}

## Mahalleler
${mahSat.join("\n")}

## Araçlar
- [Canlı harita ve arama](${SITE_KOK}/kesfet.html): tüm işletmeler haritada, kategori ve mahalleye göre filtrelenir.
- [Tuzla nöbetçi eczaneleri](${SITE_KOK}/nobetci.html): bugün Tuzla'da nöbette olan eczaneler, adres ve yol tarifiyle, her gün güncellenir.
`;
fs.writeFileSync(path.join(KOK, "llms.txt"), llms);

console.log(`${uretilen} sayfa uretildi (${GRUPLAR.filter((g) => grupSay[g.ad] > 0).length} kategori + ${mahListe.length} mahalle).`);
console.log(`sitemap.xml: ${sitemapUrls.length} URL | llms.txt: ${katSat.length + mahSat.length} link | her sayfada FAQ + WebSite schema.`);
if (SITE_KOK.includes("ORNEK")) console.log("UYARI: SITE_KOK hala ornek. Alan adi belli olunca sabiti degistir, yeniden calistir.");
