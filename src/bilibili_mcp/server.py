# src/bilibili_mcp/server.py
"""bilibili-mcp: read public Bilibili data from any MCP client.

    AI client (Claude / Cursor / ...) --MCP--> bilibili-mcp --HTTP--> Bilibili

Thin protocol layer. Volatile bilibili-api calls live in `bili.py`; pure
formatting lives in `format.py`. Tools here are glue.
"""
from mcp.server.fastmcp import FastMCP

from . import bili
from . import analyze
from .format import (
    extract_bvid,
    _format_video_info,
    _format_subtitle,
    _format_search,
    _format_danmaku,
    _format_hotwords,
    _friendly_error,
    no_credential_message,
)

mcp = FastMCP("bilibili-mcp")


@mcp.tool()
async def get_video_info(bvid: str) -> str:
    """Get basic info for a Bilibili video.

    Args:
        bvid: A BV id (e.g. "BV1xx411c7mD") or a full video URL.

    Returns:
        Title, uploader, stats, duration, publish date, description.
    """
    try:
        raw = await bili.fetch_video_info(extract_bvid(bvid))
        return _format_video_info(raw)
    except ValueError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001 - surface as readable text
        return _friendly_error(e)


@mcp.tool()
async def get_video_subtitle(
    bvid: str, lang: str = "zh-CN", with_timestamp: bool = False
) -> str:
    """Get the full subtitle/transcript text of a Bilibili video.

    Useful for asking the AI to summarize a video. Bilibili gates subtitles
    behind login, so this needs a SESSDATA cookie in the BILI_SESSDATA env var
    (see README); without it, guidance is returned. Returns a clear message
    when the video simply has no subtitles.

    Args:
        bvid: A BV id or full video URL.
        lang: Subtitle language code. Default "zh-CN".
        with_timestamp: Prefix each line with its timestamp. Default False.
    """
    if not bili.has_credential():
        return no_credential_message()
    try:
        items = await bili.fetch_subtitle(extract_bvid(bvid), lang)
        return _format_subtitle(items, with_timestamp)
    except ValueError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return _friendly_error(e)


@mcp.tool()
async def search_videos(keyword: str, page: int = 1, limit: int = 10) -> str:
    """Search Bilibili videos by keyword.

    Args:
        keyword: Search query.
        page: Result page (1-based). Default 1.
        limit: Max results to return. Default 10.
    """
    try:
        raw = await bili.fetch_search(keyword, page)
        return _format_search(raw, limit)
    except Exception as e:  # noqa: BLE001
        return _friendly_error(e)


@mcp.tool()
async def get_video_danmaku(
    bvid: str, limit: int = 200, with_timestamp: bool = False
) -> str:
    """Get a Bilibili video's danmaku (弹幕, on-screen bullet comments).

    Unlike subtitles, danmaku are public and need no login. Great for asking
    the AI what memes/jokes viewers are spamming, the overall mood, or which
    moments are "高能". Comments are returned ordered by appearance time.

    Args:
        bvid: A BV id or full video URL.
        limit: Max comments to return. Default 200.
        with_timestamp: Prefix each line with its appearance time. Default False.
    """
    try:
        items = await bili.fetch_danmaku(extract_bvid(bvid))
        return _format_danmaku(items, limit, with_timestamp)
    except ValueError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return _friendly_error(e)


@mcp.tool()
async def get_danmaku_hotwords(
    bvid: str, top: int = 20, segments: int = 5
) -> str:
    """Summarize a video's danmaku: top repeated comments + high-energy moments.

    Reuses public danmaku (no login). Great for "what are viewers spamming?" and
    "which moments are 高能?". `top` caps the hotword list; `segments` caps the
    high-energy time windows.

    Args:
        bvid: A BV id or full video URL.
        top: Max hotwords to return. Default 20.
        segments: Max high-energy segments to return. Default 5.
    """
    try:
        items = await bili.fetch_danmaku(extract_bvid(bvid))
        hot = analyze.count_hotwords(items, top)
        segs = analyze.high_energy_segments(items, segments)
        return _format_hotwords(hot, segs, total=len(items))
    except ValueError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return _friendly_error(e)


def main() -> None:
    """Entry point for the `bilibili-mcp` command (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
