"""Pure danmaku aggregation. No network, no bilibili-api, no formatting."""
from collections import Counter


def count_hotwords(items: list, top: int = 20) -> list:
    """Rank danmaku by exact-string frequency.

    Bilibili memes are spammed verbatim, so counting identical strings surfaces
    them without word segmentation. Returns up to `top` (text, count) pairs,
    descending by count. Whitespace is trimmed; blanks are dropped.
    """
    counter: Counter = Counter()
    for it in items:
        text = (it.get("text") or "").strip()
        if text:
            counter[text] += 1
    return counter.most_common(top)
