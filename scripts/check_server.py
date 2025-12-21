import sys
import urllib.request

url = 'http://127.0.0.1:5000/'
try:
    req = urllib.request.Request(url, headers={'User-Agent':'check'})
    with urllib.request.urlopen(req, timeout=5) as r:
        print('STATUS', r.status)
        body = r.read(200).decode('utf-8', errors='replace')
        print('BODY_PREVIEW:\n', body[:500])
except Exception as e:
    print('ERR', e)
    sys.exit(2)
