# stack.md — teknologi & perilaku instagram.com (logged-out)

Capture: 14 Okt 2026 · verifikasi ulang dari VPS: 15 Okt 2026.

## Frontend / backend

- Frontend web: React + Relay Modern, HTML era "xdt" (legacy GraphQL shape).
- Persisted queries (Relay): klien hanya mengirim `doc_id` + `variables`; teks query
  hanya ada di server.
- Dua host API:
  - `https://www.instagram.com` — GraphQL web (`/graphql/query` distillery,
    `/api/graphql` www) + oEmbed.
  - `https://i.instagram.com` — surface mobile (`/api/v1/users/web_profile_info/`).
- Media di `scontent*.cdninstagram.com` (signed URL).

## Protokol

- **HTTP/2 wajib** untuk `web_profile_info`. Bukti probe:
  - `curl --http2` → `200`
  - `curl --http1.1`, `python requests`, `http.client` → `429` body kosong.
- Client memakai `httpx[http2]`. GraphQL POST juga lewat HTTP/2.

## Header wajib

`web_profile_info` (mobile):

```
User-Agent: Instagram 101.0.0.15.120 Android
X-IG-App-ID: 124024574287414          # mobile app id (BUKAN web id)
```

GraphQL (web):

```
X-IG-App-ID: 936619743392459          # web app id
X-CSRFToken: <csrftoken cookie>
X-FB-Friendly-Name: <nama query>      # = fb_api_req_friendly_name
X-Root-Field-Name: <root field>       # dari metadata query (mis. xdt_api__v1__media__shortcode__web_info)
X-ASBD-ID: 129477
X-IG-WWW-Claim: 0
Content-Type: application/x-www-form-urlencoded
```

Body POST GraphQL = `getAsyncParams("POST")` + persisted query:

```
doc_id=<id>
variables=<json>
fb_api_req_friendly_name=<nama query>
fb_api_caller_class=RelayModern
server_timestamps=true
__a=1&__user=0&__req=q&__rev=<client_revision>&hsi=<hsi>&lsd=<lsd>
```

`lsd`, `hsi`, `client_revision (__rev)` dan `csrftoken` diekstrak dari landing page
`https://www.instagram.com/` (lihat `Transport._bootstrap` di client).

## Sesi / cookie

- Landing page men-set cookie `csrftoken` + `mid`; nilai `csrftoken` juga dikirim
  sebagai header `X-CSRFToken`.
- Tidak ada login; tidak ada token bearer.

## Gate / rate limit

- Respons `401 {"message":"Please wait a few minutes before you try again.",
  "require_login":true,"igweb_rollout":true}` = gate IP/jendela, bukan request salah.
  Muncul pada request beruntun; jeda ~60–120 dtk biasanya lolos.
- Kelas feed/list (timeline, posts tab, pagination, hashtag, search, komentar) membalas
  gate ini konsisten → memang butuh login.
- `/api/v1/*` di `www.instagram.com` hampir semuanya 302/401 logged-out.

## Fragilitas

- `doc_id` berubah tiap rilis bundle JS. Re-ekstrak dengan `tools/` (nama query stabil).
- Gate `igweb_rollout` bisa diperluas menjadi login-wall penuh kapan saja (HTML profil,
  `?__a=1`, feed, hashtag sudah jatuh).
- Signed media URL kedaluwarsa.

## Blokir dari server

Diuji dari VPS CrawlerFox (Oracle datacenter IP), tanpa proxy.

Request pertama:

```
GET https://i.instagram.com/api/v1/users/web_profile_info/?username=nasa
  User-Agent: Instagram 101.0.0.15.120 Android
  X-IG-App-ID: 124024574287414
→ HTTP 200 (~274 KB)
```

Setelah beberapa request dalam hitungan menit, endpoint mobile ini kena gate:

```
HTTP 401
{"message":"Please wait a few minutes before you try again.",
 "require_login":true,"igweb_rollout":true,"status":"fail"}
```

Gate bertahan >20 menit pada IP datacenter ini. Endpoint GraphQL (`post` by
shortcode, profil by id) dan oEmbed saat yang sama tetap `200`.

Kesimpulan: tidak ada hard-block (bukan Cloudflare 403), tapi endpoint profil
tidak andal dari IP server → manifest scraper **`proxy: required`, `status: beta`**.
Scraper membalas `503 UPSTREAM_BLOCKED` saat tergate (perilaku benar).
