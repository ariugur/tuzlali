// Cloudflare Pages middleware: www.tuzlali.net -> tuzlali.net (301).
// Kanonik adres apex (canonical etiketleri de apex'i işaret ediyor).
// www custom domain olarak Pages'e eklenince bu otomatik devreye girer;
// diğer tüm host'lar (apex, *.pages.dev) dokunulmadan geçer.
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.hostname === "www.tuzlali.net") {
    url.hostname = "tuzlali.net";
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
