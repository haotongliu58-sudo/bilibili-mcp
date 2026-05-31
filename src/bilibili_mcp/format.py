"""Pure formatting/parsing helpers. No network, no bilibili-api import."""
import re

_BV_RE = re.compile(r"(BV[0-9A-Za-z]{10})")


def extract_bvid(s: str) -> str:
    """Extract a BV id from a bare id or a full Bilibili video URL."""
    m = _BV_RE.search(s or "")
    if not m:
        raise ValueError(f"没找到 BV 号，请检查输入：{s!r}")
    return m.group(1)
