/* Tuzla Haritasi - TAKSONOMI: TEK KAYNAK.
 *
 * Bu liste onceden `CATS` adiyla index.html ve kesfet.html'e AYRI AYRI
 * kopyalanmisti. Iki kopya = yarisi guncellenmis taksonomi. Artik ikisi de
 * bu dosyayi okuyor.
 *
 * NEDEN "OTOMOTIV" VAR:
 *   Veride "Otomotiv" diye bir kategori yok. Oto Servis, Akaryakit, Lastikci,
 *   Egzozcu, Surucu Kursu... hepsi "Servis" kategorisinin altinda, Banka ve
 *   Noter'le ayni torbada duruyordu (165 kayit). Torba cok genisti.
 *   Otomotiv alt_kategori'ye gore cekildi (88); Servis'te kalan 77.
 *
 * NEDEN OTOMOTIV'IN RENGI SERVIS'LE AYNI:
 *   Haritada zaten 9 kategorik renk var; insan gozu ~8'den fazlasini guvenle
 *   ayirt edemiyor. 10. hue eklemek mevcut renklerden birine carpardi
 *   (mavi = aksan, petrol = marina, mor = perakende...). Otomotiv haritada
 *   Servis ailesinden -- ki oyle. Listede IKON ve BASLIK ayiriyor.
 *
 * SIRA = ekranda gorunme sirasi (kayit sayisina gore, elle).
 * Eslestirme: once alt[] (dar), sonra kat[] (genis). Bu sira sayesinde
 * Otomotiv, Servis'ten once yakalaniyor.
 */
const GRUPLAR = [
  { ad:"Sağlık",              renk:"--c-saglik",    ikon:"ph-first-aid-kit",        kat:["Sağlık"] },
  { ad:"Yeme İçme",           renk:"--c-yeme",      ikon:"ph-fork-knife",           kat:["Yeme İçme"] },
  { ad:"Market & Gıda",       renk:"--c-market",    ikon:"ph-shopping-cart-simple", kat:["Market"] },
  { ad:"Otomotiv",            renk:"--c-servis",    ikon:"ph-car",
    alt:["Oto Servis","Akaryakıt","Sürücü Kursu","Oto Yedek Parça","Oto Galeri",
         "Lastikçi","Araç Muayene","Egzozcu","Motosiklet Eğitim Alanı","Kaporta / Boya",
         "Motor Yenileme","Oto Cam","Oto Ekspertiz","Oto Kiralama","Oto Sanayi Sitesi",
         "Oto Yıkama"] },
  { ad:"Perakende",           renk:"--c-perakende", ikon:"ph-storefront",           kat:["Perakende"] },
  { ad:"Servis",              renk:"--c-servis",    ikon:"ph-wrench",               kat:["Servis"] },
  { ad:"Bakım & Güzellik",    renk:"--c-bakim",     ikon:"ph-scissors",             kat:["Bakım & Güzellik"] },
  { ad:"Marina & Denizcilik", renk:"--c-marina",    ikon:"ph-anchor",               kat:["Marina & Denizcilik"] },
  { ad:"Evcil Hayvan",        renk:"--c-evcil",     ikon:"ph-paw-print",            kat:["Evcil Hayvan"] },
  { ad:"Konaklama",           renk:"--c-konak",     ikon:"ph-bed",                  kat:["Konaklama"] },
];

/* Kaydin ust grubu. Once dar eslestirme (alt_kategori), sonra genis (kategori):
   boylece GRUPLAR dizisindeki sira degisse bile Otomotiv, Servis'e dusmez.
   Eslesmeyen kayit Servis'e dusuyor -- bugun oyle bir kayit yok (1554/1554
   eslesiyor) ama yeni bir alt_kategori girerse haritadan kaybolmasin. */
function grupBul(r){
  for(const g of GRUPLAR) if(g.alt && g.alt.includes(r.alt_kategori)) return g;
  for(const g of GRUPLAR) if(g.kat && g.kat.includes(r.kategori))     return g;
  return GRUPLAR.find(g=>g.ad==="Servis");
}

/* Her kayda _grup yaziyor. Filtre, renk, baslik hepsi bunu okuyor. */
function gruplaHepsi(DATA){ DATA.forEach(r=>{ r._grup=grupBul(r).ad; }); return DATA; }

/* MapLibre renk ifadesi: pin rengi ust gruba gore. */
function renkIfadesi(css){
  const e=["match",["get","_grup"]];
  for(const g of GRUPLAR) e.push(g.ad, css(g.renk));
  e.push(css("--c-servis"));   // varsayilan
  return e;
}
