import os
import threading
import time
import urllib.request
from multimax import create_app

app = create_app()

def _start_keepalive():
    enabled = os.getenv('KEEPALIVE_ENABLED', 'false').lower() == 'true'
    if not enabled:
        return
    url = (os.getenv('KEEPALIVE_URL') or '').strip()
    if not url:
        return
    interval = int(os.getenv('KEEPALIVE_INTERVAL', '300'))
    def _loop():
        while True:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'MultiMax-KeepAlive'})
                urllib.request.urlopen(req, timeout=10).read()
            except Exception:
                pass
            time.sleep(interval)
    t = threading.Thread(target=_loop, daemon=True)
    t.start()

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    _start_keepalive()
    try:
        from waitress import serve
    except ImportError:
        serve = None
    if serve:
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=debug)
