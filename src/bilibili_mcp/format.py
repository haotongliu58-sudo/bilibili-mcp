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


def _format_danmaku(items: list, limit: int = 200, with_timestamp: bool = False) -> str:
    if not items:
        return "该视频无弹幕。"
    ordered = sorted(items, key=lambda it: it.get("time", 0))
    header = f"共 {len(items)} 条弹幕（按出现时间，最多展示 {min(limit, len(items))} 条）："
    lines = []
    for it in ordered[:limit]:
        text = it.get("text", "")
        if with_timestamp:
            lines.append(f"[{_fmt_duration(it.get('time', 0))}] {text}")
        else:
            lines.append(text)
    return header + "\n" + "\n".join(lines)


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


_RISK_MARKERS = ("-412", "-799", "-352", "风控", "请求被拦截")


def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if any(m in msg for m in _RISK_MARKERS):
        return "被 B站临时限流了（风控），请过一会儿再试，或降低请求频率。"
    return f"调用 B站接口失败：{type(exc).__name__}: {msg}"


def no_credential_message() -> str:
    """Guidance shown when a login-gated tool runs without a configured cookie.

    Bilibili gates subtitle data behind login, so this tool needs the user's
    own SESSDATA. Video info and search still work as a guest.
    """
    return (
        "获取字幕需要登录态：B站已把字幕接口限制为登录用户。\n"
        "请在环境变量 BILI_SESSDATA 中填入你自己 B站账号的 SESSDATA cookie 后重试"
        "（仅在你本机使用、不会上传）。\n"
        "视频信息（get_video_info）和搜索（search_videos）无需登录，可直接使用。"
    )


def _format_hotwords(hotwords: list, segments: list, total: int) -> str:
    """Render hotword ranking + high-energy segments.

    hotwords: list of (text, count). segments: list of (start, end, count).
    """
    if total <= 0:
        return "该视频无弹幕。"
    lines = [f"共 {total} 条弹幕。", "", "🔥 高频弹幕："]
    for i, (text, count) in enumerate(hotwords, 1):
        lines.append(f"{i}. {text} ×{count}")
    if segments:
        lines += ["", "⚡ 高能时间段："]
        for start, end, count in segments:
            lines.append(
                f"{_fmt_duration(int(start))}–{_fmt_duration(int(end))} · {count} 条"
            )
    return "\n".join(lines)
