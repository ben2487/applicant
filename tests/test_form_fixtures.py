from pathlib import Path


def _read_fixture(name: str) -> str:
    path = Path(__file__).parent / "fixtures" / name
    return path.read_text(encoding="utf-8")


def test_no_upload_fixture_missing_file_input():
    html = _read_fixture("no_upload.html")
    assert "<input" in html
    assert "type=\"file\"" not in html


def test_happy_path_fixture_contains_upload_controls():
    html = _read_fixture("ats_happy_path.html")
    assert "type=\"file\"" in html or "role=\"button\"" in html


