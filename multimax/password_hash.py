import base64
import hashlib
import hmac
import os
from typing import Callable, cast

try:
    import importlib

    _ws = importlib.import_module("werkzeug.security")
    _gen = cast(Callable[..., str], getattr(_ws, "generate_password_hash"))
    _chk = cast(Callable[..., bool], getattr(_ws, "check_password_hash"))

    def generate_password_hash(password: str, method: str = "pbkdf2:sha256:600000") -> str:
        return str(_gen(password, method=method))

    def check_password_hash(pwhash: str, password: str) -> bool:
        return bool(_chk(pwhash, password))

except Exception:

    def _b64e(b: bytes) -> str:
        return base64.b64encode(b).decode("ascii")

    def _b64d(s: str) -> bytes:
        return base64.b64decode(s.encode("ascii"))

    def generate_password_hash(password: str, method: str = "pbkdf2:sha256:600000") -> str:
        if method.startswith("scrypt"):
            parts = method.split(":")
            n = int(parts[1]) if len(parts) > 1 else 32768
            r = int(parts[2]) if len(parts) > 2 else 8
            p = int(parts[3]) if len(parts) > 3 else 1
            salt = os.urandom(16)
            dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p)
            return f"scrypt:{n}:{r}:{p}${_b64e(salt)}${_b64e(dk)}"
        elif method.startswith("pbkdf2"):
            parts = method.split(":")
            hash_method = parts[1] if len(parts) > 1 else "sha256"
            iterations = int(parts[2]) if len(parts) > 2 else 600000
            salt = os.urandom(16)
            dk = hashlib.pbkdf2_hmac(hash_method, password.encode("utf-8"), salt, iterations)
            return f"pbkdf2:{hash_method}:{iterations}${_b64e(salt)}${_b64e(dk)}"
        else:
            digest_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return f"sha256${digest_hex}"

    def check_password_hash(pwhash: str, password: str) -> bool:
        if pwhash.startswith("scrypt:"):
            head, salt_s, hash_s = pwhash.split("$")
            _, n_s, r_s, p_s = head.split(":")
            n_i, r_i, p_i = int(n_s), int(r_s), int(p_s)
            salt = _b64d(salt_s)
            dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n_i, r=r_i, p=p_i)
            return hmac.compare_digest(_b64e(dk), hash_s)
        if pwhash.startswith("pbkdf2:"):
            head, salt_s, hash_s = pwhash.split("$")
            _, hash_method, iterations_s = head.split(":")
            iterations_i = int(iterations_s)
            salt = _b64d(salt_s)
            dk = hashlib.pbkdf2_hmac(hash_method, password.encode("utf-8"), salt, iterations_i)
            return hmac.compare_digest(_b64e(dk), hash_s)
        if pwhash.startswith("sha256$"):
            stored = pwhash.split("$", 1)[1]
            digest_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(digest_hex, stored)
        return False
