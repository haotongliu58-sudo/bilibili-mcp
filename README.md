# bilibili-mcp

An MCP server that lets any AI client (Claude, Cursor, ...) read **public** Bilibili data: video info, subtitles, danmaku, and search. It's a thin wrapper over the mature [`bilibili-api`](https://github.com/Nemo2011/bilibili-api) library — all WBI signing, cookies, and anti-abuse handling are delegated to it.

> Reads public data only. Video info and search work as a guest (no login). Subtitles are gated behind login by Bilibili itself, so the subtitle tool needs your own SESSDATA cookie (see below). For personal/research use at a reasonable request rate.

## Tools

| Tool | Description |
| --- | --- |
| `get_video_info(bvid)` | Title, uploader, play/like/coin counts, duration, publish date, description. Accepts a BV id or a full video URL. **Guest, no login.** |
| `get_video_subtitle(bvid, lang="zh-CN", with_timestamp=False)` | Full subtitle/transcript text — great for "summarize this video". **Requires login** (`BILI_SESSDATA`, see below); returns clear guidance if no cookie is set, and a clear message when a video simply has no subtitles. |
| `get_video_danmaku(bvid, limit=200, with_timestamp=False)` | All danmaku (弹幕, on-screen bullet comments), ordered by appearance time — great for asking the AI what memes viewers spam, the overall mood, or which moments are "高能". **Guest, no login.** |
| `search_videos(keyword, page=1, limit=10)` | Search videos by keyword. **Guest, no login.** |

## Install

```
git clone https://github.com/haotongliu58-sudo/bilibili-mcp
cd bilibili-mcp
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
```

## Configure your MCP client

Add to your client's MCP config (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "bilibili": {
      "command": "C:\\path\\to\\bilibili-mcp\\.venv\\Scripts\\bilibili-mcp.exe"
    }
  }
}
```

## Subtitles & login (`BILI_SESSDATA`)

Bilibili restricts subtitle data to logged-in users, so `get_video_subtitle` needs **your own** `SESSDATA` cookie. Without it, info and search still work; the subtitle tool just returns a short note telling you to set the cookie.

To enable subtitles, get the `SESSDATA` value from your browser cookies on `bilibili.com` (DevTools → Application → Cookies) and pass it as an environment variable to the server:

```json
{
  "mcpServers": {
    "bilibili": {
      "command": "C:\\path\\to\\bilibili-mcp\\.venv\\Scripts\\bilibili-mcp.exe",
      "env": { "BILI_SESSDATA": "your_sessdata_value_here" }
    }
  }
}
```

The cookie is read locally and used only to call Bilibili's API directly from your machine — it is never uploaded anywhere. Optional companions (rarely needed for read-only subtitle access): `BILI_BILI_JCT`, `BILI_BUVID3`, `BILI_DEDEUSERID`.

## Proxy

By default the server **ignores the system proxy** and connects directly (Bilibili is a domestic CN site; routing through an overseas proxy node breaks requests). If you are outside mainland China and need a proxy to reach Bilibili, set `BILI_USE_PROXY=1` in the server's environment.

## License

MIT
