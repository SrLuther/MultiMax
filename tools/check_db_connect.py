import os
import socket
import urllib.parse

url = os.getenv("DATABASE_URL", "")
print("DATABASE_URL=", url)
hostname = None
port = None
if url:
    p = urllib.parse.urlparse(url)
    hostname = p.hostname
    port = p.port
print("db host:", hostname, "port:", port)
try:
    s = socket.socket()
    s.settimeout(3)
    s.connect((hostname or "localhost", port or 5432))
    print("TCP_OK")
except Exception as e:
    print("TCP_ERR", e)
finally:
    try:
        s.close()
    except Exception:
        pass

try:
    import psycopg

    conn = psycopg.connect(url)
    conn.close()
    print("PSYCOPG_OK")
except Exception as e:
    print("PSYCOPG_ERR", e)
