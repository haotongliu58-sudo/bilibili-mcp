# src/bilibili_mcp/bili.py
"""Thin async glue over bilibili-api. The only module importing bilibili-api.

Proxy policy: Bilibili is a domestic CN site; routing through this machine's
Clash system proxy (an overseas node) breaks or slows requests. So by default
we strip proxy env vars AND tell the underlying client to ignore the system
proxy (env vars + Windows registry, both controlled by httpx trust_env). Set
BILI_USE_PROXY=1 to opt back in (useful for overseas users).
"""
import os

import httpx
from bilibili_api import video, search, request_settings

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


async def fetch_video_info(bvid: str) -> dict:
    return await video.Video(bvid=bvid).get_info()


async def fetch_subtitle(bvid: str, lang: str = "zh-CN") -> list:
    v = video.Video(bvid=bvid)
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


async def fetch_search(keyword: str, page: int = 1) -> dict:
    return await search.search_by_type(
        keyword, search_type=search.SearchObjectType.VIDEO, page=page
    )
