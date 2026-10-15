# Reverse Engineering instagram.com — Hasil Probe (14 Okt 2026)

Metode: probe HTTP statis (curl/requests), analisis bundle JS statis dari halaman
embed/landing (`rsrc.php`), tanpa browser automation dan **tanpa login**.

> Catatan: `robots.txt` Instagram menyatakan pengumpulan data otomatis butuh izin
> tertulis dari Meta. Semua endpoint di bawah adalah endpoint internal yang tidak
> dijamin stabil — bisa berubah/blanket-block kapan saja.

## 1. Status akses logged-out (hasil probe)

| Data | Endpoint | Status |
|---|---|---|
| Profil + 12 post terbaru (by username) | `GET https://i.instagram.com/api/v1/users/web_profile_info/?username=<u>` | ✅ 200 |
| Detail post (by shortcode) | `POST https://www.instagram.com/graphql/query` doc_id `28938979505735958` | ✅ 200 |
| Profil by numeric id | `POST https://www.instagram.com/api/graphql` doc_id `28036671149327607` | ✅ 200 |
| oEmbed resmi (caption, author, thumbnail) | `GET https://www.instagram.com/api/v1/oembed/?url=<post_url>` | ✅ 200 |
| Pagination post (halaman 2+) | `feed/user/{id}/username/` dll | ❌ 401 `require_login` |
| Followers / following | `friendships/{id}/followers/` | ❌ butuh session |
| Search / topsearch | `PolarisAPITopsearchQuery` | ❌ `Unauthorized logged out query` |
| Halaman hashtag | `/explore/tags/<tag>/` | ❌ server balas route `httpErrorPage` |
| Data hashtag (API) | `tags/web_info`, `tags/{t}/sections` | ❌ 403 `login_required` |
| Komentar post | `media/{id}/comments/` | ❌ `status: fail` |
| HTML halaman profil | `GET /<username>/` | ❌ 302 → `/accounts/login/` |
| `?__a=1` (legasi) | — | ❌ mati (404/201 kosong) |

Kesimpulan: tanpa login, yang tersedia hanya **objek langsung** (profil by
username/id, post by shortcode). Semua kelas "feed/list/discovery" (timeline,
pagination, followers, hashtag, search, komentar) di-balik login.

## 2. Endpoint yang hidup — detail request

### 2a. Profil + post terbaru (mobile surface)

```
GET https://i.instagram.com/api/v1/users/web_profile_info/?username=nasa
User-Agent: Instagram 101.0.0.15.120 Android     # WAJIB mobile UA
X-IG-App-ID: 124024574287414                     # mobile app id, BUKAN web id
```

- Dengan **desktop UA / web app id (936619743392459)** endpoint ini balas
  `401 {"require_login":true}` — kombinasi UA+app-id inilah kuncinya.
- **WAJIB HTTP/2.** Terdeteksi eksplisit: `curl --http2` → 200,
  `curl --http1.1` / `python requests` / `http.client` → **429 kosong**.
  Scraper harus pakai `httpx(http2=True)` (atau curl), bukan `requests`.
- Response ~285KB: `data.user.{id,username,full_name,biography,bio_links,
  follower_count,following_count,edge_owner_to_timeline_media}`.
- `edge_owner_to_timeline_media` = `count` (total post) + `edges[12]` berisi
  node lengkap: `shortcode, display_url, is_video, edge_media_to_caption,
  edge_media_to_comment, edge_media_preview_like, taken_at, location, owner`.
- Berasal dari field lama `graphql/user` (shape XDT-legacy).

### 2b. Detail post by shortcode (GraphQL doc_id, distillery)

```
POST https://www.instagram.com/graphql/query
Content-Type: application/x-www-form-urlencoded

doc_id=28938979505735958
variables={"shortcode":"Dbd3EBdnW_u","__relay_internal__pv__PolarisShortDramaEnabledrelayprovider":false,"__relay_internal__pv__PolarisMultiCaptionCarouselEnabledrelayprovider":false}
fb_api_req_friendly_name=PolarisPostRootQuery
fb_api_caller_class=RelayModern
server_timestamps=true
__a=1&__user=0&__req=q&__rev=1050297038&hsi=...&lsd=<lsd_token>
```

Header wajib (tanpa ini → `{"errors":[{"message":"execution error"...}`):

```
X-IG-App-ID: 936619743392459
X-CSRFToken: <csrftoken cookie>
X-FB-Friendly-Name: PolarisPostRootQuery          # = fb_api_req_friendly_name
X-Root-Field-Name: xdt_api__v1__media__shortcode__web_info   # dari metadata query
X-ASBD-ID: 129477
X-IG-WWW-Claim: 0
```

Response: `data.xdt_api__v1__media__shortcode__web_info.items[0]` →
`pk, code, taken_at, media_type, image_versions2.candidates[].url,
video_versions, caption/like/comment (edge_*), owner, ...`

### 2c. Profil by id (GraphQL www)

```
POST https://www.instagram.com/api/graphql
doc_id=28036671149327607
fb_api_req_friendly_name=PolarisProfilePageContentQuery
variables={"id":"528817151","enable_integrity_filters":false, + providedVariables}
```

→ `data.user.{pk, username, full_name, biography, follower_count, bio_links,
   is_private, is_verified, hd_profile_pic_*, media_count, ...}`

Catatan: error GraphQL di sini jujur dan membantu, contoh:
- `missing_required_variable_value` (code 1675012) → ada variabel wajib belum dikirim.
- `Unauthorized logged out query.` (code 1675002) → query itu butuh login.

### 2d. oEmbed resmi

