# Bilibili Data MCP Server — Apify Actor

Packages the published [`bilibili-data-mcp`](https://pypi.org/project/bilibili-data-mcp/)
server as an [Apify](https://apify.com) **standby Actor**, so any MCP client can
read public Bilibili data over a hosted HTTP endpoint, billed per tool call.

## Tools

| Tool | What it does | Login needed |
|------|--------------|--------------|
| `get_video_info` | Title, uploader, stats, duration, description | No |
| `search_videos` | Search videos by keyword | No |
| `get_video_danmaku` | On-screen bullet comments (弹幕) | No |
| `get_danmaku_hotwords` | Top repeated danmaku + high-energy moments | No |
| `get_video_comments` | Top-level comments (hot / newest) | No |
| `get_video_subtitle` | Full transcript text | Yes — `BILI_SESSDATA` |

## Endpoint

Once deployed and in standby mode, connect your MCP client to:

```
https://<your-username>--bilibili-data-mcp.apify.actor/mcp
```

(streamable-HTTP transport)

## Configuration

- `BILI_SESSDATA` — optional. Set it in **Apify Console → Actor → Settings →
  Environment variables** to enable `get_video_subtitle`. Mark it *secret*.
- `SESSION_TIMEOUT_SECS` — optional, default `300`. Idle MCP sessions are closed
  after this many seconds.

## Billing

Pay-per-event: each **successful** tool call charges the `tool-call` event
(see `.actor/pay_per_event.json`, default $0.02). Failed calls are not charged.

## Local run

```bash
npm i -g apify-cli
cd apify-actor
apify run
```

The data logic lives in the upstream package; this Actor only adds the standby
web server and billing wrapper.
