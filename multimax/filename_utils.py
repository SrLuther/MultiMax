import re
import unicodedata

_filename_strip_re = re.compile(r"[^A-Za-z0-9_.-]|")


def secure_filename(filename: object) -> str:
    if not isinstance(filename, str):
        filename = str(filename or "")
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("utf-8", "ignore").decode("utf-8")
    filename = filename.strip().replace("\\", "/").split("/")[-1]
    filename = filename.replace("\x00", "")
    filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
    if filename in ("", ".", ".."):
        filename = "file"
    return filename[:255]
