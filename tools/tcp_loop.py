import os
import socket
import time
from urllib.parse import urlparse

url = os.getenv("DATABASE_URL", "")
parsed = urlparse(url)
host = parsed.hostname or "multimax-postgres"
port = parsed.port or 5432
print("TESTING CONNECT to", host, port)
for i in range(1, 31):
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect((host, port))
        print(i, "OK")
    except Exception as e:
        print(i, "ERR", e)
    finally:
        try:
            s.close()
        except Exception:
            pass
    time.sleep(0.5)
