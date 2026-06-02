# src/bilibili_mcp/bili.py
"""Thin async glue over bilibili-api. The only module importing bilibili-api.

Proxy policy: Bilibili is a domestic CN site; routing through this machine's
Clash system proxy (an overseas node) breaks or slows requests. So by default
we strip proxy env vars AND tell the underlying client to ignore the system
proxy (env vars + Windows registry, both controlled by httpx trust_env). Set
BILI_USE_PROXY=1 to opt back in (useful for overseas users).

Auth policy: video info and search work as a guest (no login). Subtitles are
gated behind login by Bilibili, so they require the user's own SESSDATA cookie,
supplied via the BILI_SESSDATA env var. Without it, the subtitle tool returns
friendly guidance instead of failing. Optional companions: BILI_BILI_JCT,
BILI_BUVID3, BILI_DEDEUSERID (rarely needed for read-only subtitle access).
"""
import os

import httpx
from bilibili_api import video, search, comment, request_settings, Credential

_USE_PROXY = os.environ.get("BILI_USE_PROXY", "") not in ("", "0", "false", "False")


def _configure_proxy() -> None:
    # Pick up a guest buvid3 automatically (public read, no login).
    try:
        request_settings.set_enable_auto_buvid(True)
    except Exception:
        pass
    if _USE_PROXY:
        # Overseas user: let httpx read the system/env proxy.
        try:
            request_settings.set_trust_env(True)
        except Exception:
            pass
        return
    # Default: direct connection. Strip proxy env vars and tell the underlying
    # httpx client to ignore the system proxy (env + Windows registry).
    for v in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(v, None)
    try:
        request_settings.set_trust_env(False)
    except Exception:
        pass
    try:
        request_settings.set_proxy("")
    except Exception:
        pass


_configure_proxy()


def _load_credential():
    """Build a Credential from env vars, or return None if no SESSDATA set."""
    sessdata = os.environ.get("BILI_SESSDATA", "").strip()
    if not sessdata:
        return None
    return Credential(
        sessdata=sessdata,
        bili_jct=os.environ.get("BILI_BILI_JCT", "").strip() or None,
        buvid3=os.environ.get("BILI_BUVID3", "").strip() or None,
        dedeuserid=os.environ.get("BILI_DEDEUSERID", "").strip() or None,
    )


def has_credential() -> bool:
    """True if a SESSDATA cookie is configured (subtitles available)."""
    return bool(os.environ.get("BILI_SESSDATA", "").strip())


async def fetch_video_info(bvid: str) -> dict:
    return await video.Video(bvid=bvid).get_info()


async def fetch_subtitle(bvid: str, lang: str = "zh-CN") -> list:
    """Fetch subtitle lines. Requires a configured credential (SESSDATA)."""
    v = video.Video(bvid=bvid, credential=_load_credential())
    cid = await v.get_cid(0)
    data = await v.get_subtitle(cid)
    subs = data.get("subtitles", []) if isinstance(data, dict) else []
    if not subs:
        return []
    chosen = next((s for s in subs if s.get("lan") == lang), subs[0])
    url = chosen.get("subtitle_url", "") or ""
    if url.startswith("//"):
        url = "https:" + url
    if not url:
        return []
    async with httpx.AsyncClient(trust_env=_USE_PROXY) as client:
        r = await client.get(url, timeout=20)
    return r.json().get("body", [])


async def fetch_danmaku(bvid: str) -> list:
    """Fetch danmaku (bullet comments) as plain dicts. Works as a guest.

    Unlike subtitles, danmaku are public and need no login. Returns a list of
    {"text": str, "time": float} where time is the second the comment appears.
    """
    v = video.Video(bvid=bvid)
    cid = await v.get_cid(0)
    dms = await v.get_danmakus(0, cid=cid)
    return [{"text": d.text, "time": float(d.dm_time)} for d in dms]


async def fetch_search(keyword: str, page: int = 1) -> dict:
    return await search.search_by_type(
        keyword, search_type=search.SearchObjectType.VIDEO, page=page
    )


async def fetch_comments(bvid: str, sort: str = "hot", limit: int = 20) -> list:
    """Fetch top-level video comments as raw reply dicts. Works as a guest.

    sort: "hot" (by likes) or "time" (newest). Pages until `limit` is reached.
    """
    if sort == "hot":
        order = comment.OrderType.LIKE
    elif sort == "time":
        order = comment.OrderType.TIME
    else:
        raise ValueError(f"sort 只能是 'hot' 或 'time'，收到：{sort!r}")
    aid = video.Video(bvid=bvid).get_aid()
    out: list = []
    page = 1
    while len(out) < limit:
        data = await comment.get_comments(
            int(aid), comment.CommentResourceType.VIDEO, page, order
        )
        replies = (data or {}).get("replies") or []
        if not replies:
            break
        out.extend(replies)
        page += 1
    return out[:limit]
