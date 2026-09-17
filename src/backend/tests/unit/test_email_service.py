import logging

import httpx
import pytest

from app.core.config import settings
from app.services.email_service import send_password_reset_email


@pytest.fixture(autouse=True)
def _reset_resend_api_key(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", None)


class TestSendPasswordResetEmail:
    def test_logs_the_link_when_no_api_key_configured(self, caplog):
        with caplog.at_level(logging.WARNING):
            send_password_reset_email("user@example.com", "http://localhost:3000/reset-password?token=abc")

        assert "user@example.com" in caplog.text
        assert "token=abc" in caplog.text

    def test_sends_via_resend_when_api_key_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "resend_api_key", "fake-key")
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return httpx.Response(200, json={"id": "email-id"}, request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx, "post", fake_post)

        send_password_reset_email("user@example.com", "http://localhost:3000/reset-password?token=abc")

        assert captured["url"] == "https://api.resend.com/emails"
        assert captured["headers"]["Authorization"] == "Bearer fake-key"
        assert captured["json"]["to"] == ["user@example.com"]
        assert "token=abc" in captured["json"]["html"]

    def test_swallows_http_errors_without_raising(self, monkeypatch):
        monkeypatch.setattr(settings, "resend_api_key", "fake-key")

        def fake_post(*args, **kwargs):
            raise httpx.ConnectError("boom")

        monkeypatch.setattr(httpx, "post", fake_post)

        send_password_reset_email("user@example.com", "http://localhost:3000/reset-password?token=abc")

    def test_swallows_non_2xx_response_without_raising(self, monkeypatch):
        monkeypatch.setattr(settings, "resend_api_key", "fake-key")

        def fake_post(url, headers=None, json=None, timeout=None):
            request = httpx.Request("POST", url)
            return httpx.Response(500, json={"message": "server error"}, request=request)

        monkeypatch.setattr(httpx, "post", fake_post)

        send_password_reset_email("user@example.com", "http://localhost:3000/reset-password?token=abc")
