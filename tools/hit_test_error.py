import urllib.error
import urllib.request

try:
    res = urllib.request.urlopen("http://localhost:5000/api/test-error")
    print("STATUS", res.status)
    print(res.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP ERROR", e.code)
    print(e.read().decode())
except Exception as e:
    print("ERR", e)
