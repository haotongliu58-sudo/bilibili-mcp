"""Offline smoke test: build the server, assert all 6 tools register, and that
the streamable-HTTP ASGI app is constructible. No network, no Apify platform."""
import asyncio
import sys

from my_actor.main import get_server


async def run() -> None:
    server = get_server()
    tools = await server.list_tools()  # fastmcp 3: list[Tool]
    names = sorted(t.name for t in tools)
    expected = sorted([
        'get_video_info', 'get_video_subtitle', 'search_videos',
        'get_video_danmaku', 'get_danmaku_hotwords', 'get_video_comments',
    ])
    assert names == expected, f'tool mismatch:\n got={names}\n want={expected}'
    app = server.http_app(
        transport='streamable-http', stateless_http=True, json_response=True
    )
    assert app is not None
    print('SMOKE OK: 6 tools registered ->', names)
    print('SMOKE OK: stateless streamable-http ASGI app built ->', type(app).__name__)


if __name__ == '__main__':
    try:
        asyncio.run(run())
    except Exception as e:
        print('SMOKE FAIL:', repr(e))
        sys.exit(1)
