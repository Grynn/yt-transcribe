"""Telegram sender with PDF support for long messages."""

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

from .config import TELEGRAM_CHAR_LIMIT


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
    # Get credentials
    if bot_token is None:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable not set")

    if chat_id is None:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not chat_id:
            raise RuntimeError("TELEGRAM_CHAT_ID environment variable not set")

    try:
        bot = Bot(token=bot_token)

        # Check message length
        if len(markdown_content) <= TELEGRAM_CHAR_LIMIT:
            # Send as text message with markdown formatting
            bot.send_message(
                chat_id=chat_id,
                text=markdown_content,
                parse_mode=ParseMode.MARKDOWN_V2,
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
                    bot.send_document(
                        chat_id=chat_id,
                        document=pdf_file,
                        filename=f"{title[:50]}.pdf",  # Limit filename length
                        caption=f"Summary too long for message ({len(markdown_content)} chars), sent as PDF"
                    )
            finally:
                # Clean up temp file
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

    except Exception as e:
        raise RuntimeError(f"Failed to send to Telegram: {e}") from e


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
