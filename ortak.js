/* Tuzla Haritası - ortak davranış
   TEK KAYNAK: mobil menü ve esc() burada. Sayfalarda kopyası olmayacak.
   <head>'de defer OLMADAN yüklenir: sayfa sonundaki satır içi script'ler
   esc()'i çağırıyor, defer olsaydı onlardan sonra çalışırdı. */

/* Google Analytics (GA4: G-7KENG4PVTE).
   TEK KAYNAK: ortak.js her sayfada (27 SEO sayfası dahil) yüklenir, o yüzden
   snippet'i her <head>'e ayrı koymak yerine buradan enjekte ediyoruz.
   Not (KVKK): GA çerez kullanır; ileride çerez onayı / aydınlatma metni gerekebilir. */
(function(){
  var s=document.createElement("script");
  s.async=true;
  s.src="https://www.googletagmanager.com/gtag/js?id=G-7KENG4PVTE";
  document.head.appendChild(s);
  window.dataLayer=window.dataLayer||[];
  window.gtag=function(){dataLayer.push(arguments);};
  gtag("js", new Date());
  gtag("config", "G-7KENG4PVTE");
})();

/* HTML kaçışı. İşletme adları Google Places'ten geliyor, yani işletme
   sahibinin yazdığı metin. innerHTML'e kaçışsız girerse depolanmış XSS
   olur. Metin ve öznitelik bağlamlarının ikisinde de güvenli. */
function esc(s){
  return String(s == null ? "" : s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

/* URL slug. sayfa_uret.js'teki slug() ile BİREBİR aynı algoritma olmalı;
   index.html kartları statik SEO sayfalarına bu fonksiyonla link veriyor,
   ayrışırsa link kırılır. Değiştirirsen iki yeri birlikte değiştir. */
function slug(s){
  var tr={"ç":"c","ğ":"g","ı":"i","ö":"o","ş":"s","ü":"u","İ":"i"};
  return String(s).replace(/[çğıöşüİ]/g,function(c){return tr[c]||c;})
    .toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"");
}

/* ---- ÇALIŞMA SAATİ: "şu an açık mı?" ----
   Veri OSM opening_hours biçiminde: "Mo-Fr 09:00-23:00; Sa 10:00-20:00".
   Bu teknik metni kullanıcıya ham göstermek yerine canlı duruma çeviriyoruz.
   TEK KAYNAK: kesfet kartı + harita balonu ikisi de bunu çağırır.
   Kasıtlı olarak muhafazakâr: çözemezse {durum:"bilinmiyor"} döner, sayfa
   ham metne düşer -- yanlış "açık" demektense hiç dememek yeğ. */
function istanbulNow(){
  // Ziyaretçinin saat dilimi ne olursa olsun ölçüt Tuzla (İstanbul) saati.
  try{
    var f=new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Istanbul",
      hour12:false,weekday:"short",hour:"2-digit",minute:"2-digit"});
    var p={}; f.formatToParts(new Date()).forEach(function(x){p[x.type]=x.value;});
    var wd={Sun:0,Mon:1,Tue:2,Wed:3,Thu:4,Fri:5,Sat:6}[p.weekday];
    return {day:wd, min:(parseInt(p.hour,10)%24)*60+parseInt(p.minute,10)};
  }catch(e){ var d=new Date(); return {day:d.getDay(), min:d.getHours()*60+d.getMinutes()}; }
}
function saatDurum(str, ref){
  if(!str) return {durum:"bilinmiyor"};
  str=String(str).trim();
  var low=str.toLowerCase();
  if(low==="closed"||low==="off") return {durum:"bilinmiyor"};
  var now=ref||istanbulNow();
  if(low==="24/7") return {durum:"acik", hep:true};

  str=str.replace(/her gün/ig,"Mo-Su");
  var DG={mo:1,tu:2,we:3,th:4,fr:5,sa:6,su:0};
  var gunler={0:[],1:[],2:[],3:[],4:[],5:[],6:[]};   // gun -> [ [bas,bit], ... ]  bit>1440 = gece aşımı

  str.split(";").forEach(function(kural){
    kural=kural.trim();
    if(!kural || /ph/i.test(kural)) return;          // bos / resmi tatil kuralini atla
    var m=kural.match(/^([a-z,\s\-]*?)\s*(\d.*|off|closed)$/i);
    if(!m) return;
    var gunStr=m[1].trim(), zamanStr=m[2].trim(), gs=[];
    if(!gunStr){ gs=[0,1,2,3,4,5,6]; }               // gun belirtilmemis -> her gun
    else gunStr.split(",").forEach(function(tok){
      tok=tok.trim().toLowerCase();
      var r=tok.match(/^([a-z]{2})\s*-\s*([a-z]{2})$/);
      if(r){
        var a=DG[r[1]], b=DG[r[2]];
        if(a==null||b==null) return;
        var ai=a===0?7:a, bi=b===0?7:b;              // Su(0)'yu 7 say ki Mo-Su ve Sa-Su sarmasin
        for(var i=ai;i<=bi;i++) gs.push(i%7);
      } else if(DG[tok]!=null) gs.push(DG[tok]);
    });
    if(/^(off|closed)$/i.test(zamanStr)){ gs.forEach(function(d){gunler[d]=[];}); return; }
    zamanStr.split(",").forEach(function(sp){
      var t=sp.match(/(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})/);
      if(!t) return;
      var bas=(+t[1])*60+(+t[2]), bit=(+t[3])*60+(+t[4]);
      if(bit<=bas) bit+=1440;                        // gece aşımı: 11:30-01:00
      gs.forEach(function(d){ gunler[d].push([bas,bit]); });
    });
  });

  function hhmm(x){ if(x===1440) return "24:00"; x=((x%1440)+1440)%1440;
    var h=Math.floor(x/60), mm=x%60; return (h<10?"0":"")+h+":"+(mm<10?"0":"")+mm; }

  var bugun=gunler[now.day], dun=gunler[(now.day+6)%7], acik=null;
  for(var i=0;i<bugun.length;i++)
    if(now.min>=bugun[i][0] && now.min<bugun[i][1]){ acik=bugun[i]; break; }
  if(!acik) for(var j=0;j<dun.length;j++)           // dünden sarkan gece aşımı bugüne taşıyor mu?
    if(dun[j][1]>1440 && now.min<dun[j][1]-1440){ acik=[dun[j][0]-1440,dun[j][1]-1440]; break; }
  if(acik) return {durum:"acik", kapanis:hhmm(acik[1])};

  var sonraki=null;                                  // bugün ilerde açılış var mı?
  bugun.forEach(function(a){ if(a[0]>now.min && (sonraki==null||a[0]<sonraki)) sonraki=a[0]; });
  return sonraki!=null ? {durum:"kapali", acilis:hhmm(sonraki)} : {durum:"kapali"};
}

