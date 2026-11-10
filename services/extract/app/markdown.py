from collections import Counter

H1_SIZE_RATIO = 1.5
H2_SIZE_RATIO = 1.2


def _span_sizes(block: dict) -> list[tuple[float, int]]:
    return [
        (round(span["size"], 1), len(span["text"].strip()))
        for line in block.get("lines", [])
        for span in line["spans"]
        if span["text"].strip()
    ]


def _body_font_size(blocks: list[dict]) -> float:
    chars_by_size: Counter[float] = Counter()
    for block in blocks:
        for size, chars in _span_sizes(block):
            chars_by_size[size] += chars
    return chars_by_size.most_common(1)[0][0] if chars_by_size else 0.0


def _to_markdown(block: dict, text: str, body_size: float) -> str:
    sizes = [size for size, _ in _span_sizes(block)]
    ratio = max(sizes) / body_size if sizes and body_size else 0
    if ratio >= H1_SIZE_RATIO:
        return "# " + text.replace("\n", " ")
    if ratio >= H2_SIZE_RATIO:
        return "## " + text.replace("\n", " ")
    return text


def format_markdown(blocks: list[dict], texts: list[list[str]]) -> str:
    body_size = _body_font_size(blocks)
    return "\n\n".join(
        _to_markdown(block, text, body_size)
        for block, rows in zip(blocks, texts, strict=True)
        for text in rows
    )
