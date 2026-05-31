"""Pure formatting/parsing helpers. No network, no bilibili-api import."""
import re

_BV_RE = re.compile(r"(BV[0-9A-Za-z]{10})")


def extract_bvid(s: str) -> str:
    """Extract a BV id from a bare id or a full Bilibili video URL."""
    m = _BV_RE.search(s or "")
    if not m:
        raise ValueError(f"没找到 BV 号，请检查输入：{s!r}")
    return m.group(1)


from datetime import datetime, timezone, timedelta

_CN_TZ = timezone(timedelta(hours=8))


def _fmt_duration(sec: int) -> str:
    m, s = divmod(int(sec or 0), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _format_video_info(raw: dict) -> str:
    stat = raw.get("stat", {}) or {}
    owner = raw.get("owner", {}) or {}
    pub = raw.get("pubdate")
    pub_str = (
        datetime.fromtimestamp(pub, _CN_TZ).strftime("%Y-%m-%d") if pub else "未知"
    )
    desc = (raw.get("desc") or "").strip() or "（无）"
    return "\n".join([
        f"标题：{raw.get('title', '')}",
        f"UP主：{owner.get('name', '')}",
        f"分区：{raw.get('tname', '')}",
        f"时长：{_fmt_duration(raw.get('duration', 0))}",
        f"发布：{pub_str}",
        f"播放：{stat.get('view', 0)}  点赞：{stat.get('like', 0)}  投币：{stat.get('coin', 0)}",
        f"简介：{desc}",
        f"BV号：{raw.get('bvid', '')}",
    ])


def _format_subtitle(items: list, with_timestamp: bool = False) -> str:
    if not items:
        return "该视频无字幕（UP主未上传，且无 AI 字幕）。"
    if with_timestamp:
        return "\n".join(
            f"[{_fmt_duration(it.get('from', 0))}] {it.get('content', '')}"
            for it in items
        )
    return " ".join(it.get("content", "") for it in items)


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(s: str) -> str:
    return _TAG_RE.sub("", s or "")


def _format_search(raw: dict, limit: int = 10) -> str:
    results = (raw or {}).get("result") or []
    if not results:
        return "没有搜到相关视频。"
    lines = []
    for i, r in enumerate(results[:limit], 1):
        lines.append(
            f"{i}. {_strip_tags(r.get('title', ''))}\n"
            f"   UP主：{r.get('author', '')}  播放：{r.get('play', '')}  "
            f"时长：{r.get('duration', '')}  BV号：{r.get('bvid', '')}"
        )
    return "\n".join(lines)
