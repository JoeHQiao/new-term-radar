"""可选的日报邮件：默认使用 Resend，RADAR_MAIL_PROVIDER=qq 时使用 QQ SMTP。

QQ 使用 SMTP_USERNAME、SMTP_PASSWORD（专用授权码）和 RADAR_EMAIL_TO。
Resend 保留 RESEND_API_KEY、EMAIL_FROM 和 RADAR_EMAIL_TO 的原有用法。
未配置收件人时跳过发送。HTML 正文需要 markdown 包。
"""
from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

from . import UA

# Inline styles: Gmail drops a <style> block that sits outside <head>, which leaves
# tables unbordered with centred headers. Every tag carries its own.
FONT = "-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif"
INLINE = {
    "h2": "font-size:18px;margin:0 0 12px;color:#1f2328",
    "h3": "font-size:15px;margin:24px 0 8px;color:#1f2328",
    "p": "margin:8px 0",
    "table": "border-collapse:collapse;margin:8px 0;width:100%",
    "th": "border:1px solid #d0d7de;padding:6px 10px;font-size:13px;background:#f6f8fa;text-align:left;white-space:nowrap",
    "td": "border:1px solid #d0d7de;padding:6px 10px;font-size:13px;vertical-align:top",
    "ul": "padding-left:0;margin:8px 0;list-style:none",
    "li": "margin:0 0 10px;padding:8px 12px;border-left:3px solid #d0d7de;background:#f6f8fa;font-size:13px",
    "a": "color:#0969da",
}
TAG = re.compile(r"<(" + "|".join(INLINE) + r")(\s[^>]*)?>")
_ADDRESS = re.compile(r"^[^@\s<>\"']+@[^@\s<>\"']+\.[a-z]{2,}$", re.I)


def _inline(m: re.Match) -> str:
    attrs = m.group(2) or ""
    if m.group(1) == "td" and 'style="text-align' in attrs:   # markdown's own column alignment
        return f"<td{attrs}>"
    return f'<{m.group(1)} style="{INLINE[m.group(1)]}"{attrs}>'


def html(md_text: str) -> str:
    import markdown
    body = TAG.sub(_inline, markdown.markdown(md_text, extensions=["tables"]))
    return f'<div style="font:14px/1.6 {FONT};color:#1f2328;max-width:900px">{body}</div>'


def recipients(raw: str) -> list[str]:
    """RADAR_EMAIL_TO as people type it: commas (also full-width), semicolons or spaces
    between addresses; quotes and angle brackets around them are dropped."""
    parts = re.split(r"[,，;；\s]+", raw.strip().strip("\"'"))
    return [p.strip("\"'<>") for p in parts if p.strip("\"'<>")]


def _send_qq(subject: str, md_text: str, to: list[str]) -> str:
    """通过 QQ 的 SSL SMTP 发送日报；授权码仅从环境变量读取。"""
    required = ("SMTP_USERNAME", "SMTP_PASSWORD")
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        return "邮件未发送：缺少 " + "、".join(missing)
    username = os.environ["SMTP_USERNAME"].strip()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = username
    message["To"] = ", ".join(to)
    message.set_content(md_text)
    message.add_alternative(html(md_text), subtype="html")
    smtp = None
    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30, context=ssl.create_default_context())
        smtp.login(username, os.environ["SMTP_PASSWORD"].strip())
        refused = smtp.send_message(message, from_addr=username, to_addrs=to)
        if refused:
            raise SystemExit("QQ 邮件发送失败：部分收件地址被拒绝，请检查邮箱设置。")
    except (smtplib.SMTPException, OSError) as exc:
        # 服务端响应可能包含账号信息，日志仅保留异常类型。
        raise SystemExit(f"QQ 邮件发送失败（{type(exc).__name__}），请检查 SMTP 授权码、邮箱设置或网络。") from None
    finally:
        if smtp is not None:
            try:
                # 以 DATA 接受结果为准，关闭连接的异常不改变已提交状态。
                smtp.close()
            except OSError:
                pass
    return "邮件已提交至 QQ SMTP，最终送达以收件箱为准。"


def send(subject: str, md_text: str) -> str:
    to = recipients(os.environ.get("RADAR_EMAIL_TO", ""))
    if not to:
        return "mail skipped: RADAR_EMAIL_TO not set"
    bad = [i + 1 for i, a in enumerate(to) if not _ADDRESS.match(a)]
    if bad:   # the address itself stays out of the log
        raise SystemExit(f"RADAR_EMAIL_TO: {len(to)} address(es), number {bad} is not an email address")
    if os.environ.get("RADAR_MAIL_PROVIDER") == "qq":
        return _send_qq(subject, md_text, to)
    body = json.dumps({"from": os.environ["EMAIL_FROM"], "to": to, "subject": subject, "html": html(md_text)}).encode()
    # Resend sits behind Cloudflare, which answers Python's default User-Agent with 403 "error code: 1010".
    req = urllib.request.Request("https://api.resend.com/emails", data=body, method="POST", headers={
        "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}", "Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return f"mail sent ({res.status})"
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Resend {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}") from exc
