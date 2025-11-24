"""Email sender using macOS local MTA (sendmail)."""

import os
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import markdown


# CSS for email-friendly HTML
EMAIL_CSS = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        background-color: #f5f5f5;
    }
    .content {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1, h2, h3 {
        color: #1a1a1a;
        margin-top: 24px;
        margin-bottom: 16px;
    }
    h1 {
        font-size: 28px;
        border-bottom: 2px solid #e1e4e8;
        padding-bottom: 8px;
    }
    h2 {
        font-size: 24px;
        border-bottom: 1px solid #e1e4e8;
        padding-bottom: 6px;
    }
    h3 {
        font-size: 20px;
    }
    ul, ol {
        margin: 16px 0;
        padding-left: 32px;
    }
    li {
        margin: 8px 0;
    }
    strong {
        color: #0366d6;
        font-weight: 600;
    }
    code {
        background-color: #f6f8fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
        font-size: 85%;
    }
    pre {
        background-color: #f6f8fa;
        padding: 16px;
        border-radius: 6px;
        overflow-x: auto;
        border: 1px solid #e1e4e8;
    }
    pre code {
        background-color: transparent;
        padding: 0;
    }
    a {
        color: #0366d6;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    blockquote {
        margin: 16px 0;
        padding: 0 16px;
        border-left: 4px solid #dfe2e5;
        color: #6a737d;
    }
    .meta {
        color: #666;
        font-size: 14px;
        margin-bottom: 20px;
        padding: 10px;
        background-color: #f6f8fa;
        border-radius: 4px;
    }
</style>
"""


def markdown_to_html(markdown_text: str) -> str:
    """
    Convert markdown to email-friendly HTML with inline styling.

    Args:
        markdown_text: Markdown content

    Returns:
        HTML string with inline CSS
    """
    # Convert markdown to HTML
    html_content = markdown.markdown(
        markdown_text,
        extensions=['extra', 'nl2br', 'sane_lists']
    )

    # Wrap in styled container
    full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {EMAIL_CSS}
</head>
<body>
    <div class="content">
        {html_content}
    </div>
</body>
</html>
"""

    return full_html


def send_email(
    markdown_content: str,
    subject: str,
    recipient: Optional[str] = None,
    sender: Optional[str] = None
):
    """
    Send markdown content as email using macOS sendmail.

    Args:
        markdown_content: Markdown text to send
        subject: Email subject line
        recipient: Email recipient (defaults to EMAIL_RECIPIENT env var or current user)
        sender: Email sender (defaults to EMAIL_SENDER env var or current user@hostname)

    Environment variables:
        EMAIL_RECIPIENT: Default recipient email address
        EMAIL_SENDER: Default sender email address

    Raises:
        RuntimeError: If sendmail fails
    """
    # Get recipient and sender
    if recipient is None:
        recipient = os.getenv("EMAIL_RECIPIENT")
        if not recipient:
            # Default to current user
            recipient = os.getenv("USER", "user") + "@localhost"

    if sender is None:
        sender = os.getenv("EMAIL_SENDER")
        if not sender:
            # Default to current user@hostname
            import socket
            hostname = socket.gethostname()
            sender = f"{os.getenv('USER', 'user')}@{hostname}"

    # Create MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[YT Transcribe] {subject}"
    msg["From"] = sender
    msg["To"] = recipient

    # Plain text version (strip markdown formatting loosely)
    plain_text = markdown_content

    # HTML version
    html_content = markdown_to_html(markdown_content)

    # Attach both versions
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    # Send via sendmail
    try:
        sendmail_path = "/usr/sbin/sendmail"
        if not os.path.exists(sendmail_path):
            raise RuntimeError("sendmail not found at /usr/sbin/sendmail")

        process = subprocess.Popen(
            [sendmail_path, "-t", "-oi"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = process.communicate(msg.as_bytes())

        if process.returncode != 0:
            raise RuntimeError(f"sendmail failed with code {process.returncode}: {stderr.decode()}")

    except Exception as e:
        raise RuntimeError(f"Failed to send email: {e}") from e
