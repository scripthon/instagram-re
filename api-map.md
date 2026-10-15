# api-map.md — endpoint Instagram (logged-out)

Capture 14 Okt 2026. Base URL: `https://www.instagram.com` kecuali disebut lain.
Semua endpoint di bawah **publik** (tanpa login). Endpoint yang butuh login dicatat di
bagian akhir. Contoh `curl` sudah diverifikasi dari VPS.

---

## 1. Profil + 12 post terbaru (by username)

```
GET https://i.instagram.com/api/v1/users/web_profile_info/?username=<username>
```

- **Param**: `username` (path-query, wajib) — tanpa `@`.
- **Header wajib**: `User-Agent: Instagram 101.0.0.15.120 Android`,
  `X-IG-App-ID: 124024574287414`. Wajib HTTP/2.
- **Pagination**: tidak ada (hanya 12 post terbaru di `edge_owner_to_timeline_media`).
- **Status**: `200` normal; username tidak ada → `404` (HTML "Page Not Found", bukan JSON);
  request beruntun → `401 {"require_login":true,...}` (gate).
- **Bentuk respons**: `data.user.{id,username,full_name,biography,bio_links,
  edge_followed_by.count, edge_follow.count, edge_owner_to_timeline_media{count,edges[12]}}`.
  Setiap node: `shortcode, display_url, is_video, edge_media_to_caption, taken_at, location, owner`.
- **Sample**: [`data-samples/profile-nasa.json`](data-samples/profile-nasa.json).

```bash
curl -s --http2 \
  -H "User-Agent: Instagram 101.0.0.15.120 Android" \
  -H "X-IG-App-ID: 124024574287414" \
  "https://i.instagram.com/api/v1/users/web_profile_info/?username=nasa"
```

---

## 2. Detail post (by shortcode)

```
POST https://www.instagram.com/graphql/query
Content-Type: application/x-www-form-urlencoded
```

- **Body**: `doc_id=28938979505735958` +
  `variables={"shortcode":"<code>","__relay_internal__pv__PolarisShortDramaEnabledrelayprovider":false,
  "__relay_internal__pv__PolarisMultiCaptionCarouselEnabledrelayprovider":false}` +
  `fb_api_req_friendly_name=PolarisPostRootQuery` + `fb_api_caller_class=RelayModern` +
  `server_timestamps=true` + `__a=1&__user=0&__req=q&__rev=<rev>&hsi=<hsi>&lsd=<lsd>`.
- **Header wajib**: `X-IG-App-ID: 936619743392459`, `X-CSRFToken`, `X-FB-Friendly-Name:
  PolarisPostRootQuery`, `X-Root-Field-Name: xdt_api__v1__media__shortcode__web_info`,
  `X-ASBD-ID: 129477`, `X-IG-WWW-Claim: 0`.
- **Respons**: `data.xdt_api__v1__media__shortcode__web_info.items[0]` → `pk, code, taken_at,
  media_type, image_versions2.candidates[].url, video_versions, caption/like/comment
  (edge_*), owner`.
- **Error**: shortcode tidak ada → `200` dengan `{"data":null,"errors":[{"code":1675030,...}]}`
  (bukan HTTP 404). Header kurang → `{"errors":[{"message":"execution error"...}]}`.
- **Sample**: [`data-samples/post-Dbd3EBdnW_u.json`](data-samples/post-Dbd3EBdnW_u.json).

```bash
# butuh bootstrap cookie + lsd/hsi/rev dari https://www.instagram.com/ (lihat client)
curl -s --http2 -c /tmp/jar -A "Mozilla/5.0 ... Chrome/131.0.0.0 Safari/537.36" https://www.instagram.com/ >/dev/null
CSRF=$(awk '$6=="csrftoken"{print $7}' /tmp/jar | tail -1)
curl -s --http2 -b /tmp/jar \
  -H "X-IG-App-ID: 936619743392459" -H "X-CSRFToken: $CSRF" \
  -H "X-FB-Friendly-Name: PolarisPostRootQuery" \
  -H "X-Root-Field-Name: xdt_api__v1__media__shortcode__web_info" \
  -H "X-ASBD-ID: 129477" -H "X-IG-WWW-Claim: 0" \
  -X POST "https://www.instagram.com/graphql/query" \
  --data-urlencode "doc_id=28938979505735958" \
  --data-urlencode 'variables={"shortcode":"Dbd3EBdnW_u","__relay_internal__pv__PolarisShortDramaEnabledrelayprovider":false,"__relay_internal__pv__PolarisMultiCaptionCarouselEnabledrelayprovider":false}' \
  --data-urlencode "fb_api_req_friendly_name=PolarisPostRootQuery" \
  --data-urlencode "fb_api_caller_class=RelayModern" \
  --data-urlencode "server_timestamps=true" \
  --data-urlencode "__a=1" --data-urlencode "__user=0" --data-urlencode "__req=q" \
  --data-urlencode "__rev=1050297038" --data-urlencode "hsi=<hsi>" --data-urlencode "lsd=<lsd>"
```

