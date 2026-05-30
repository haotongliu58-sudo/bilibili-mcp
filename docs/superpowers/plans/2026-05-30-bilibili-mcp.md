# bilibili-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a thin MCP server that lets any AI client read public Bilibili data (video info, subtitles, search) via the mature `bilibili-api` library.

**Architecture:** Three layers. `format.py` holds pure, fully-unit-tested string logic (BV-id extraction, output formatting, error mapping) with zero external deps. `bili.py` isolates the version-volatile `bilibili-api` + `httpx` calls (proxy config + async fetch functions), verified by an end-to-end run. `server.py` wires FastMCP tools as thin glue over the two.

**Tech Stack:** Python ≥3.10, `mcp` (FastMCP, stdio), `bilibili-api-python` (async), `httpx`, `pytest`.

**Conventions:**
- Run tests with `.venv\Scripts\python.exe -m pytest tests/ -v` (Windows).
- git proxy is already configured (`http.proxy=http://127.0.0.1:7897`) and identity is set (`haotongliu58-sudo`).
- `.gitignore` already exists in the repo root.
- Author/repo references use the clean identity `haotongliu58-sudo`. The repo must contain nothing linking to any private NSFW bot.

---

### Task 1: Scaffold project, install deps, and discover the library API

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`
- Create: `README.md`
- Create: `src/bilibili_mcp/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "bilibili-mcp"
version = "0.1.0"
description = "An MCP server that lets any AI client read public Bilibili data (video info, subtitles, search)."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "bilibili-mcp contributors" }]
keywords = ["mcp", "model-context-protocol", "bilibili", "video", "subtitle", "ai"]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "mcp>=1.2.0",
    "bilibili-api-python>=16.0.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
bilibili-mcp = "bilibili_mcp.server:main"

[project.urls]
Homepage = "https://github.com/haotongliu58-sudo/bilibili-mcp"
Issues = "https://github.com/haotongliu58-sudo/bilibili-mcp/issues"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/bilibili_mcp"]
```

- [ ] **Step 2: Create `LICENSE`** (standard MIT text)

```
MIT License

Copyright (c) 2026 bilibili-mcp contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Create `README.md` stub** (filled out in Task 10)

```markdown
# bilibili-mcp

An MCP server that lets any AI client (Claude, Cursor, ...) read public Bilibili data: video info, subtitles, and search. Thin wrapper over the `bilibili-api` library.

Status: under construction.
```

- [ ] **Step 4: Create `src/bilibili_mcp/__init__.py`**

```python
"""bilibili-mcp: read public Bilibili data from any MCP client."""

__version__ = "0.1.0"
```

- [ ] **Step 5: Create venv and install**

Run:
```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
Expected: installs `mcp`, `bilibili-api-python`, `httpx`, `pytest` without error.

- [ ] **Step 6: Discover the installed library's real API**

Run:
```
.venv\Scripts\python.exe -c "import bilibili_api as b; print('version', b.__version__); from bilibili_api import video, search, request_settings; print('Video attrs:', [a for a in dir(video.Video) if not a.startswith('__')]); print('search attrs:', [a for a in dir(search) if not a.startswith('_')]); print('SearchObjectType.VIDEO:', search.SearchObjectType.VIDEO); print('request_settings:', [a for a in dir(request_settings) if not a.startswith('_')])"
```
Confirm these exist (names used by later tasks). Record any deviations:
- `video.Video(bvid=...)` with methods `get_info`, `get_cid`, `get_subtitle`
- `search.search_by_type` and `search.SearchObjectType.VIDEO`
- a proxy setter on `request_settings` (e.g. `set_proxy` or `set`)

If a name differs in this version, note the actual name — Tasks 7 and 9 reference these and must be updated to match.

- [ ] **Step 7: Commit**

```
git add pyproject.toml LICENSE README.md src/bilibili_mcp/__init__.py
git commit -m "chore: scaffold bilibili-mcp project"
```

---

### Task 2: `extract_bvid` — pull a BV id from raw input or a URL

**Files:**
- Create: `src/bilibili_mcp/format.py`
- Test: `tests/test_format.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_format.py
import pytest
from bilibili_mcp.format import extract_bvid


