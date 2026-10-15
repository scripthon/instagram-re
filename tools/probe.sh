#!/usr/bin/env bash
# Probe endpoint Instagram (logged-out) dengan header + cookie ala browser.
set -u
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
APPID='936619743392459'
JAR=/tmp/opencode/ig_jar.txt
BASE='https://www.instagram.com'
IH='https://i.instagram.com'

# 1. Ambil cookie awal dari homepage
curl -s -c "$JAR" -A "$UA" -o /dev/null "$BASE/"
CSRF=$(awk '$6=="csrftoken"{print $7}' "$JAR" | tail -1)

hdrs=(-A "$UA"
  -H "Accept: */*"
  -H "Accept-Language: en-US,en;q=0.9"
  -H "X-IG-App-ID: $APPID"
  -H "X-ASBD-ID: 129477"
  -H "X-IG-WWW-Claim: 0"
  -H "Sec-Fetch-Site: same-origin"
  -H "Sec-Fetch-Mode: cors"
  -H "Sec-Fetch-Dest: empty"
  -H "Referer: $BASE/")
[ -n "${CSRF:-}" ] && hdrs+=(-H "X-CSRFToken: $CSRF")

probe() {
  local method=$1 url=$2 data=${3:-}
  if [ "$method" = GET ]; then
    out=$(curl -s -b "$JAR" -c "$JAR" "${hdrs[@]}" -w '\nHTTP:%{http_code}' "$url")
  else
    out=$(curl -s -b "$JAR" -c "$JAR" "${hdrs[@]}" -H 'Content-Type: application/x-www-form-urlencoded' -w '\nHTTP:%{http_code}' -X POST --data "$data" "$url")
  fi
  local code=${out##*HTTP:}
  local body=${out%$'\n'HTTP:*}
  echo "== $method $url -> $code"
  echo "   ${body:0:220}"
}

echo "### PROFIL"
probe GET  "$BASE/api/v1/users/web_profile_info/?username=nasa"
probe GET  "$IH/api/v1/users/web_profile_info/?username=nasa"
probe GET  "$BASE/api/v1/feed/user/nasa/username/?count=5"
probe GET  "$BASE/nasa/?__a=1&__d=dis"
probe GET  "$BASE/graphql/query?doc_id=8845758582119845&variables=%7B%22username%22%3A%22nasa%22%7D"

echo "### POST/FEED"
probe GET  "$BASE/api/v1/oembed/?url=https://www.instagram.com/p/Dbd3EBdnW_u/"
probe GET  "$BASE/api/v1/media/3953558216907780078/info/"
probe GET  "$BASE/api/v1/media/3953558216907780078/comments/?can_support_threading=true"
probe GET  "$IH/api/v1/media/3953558216907780078/info/"

echo "### HASHTAG"
probe GET  "$BASE/api/v1/tags/web_info/?q=nasa"
probe GET  "$BASE/api/v1/fbsearch/topsearch/?context=blended&query=nasa"
probe GET  "$IH/api/v1/feed/tag/nasa/?count=5"
probe GET  "$BASE/explore/tags/nasa/?__a=1&__d=dis"

echo "### SEARCH"
probe GET  "$BASE/api/v1/fbsearch/web/topsearch/?context=blended&query=nasa&rank_token="
