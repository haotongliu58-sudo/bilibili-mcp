"""Live end-to-end tests against the real Bilibili site.

Skipped by default; run with:  pytest -m live
Bilibili is reached directly (no proxy) — do not set HTTPS_PROXY.

These assert response *shape*, not exact content, so they stay stable. They use
asyncio.run() rather than pytest-asyncio to avoid an extra test dependency.
"""
import asyncio
import os

import pytest

from bilibili_mcp import server

pytestmark = pytest.mark.live

# A long-lived, popular video (verified to exist with danmaku + comments).
# Replace if it ever 404s.
_BVID = "BV1Jgf6YvE8e"


def test_live_search_returns_results():
    out = asyncio.run(server.search_videos("Python", limit=3))
    assert "BV" in out


def test_live_video_info():
    out = asyncio.run(server.get_video_info(_BVID))
    assert "标题：" in out


def test_live_danmaku_hotwords():
    out = asyncio.run(server.get_danmaku_hotwords(_BVID, top=5, segments=3))
    # Either real hotwords or the clean empty message — both are valid shapes.
    assert ("高频弹幕" in out) or ("无弹幕" in out)


def test_live_comments_guest():
    out = asyncio.run(server.get_video_comments(_BVID, sort="hot", limit=5))
    assert ("👤" in out) or ("暂无评论" in out)


def test_live_subtitle_without_credential_guides():
    # In CI / no-cookie env this returns the guidance message, not an error.
    if os.environ.get("BILI_SESSDATA", "").strip():
        pytest.skip("credential configured; guidance path not exercised")
    out = asyncio.run(server.get_video_subtitle(_BVID))
    assert "SESSDATA" in out
