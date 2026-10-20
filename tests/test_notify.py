"""QQ 邮件的凭证、加密连接、中文正文和失败日志检查；不访问网络。"""
import smtplib
import ssl

import pytest

from radar import notify


@pytest.fixture
def qq_env(monkeypatch):
    monkeypatch.setenv("RADAR_MAIL_PROVIDER", "qq")
    monkeypatch.setenv("SMTP_USERNAME", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "test-authorization-code")
    monkeypatch.setenv("RADAR_EMAIL_TO", "reader@example.com")


def test_qq_sends_chinese_text_and_html_with_verified_tls(qq_env, monkeypatch):
    calls = {}

    class SMTP:
        def __init__(self, host, port, *, timeout, context):
            calls["connection"] = (host, port, timeout, context)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def close(self):
            calls["closed"] = True

        def login(self, username, password):
            calls["login"] = (username, password)

        def send_message(self, message, *, from_addr, to_addrs):
            calls["message"] = (message, from_addr, to_addrs)
            return {}

    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP)
    body = "## 中文日报\n\n| 词 | 信号 |\n|---|---|\n| 新工具 | 新增 |\n"
    result = notify.send("新词雷达日报 · 2026-10-20", body)
    host, port, timeout, context = calls["connection"]
    assert (host, port, timeout) == ("smtp.qq.com", 465, 30)
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    assert calls["login"] == ("sender@example.com", "test-authorization-code")
    message, sender, to = calls["message"]
    assert sender == "sender@example.com" and to == ["reader@example.com"]
    assert message["Subject"] == "新词雷达日报 · 2026-10-20"
    assert message.get_body(preferencelist=("plain",)).get_content().strip() == body.strip()
    rendered = message.get_body(preferencelist=("html",)).get_content()
    assert "中文日报" in rendered and "<table style=" in rendered
    assert "邮件已提交" in result
    assert calls["closed"]


@pytest.mark.parametrize("missing", ["SMTP_USERNAME", "SMTP_PASSWORD"])
def test_qq_missing_credentials_never_connects(qq_env, monkeypatch, missing):
    monkeypatch.delenv(missing)
    monkeypatch.setattr(smtplib, "SMTP_SSL", lambda *a, **k: pytest.fail("缺少凭证时不应连接网络"))
    result = notify.send("日报", "内容")
    assert result.startswith("邮件未发送") and missing in result


@pytest.mark.parametrize("failure", ["login", "send"])
def test_qq_failures_do_not_disclose_server_response_or_credentials(qq_env, monkeypatch, failure):
    secret = "test-authorization-code"

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def close(self):
            pass

        def login(self, *args):
            if failure == "login":
                raise smtplib.SMTPAuthenticationError(535, secret.encode())

        def send_message(self, *args, **kwargs):
            raise smtplib.SMTPDataError(554, secret.encode())

    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP)
    with pytest.raises(SystemExit) as error:
        notify.send("日报", "内容")
    assert "QQ 邮件发送失败" in str(error.value)
    assert secret not in str(error.value)


def test_qq_partial_recipient_rejection_is_not_reported_as_success(qq_env, monkeypatch):
    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def close(self):
            pass

        def login(self, *args):
            pass

        def send_message(self, *args, **kwargs):
            return {"reader@example.com": (550, b"rejected")}

    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP)
    with pytest.raises(SystemExit, match="部分收件地址被拒绝"):
        notify.send("日报", "内容")


def test_qq_accepted_message_stays_successful_when_cleanup_fails(qq_env, monkeypatch):
    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            raise smtplib.SMTPResponseException(-1, b"unexpected quit response")

        def login(self, *args):
            pass

        def send_message(self, *args, **kwargs):
            return {}

        def close(self):
            raise OSError("connection already closed")

    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP)
    assert "邮件已提交" in notify.send("日报", "内容")