---

## 3. Profil by numeric id

```
POST https://www.instagram.com/api/graphql
```

- **Body**: `doc_id=28036671149327607`, `fb_api_req_friendly_name=PolarisProfilePageContentQuery`,
  `variables={"id":"<user_id>","enable_integrity_filters":false, + providedVariables}`.
- **Respons**: `data.user.{pk, username, full_name, biography, follower_count, bio_links,
  is_private, is_verified, hd_profile_pic_*, media_count}`.
- **Error jujur** dari server: `missing_required_variable_value` (code 1675012),
  `Unauthorized logged out query.` (code 1675002). ID tidak ada → `200` dengan errors,
  `data` kosong.
- **Catatan**: `media_count` bisa `null` saat logged-out; jumlah post asli ada di
  endpoint 1 (`edge_owner_to_timeline_media.count`).
- **Sample**: [`data-samples/user-by-id-528817151.json`](data-samples/user-by-id-528817151.json).

---

## 4. oEmbed resmi

```
GET https://www.instagram.com/api/v1/oembed/?url=<post_url>
```

- **Param**: `url` (wajib) — URL post, mis. `https://www.instagram.com/p/<code>/`.
- **Header**: tidak ada yang khusus (tanpa auth).
- **Respons**: `title` (caption), `author_name`, `author_url`, `author_id` (user id),
  `media_id` (`<pk>_<user_id>`), `thumbnail_url`, `html`.
- **Error**: URL tidak cocok → `404` body teks `No Media Match` (bukan JSON).
- **Sample**: [`data-samples/oembed-Dbd3EBdnW_u.json`](data-samples/oembed-Dbd3EBdnW_u.json).

```bash
curl -s --http2 "https://www.instagram.com/api/v1/oembed/?url=https://www.instagram.com/p/Dbd3EBdnW_u/"
```

---

## Butuh login (tidak diekspos scraper)

| Data | Endpoint | Hasil logged-out |
|---|---|---|
| Pagination post (halaman 2+) | `feed/user/{id}/username/` | 401 `require_login` |
| Followers / following | `friendships/{id}/followers/` | butuh session |
| Search / topsearch | `PolarisAPITopsearchQuery` | `Unauthorized logged out query` |
| Halaman & API hashtag | `/explore/tags/<tag>/`, `tags/web_info`, `tags/{t}/sections` | route `httpErrorPage` / 403 `login_required` |
| Komentar post | `media/{id}/comments/` | `status: fail` |
| HTML halaman profil | `GET /<username>/` | 302 → `/accounts/login/` |
| `?__a=1` (legacy) | — | mati (404 / body kosong) |

## Arsitektur GraphQL (catatan)

- Dua endpoint dipilih dari metadata query (`createRelayIGNetwork`,
  `metadata.is_distillery === true` → distillery):
  - **distillery** → `https://www.instagram.com/graphql/query`
  - **www** → `https://www.instagram.com/api/graphql`
- Header tambahan dari `createRelayFBNetworkFetch`: `X-FB-Friendly-Name`,
  `X-Root-Field-Name`.
- `providedVariables` disertakan dengan suffix `relayprovider`; nilainya boleh `false`.
- Cara ekstrak `doc_id` (reproducible): unduh bundle JS (`rsrc.php`) lalu
  `grep -ho '__d("..._instagramRelayOperation",\[\],(function(t,n,r,o,a,i){a.exports="[0-9]*"'`
  — lihat `tools/graphql_probe2.py` dan `tools/doc_ids.txt`.
