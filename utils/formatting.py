from __future__ import annotations

import html
import re
from typing import List, Tuple, Dict

MAX_TELEGRAM_CHARS = 4096
SAFE_LIMIT = 3800  # небольшой запас


def _split_markdown_code_blocks(text: str) -> List[dict]:
    """
    Разбивает текст на сегменты вида {type: 'code'|'text', content: str} по тройным бэктикам.
    Язык после ``` игнорируем, всё внутри блока не трогаем.
    """
    segments: List[dict] = []
    code_fence_pattern = re.compile(r"```(.*?)```", re.DOTALL)

    last_idx = 0
    for m in code_fence_pattern.finditer(text):
        # текст до блока
        if m.start() > last_idx:
            segments.append({"type": "text", "content": text[last_idx:m.start()]})
        code_content = m.group(1)
        # Если указан язык в первой строке – срежем его
        if "\n" in code_content:
            first_line, rest = code_content.split("\n", 1)
            # если first_line выглядит как язык (без пробелов) – отбросим
            if len(first_line.strip()) > 0 and " " not in first_line.strip():
                code_content = rest
        segments.append({"type": "code", "content": code_content})
        last_idx = m.end()

    # хвост
    if last_idx < len(text):
        segments.append({"type": "text", "content": text[last_idx:]})

    return segments


def _format_text_segment_to_html(text: str) -> str:
    """
    Базовый markdown -> HTML для Telegram:
    - Заголовки ### ... -> <b>...</b>
    - **bold** -> <b>...</b>
    - *italic* -> <i>...</i>
    - Инлайн-код `...` -> <code>...</code>
    - Буллеты (- или *) в начале строки -> символ •

    Реализация через плейсхолдеры, чтобы корректно экранировать остальной текст.
    """
    raw = html.unescape(text)

    # 1) Инлайн-код -> плейсхолдеры
    code_placeholders: Dict[str, str] = {}
    def repl_code(m: re.Match) -> str:
        idx = len(code_placeholders)
        key = f"§CODE{idx}§"
        # содержимое кода экранируем отдельно
        code_escaped = html.escape(m.group(1))
        code_placeholders[key] = f"<code>{code_escaped}</code>"
        return key
    raw = re.sub(r"`([^`\n]+)`", repl_code, raw)

    # 2) Заголовки (### .../## .../# ...)
    def repl_heading(line: str) -> str:
        m = re.match(r"^\s{0,3}(#{1,6})\s+(.*)$", line)
        if not m:
            return line
        content = m.group(2)
        return f"§B§{content}§/B§"

    lines = raw.split("\n")
    lines = [repl_heading(ln) for ln in lines]
    raw = "\n".join(lines)

    # 3) Буллеты в начале строки -> •
    raw = re.sub(r"^\s*[-*]\s+", "• ", raw, flags=re.MULTILINE)

    # 4) Жирный и курсив -> плейсхолдеры
    bold_placeholders: Dict[str, str] = {}
    italic_placeholders: Dict[str, str] = {}

    def repl_bold(m: re.Match) -> str:
        idx = len(bold_placeholders)
        key = f"§B{idx}§"
        bold_placeholders[key] = m.group(1)
        return f"§B§{key}§/B§"

    def repl_italic(m: re.Match) -> str:
        idx = len(italic_placeholders)
        key = f"§I{idx}§"
        italic_placeholders[key] = m.group(1)
        return f"§I§{key}§/I§"

    # Сначала жирный, затем курсив
    raw = re.sub(r"\*\*([^*]+)\*\*", repl_bold, raw)
    raw = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", repl_italic, raw)

    # 5) Экранируем весь текст
    escaped_all = html.escape(raw)

    # 6) Восстанавливаем плейсхолдеры жирного/курсива и инлайн-кода
    # Жирный: §B§<key>§/B§ -> <b>escaped(content)</b>
    def restore_bold(m: re.Match) -> str:
        key = m.group(1)
        content = bold_placeholders.get(key, "")
        return f"<b>{html.escape(content)}</b>"

    def restore_italic(m: re.Match) -> str:
        key = m.group(1)
        content = italic_placeholders.get(key, "")
        return f"<i>{html.escape(content)}</i>"

    escaped_all = re.sub(r"§B§(§B\d+§)§/B§", restore_bold, escaped_all)
    escaped_all = re.sub(r"§I§(§I\d+§)§/I§", restore_italic, escaped_all)

    # Заголовки: §B§(content)§/B§
    def restore_heading(m: re.Match) -> str:
        content = m.group(1)
        return f"<b>{content}</b>"
    escaped_all = re.sub(r"§B§([^§]+)§/B§", restore_heading, escaped_all)

    # Инлайн-код
    for key, html_fragment in code_placeholders.items():
        escaped_all = escaped_all.replace(html.escape(key), html_fragment)

    return escaped_all