def test_extract_bvid_from_plain_id():
    assert extract_bvid("BV1xx411c7mD") == "BV1xx411c7mD"


def test_extract_bvid_from_full_url():
    url = "https://www.bilibili.com/video/BV1xx411c7mD/?spm_id=333"
    assert extract_bvid(url) == "BV1xx411c7mD"


def test_extract_bvid_raises_when_absent():
    with pytest.raises(ValueError):
        extract_bvid("https://www.bilibili.com/video/")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bilibili_mcp.format'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/bilibili_mcp/format.py
"""Pure formatting/parsing helpers. No network, no bilibili-api import."""
import re

_BV_RE = re.compile(r"(BV[0-9A-Za-z]{10})")


def extract_bvid(s: str) -> str:
    """Extract a BV id from a bare id or a full Bilibili video URL."""
    m = _BV_RE.search(s or "")
    if not m:
        raise ValueError(f"没找到 BV 号，请检查输入：{s!r}")
    return m.group(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```
git add src/bilibili_mcp/format.py tests/test_format.py
git commit -m "feat: extract_bvid from id or url"
```

---

### Task 3: `_fmt_duration` + `_format_video_info`

**Files:**
- Modify: `src/bilibili_mcp/format.py`
- Test: `tests/test_format.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_format.py`)

```python
from bilibili_mcp.format import _fmt_duration, _format_video_info


def test_fmt_duration():
    assert _fmt_duration(65) == "1:05"
    assert _fmt_duration(3725) == "1:02:05"


def test_format_video_info():
    raw = {
        "bvid": "BV1xx411c7mD",
        "title": "测试视频",
        "owner": {"name": "某UP主"},
        "tname": "科技",
        "duration": 125,
        "pubdate": 1700000000,
        "stat": {"view": 1000, "like": 200, "coin": 50},
        "desc": "  这是简介  ",
    }
    out = _format_video_info(raw)
    assert "标题：测试视频" in out
    assert "UP主：某UP主" in out
    assert "时长：2:05" in out
    assert "播放：1000" in out
    assert "这是简介" in out
    assert "BV1xx411c7mD" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: FAIL — `ImportError: cannot import name '_fmt_duration'`

- [ ] **Step 3: Write minimal implementation** (append to `src/bilibili_mcp/format.py`)

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add src/bilibili_mcp/format.py tests/test_format.py
git commit -m "feat: format video info"
```

---

### Task 4: `_format_subtitle` — including the no-subtitle branch

