# Başvuru ucu (Cloudflare Worker)

`ekle.html` formunu alır, ispat belgesini R2'ye yazar, sana e-posta atar.

## Neden bu sıra

Worker önce R2'ye yazıyor, sonra e-posta deniyor. E-posta sağlayıcısı düşerse
başvuru kaybolmaz, sadece bildirim gelmez. Tersi olsaydı sağlayıcı hatasında
vergi levhası uçardı. R2 tek gerçek kaynak; e-posta sadece haber.

## Kurulum

```bash
cd worker
npm i -D wrangler

# 1) R2 kovasi
npx wrangler r2 bucket create tuzla-basvuru

# 2) deploy
npx wrangler deploy
# ciktidaki https://tuzla-basvuru.<hesap>.workers.dev adresini not al
```

Sonra iki dosyayı elle güncelle:

1. **`ekle.html`** içindeki `GONDER_UCU = null` → Worker adresini yaz.
2. **`worker/src/index.js`** içindeki `IZINLI_KOKEN` → Pages adresini ve domaini ekle.

`npx wrangler deploy` tekrar çalıştır.

## E-posta (henüz çalışmıyor)

`RESEND_API_KEY` tanımlı değilken Worker e-posta atmaz, **ama başvuruyu yine de
kabul eder ve R2'ye yazar**. Yani form bugün çalışır, sen kayıtları R2'den okursun:

```bash
npx wrangler r2 object get tuzla-basvuru --prefix basvuru/
```

E-postayı açmak için:

```bash
npx wrangler secret put RESEND_API_KEY
```

Ve `wrangler.toml` içindeki `MAIL_KIMDEN` alanını doğrulanmış bir gönderen
adresiyle değiştir.

> **Doğrulanmadı:** Resend'in güncel ücretsiz kotası ve domain doğrulama
> zorunluluğu bu oturumda kontrol edilmedi. Gönderen domaini doğrulanmadan
> mail gitmeyebilir; domain zaten sona bırakılmıştı. Sağlayıcıyı değiştirmek
> istersen sadece `bildir()` fonksiyonu değişir, gerisi aynı kalır.

## Doğrulama tarafında ne yapıyor

- Zorunlu alanlar, e-posta biçimi, ispat türü sunucuda tekrar kontrol ediliyor
  (tarayıcı doğrulaması atlanabilir).
- `gbp_sahipligi` dışındaki her ispat türünde belge **zorunlu**.
- Belge: 8 MB üst sınır, sadece jpeg/png/webp/heic/pdf.
- CORS yalnızca `IZINLI_KOKEN` listesindeki adreslere açık.

## Belge saklama: 24 saat

İki ayrı yer var, bilerek:

| Prefix | İçerik | Ömür |
|---|---|---|
| `belge/` | Vergi levhası, ruhsat | **24 saat**, cron siliyor |
| `basvuru/` | İşletme bilgisi, iletişim | Kalıyor (haritaya eklemek için lazım) |

Aynı klasörde olsalardı belgeyi silmek başvuruyu da götürürdü.

Cron saatte bir dönüyor (`17 * * * *`), 24 saati dolmuş belgeleri siliyor.
Saatlik döndüğü için **gerçek ömür 24-25 saat arası**. Kesin "24 saatten az"
istiyorsan `SAKLAMA_MS` değerini 23 saate çek.

### Onayladıktan sonra hemen silmek

Bildirim e-postasının altında o başvuruya ait silme komutu hazır geliyor:

```bash
npx wrangler r2 object delete tuzla-basvuru/belge/<kayit>.jpg
```

Ya da Cloudflare panelinden: **R2 > tuzla-basvuru > belge/** klasöründen elle sil.
Silmesen de cron 24 saat dolunca alıyor.

> **Doğrulanmadı:** `wrangler r2 object delete` söz dizimini bu oturumda
> çalıştırmadım. Panel yolu her hâlükârda çalışır.

## Eksikler

- **KVKK:** Form kişisel veri ve vergi levhası topluyor. Aydınlatma metni ve
  açık rıza yazılmadan canlıya alınmamalı. Saklama/imha tarafı artık kurulu
  (24 saat), ama metne dökülmedi. `basvuru/*.json` içinde IP ve e-posta
  süresiz duruyor; onun için de bir süre belirlemek gerekebilir.
- **Spam:** Turnstile eklenmedi. Belge zorunluluğu botların çoğunu eler ama
  hız sınırı yok.
- **Test edilmedi:** Worker deploy edilmedi, tek bir gerçek başvuru akmadı.
