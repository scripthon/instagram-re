# instagram-re — reverse engineering instagram.com

Peta API publik Instagram yang bisa dipakai **tanpa login** (logged-out), hasil probe
14 Okt 2026. Semua endpoint diambil dari server CrawlerFox (VPS), bukan dari laptop.

> `robots.txt` Instagram menyatakan pengumpulan data otomatis butuh izin tertulis Meta.
> Semua endpoint di bawah adalah endpoint internal yang tidak dijamin stabil.

## Ringkasan

| Hal | Nilai |
|---|---|
| Endpoint hidup | `web_profile_info` (profil+12 post), GraphQL `PolarisPostRootQuery` (post), GraphQL `PolarisProfilePageContentQuery` (profil by id), oEmbed |
| Metode | HTTP (tanpa browser), **wajib HTTP/2** |
| Auth | tidak ada — logged-out guest |
| Blokir dari server | **Tidak diblokir** (profil `nasa` → 200) → manifest `proxy: optional` |
| Yang butuh login | pagination post, followers/following, hashtag, search, komentar, HTML profil |

Detail lengkap:

- [`stack.md`](stack.md) — teknologi, UA/app-id, cookie/token, perilaku gate, fragilitas.
- [`api-map.md`](api-map.md) — setiap endpoint: parameter, header, contoh `curl`, error.
- [`data-samples/`](data-samples/) — satu respons JSON asli (ter-scrub) per endpoint.
- [`tools/`](tools/) — skrip probe + inventaris `doc_id`.

## Catatan penting

- Kombinasi **mobile User-Agent + mobile X-IG-App-ID** (`124024574287414`) adalah kunci
  `web_profile_info`; UA desktop / web app-id (`936619743392459`) → `401 require_login`.
- **HTTP/2 wajib**: `curl --http2` → 200, sedangkan `curl --http1.1` / `requests` →
  429 kosong. Client memakai `httpx(http2=True)`.
- `doc_id` GraphQL berubah tiap rilis bundle JS — re-ekstrak berkala (`tools/`).
- URL media (`scontent*.cdninstagram.com`) bertanda tangan (`oh`/`oe`) yang kedaluwarsa;
  jangan disimpan mentah untuk jangka panjang.

## Tanggal capture

14 Okt 2026 (verifikasi ulang dari VPS: 15 Okt 2026).
