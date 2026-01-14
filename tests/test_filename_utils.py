from multimax.filename_utils import secure_filename


def test_secure_filename_basic() -> None:
    assert secure_filename("abc.txt") == "abc.txt"


def test_secure_filename_strips_paths_and_invalid_chars() -> None:
    assert secure_filename(r"..\\pasta\\a r q u i v o!.pdf").endswith(".pdf")
    assert " " not in secure_filename("a b.txt")
    assert "!" not in secure_filename("a!b.txt")


def test_secure_filename_handles_non_string() -> None:
    assert secure_filename(None) == "file"
