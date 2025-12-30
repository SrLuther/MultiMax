import os
import base64
import hashlib
import hmac

try:
    import importlib
    _ws = importlib.import_module('werkzeug.security')
    _gen = getattr(_ws, 'generate_password_hash')
    _chk = getattr(_ws, 'check_password_hash')
    def generate_password_hash(password: str, method: str = 'pbkdf2:sha256:600000') -> str:
        return _gen(password, method=method)
    def check_password_hash(pwhash: str, password: str) -> bool:
        return _chk(pwhash, password)
except Exception:
    def _b64e(b: bytes) -> str:
        return base64.b64encode(b).decode('ascii')
    def _b64d(s: str) -> bytes:
        return base64.b64decode(s.encode('ascii'))
    def generate_password_hash(password: str, method: str = 'pbkdf2:sha256:600000') -> str:
        if method.startswith('scrypt'):
            parts = method.split(':')
            n = int(parts[1]) if len(parts) > 1 else 32768
            r = int(parts[2]) if len(parts) > 2 else 8
            p = int(parts[3]) if len(parts) > 3 else 1
            salt = os.urandom(16)
            h = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=n, r=r, p=p)
            return f"scrypt:{n}:{r}:{p}${_b64e(salt)}${_b64e(h)}"
        elif method.startswith('pbkdf2'):
            parts = method.split(':')
            hash_method = parts[1] if len(parts) > 1 else 'sha256'
            iterations = int(parts[2]) if len(parts) > 2 else 600000
            salt = os.urandom(16)
            h = hashlib.pbkdf2_hmac(hash_method, password.encode('utf-8'), salt, iterations)
            return f"pbkdf2:{hash_method}:{iterations}${_b64e(salt)}${_b64e(h)}"
        else:
            h = hashlib.sha256(password.encode('utf-8')).hexdigest()
            return f"sha256${h}"
    def check_password_hash(pwhash: str, password: str) -> bool:
        if pwhash.startswith('scrypt:'):
            head, salt_s, hash_s = pwhash.split('$')
            _, n, r, p = head.split(':')
            n, r, p = int(n), int(r), int(p)
            salt = _b64d(salt_s)
            h = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=n, r=r, p=p)
            return hmac.compare_digest(_b64e(h), hash_s)
        if pwhash.startswith('pbkdf2:'):
            head, salt_s, hash_s = pwhash.split('$')
            _, hash_method, iterations = head.split(':')
            iterations = int(iterations)
            salt = _b64d(salt_s)
            h = hashlib.pbkdf2_hmac(hash_method, password.encode('utf-8'), salt, iterations)
            return hmac.compare_digest(_b64e(h), hash_s)
        if pwhash.startswith('sha256$'):
            stored = pwhash.split('$', 1)[1]
            h = hashlib.sha256(password.encode('utf-8')).hexdigest()
            return hmac.compare_digest(h, stored)
        return False
