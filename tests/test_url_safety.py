"""Tests for SSRF URL validation (app.core.url_safety)."""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.url_safety import validate_calendar_url, is_url_safe_for_fetch


class TestUrlSafety(unittest.TestCase):
    def test_rejects_file_scheme(self):
        with self.assertRaises(ValueError) as ctx:
            validate_calendar_url("file:///etc/passwd")
        self.assertIn("esquema http o https", str(ctx.exception))

    def test_rejects_loopback(self):
        with self.assertRaises(ValueError) as ctx:
            validate_calendar_url("http://127.0.0.1/cal.ics")
        self.assertIn("redes privadas o locales", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx2:
            validate_calendar_url("https://localhost/cal.ics")
        self.assertIn("redes privadas o locales", str(ctx2.exception))

    def test_rejects_private_ip(self):
        for url in (
            "http://192.168.1.1/cal.ics",
            "http://10.0.0.1/cal.ics",
            "http://172.16.0.1/cal.ics",
        ):
            with self.assertRaises(ValueError) as ctx:
                validate_calendar_url(url)
            self.assertIn("redes privadas o locales", str(ctx.exception))

    def test_rejects_link_local(self):
        with self.assertRaises(ValueError) as ctx:
            validate_calendar_url("http://169.254.169.254/latest/meta-data/")
        self.assertIn("redes privadas o locales", str(ctx.exception))

    def test_rejects_empty_host(self):
        with self.assertRaises(ValueError) as ctx:
            validate_calendar_url("http:///path")
        self.assertIn("host válido", str(ctx.exception))

    def test_is_url_safe_for_fetch_returns_false_for_unsafe(self):
        self.assertFalse(is_url_safe_for_fetch("file:///etc/passwd"))
        self.assertFalse(is_url_safe_for_fetch("http://127.0.0.1/cal.ics"))
        self.assertFalse(is_url_safe_for_fetch("http://192.168.1.1/cal.ics"))

    def test_accepts_public_https_url(self):
        validate_calendar_url("https://example.com/cal.ics")

    def test_accepts_public_http_url(self):
        validate_calendar_url("http://example.com/cal.ics")


if __name__ == "__main__":
    unittest.main()
