"""Telegram sender with PDF support for long messages."""

import asyncio
import html
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from telegram import Bot
from telegram.constants import ParseMode

from .config import TELEGRAM_CHAR_LIMIT, get_telegram_chat_id, get_telegram_token


def markdown_to_pdf(markdown_content: str, output_path: str, title: str):
    """
    Convert markdown to PDF using reportlab.

    Args:
        markdown_content: Markdown text
        output_path: Path to save PDF
        title: Document title
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='#1a1a1a',
        spaceAfter=30,
    )

    # Custom heading styles
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='#1a1a1a',
        spaceAfter=12,
    )

    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#333333',
        spaceAfter=10,
    )

    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor='#333333',
        spaceAfter=8,
    )

    # Body text style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        leading=16,
        textColor='#333333',
    )

    # Parse markdown line by line
    lines = markdown_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            elements.append(Spacer(1, 0.1 * inch))
            i += 1
            continue

        # Headers
        if line.startswith('# '):
            text = line[2:].strip()
            elements.append(Paragraph(text, h1_style))
            elements.append(Spacer(1, 0.2 * inch))
        elif line.startswith('## '):
            text = line[3:].strip()
            elements.append(Paragraph(text, h2_style))
            elements.append(Spacer(1, 0.15 * inch))
        elif line.startswith('### '):
            text = line[4:].strip()
            elements.append(Paragraph(text, h3_style))
            elements.append(Spacer(1, 0.1 * inch))
        # Bullet points
        elif line.startswith('- ') or line.startswith('* '):
            text = line[2:].strip()
            # Handle bold
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
            # Handle italic
            text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
            text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
            # Handle links
            text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)

            elements.append(Paragraph(f'• {text}', body_style))
        # Regular paragraph
        else:
            text = line
            # Handle bold
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
            # Handle italic
            text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
            text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
            # Handle links
            text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)

            elements.append(Paragraph(text, body_style))

        i += 1

    # Build PDF
    doc.build(elements)


async def _send_to_telegram_async(
    markdown_content: str,
    source_file: str,
    title: str,
    bot_token: str,
    chat_id: str
):
    """
    Internal async function to send content to Telegram.

    Args:
        markdown_content: Markdown text to send
        source_file: Path to source markdown file (for reference)
        title: Title for the message/document
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
    """
    bot = Bot(token=bot_token)

    formatted_text = format_markdown_for_telegram(markdown_content)

    # Check message length (use formatted text length)
    if len(formatted_text) <= TELEGRAM_CHAR_LIMIT:
        # Send as text message with HTML formatting
        await bot.send_message(
            chat_id=chat_id,
            text=formatted_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
    else:
        # Content too long - convert to PDF and send as document
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name

        try:
            markdown_to_pdf(markdown_content, pdf_path, title)

            # Send PDF document
            with open(pdf_path, "rb") as pdf_file:
                await bot.send_document(
                    chat_id=chat_id,
                    document=pdf_file,
                    filename=f"{title[:50]}.pdf",  # Limit filename length
                    caption=f"Summary too long for message ({len(markdown_content)} chars), sent as PDF"
                )
        finally:
            # Clean up temp file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)


def send_to_telegram(
    markdown_content: str,
    source_file: str,
    title: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None
):
    """
    Send content to Telegram as text or PDF (if too long).

    If the markdown content is under TELEGRAM_CHAR_LIMIT characters, it will be sent
    as a formatted text message. Otherwise, it will be converted to PDF and sent
    as a document.

    Args:
        markdown_content: Markdown text to send
        source_file: Path to source markdown file (for reference)
        title: Title for the message/document
        bot_token: Telegram bot token (defaults to TELEGRAM_BOT_TOKEN env var)
        chat_id: Telegram chat ID (defaults to TELEGRAM_CHAT_ID env var)

    Environment variables:
        TELEGRAM_BOT_TOKEN: Bot token from @BotFather
        TELEGRAM_CHAT_ID: Chat ID to send messages to

    Raises:
        RuntimeError: If Telegram send fails
    """
    # Get credentials from config or environment
    if bot_token is None:
        bot_token = get_telegram_token()
        if not bot_token:
            raise RuntimeError("Telegram bot token not configured (set in ~/.config/yt-transcribe/config.toml or TELEGRAM_BOT_TOKEN env var)")

    if chat_id is None:
        chat_id = get_telegram_chat_id()
        if not chat_id:
            raise RuntimeError("Telegram chat ID not configured (set in ~/.config/yt-transcribe/config.toml or TELEGRAM_CHAT_ID env var)")

    try:
        asyncio.run(_send_to_telegram_async(
            markdown_content=markdown_content,
            source_file=source_file,
            title=title,
            bot_token=bot_token,
            chat_id=chat_id
        ))
    except Exception as e:
        raise RuntimeError(f"Failed to send to Telegram: {e}") from e


def format_markdown_for_telegram(markdown_content: str) -> str:
    """Convert basic markdown to Telegram-compatible HTML."""
    lines = markdown_content.splitlines()
    formatted_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted_lines.append("")
            continue

        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip()
            formatted_lines.append(f"<b>{html.escape(heading_text)}</b>")
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet_match:
            content = bullet_match.group(1)
            formatted_lines.append(f"- {_format_inline_html(content)}")
            continue

        formatted_lines.append(_format_inline_html(stripped))

    return "\n".join(formatted_lines)


def _format_inline_html(text: str) -> str:
    """Format bold markdown segments into Telegram HTML."""
    bold_segments: list[str] = []

    def replace_bold(match: re.Match[str]) -> str:
        content = match.group(1) or match.group(2)
        bold_segments.append(content)
        return f"CODEXBOLDTOKEN{len(bold_segments) - 1}"

    text = re.sub(r"\*\*(.+?)\*\*", replace_bold, text)
    text = re.sub(r"__(.+?)__", replace_bold, text)

    escaped = html.escape(text)
    for idx, content in enumerate(bold_segments):
        token = f"CODEXBOLDTOKEN{idx}"
        bold_text = html.escape(content)
        escaped = escaped.replace(token, f"<b>{bold_text}</b>")

    return escaped
