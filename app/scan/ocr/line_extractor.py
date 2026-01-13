def extract_lines(document) -> list[str]:
    lines: list[str] = []

    for page in document.pages:
        for line in page.lines:
            text = _get_text(document, line.layout.text_anchor)
            if text:
                lines.append(text.strip())

    return lines


def _get_text(document, anchor):
    text = ""
    for seg in anchor.text_segments:
        start = seg.start_index or 0
        end = seg.end_index
        text += document.text[start:end]
    return text.strip()
