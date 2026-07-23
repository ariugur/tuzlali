/**
 * Tuzla Haritasi - isletme ekleme formu ucu.
 *
 * TASARIM KARARI: R2 tek gercek kaynak.
 * Once basvuru R2'ye yazilir, SONRA e-posta denenir. E-posta saglayicisi
 * duserse basvuru kaybolmaz, sadece bildirim gelmez. Tersi olsaydi
 * (once mail, sonra kayit) saglayici hatasinda vergi levhasi ucardi.
 */

const IZINLI_KOKEN = [
  "https://tuzla-haritasi.pages.dev",
  "http://localhost:8777",
  // domain alininca buraya eklenecek
];

const MAX_BAYT = 8 * 1024 * 1024;          // ekle.html ile ayni: 8 MB
const SAKLAMA_MS = 24 * 60 * 60 * 1000;    // ispat belgesi en fazla 24 saat durur
const IZINLI_TIP = ["image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"];

const ZORUNLU = ["ad", "kategori", "mahalle", "adres", "telefon", "yetkili", "eposta", "gbp", "site", "ispat_tur", "kvkk"];
const ISPAT_TURLERI = ["vergi_levhasi", "ruhsat", "imza_sirkuleri", "gbp_sahipligi"];

function cors(origin) {
  const ok = IZINLI_KOKEN.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : IZINLI_KOKEN[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

const json = (obj, status, origin) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors(origin) },
  });

function slug(s) {
  const tr = { "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c", "İ": "i" };
  return String(s || "")
    .toLowerCase()
    .replace(/[ığüşöçİ]/g, (c) => tr[c] || c)
    .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")   // birlesim isaretleri
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50) || "isimsiz";
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/** Basvuruyu e-posta govdesine cevirir. GBP/site cevaplari one cikiyor:
 *  teklif verilip verilmeyecegine bakilan iki alan bunlar. */
function mailGovdesi(d, belgeBilgi, belgeYolu) {
  const satir = (k, v) => `<tr><td style="padding:5px 14px 5px 0;color:#6c6f76;white-space:nowrap">${esc(k)}</td><td style="padding:5px 0;color:#17181a">${esc(v) || "-"}</td></tr>`;
  const gbpEtiket = {
    var: "VAR, kendisi yonetiyor",
    var_yonetmiyorum: "VAR ama erisimi yok",
    yok: "YOK",
    bilmiyorum: "BILMIYOR",
  }[d.gbp] || d.gbp;
  const siteEtiket = { var: "VAR", sadece_sosyal: "Sadece sosyal medya", yok: "YOK" }[d.site] || d.site;

  return `<div style="font-family:system-ui,sans-serif;max-width:640px">
    <h2 style="margin:0 0 4px;font-size:18px;color:#17181a">${esc(d.ad)}</h2>
    <p style="margin:0 0 18px;color:#6c6f76;font-size:13px">${esc(d.kategori)} &middot; ${esc(d.mahalle)}</p>

    <div style="background:#e9f0fc;border:1px solid #bcd4f5;border-radius:10px;padding:12px 14px;margin-bottom:18px">
      <b style="color:#0a52b5;font-size:13px">Dijital durum</b>
      <table style="font-size:13px;margin-top:6px;border-collapse:collapse">
        ${satir("Google profili", gbpEtiket)}
        ${satir("Web sitesi", siteEtiket)}
        ${satir("Adres/hesap", d.web)}
      </table>
    </div>

    <table style="font-size:13px;border-collapse:collapse;width:100%">
      ${satir("Adres", d.adres)}
      ${satir("Telefon", d.telefon)}
      ${satir("Saatler", d.saat)}
      ${satir("Yetkili", d.yetkili)}
      ${satir("E-posta", d.eposta)}
      ${satir("Not", d.not)}
      ${satir("Ispat turu", d.ispat_tur)}
      ${satir("Belge", belgeBilgi)}
    </table>

    ${belgeYolu ? `<p style="margin:18px 0 0;font-size:12px;color:#8a4b08;background:#fff4e6;
       border:1px solid #ffd8a8;border-radius:8px;padding:10px 12px">
      Belge en gec 24 saat icinde otomatik silinecek. Onayladiktan sonra hemen silmek istersen:<br>
      <code style="font-size:11px">npx wrangler r2 object delete tuzla-basvuru/${esc(belgeYolu)}</code>
    </p>` : ""}
  </div>`;
}

/** Resend uzerinden bildirim. Anahtar yoksa sessizce atlanir:
 *  basvuru zaten R2'de, bildirim ikincil. */
async function bildir(env, d, belgeBilgi, belgeYolu) {
  if (!env.RESEND_API_KEY || !env.MAIL_KIME || !env.MAIL_KIMDEN) {
    return { gonderildi: false, sebep: "eposta yapilandirilmadi" };
  }
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env.MAIL_KIMDEN,
      to: [env.MAIL_KIME],
      reply_to: d.eposta,
      subject: `Tuzla Haritasi basvuru: ${d.ad}`,
      html: mailGovdesi(d, belgeBilgi, belgeYolu),
    }),
  });
  if (!r.ok) return { gonderildi: false, sebep: `resend ${r.status}: ${(await r.text()).slice(0, 200)}` };
  return { gonderildi: true };
}