/* ---- WhatsApp linki ----
   Türkiye'de yerel ticaret WhatsApp'tan döner. Ama WhatsApp yalnız CEP
   numaralarında (05xx) çalışır; sabit hat (0216/0212) için wa.me linki
   kırık sohbet açar -> o yüzden sadece cep numarasi icin link döneriz,
   degilse null (sabit hatta yalniz tel: kalir). TEK KAYNAK. */
function waLink(tel){
  if(!tel) return null;
  var n=String(tel).replace(/[^0-9+]/g,"").replace(/^\+?90/,"0");
  if(!/^0/.test(n) && n.length===10) n="0"+n;
  return /^05\d{9}$/.test(n) ? "https://wa.me/9"+n : null;   // 0532... -> 90532...
}

(function(){
  "use strict";

  function mobilMenu(){
    var btn   = document.querySelector(".nav-burger");
    var panel = document.getElementById("navPanel");
    if(!btn || !panel) return;

    function kapat(){
      panel.classList.remove("acik");
      btn.setAttribute("aria-expanded","false");
      btn.innerHTML = '<i class="ph ph-list" aria-hidden="true"></i>';
    }
    function ac(){
      panel.classList.add("acik");
      btn.setAttribute("aria-expanded","true");
      btn.innerHTML = '<i class="ph ph-x" aria-hidden="true"></i>';
    }

    btn.addEventListener("click", function(e){
      e.stopPropagation();
      panel.classList.contains("acik") ? kapat() : ac();
    });

    // panel disina tiklayinca kapansin
    document.addEventListener("click", function(e){
      if(panel.classList.contains("acik") && !panel.contains(e.target)) kapat();
    });

    // Esc ile kapat, odagi butona geri ver
    document.addEventListener("keydown", function(e){
      if(e.key === "Escape" && panel.classList.contains("acik")){ kapat(); btn.focus(); }
    });

    // masaustune buyurken acik kalmasin
    var mq = window.matchMedia("(min-width:981px)");
    (mq.addEventListener ? mq.addEventListener.bind(mq,"change") : mq.addListener.bind(mq))(function(){
      if(mq.matches) kapat();
    });
  }

  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", mobilMenu);
  } else {
    mobilMenu();
  }
})();