**Files:**
- Modify: `src/bilibili_mcp/format.py`
- Test: `tests/test_format.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from bilibili_mcp.format import _format_subtitle


def test_format_subtitle_plain():
    items = [
        {"from": 0.0, "to": 2.0, "content": "你好"},
        {"from": 2.0, "to": 4.0, "content": "世界"},
    ]
    assert _format_subtitle(items, with_timestamp=False) == "你好 世界"


def test_format_subtitle_with_timestamp():
    items = [{"from": 65.0, "to": 67.0, "content": "开始"}]
    out = _format_subtitle(items, with_timestamp=True)
    assert "[1:05] 开始" in out


def test_format_subtitle_empty_returns_friendly_message():
    out = _format_subtitle([], with_timestamp=False)
    assert "无字幕" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: FAIL — `ImportError: cannot import name '_format_subtitle'`

- [ ] **Step 3: Write minimal implementation** (append)

```python
def _format_subtitle(items: list, with_timestamp: bool = False) -> str:
    if not items:
        return "该视频无字幕（UP主未上传，且无 AI 字幕）。"
    if with_timestamp:
        return "\n".join(
            f"[{_fmt_duration(it.get('from', 0))}] {it.get('content', '')}"
            for it in items
        )
    return " ".join(it.get("content", "") for it in items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add src/bilibili_mcp/format.py tests/test_format.py
git commit -m "feat: format subtitles with no-subtitle branch"
```

---

### Task 5: `_strip_tags` + `_format_search`

**Files:**
- Modify: `src/bilibili_mcp/format.py`
- Test: `tests/test_format.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from bilibili_mcp.format import _format_search


def test_format_search_strips_highlight_tags():
    raw = {
        "result": [
            {
                "bvid": "BV1aa",
                "title": '关于<em class="keyword">Python</em>的教程',
                "author": "老师",
                "play": 5000,
                "duration": "10:00",
            }
        ]
    }
    out = _format_search(raw, limit=10)
    assert "关于Python的教程" in out
    assert "<em" not in out
    assert "BV1aa" in out


def test_format_search_respects_limit():
    raw = {"result": [{"bvid": f"BV{i}", "title": str(i), "author": "a",
                       "play": 0, "duration": "0:10"} for i in range(20)]}
    out = _format_search(raw, limit=3)
    assert out.count("BV") == 3


def test_format_search_empty():
    assert "没有搜到" in _format_search({"result": []}, limit=10)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: FAIL — `ImportError: cannot import name '_format_search'`

- [ ] **Step 3: Write minimal implementation** (append)

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add src/bilibili_mcp/format.py tests/test_format.py
git commit -m "feat: format search results, strip highlight tags"
```

---

### Task 6: `_friendly_error` — map risk-control errors to a clear message

**Files:**
- Modify: `src/bilibili_mcp/format.py`
- Test: `tests/test_format.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from bilibili_mcp.format import _friendly_error


def test_friendly_error_detects_risk_control():
    out = _friendly_error(Exception("response code: -412 请求被拦截"))
    assert "限流" in out


def test_friendly_error_passes_through_other():
    out = _friendly_error(ValueError("boom"))
    assert "ValueError" in out
    assert "boom" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: FAIL — `ImportError: cannot import name '_friendly_error'`

- [ ] **Step 3: Write minimal implementation** (append)

```python
_RISK_MARKERS = ("-412", "-799", "-352", "风控", "请求被拦截")


def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if any(m in msg for m in _RISK_MARKERS):
        return "被 B站临时限流了（风控），请过一会儿再试，或降低请求频率。"
    return f"调用 B站接口失败：{type(exc).__name__}: {msg}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_format.py -v`
Expected: PASS (all format tests green)

- [ ] **Step 5: Commit**

```
git add src/bilibili_mcp/format.py tests/test_format.py
git commit -m "feat: friendly error mapping for risk-control codes"
```

---

### Task 7: `bili.py` — proxy config + async fetch functions (library boundary)

This module is the only place that imports `bilibili-api`. It has no unit tests (it is the volatile I/O boundary); it is verified by the end-to-end run in Task 9. Use the exact method names confirmed in Task 1 Step 6 — if any differ, substitute them here.

**Files:**
- Create: `src/bilibili_mcp/bili.py`

- [ ] **Step 1: Write the module**

```python
# src/bilibili_mcp/bili.py
"""Thin async glue over bilibili-api. The only module importing bilibili-api.

Proxy policy: Bilibili is a domestic CN site; routing through this machine's
Clash system proxy (an overseas node) breaks or slows requests. So by default
we strip proxy env vars AND tell the underlying client to ignore the system
proxy. Set BILI_USE_PROXY=1 to opt back in (useful for overseas users).
"""
import os

import httpx
from bilibili_api import video, search, request_settings

_USE_PROXY = os.environ.get("BILI_USE_PROXY", "") not in ("", "0", "false", "False")


def _configure_proxy() -> None:
    if _USE_PROXY:
        return
    for v in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(v, None)
    # Tell bilibili-api's client to use no proxy. Exact setter confirmed in
    # Task 1 Step 6; `set_proxy("")` is the expected API for recent versions.
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
```

- [ ] **Step 2: Verify it imports cleanly (no network)**

Run: `.venv\Scripts\python.exe -c "from bilibili_mcp import bili; print('bili import OK')"`
Expected: prints `bili import OK` with no traceback.

- [ ] **Step 3: Commit**

```
git add src/bilibili_mcp/bili.py
git commit -m "feat: bilibili-api glue with proxy-bypass policy"
```

---

### Task 8: `server.py` — FastMCP tools wiring the layers together

**Files:**
- Create: `src/bilibili_mcp/server.py`

- [ ] **Step 1: Write the module**

```python
# src/bilibili_mcp/server.py
"""bilibili-mcp: read public Bilibili data from any MCP client.

    AI client (Claude / Cursor / ...) --MCP--> bilibili-mcp --HTTP--> Bilibili

Thin protocol layer. Volatile bilibili-api calls live in `bili.py`; pure
formatting lives in `format.py`. Tools here are glue.
"""
from mcp.server.fastmcp import FastMCP

from . import bili
from .format import (
    extract_bvid,
    _format_video_info,
    _format_subtitle,
    _format_search,
    _friendly_error,
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

    Useful for asking the AI to summarize a video. Returns a clear message
    when the video has no subtitles.

    Args:
        bvid: A BV id or full video URL.
        lang: Subtitle language code. Default "zh-CN".
        with_timestamp: Prefix each line with its timestamp. Default False.
    """
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


def main() -> None:
    """Entry point for the `bilibili-mcp` command (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the package imports and the entry point exists**

Run: `.venv\Scripts\python.exe -c "from bilibili_mcp.server import main, get_video_info, get_video_subtitle, search_videos; print('server import OK')"`
Expected: prints `server import OK`.

- [ ] **Step 3: Verify the console script is installed**

Run: `.venv\Scripts\bilibili-mcp.exe --help` (it will start the stdio server and wait; Ctrl-C to exit) — confirm it launches without an import error.
Expected: no traceback on startup. (Press Ctrl-C to stop.)

- [ ] **Step 4: Commit**

```
git add src/bilibili_mcp/server.py
git commit -m "feat: FastMCP server with 3 read tools"
```

---

### Task 9: End-to-end verification against real Bilibili (proxy + 3 tools)

This is where the volatile `bili.py` boundary and the proxy-bypass policy are proven. Pick a known **public video that has subtitles** (AI subtitles count). If method names from Task 1 Step 6 differed, fix `bili.py` now and re-run.

**Files:**
- Create (temporary, do not commit): `scripts/e2e_check.py`

- [ ] **Step 1: Write the e2e script**

```python
# scripts/e2e_check.py
import asyncio
from bilibili_mcp import bili
from bilibili_mcp.format import _format_video_info, _format_subtitle, _format_search

TEST_BVID = "BV1xx411c7mD"  # replace with a current public video that has subtitles
TEST_QUERY = "Python 教程"


async def main():
    print("== video info ==")
    info = await bili.fetch_video_info(TEST_BVID)
    print(_format_video_info(info))

    print("\n== subtitle (first 200 chars) ==")
    subs = await bili.fetch_subtitle(TEST_BVID)
    print(_format_subtitle(subs)[:200])

    print("\n== search ==")
    res = await bili.fetch_search(TEST_QUERY, 1)
    print(_format_search(res, 5))


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run it — proxy bypass is the first checkpoint**

Run: `.venv\Scripts\python.exe scripts\e2e_check.py`
Expected:
- Video info returns a real title within a couple seconds (fast return = **direct connection works**, proxy bypass succeeded).
- Subtitle prints real text (if the chosen video has no subtitles, the no-subtitle message appears — pick a different BVID that has subtitles).
- Search prints a few real results.

If requests hang/timeout or raise a connection error: proxy is still in play. Re-check `_configure_proxy` and the `request_settings` proxy setter name from Task 1 Step 6.
If you get a `-412`/`-799` error: you are rate-limited — wait a few minutes and retry; do not loop fast.

- [ ] **Step 3: Delete the temporary script**

Run: `Remove-Item scripts\e2e_check.py; Remove-Item scripts -ErrorAction SilentlyContinue`
(Do not commit the e2e script.)

- [ ] **Step 4: Confirm full unit suite still passes**

Run: `.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: all format tests PASS.

- [ ] **Step 5: Commit any `bili.py` fixes made during e2e**

```
git add -A
git commit -m "fix: align bili.py with installed bilibili-api API (verified e2e)"
```
(Skip the commit if `bili.py` needed no changes.)

---

### Task 10: README and publish prep

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the full README**

```markdown
# bilibili-mcp

An MCP server that lets any AI client (Claude, Cursor, ...) read **public** Bilibili data: video info, subtitles, and search. It's a thin wrapper over the mature [`bilibili-api`](https://github.com/Nemo2011/bilibili-api) library — all WBI signing, cookies, and anti-abuse handling are delegated to it.

> Reads public data only, as a guest (no login). For personal/research use at a reasonable request rate.

## Tools

| Tool | Description |
| --- | --- |
| `get_video_info(bvid)` | Title, uploader, play/like/coin counts, duration, publish date, description. Accepts a BV id or a full video URL. |
| `get_video_subtitle(bvid, lang="zh-CN", with_timestamp=False)` | Full subtitle/transcript text — great for "summarize this video". Returns a clear message when the video has no subtitles. |
| `search_videos(keyword, page=1, limit=10)` | Search videos by keyword. |

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

## Proxy

By default the server **ignores the system proxy** and connects directly (Bilibili is a domestic CN site; routing through an overseas proxy node breaks requests). If you are outside mainland China and need a proxy to reach Bilibili, set `BILI_USE_PROXY=1` in the server's environment.

## License

MIT
```

- [ ] **Step 2: Commit**

```
git add README.md
git commit -m "docs: full README with tools, install, client config, proxy note"
```

- [ ] **Step 3: (Manual, optional) Publish to GitHub**

The user publishes when ready (same flow as anime-sd-mcp):
```
gh repo create bilibili-mcp --public --source=. --remote=origin --push
```
(git proxy `7897` is already configured for pushes.) Do not run this automatically — leave publishing to the user.

---

## Self-Review

**Spec coverage:**
- Thin wrapper over `bilibili-api` → Tasks 7, 8. ✅
- `get_video_info` (BV or URL) → Tasks 2, 3, 8. ✅
- `get_video_subtitle` incl no-subtitle branch → Tasks 4, 8. ✅
- `search_videos` → Tasks 5, 8. ✅
- Proxy bypass + `BILI_USE_PROXY` escape hatch → Task 7, verified Task 9. ✅
- Guest-only, no login → Task 7 (no Credential used). ✅
- Risk-control friendly errors → Task 6, wired Task 8. ✅
- Input tolerance (BV or URL) → Task 2. ✅
- Project structure mirroring M1 → Task 1 (pyproject, src layout, dev=pytest). ✅
- Unit tests mock-free pure logic; e2e real run → Tasks 2–6 (unit), Task 9 (e2e). ✅
- Clean identity / no NSFW link → Conventions + Tasks 1, 10. ✅
- Non-goals (login, user_videos/comments, ASR, SaaS) → not implemented (correctly absent). ✅

**Placeholder scan:** No TBD/TODO. The two honest version-dependent points (subtitle method names, proxy setter) are pinned by Task 1 Step 6 and corrected in Task 9 — not placeholders, but a verify-then-fix loop with concrete best-known code provided.

**Type consistency:** `bili.fetch_video_info/fetch_subtitle/fetch_search` and `format.extract_bvid/_format_video_info/_format_subtitle/_format_search/_friendly_error` are referenced with identical names across Tasks 7, 8, 9. Subtitle item shape `{"from","to","content"}` is consistent between Task 4 tests and Task 7's fetch normalization. ✅