```
GET https://www.instagram.com/api/v1/oembed/?url=https://www.instagram.com/p/<code>/
```
Tanpa auth, tanpa header khusus. Return `title` (caption), `author_name`,
`author_url`, `author_id` (→ user id!), `media_id`, `thumbnail_url`.

## 3. Arsitektur GraphQL web Instagram (catatan RE)

- Dua endpoint, dipilih dari `metadata` query (lihat
  `createRelayIGNetwork`: `metadata.is_distillery === true` → distillery):
  - **distillery** → `https://www.instagram.com/graphql/query`
  - **www** → `https://www.instagram.com/api/graphql`
- Request body = `getAsyncParams("POST")` (`__a,__user,__req,__rev,hsi,lsd,hs,dpr`)
  + `doc_id` + `variables` (JSON string) + `fb_api_req_friendly_name`
  + `fb_api_caller_class=RelayModern` + `server_timestamps=true`.
- Header tambahan dari `createRelayFBNetworkFetch`:
  `X-FB-Friendly-Name` dan `X-Root-Field-Name` (isi `metadata.root_field_name[0]`).
- `providedVariables` ada di variabel, **dengan suffix `relayprovider`**:
  `"__relay_internal__pv__PolarisShortDramaEnabledrelayprovider": false`.
  Nilainya boleh `false` (server hanya cek keberadaan/tipe).
- Query persisten (`text:null`) — teks query hanya ada di server; klien cuma
  kirim `doc_id` + `variables`.

### Cara ekstrak doc_id (reproducible)

Ambil bundle JS dari halaman mana pun (tag `<script src="…rsrc.php…">` di HTML),
lalu:

```bash
grep -ho '__d("[A-Za-z0-9_]*_instagramRelayOperation",\[\],(function(t,n,r,o,a,i){a.exports="[0-9]*"' *.js \
  | sed 's/__d("//;s/_instagramRelayOperation".*a.exports="/ /;s/"$//'
```

Variabel tiap query ada di modul `"<QueryName>.graphql"`: pola
`{defaultValue:…,kind:"LocalArgument",name:"<var>"}`.
Metadata (root field, distillery/www) ada di `"<QueryName>$Parameters"` /
`params:{id:…,metadata:{…}}`.

Daftar doc_id yang terekstrak (per 14 Okt 2026, bundle embed/landing) — lihat
`doc_ids.txt`.

## 4. Perilaku gate / rate limit

- Respons `401 {"message":"Please wait a few minutes before you try again.",
  "require_login":true,"igweb_rollout":true}` = **gate IP/window**, bukan
  salah request. Muncul untuk request beruntun; jeda ~60–120 dtk biasanya lolos.
- Query kelas feed/list (timeline, posts tab) balas gate ini **konsisten**
  bahkan setelah idle → memang butuh login, bukan soal pacing.
- `/api/v1/*` di www.instagram.com hampir semuanya 302/401 logged-out;
  gunakan `i.instagram.com` + mobile UA untuk `web_profile_info`.

## 5. Fragilitas

- `doc_id` berubah tiap rilis bundle (re-ekstrak berkala — ada script-nya).
- Gate `igweb_rollout` bisa diperluas menjadi blanket login-wall kapan saja
  (sudah terbukti: profil HTML, `?__a=1`, feed, hashtag semua sudah jatuh).
- URL media (`scontent…cdninstagram.com`) punya signature (`oh`/`oe`) yang
  kedaluwarsa — jangan simpan mentah untuk jangka panjang.

## 6. Dua repo & cara pakai

| Repo | Isi |
|---|---|
| `scripthon/instagram-re` (repo ini) | NOTES.md ini, `graphql_probe2.py`, `probe.sh`, `doc_ids.txt` |
| `scripthon/instagram-client` | client Python berbasis uv (`httpx[http2]`): CLI `instagram-client` + class `InstagramScraper` |

Client hanya **mengirim raw response** (JSON mentah dari endpoint, tanpa
normalisasi; error API seperti gate/login_required ikut sebagai isi JSON):

```bash
uv run instagram-client profile <username>   # web_profile_info (profil + 12 post)
uv run instagram-client post <shortcode>     # PolarisPostRootQuery
uv run instagram-client by-id <user_id>      # PolarisProfilePageContentQuery
uv run instagram-client oembed <url-post>    # oEmbed resmi
```

```python
from instagram_client import InstagramScraper

s = InstagramScraper()          # throttle + retry gate/429
prof = s.profile("nasa")        # {"data": {"user": {...}}, "status": "ok"}
node = prof["data"]["user"]["edge_owner_to_timeline_media"]["edges"][0]["node"]
detail = s.post(node["shortcode"])   # {"data": {"xdt_api__v1__media__shortcode__web_info": ...}}
```

Catatan respons:
- Prefix anti-JSON Facebook `for (;;);` dilepas supaya body valid JSON; sisanya
  mentah. Bila body bukan JSON sama sekali, client membungkus
  `{"__raw__": "<teks>", "__http_status__": <kode>}`.
- `by-id` membalas `media_count: null` untuk logged-out (memang begitu dari
  server); jumlah post asli ada di `profile()` (field
  `edge_owner_to_timeline_media.count`).
- Transport: throttle acak (~6 dtk), retry backoff untuk gate 401
  `require_login` / HTTP 429, retry untuk envelope error FB
  `for (;;);{"__ar":1,…}`, ekstraksi otomatis `lsd`/`hsi`/`__rev`/`csrftoken`
  dari landing page.

Refresh doc_id bila query mulai error: unduh bundle JS dari halaman mana pun
lalu jalankan pola grep di §3 (nama query relatif stabil, angkanya berubah tiap
rilis bundle).