def _split_text_raw(text: str, max_len: int) -> List[str]:
    """Грубое разбиение сырого текста на части <= max_len: по абзацам, строкам, затем по длине."""
    parts: List[str] = []
    for paragraph in re.split(r"\n\n+", text):
        if not paragraph:
            continue
        if len(paragraph) <= max_len:
            parts.append(paragraph)
        else:
            # по строкам
            lines = paragraph.split("\n")
            buf = ""
            for line in lines:
                if len(buf) + len(line) + 1 <= max_len:
                    buf = f"{buf}\n{line}" if buf else line
                else:
                    if buf:
                        parts.append(buf)
                    # если строка больше лимита — режем по длине
                    while len(line) > max_len:
                        parts.append(line[:max_len])
                        line = line[max_len:]
                    buf = line
            if buf:
                parts.append(buf)
    return parts if parts else [text]


def _ensure_piece_fits_html(raw_text: str, limit: int) -> List[str]:
    """Конвертирует сырой текст в HTML с инлайн-кодом. Если результат > limit, делит сырой текст и конвертирует части отдельно."""
    html_text = _format_text_segment_to_html(raw_text)
    if len(html_text) <= limit:
        return [html_text]
    # делим сырой текст пополам и рекурсивно применяем
    mid = max(1, len(raw_text) // 2)
    left = raw_text[:mid]
    right = raw_text[mid:]
    return _ensure_piece_fits_html(left, limit) + _ensure_piece_fits_html(right, limit)


def format_response_html_chunks(text: str, chunk_limit: int = SAFE_LIMIT) -> List[str]:
    """
    Форматирует исходный markdown-подобный ответ модели в HTML и режет на чанки.
    Гарантирует, что каждый чанк содержит валидный HTML Telegram (сбалансированные теги),
    не режет внутри <pre><code>...</code></pre> и инлайн-кода.
    """
    segments = _split_markdown_code_blocks(text)

    # Сначала превращаем сегменты в список HTML-«кусочков», каждый <= chunk_limit
    pieces: List[str] = []

    for seg in segments:
        if seg["type"] == "code":
            code_text = seg["content"]
            # учтём накладные расходы тегов
            overhead = len("<pre><code></code></pre>")
            max_payload = max(1, chunk_limit - overhead)
            while code_text:
                sub = code_text[:max_payload]
                code_text = code_text[max_payload:]
                pieces.append(f"<pre><code>{html.escape(sub)}</code></pre>")
        else:
            # сырой текст режем на небольшие кусочки, затем гарантируем попадание в лимит после конверсии
            raw_parts = _split_text_raw(seg["content"], chunk_limit - 50)
            for raw in raw_parts:
                pieces.extend(_ensure_piece_fits_html(raw, chunk_limit))

    # Теперь собираем итоговые чанки из маленьких HTML-писов
    chunks: List[str] = []
    current = ""
    for p in pieces:
        if len(current) + len(p) + (1 if current else 0) <= chunk_limit:
            current = f"{current}\n{p}" if current else p
        else:
            if current:
                chunks.append(current)
            current = p
    if current:
        chunks.append(current)

    return chunks if chunks else [html.escape(text)]

