#!/usr/bin/env python3
"""Probe GraphQL Instagram v2: routing distillery vs www + header X-FB-Friendly-Name/X-Root-Field-Name."""
import json, subprocess, time, sys

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
JAR = '/tmp/opencode/jar2.txt'
OUT = '/tmp/opencode/graphql_results2.jsonl'
WWW = 'https://www.instagram.com/api/graphql'
DIST = 'https://www.instagram.com/graphql/query'

PV = {
    'shortd': ('__relay_internal__pv__PolarisShortDramaEnabledrelayprovider', False),
    'multic': ('__relay_internal__pv__PolarisMultiCaptionCarouselEnabledrelayprovider', False),
    'reco': ('__relay_internal__pv__PolarisReelsRecoDebugOverlayEnabledrelayprovider', False),
    'cannes': ('__relay_internal__pv__PolarisCannesGuardianExperienceEnabledrelayprovider', False),
    'casb': ('__relay_internal__pv__PolarisCASB976ProfileEnabledrelayprovider', False),
    'repost': ('__relay_internal__pv__PolarisRepostsConsumptionEnabledrelayprovider', False),
    'schools': ('__relay_internal__pv__PolarisWebSchoolsEnabledrelayprovider', False),
}


def pv(*ks):
    return dict(PV[k] for k in ks)


TESTS = [
    dict(name='post_root', url=DIST, doc='28938979505735958',
         friendly='PolarisPostRootQuery',
         root='xdt_api__v1__media__shortcode__web_info',
         vars={'shortcode': 'Dbd3EBdnW_u', **pv('shortd', 'multic')},
         referer='https://www.instagram.com/p/Dbd3EBdnW_u/'),
    dict(name='owner_timeline', url=DIST, doc='39002825106027755',
         friendly='PolarisOwnerToTimelineMediaLoggedOutQuery',
         root='xdt_get_owner_to_timeline_media_logged_out',
         vars={'owner_id': '528817151', 'first': 12,
               'additional_media_to_fetch': [], **pv('shortd')},
         referer='https://www.instagram.com/nasa/'),
    dict(name='profile_posts', url=DIST, doc='28542612348729311',
         friendly='PolarisProfilePostsQuery', root=None,
         vars={'username': 'nasa', 'first': 12, **pv('multic', 'shortd', 'reco')},
         referer='https://www.instagram.com/nasa/'),
    dict(name='www_post_root', url=WWW, doc='27776306792043877',
         friendly='PolarisLoggedOutDesktopWWWPostRootContentQuery', root=None,
         vars={'shortcode': 'Dbd3EBdnW_u'},
         referer='https://www.instagram.com/p/Dbd3EBdnW_u/'),
    dict(name='topsearch', url=WWW, doc='29386906664232128',
         friendly='PolarisAPITopsearchQuery', root=None,
         vars={'data': 'nasa'},
         referer='https://www.instagram.com/'),
    dict(name='profile_page_content', url=WWW, doc='28036671149327607',
         friendly='PolarisProfilePageContentQuery', root=None,
         vars={'id': '528817151', 'enable_integrity_filters': False,
               **pv('cannes', 'casb', 'schools', 'repost', 'shortd')},
         referer='https://www.instagram.com/nasa/'),
]


def run_one(t):
    csrf = subprocess.run(['awk', '$6=="csrftoken"{print $7}', JAR],
                          capture_output=True, text=True).stdout.strip().splitlines()
    csrf = csrf[-1] if csrf else ''
    form = {
        'doc_id': t['doc'],
        'variables': json.dumps(t['vars'], separators=(',', ':')),
        'fb_api_req_friendly_name': t['friendly'],
        'fb_api_caller_class': 'RelayModern',
        'server_timestamps': 'true',
        '__a': '1', '__user': '0', '__req': 'q',
        '__rev': '1050297038',
        'hsi': '<HSI>',
        'lsd': '<LSD>',
    }
    cmd = ['curl', '-s', '-b', JAR, '-c', JAR, '-A', UA,
           '-H', 'Accept: */*', '-H', 'Accept-Language: en-US,en;q=0.9',
           '-H', 'X-IG-App-ID: 936619743392459',
           '-H', f'X-CSRFToken: {csrf}',
           '-H', 'X-ASBD-ID: 129477', '-H', 'X-IG-WWW-Claim: 0',
           '-H', 'X-IG-Max-Touch-Points: 1',
           '-H', f'X-FB-Friendly-Name: {t["friendly"]}',
           '-H', 'Sec-Fetch-Site: same-origin', '-H', 'Sec-Fetch-Mode: cors',
           '-H', 'Sec-Fetch-Dest: empty',
           '-H', 'Content-Type: application/x-www-form-urlencoded',
           '-H', f'Referer: {t["referer"]}',
           '-w', '\nHTTP:%{http_code}',
           '-X', 'POST', t['url']]
    if t.get('root'):
        cmd += ['-H', f'X-Root-Field-Name: {t["root"]}']
    for k, v in form.items():
        cmd += ['--data-urlencode', f'{k}={v}']
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    raw = p.stdout
    code = raw.rsplit('HTTP:', 1)[-1].strip() if 'HTTP:' in raw else '?'
    body = raw[:raw.rfind('HTTP:')] if 'HTTP:' in raw else raw
    rec = dict(name=t['name'], url=t['url'], http=code, body=body[:8000])
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec) + '\n')
    print(f"[{t['name']}] HTTP {code} :: {body[:300]}", flush=True)


def main():
    only = set(sys.argv[1:])
    first = True
    for t in TESTS:
        if only and t['name'] not in only:
            continue
        if not first:
            time.sleep(70)
        first = False
        try:
            run_one(t)
        except Exception as e:
            print(f"[{t['name']}] ERROR {e}", flush=True)


if __name__ == '__main__':
    main()