/**
 * Saatlik cron: 24 saati dolmus ispat belgelerini siler.
 *
 * Neden R2 lifecycle kurali degil de cron: kural bucket geneli calisir ve
 * basvuru/ ile belge/ ayrimini gozetmesi icin dogru prefix'e baglanmasi gerekir;
 * burada silme mantigi kodda duruyor, gorulebiliyor ve test edilebiliyor.
 * Saatte bir dondugu icin gercek omur 24-25 saat arasi. "En fazla 24 saat"
 * demek istersek esigi 23 saate cekmek gerekir.
 *
 * Silinen SADECE belge. basvuru/*.json duruyor.
 */
async function belgeleriTemizle(env) {
  const simdi = Date.now();
  let cursor, silinen = 0, kalan = 0;
  do {
    const l = await env.BASVURU.list({ prefix: "belge/", cursor, limit: 1000 });
    const eskiler = l.objects.filter((o) => simdi - o.uploaded.getTime() > SAKLAMA_MS);
    kalan += l.objects.length - eskiler.length;
    // R2 delete tek cagride liste alabiliyor; 1000'lik gruplar halinde.
    if (eskiler.length) {
      await env.BASVURU.delete(eskiler.map((o) => o.key));
      silinen += eskiler.length;
    }
    cursor = l.truncated ? l.cursor : undefined;
  } while (cursor);
  console.log(`belge temizligi: ${silinen} silindi, ${kalan} duruyor`);
  return { silinen, kalan };
}

export default {
  // wrangler.toml icindeki [triggers] crons ile saatlik tetikleniyor
  async scheduled(event, env, ctx) {
    ctx.waitUntil(belgeleriTemizle(env));
  },

  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin") || "";

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
    if (request.method !== "POST") return json({ hata: "yalnizca POST" }, 405, origin);
    if (origin && !IZINLI_KOKEN.includes(origin)) return json({ hata: "koken izinli degil" }, 403, origin);

    let fd;
    try {
      fd = await request.formData();
    } catch {
      return json({ hata: "form okunamadi" }, 400, origin);
    }

    const d = {};
    for (const [k, v] of fd.entries()) if (!(v instanceof File)) d[k] = String(v).trim();

    const eksik = ZORUNLU.filter((k) => !d[k]);
    if (eksik.length) return json({ hata: "zorunlu alan eksik", alanlar: eksik }, 400, origin);
    if (!ISPAT_TURLERI.includes(d.ispat_tur)) return json({ hata: "gecersiz ispat turu" }, 400, origin);
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.eposta)) return json({ hata: "gecersiz e-posta" }, 400, origin);

    // ISPAT KURALI: GBP sahipligi disinda belge sart. Uc tarafta da dogruluyoruz,
    // cunku tarayici dogrulamasi atlanabilir.
    const belge = fd.get("belge");
    const belgeVar = belge instanceof File && belge.size > 0;
    if (d.ispat_tur !== "gbp_sahipligi" && !belgeVar) {
      return json({ hata: "bu ispat turu icin belge zorunlu" }, 400, origin);
    }
    if (belgeVar) {
      if (belge.size > MAX_BAYT) return json({ hata: `belge ${MAX_BAYT / 1048576} MB'tan buyuk` }, 413, origin);
      if (!IZINLI_TIP.includes(belge.type)) return json({ hata: "belge turu desteklenmiyor", tur: belge.type }, 415, origin);
    }

    // ANAHTAR AYRIMI (KVKK):
    //   belge/...   -> ispat belgesi. Cron 24 saatte siliyor.
    //   basvuru/... -> isletme bilgisi. Kaliyor, cunku haritaya eklemek icin lazim.
    // Ayni klasorde olsalardi belgeyi silmek basvuruyu da goturecekti.
    const damga = new Date().toISOString().replace(/[:.]/g, "-");
    const kimlik = `${damga}-${slug(d.ad)}`;
    let belgeYolu = "";
    let belgeBilgi = d.ispat_tur === "gbp_sahipligi" ? "Google profili uzerinden dogrulanacak" : "-";

    try {
      if (belgeVar) {
        const uzanti = (belge.name.split(".").pop() || "bin").toLowerCase().slice(0, 5);
        belgeYolu = `belge/${kimlik}.${uzanti}`;
        await env.BASVURU.put(belgeYolu, belge.stream(), {
          httpMetadata: { contentType: belge.type },
          customMetadata: { isletme: d.ad, eposta: d.eposta, ispat: d.ispat_tur },
        });
        belgeBilgi = `${belgeYolu} (${(belge.size / 1024).toFixed(0)} KB)`;
      }
      await env.BASVURU.put(
        `basvuru/${kimlik}.json`,
        JSON.stringify(
          {
            ...d,
            belge_yolu: belgeYolu,
            belge_silinir: belgeYolu ? new Date(Date.now() + SAKLAMA_MS).toISOString() : "",
            ip: request.headers.get("CF-Connecting-IP") || "",
            ts: damga,
          },
          null,
          1
        ),
        { httpMetadata: { contentType: "application/json" } }
      );
    } catch (e) {
      // R2 duserse basvuruyu kabul etmiyoruz: kaybolmus basvuru,
      // reddedilmis basvurudan daha kotu.
      return json({ hata: "kayit yazilamadi, lutfen tekrar dene" }, 500, origin);
    }

    // Bildirim basarisiz olsa bile basvuru kabul edildi (R2'de duruyor).
    ctx.waitUntil(bildir(env, d, belgeBilgi, belgeYolu));
    return json({ ok: true, kayit: kimlik }, 200, origin);
  },
};
