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


def high_energy_segments(
    items: list, segments: int = 5, min_window: float = 10.0
) -> list:
    """Find the time windows with the most danmaku ("高能" moments).

    Bucket danmaku into windows sized adaptively to video length (so short and
    long videos both bucket sensibly), then return the densest `segments`
    windows as (start_sec, end_sec, count) tuples, descending by count.
    """
    times = [float(it.get("time", 0)) for it in items if (it.get("text") or "").strip()]
    if not times:
        return []
    duration = max(times)
    target_buckets = max(20.0, duration / 60.0)
    window = max(min_window, duration / target_buckets)
    buckets: Counter = Counter()
    for t in times:
        buckets[int(t // window)] += 1
    return [
        (idx * window, (idx + 1) * window, count)
        for idx, count in buckets.most_common(segments)
    ]
