#!/usr/bin/env python3
"""Check supplied Apple CMS endpoints; Python standard library + curl only."""
import concurrent.futures
import datetime
import json
import pathlib
import re
import subprocess
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent
TIMEOUT = 15


def request(url, **params):
    query = urllib.parse.urlencode(params)
    target = url + ('&' if '?' in url else '?') + query
    proc = subprocess.run([
        'curl', '--silent', '--show-error', '--location', '--max-redirs', '4',
        '--connect-timeout', '7', '--max-time', str(TIMEOUT),
        '--max-filesize', '5242880', '--proto', '=http,https',
        '--proto-redir', '=http,https', '--user-agent', 'Mozilla/5.0',
        '--header', 'Accept: application/json',
        '--write-out', '\n__META__%{http_code} %{url_effective}', target
    ], capture_output=True, timeout=TIMEOUT + 3)
    raw, _, meta = proc.stdout.rpartition(b'\n__META__')
    parts = meta.decode('utf-8', 'replace').split(' ', 1)
    status = int(parts[0]) if parts and parts[0].isdigit() else 0
    final_url = parts[1] if len(parts) > 1 else target
    result = {'http_status': status, 'final_url': final_url}
    if proc.returncode:
        result['error'] = proc.stderr.decode('utf-8', 'replace').strip()[:300]
        return result, None
    if not 200 <= status < 300:
        result['error'] = f'HTTP {status}'
        # A proxy block is inconclusive, rather than evidence of a dead endpoint.
        if b'HTTPS' in raw and b'Blocked' in raw:
            result['error'] = 'environment_requires_https'
        return result, None
    try:
        text = raw.decode('utf-8-sig')
        data = json.loads(text)
    except (ValueError, UnicodeError):
        result['error'] = 'XML response' if raw.lstrip().startswith(b'<?xml') else 'non-JSON response'
        result['response_preview'] = raw[:180].decode('utf-8', 'replace')
        return result, None
    if not isinstance(data, dict) or not isinstance(data.get('list'), list):
        result['error'] = 'missing Apple CMS list array'
        return result, None
    result['items'] = len(data['list'])
    return result, data


def check(item):
    name, url = item['name'], item['url']
    record = {**item, 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'checks': {}}
    try:
        meta, data = request(url, ac='list')
        record['checks']['list'] = meta
        if data is None or not data['list']:
            record['status'] = 'unverified' if data is None else 'empty'
            return record
        samples = [v for v in data['list'][:5] if isinstance(v, dict) and v.get('vod_id') and v.get('vod_name')]
        if not samples:
            record['status'] = 'incompatible'
            return record
        ids = ','.join(str(v['vod_id']) for v in samples[:3])
        meta, detail = request(url, ac='detail', ids=ids)
        record['checks']['detail'] = meta
        playable = [] if detail is None else [v for v in detail['list'] if isinstance(v, dict) and
            isinstance(v.get('vod_play_url'), str) and '.m3u8' in v['vod_play_url'] and
            ('$http://' in v['vod_play_url'] or '$https://' in v['vod_play_url'])]
        record['detail_sample_count'] = len(playable)
        if not playable:
            record['status'] = 'unverified' if detail is None else 'no_m3u8_in_sample'
            return record
        # Common, short title fragment avoids title punctuation and overly long WD filters.
        keyword = ''.join(re.findall(r'[\w\u4e00-\u9fff]', str(samples[0]['vod_name'])))[:2]
        meta, search = request(url, ac='detail', wd=keyword)
        record['checks']['search'] = {**meta, 'keyword': keyword}
        record['status'] = 'verified' if search is not None and search['list'] and all(
            isinstance(v, dict) and v.get('vod_id') and v.get('vod_name') for v in search['list']) else 'search_unverified'
    except Exception as exc:
        record['status'] = 'unverified'
        record['error'] = str(exc)[:300]
    return record


def main():
    items, duplicates, seen = [], [], set()
    for line in (ROOT / 'candidates.txt').read_text().splitlines():
        name, url = line.split('|', 1)
        url = url.strip().rstrip('/')
        item = {'name': name, 'url': url}
        if url in seen:
            duplicates.append(item)
        else:
            seen.add(url)
            items.append(item)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(check, items))
    retry_indices = [i for i, result in enumerate(results) if result['status'] != 'verified']
    global TIMEOUT
    TIMEOUT = 22
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        retries = list(pool.map(check, (items[i] for i in retry_indices)))
    for i, retry in zip(retry_indices, retries):
        retry['previous_attempt'] = {k: v for k, v in results[i].items() if k not in ('name', 'url')}
        results[i] = retry
    report = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'method': 'ac=list + ac=detail(ids, up to 3) + ac=detail(wd, sampled title); no media playback test',
              'duplicates': duplicates, 'results': results}
    (ROOT / 'check-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    counts = {}
    for result in results:
        counts[result['status']] = counts.get(result['status'], 0) + 1
    print(json.dumps({'unique': len(items), 'duplicates': len(duplicates), 'statuses': counts}, ensure_ascii=False))


if __name__ == '__main__':
    main()
