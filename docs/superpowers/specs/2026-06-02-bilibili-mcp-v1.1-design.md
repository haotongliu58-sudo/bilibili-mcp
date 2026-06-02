# bilibili-mcp v1.1 — Design

**Date:** 2026-06-02
**Status:** Approved (design), pending implementation plan

## Goal

Add two read tools that help an AI understand audience reaction to a video —
danmaku hotword aggregation and video comments — and harden the project so
others can install and run it in one line with CI guarding regressions.

Out of scope for v1.1 (deferred to v1.2): UP主 (user) pages, popular/ranking
feeds, nested comment replies (楼中楼), and jieba word segmentation.

## Architecture

Keeps v1's layering:

- `bili.py` — the only module that touches the network / `bilibili-api`.
- `format.py` — pure text formatting of raw data.
- `analyze.py` — **new** — pure aggregation logic (no network, no formatting).
- `server.py` — thin MCP glue (`@mcp.tool()` functions).

All tools read **public** data. Both new tools work as a guest (no login),
consistent with `get_video_info`, `search_videos`, and `get_video_danmaku`.

## Tool 1: `get_danmaku_hotwords(bvid, top=20, segments=5)`

Reuses the existing `bili.fetch_danmaku(bvid)` — no new network code. Danmaku
are public and need no login.

**Aggregation (in `analyze.py`, pure functions over a list of
`{"text": str, "time": float}`):**

1. **Hotwords by exact-string count.** Bilibili memes are spammed verbatim
   ("草", "前方高能", "awsl"), so counting identical danmaku strings surfaces
   them well without word segmentation. Return the top `top` strings with their
   counts, descending. Trim/normalize whitespace before counting; drop entries
   that are empty after trimming.
2. **高能 (high-energy) segments by density.** Bucket danmaku into time windows
   and return the `segments` windows with the most danmaku. Window size is
   adaptive to video length so short and long videos both give sensible buckets:
   - target ~`max(20, total_duration_seconds / 60)` buckets, i.e. window ≈
     `total_duration / target_buckets`, clamped to a minimum window of 10s.
   - duration is taken from the max danmaku `time` (no extra API call needed).
   - each returned segment: `mm:ss–mm:ss` range + danmaku count, descending by
     count.

**Output (`_format_hotwords` in `format.py`):** two labelled blocks —
a hotword ranking (`N. <text> ×<count>`) and a high-energy segment list
(`mm:ss–mm:ss · <count> 条`). When there are no danmaku, return a clear short
message (mirrors the empty-subtitle message style).

**Signature notes:** `top` and `segments` are caps, not guarantees; fewer are
returned if the data is thin.

## Tool 2: `get_video_comments(bvid, sort="hot", limit=20)`

New `bili.fetch_comments(bvid, sort)` calling `bilibili-api`'s comment module
for the video's `aid`/`oid`. Comments are public → guest access (auto-buvid is
already enabled in `bili.py`'s `_configure_proxy`).

- `sort`: `"hot"` (by likes, default) or `"time"` (newest). Map to the library's
  comment sort enum. Reject unknown values with a `ValueError` surfaced as text.
- **Top-level comments only** — no nested replies in v1.1.
- `limit`: max comments returned (cap). Fetch as few pages as needed to reach it.

**Output (`_format_comments` in `format.py`):** one line group per comment —
username, like count, and content (content may contain newlines; keep it
readable). Header notes how many are shown and the sort used. Empty result →
clear short message.

**Risk-control note:** comment endpoints are more likely than info/search to hit
rate limiting. Errors flow through the existing `_friendly_error` mapping; verify
the guest path end-to-end during implementation and, if guest access proves
unreliable, document that `BILI_SESSDATA` improves reliability (do **not** make
it mandatory).

## Engineering

1. **CI** — `.github/workflows/ci.yml`: checkout, set up Python (3.11), install
   the package, run `pytest` (unit tests only; live tests excluded by default,
   see below). Runs on push and PR to `master`.
2. **Live tests** — `tests/test_live.py` marked `@pytest.mark.live`, covering all
   tools against the real site (info, search, danmaku, hotwords, comments;
   subtitle asserts the no-credential guidance path). `pyproject.toml` sets
   `addopts = -m "not live"` and registers the `live` marker so CI and the
   default `pytest` run skip them; run manually with `pytest -m live`.
3. **README** — add the two new tools to the tools table; add a `uvx` one-line
   run path so users can run without cloning:
   `uvx --from git+https://github.com/haotongliu58-sudo/bilibili-mcp bilibili-mcp`,
   plus the matching MCP client config block using a `uvx` command. Keep the
   existing clone + `pip install -e .` path as the alternative for development.

## Changed files

| File | Change |
| --- | --- |
| `src/bilibili_mcp/bili.py` | add `fetch_comments` |
| `src/bilibili_mcp/analyze.py` | **new** — danmaku hotword + high-energy segment logic (pure) |
| `src/bilibili_mcp/format.py` | add `_format_hotwords`, `_format_comments` |
| `src/bilibili_mcp/server.py` | add `get_danmaku_hotwords`, `get_video_comments` tools |
| `tests/test_analyze.py` | **new** — unit tests for aggregation (fixtures, no network) |
| `tests/test_format.py` | add cases for `_format_hotwords`, `_format_comments` |
| `tests/test_live.py` | **new** — `@pytest.mark.live` end-to-end checks |
| `.github/workflows/ci.yml` | **new** — run unit tests on push/PR |
| `pyproject.toml` | register `live` marker + `addopts = -m "not live"` |
| `README.md` | new tools in table + `uvx` usage |

## Testing strategy

- **Unit (CI):** `analyze.py` aggregation is pure and tested with crafted
  danmaku fixtures (known counts, known density peaks → known segments). New
  `format.py` helpers tested with sample dicts. No network in CI.
- **Live (manual):** `pytest -m live` exercises the real endpoints, including
  the guest comment path and hotword aggregation on a real video.

## Success criteria

- `get_danmaku_hotwords` returns a hotword ranking + high-energy segments for a
  real video, guest, no login.
- `get_video_comments` returns hot/newest top-level comments for a real video,
  guest, no login.
- `pytest` (default) runs unit tests only and passes; `pytest -m live` passes
  against the live site.
- CI is green on push.
- README shows a one-line `uvx` run that works.
