import logging
import sys
from datetime import datetime as real_datetime
from pathlib import Path

# Add project root before importing main
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main as qr_app


def test_create_directory_creates_nested_path(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    qr_app.create_directory(target)
    assert target.exists()
    assert target.is_dir()


def test_is_valid_url_returns_true_for_valid_url():
    assert qr_app.is_valid_url("https://example.com") is True


def test_is_valid_url_returns_false_and_logs_for_invalid_url(caplog):
    with caplog.at_level(logging.ERROR):
        assert qr_app.is_valid_url("not-a-url") is False
    assert "Invalid URL provided: not-a-url" in caplog.text


def test_generate_qr_code_writes_file_for_valid_url(monkeypatch, tmp_path):
    class DummyImage:
        def save(self, file_obj):
            file_obj.write(b"fake-png")

    class DummyQRCode:
        def add_data(self, data):
            self.data = data

        def make(self, fit=True):
            self.fit = fit

        def make_image(self, fill_color="red", back_color="white"):
            self.fill_color = fill_color
            self.back_color = back_color
            return DummyImage()

    monkeypatch.setattr(qr_app, "is_valid_url", lambda _: True)
    monkeypatch.setattr(qr_app.qrcode, "QRCode", lambda **kwargs: DummyQRCode())

    out_file = tmp_path / "qr.png"
    qr_app.generate_qr_code("https://example.com", out_file, "black", "white")

    assert out_file.exists()
    assert out_file.read_bytes() == b"fake-png"


def test_generate_qr_code_skips_when_invalid_url(monkeypatch, tmp_path):
    monkeypatch.setattr(qr_app, "is_valid_url", lambda _: False)

    def should_not_be_called(**kwargs):
        raise AssertionError("QRCode should not be created for invalid URL")

    monkeypatch.setattr(qr_app.qrcode, "QRCode", should_not_be_called)

    out_file = tmp_path / "qr.png"
    qr_app.generate_qr_code("invalid-url", out_file)

    assert not out_file.exists()


def test_main_builds_expected_path_and_calls_dependencies(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(qr_app, "QR_DIRECTORY", "qr_codes_test")
    monkeypatch.setattr(qr_app, "FILL_COLOR", "blue")
    monkeypatch.setattr(qr_app, "BACK_COLOR", "yellow")
    monkeypatch.setattr(sys, "argv", ["main.py", "--url", "https://example.com"])

    class FixedDateTime:
        @classmethod
        def now(cls):
            return real_datetime(2026, 1, 2, 3, 4, 5)

    monkeypatch.setattr(qr_app, "datetime", FixedDateTime)

    called = {}

    def fake_create_directory(path: Path):
        called["dir"] = path

    def fake_generate_qr_code(data, path, fill_color, back_color):
        called["url"] = data
        called["path"] = path
        called["fill"] = fill_color
        called["back"] = back_color

    monkeypatch.setattr(qr_app, "create_directory", fake_create_directory)
    monkeypatch.setattr(qr_app, "generate_qr_code", fake_generate_qr_code)

    qr_app.main()

    expected_dir = tmp_path / "qr_codes_test"
    expected_file = expected_dir / "QRCode_20260102030405.png"

    assert called["dir"] == expected_dir
    assert called["url"] == "https://example.com"
    assert called["path"] == expected_file
    assert called["fill"] == "blue"
    assert called["back"] == "yellow"
