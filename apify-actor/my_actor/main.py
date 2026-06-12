"""Bilibili Data MCP Server, packaged as an Apify standby Actor.

The data logic (bili.py / analyze.py / format.py) lives in the published
`bilibili-data-mcp` package and is reused as-is. This module only:
  - re-registers the 6 tools on a FastMCP server,
  - charges one pay-per-event `tool-call` per *successful* call,
  - serves the server over stateless streamable-HTTP in Apify standby mode.

Stateless HTTP is required because Apify standby load-balances requests across
multiple Actor runs with no session stickiness; an in-memory MCP session would
be "not found" on a follow-up request routed to a different run.
"""

import os

import uvicorn
from apify import Actor
from fastmcp import FastMCP

# Reused, single-source-of-truth Bilibili logic from the PyPI package.
from bilibili_mcp import analyze, bili
from bilibili_mcp.format import (
    _format_comments,
    _format_danmaku,
    _format_hotwords,
    _format_search,
    _format_subtitle,
    _format_video_info,
    _friendly_error,
    extract_bvid,
    no_credential_message,
)


def get_server() -> FastMCP:
    """Create the Bilibili MCP server with all 6 public-data tools."""
    server = FastMCP('bilibili-data-mcp', '0.2.0')

    async def _charge() -> None:
        """Charge one pay-per-event unit; never let billing break a response."""
        try:
            await Actor.charge('tool-call')
        except Exception as e:  # noqa: BLE001 - billing must not crash the tool
            Actor.log.warning(f'charge failed: {e}')

    @server.tool()
    async def get_video_info(bvid: str) -> str:
        """Get basic info for a Bilibili video.

        Args:
            bvid: A BV id (e.g. "BV1xx411c7mD") or a full video URL.

        Returns:
            Title, uploader, stats, duration, publish date, description.
        """
        try:
            raw = await bili.fetch_video_info(extract_bvid(bvid))
        except ValueError as e:
            return str(e)
        except Exception as e:  # noqa: BLE001
            return _friendly_error(e)
        await _charge()
        return _format_video_info(raw)

    @server.tool()
    async def get_video_subtitle(
        bvid: str, lang: str = 'zh-CN', with_timestamp: bool = False
    ) -> str:
        """Get the full subtitle/transcript text of a Bilibili video.

        Bilibili gates subtitles behind login, so this needs a SESSDATA cookie
        in the BILI_SESSDATA env var (set it in the Apify Console under the
        Actor's environment variables); without it, guidance is returned.

        Args:
            bvid: A BV id or full video URL.
            lang: Subtitle language code. Default "zh-CN".
            with_timestamp: Prefix each line with its timestamp. Default False.
        """
        if not bili.has_credential():
            return no_credential_message()
        try:
            items = await bili.fetch_subtitle(extract_bvid(bvid), lang)
        except ValueError as e:
            return str(e)
        except Exception as e:  # noqa: BLE001
            return _friendly_error(e)
        await _charge()
        return _format_subtitle(items, with_timestamp)

    @server.tool()
    async def search_videos(keyword: str, page: int = 1, limit: int = 10) -> str:
        """Search Bilibili videos by keyword.

        Args:
            keyword: Search query.
            page: Result page (1-based). Default 1.
            limit: Max results to return. Default 10.
        """
        try:
            raw = await bili.fetch_search(keyword, page)
        except Exception as e:  # noqa: BLE001
            return _friendly_error(e)
        await _charge()
        return _format_search(raw, limit)

    @server.tool()
    async def get_video_danmaku(
        bvid: str, limit: int = 200, with_timestamp: bool = False
    ) -> str:
        """Get a Bilibili video's danmaku (弹幕, on-screen bullet comments).

        Public, no login. Great for what memes/jokes viewers are spamming, the
        overall mood, or which moments are "高能". Ordered by appearance time.

        Args:
            bvid: A BV id or full video URL.
            limit: Max comments to return. Default 200.
            with_timestamp: Prefix each line with its appearance time. Default False.
        """
        try:
            items = await bili.fetch_danmaku(extract_bvid(bvid))
        except ValueError as e:
            return str(e)
        except Exception as e:  # noqa: BLE001
            return _friendly_error(e)
        await _charge()
        return _format_danmaku(items, limit, with_timestamp)

    @server.tool()
    async def get_danmaku_hotwords(
        bvid: str, top: int = 20, segments: int = 5
    ) -> str:
        """Summarize a video's danmaku: top repeated comments + high-energy moments.

        Reuses public danmaku (no login). `top` caps the hotword list; `segments`
        caps the high-energy time windows.

        Args:
            bvid: A BV id or full video URL.
            top: Max hotwords to return. Default 20.
            segments: Max high-energy segments to return. Default 5.
        """
        try:
            items = await bili.fetch_danmaku(extract_bvid(bvid))
        except ValueError as e:
            return str(e)
        except Exception as e:  # noqa: BLE001
            return _friendly_error(e)
        hot = analyze.count_hotwords(items, top)
        segs = analyze.high_energy_segments(items, segments)
        await _charge()
        return _format_hotwords(hot, segs, total=len(items))

    @server.tool()
    async def get_video_comments(
        bvid: str, sort: str = 'hot', limit: int = 20
    ) -> str:
        """Get a Bilibili video's top-level comments. Guest, no login.

        Great for summarizing audience reception or finding points of debate.

        Args:
            bvid: A BV id or full video URL.
            sort: "hot" (by likes, default) or "time" (newest).
            limit: Max comments to return. Default 20.
        """
        try:
            replies = await bili.fetch_comments(extract_bvid(bvid), sort, limit)
        except ValueError as e:
            return str(e)
        except Exception as e:  # noqa: BLE001
            return _friendly_error(e)
        await _charge()
        return _format_comments(replies, limit, sort)

    return server


async def main() -> None:
    """Run the Bilibili MCP Server Actor over stateless streamable-HTTP."""
    await Actor.init()

    port = int(os.environ.get('APIFY_CONTAINER_PORT', '3000'))

    server = get_server()
    # Stateless HTTP: Apify standby load-balances requests across multiple Actor
    # runs with no session stickiness, so an in-memory MCP session created on one
    # run is "not found" on the next. Stateless mode makes every request
    # self-contained (no session id), which is the correct model here.
    app = server.http_app(
        transport='streamable-http', stateless_http=True, json_response=True
    )

    try:
        Actor.log.info(f'Starting Bilibili MCP server on port {port} (stateless)')
        config = uvicorn.Config(app, host='0.0.0.0', port=port, log_level='info')  # noqa: S104
        await uvicorn.Server(config).serve()
    except KeyboardInterrupt:
        Actor.log.info('Shutting down...')
    except Exception as e:
        Actor.log.error(f'Server failed: {e}')
        raise
