// Cloudflare Pages Function: /api/otopark
// İSPARK canlı doluluk verisini SUNUCU TARAFINDA çeker (CORS derdi yok),
// yalnız Tuzla otoparklarını döner. İSPARK'ı korumak için 60 sn cache'lenir.
// Kaynak: İBB İSPARK açık API (api.ibb.gov.tr/ispark/Park).

const ISPARK = "https://api.ibb.gov.tr/ispark/Park";

export async function onRequest() {
  try {
    const res = await fetch(ISPARK, {
      headers: { "User-Agent": "tuzlali.net otopark" },
      cf: { cacheTtl: 60, cacheEverything: true },
    });
    if (!res.ok) throw new Error("ispark " + res.status);
    const all = await res.json();

    const otoparklar = (Array.isArray(all) ? all : [])
      .filter((p) => String(p.district || "").toUpperCase() === "TUZLA")
      .map((p) => ({
        id: p.parkID,
        ad: p.parkName,
        lat: parseFloat(p.lat),
        lon: parseFloat(p.lng),
        kapasite: Number(p.capacity) || 0,
        bos: Number(p.emptyCapacity) || 0,
        tur: p.parkType || "",
        saat: p.workHours || "",
        acik: Number(p.isOpen) === 1,
        ucretsizDk: Number(p.freeTime) || 0,
      }))
      .sort((a, b) => b.kapasite - a.kapasite);

    return new Response(
      JSON.stringify({ guncelleme: new Date().toISOString(), otoparklar }),
      {
        headers: {
          "content-type": "application/json; charset=utf-8",
          "access-control-allow-origin": "*",
          "cache-control": "public, max-age=60",
        },
      }
    );
  } catch (e) {
    return new Response(JSON.stringify({ hata: true, mesaj: String(e) }), {
      status: 502,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "access-control-allow-origin": "*",
        "cache-control": "no-store",
      },
    });
  }
}
