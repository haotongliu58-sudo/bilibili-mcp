# bilibili-mcp v1.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two guest read tools — danmaku hotword/high-energy aggregation and video comments — and harden the project with CI, marked live tests, and a one-line `uvx` install path.

**Architecture:** Keep v1's layering — `bili.py` (network), `format.py` (pure rendering), `server.py` (MCP glue) — and add `analyze.py` for pure danmaku aggregation. The hotwords tool reuses the existing `bili.fetch_danmaku`; the comments tool adds `bili.fetch_comments`. The server computes via `analyze` and renders via `format`, staying thin.

**Tech Stack:** Python 3.10+, `mcp` (FastMCP), `bilibili-api-python` (>=16), `httpx`, `pytest`, GitHub Actions.

---

## Environment notes (read once)

- Run everything from `D:\mcp\bilibili-mcp` using the project venv:
  `.\.venv\Scripts\python.exe -m pytest ...`
- Bilibili is reached **directly** (proxy stripped in `bili.py`). Do NOT set
  `HTTPS_PROXY` for bilibili calls or live tests. (Proxy is only for `git push`.)
- Confirmed API facts used below:
  - `from bilibili_api import comment`
  - `comment.get_comments(oid: int, type_: CommentResourceType, page_index=1, order=OrderType, credential=None) -> dict`
  - `comment.OrderType.LIKE` / `comment.OrderType.TIME`
  - `comment.CommentResourceType.VIDEO`
  - `video.Video(bvid=...).get_aid()` returns the numeric aid (oid for comments).
  - Comment dict shape: `data["replies"]` is a list; each reply has
    `member.uname`, `like` (int), `content.message` (str).

---

## Task 1: `analyze.count_hotwords`

**Files:**
- Create: `src/bilibili_mcp/analyze.py`
- Test: `tests/test_analyze.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_analyze.py`:

```python
from bilibili_mcp.analyze import count_hotwords


def test_count_hotwords_ranks_by_frequency():
    items = [
        {"text": "草", "time": 1.0},
        {"text": "草", "time": 2.0},
        {"text": "草", "time": 3.0},
        {"text": "awsl", "time": 4.0},
        {"text": "awsl", "time": 5.0},
        {"text": "前排", "time": 6.0},
    ]
    assert count_hotwords(items, top=2) == [("草", 3), ("awsl", 2)]


def test_count_hotwords_trims_and_drops_empty():
    items = [
        {"text": " 草 ", "time": 1.0},
        {"text": "草", "time": 2.0},
        {"text": "   ", "time": 3.0},
        {"text": "", "time": 4.0},
    ]
    assert count_hotwords(items, top=10) == [("草", 2)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analyze.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bilibili_mcp.analyze'`

- [ ] **Step 3: Write minimal implementation**

Create `src/bilibili_mcp/analyze.py`:

```python
"""Pure danmaku aggregation. No network, no bilibili-api, no formatting."""
from collections import Counter


def count_hotwords(items: list, top: int = 20) -> list:
    """Rank danmaku by exact-string frequency.

    Bilibili memes are spammed verbatim, so counting identical strings surfaces
    them without word segmentation. Returns up to `top` (text, count) pairs,
    descending by count. Whitespace is trimmed; blanks are dropped.
    """
    counter: Counter = Counter()
    for it in items:
        text = (it.get("text") or "").strip()
        if text:
            counter[text] += 1
    return counter.most_common(top)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analyze.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/bilibili_mcp/analyze.py tests/test_analyze.py
git commit -m "feat: add danmaku hotword frequency aggregation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `analyze.high_energy_segments`

**Files:**
- Modify: `src/bilibili_mcp/analyze.py`
- Test: `tests/test_analyze.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_analyze.py`:

```python
from bilibili_mcp.analyze import high_energy_segments


def test_high_energy_segments_finds_densest_windows():
    # max time 95 -> target_buckets max(20, 95/60)=20 -> window max(10, 95/20)=10
    items = (
        [{"text": "x", "time": t} for t in (5.0, 6.0, 7.0)]   # bucket 0-10: 3
        + [{"text": "x", "time": t} for t in (11.0, 12.0)]    # bucket 10-20: 2
        + [{"text": "x", "time": 95.0}]                        # bucket 90-100: 1
    )
    assert high_energy_segments(items, segments=2) == [
        (0.0, 10.0, 3),
        (10.0, 20.0, 2),
    ]


def test_high_energy_segments_empty():
    assert high_energy_segments([], segments=5) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analyze.py -v`
Expected: FAIL — `ImportError: cannot import name 'high_energy_segments'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/bilibili_mcp/analyze.py`:

```python
def high_energy_segments(
    items: list, segments: int = 5, min_window: float = 10.0
) -> list:
    """Find the time windows with the most danmaku ("高能" moments).

    Bucket danmaku into windows sized adaptively to video length (so short and
    long videos both bucket sensibly), then return the densest `segments`
    windows as (start_sec, end_sec, count) tuples, descending by count.
    """
    times = [float(it.get("time", 0)) for it in items if (it.get("text") or "").strip()]
    if not times:
        return []
    duration = max(times)
    target_buckets = max(20.0, duration / 60.0)
    window = max(min_window, duration / target_buckets)
    buckets: Counter = Counter()
    for t in times:
        buckets[int(t // window)] += 1
    return [
        (idx * window, (idx + 1) * window, count)
        for idx, count in buckets.most_common(segments)
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analyze.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/bilibili_mcp/analyze.py tests/test_analyze.py
git commit -m "feat: add danmaku high-energy segment detection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `format._format_hotwords`

**Files:**
- Modify: `src/bilibili_mcp/format.py`
- Test: `tests/test_format.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_format.py`:

```python
from bilibili_mcp.format import _format_hotwords


def test_format_hotwords_renders_words_and_segments():
    hot = [("草", 3), ("awsl", 2)]
    segs = [(0.0, 10.0, 3), (10.0, 20.0, 2)]
    out = _format_hotwords(hot, segs, total=5)
    assert "共 5 条弹幕" in out
    assert "草 ×3" in out
    assert "awsl ×2" in out
    assert "0:00–0:10 · 3 条" in out
    assert "0:10–0:20 · 2 条" in out


def test_format_hotwords_empty_returns_friendly_message():
    assert "无弹幕" in _format_hotwords([], [], total=0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_format.py -v -k hotwords`
Expected: FAIL — `ImportError: cannot import name '_format_hotwords'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/bilibili_mcp/format.py` (uses existing `_fmt_duration`):

```python
def _format_hotwords(hotwords: list, segments: list, total: int) -> str:
    """Render hotword ranking + high-energy segments.

    hotwords: list of (text, count). segments: list of (start, end, count).
    """
    if total <= 0:
        return "该视频无弹幕。"
    lines = [f"共 {total} 条弹幕。", "", "🔥 高频弹幕："]
    for i, (text, count) in enumerate(hotwords, 1):
        lines.append(f"{i}. {text} ×{count}")
    if segments:
        lines += ["", "⚡ 高能时间段："]
        for start, end, count in segments:
            lines.append(
                f"{_fmt_duration(int(start))}–{_fmt_duration(int(end))} · {count} 条"
            )
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_format.py -v -k hotwords`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/bilibili_mcp/format.py tests/test_format.py
git commit -m "feat: add hotwords formatter

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: wire `get_danmaku_hotwords` tool

**Files:**
- Modify: `src/bilibili_mcp/server.py`

- [ ] **Step 1: Add the analyze import**

In `src/bilibili_mcp/server.py`, add below `from . import bili`:

```python
from . import analyze
```

And add `_format_hotwords` to the existing `from .format import (...)` block.

- [ ] **Step 2: Add the tool**

Append a tool to `src/bilibili_mcp/server.py` (after `get_video_danmaku`):

```python
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
```

- [ ] **Step 3: Verify the server imports and registers the tool**

Run:
```
.\.venv\Scripts\python.exe -c "from bilibili_mcp import server; print('get_danmaku_hotwords' in [t.name for t in __import__('asyncio').get_event_loop().run_until_complete(server.mcp.list_tools())])"
```
Expected: prints `True`

(If the asyncio one-liner is awkward in your shell, instead run
`.\.venv\Scripts\python.exe -c "from bilibili_mcp import server"` and confirm it
imports with no error; the live test in Task 9 exercises the tool for real.)

- [ ] **Step 4: Run the full unit suite**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: PASS (all prior tests still green)

- [ ] **Step 5: Commit**

```bash
git add src/bilibili_mcp/server.py
git commit -m "feat: add get_danmaku_hotwords MCP tool

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `bili.fetch_comments`

**Files:**
- Modify: `src/bilibili_mcp/bili.py`

No unit test: like the other `bili.py` functions this is thin network glue and
is covered by the live test in Task 9.

- [ ] **Step 1: Add the import**

In `src/bilibili_mcp/bili.py`, extend the bilibili-api import line:

```python
from bilibili_api import video, search, comment, request_settings, Credential
```

- [ ] **Step 2: Add the function**

Append to `src/bilibili_mcp/bili.py`:

```python
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
```

- [ ] **Step 3: Verify it imports**

Run: `.\.venv\Scripts\python.exe -c "from bilibili_mcp import bili; print(hasattr(bili, 'fetch_comments'))"`
Expected: prints `True`

- [ ] **Step 4: Commit**

```bash
git add src/bilibili_mcp/bili.py
git commit -m "feat: add guest video-comment fetch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `format._format_comments`

**Files:**
- Modify: `src/bilibili_mcp/format.py`
- Test: `tests/test_format.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_format.py`:

```python
from bilibili_mcp.format import _format_comments


def test_format_comments_renders_user_likes_content():
    replies = [
        {"member": {"uname": "张三"}, "like": 100, "content": {"message": "好视频"}},
        {"member": {"uname": "李四"}, "like": 5, "content": {"message": "学到了"}},
    ]
    out = _format_comments(replies, limit=20, sort="hot")
    assert "张三" in out
    assert "100" in out
    assert "好视频" in out
    assert "李四" in out
    assert "热评" in out  # header notes the sort


def test_format_comments_respects_limit_label():
    replies = [
        {"member": {"uname": f"u{i}"}, "like": i, "content": {"message": str(i)}}
        for i in range(20)
    ]
    out = _format_comments(replies[:3], limit=3, sort="time")
    assert out.count("👤") == 3  # one marker per comment
    assert "最新" in out


def test_format_comments_empty():
    assert "暂无评论" in _format_comments([], limit=20, sort="hot")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_format.py -v -k comments`
Expected: FAIL — `ImportError: cannot import name '_format_comments'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/bilibili_mcp/format.py`:

```python
def _format_comments(replies: list, limit: int = 20, sort: str = "hot") -> str:
    """Render top-level comments: username, likes, content."""
    if not replies:
        return "该视频暂无评论。"
    sort_label = "热评" if sort == "hot" else "最新"
    shown = replies[:limit]
    lines = [f"共展示 {len(shown)} 条评论（{sort_label}）："]
    for r in shown:
        uname = (r.get("member") or {}).get("uname", "")
        like = r.get("like", 0)
        message = (r.get("content") or {}).get("message", "")
        lines.append(f"👤 {uname}（👍{like}）：{message}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_format.py -v -k comments`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/bilibili_mcp/format.py tests/test_format.py
git commit -m "feat: add comments formatter

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: wire `get_video_comments` tool

**Files:**
- Modify: `src/bilibili_mcp/server.py`

- [ ] **Step 1: Add `_format_comments` to the format import**

In `src/bilibili_mcp/server.py`, add `_format_comments` to the
`from .format import (...)` block.

- [ ] **Step 2: Add the tool**

Append to `src/bilibili_mcp/server.py`:

```python
@mcp.tool()
async def get_video_comments(
    bvid: str, sort: str = "hot", limit: int = 20
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
        return _format_comments(replies, limit, sort)
    except ValueError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return _friendly_error(e)
```

- [ ] **Step 3: Verify import**

Run: `.\.venv\Scripts\python.exe -c "from bilibili_mcp import server"`
Expected: no error

- [ ] **Step 4: Run the full unit suite**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: PASS (all unit tests green)

- [ ] **Step 5: Commit**

```bash
git add src/bilibili_mcp/server.py
git commit -m "feat: add get_video_comments MCP tool

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: register `live` marker, default-skip live tests

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pytest config**

Append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "-m 'not live'"
markers = [
    "live: hits the real Bilibili site; run manually with -m live",
]
```

- [ ] **Step 2: Verify default run still works and excludes live**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: PASS — runs only unit tests; no live tests collected (none exist yet,
so just confirm the suite is green and no marker warnings appear).

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "test: register live marker, skip live tests by default

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: live end-to-end tests

**Files:**
- Create: `tests/test_live.py`

These hit the real site and are skipped by default (Task 8). They assert shape,
not exact content, so they stay stable.

- [ ] **Step 1: Write the live tests**

Create `tests/test_live.py`:

```python
"""Live end-to-end tests against the real Bilibili site.

Skipped by default; run with:  pytest -m live
Bilibili is reached directly (no proxy) — do not set HTTPS_PROXY.
"""
import pytest

from bilibili_mcp import server

pytestmark = pytest.mark.live

# A long-lived, popular video id; replace if it ever 404s.
_BVID = "BV1GJ411x7h7"


@pytest.mark.asyncio
async def test_live_search_returns_results():
    out = await server.search_videos("Python", limit=3)
    assert "BV" in out


@pytest.mark.asyncio
async def test_live_video_info():
    out = await server.get_video_info(_BVID)
    assert "标题：" in out


@pytest.mark.asyncio
async def test_live_danmaku_hotwords():
    out = await server.get_danmaku_hotwords(_BVID, top=5, segments=3)
    # Either real hotwords or the clean empty message — both are valid shapes.
    assert ("高频弹幕" in out) or ("无弹幕" in out)


@pytest.mark.asyncio
async def test_live_comments_guest():
    out = await server.get_video_comments(_BVID, sort="hot", limit=5)
    assert ("👤" in out) or ("暂无评论" in out)


@pytest.mark.asyncio
async def test_live_subtitle_without_credential_guides():
    # In CI / no-cookie env this returns the guidance message, not an error.
    import os
    if os.environ.get("BILI_SESSDATA", "").strip():
        pytest.skip("credential configured; guidance path not exercised")
    out = await server.get_video_subtitle(_BVID)
    assert "SESSDATA" in out
```

- [ ] **Step 2: Ensure async test support is available**

Run: `.\.venv\Scripts\python.exe -c "import pytest_asyncio; print('ok')"`

- If it prints `ok`, also add `asyncio_mode = "auto"` under
  `[tool.pytest.ini_options]` in `pyproject.toml` and add
  `"pytest-asyncio>=0.23"` to the `dev` extra in `pyproject.toml`.
- If it raises `ModuleNotFoundError`, install it into the venv first:
  `.\.venv\Scripts\python.exe -m pip install "pytest-asyncio>=0.23"`
  then do the two `pyproject.toml` edits above.

With `asyncio_mode = "auto"` the `@pytest.mark.asyncio` decorators are optional,
but harmless — leave them for clarity.

- [ ] **Step 3: Run the live tests for real**

Run: `.\.venv\Scripts\python.exe -m pytest -m live -v`
Expected: PASS (5 passed). This is the real end-to-end verification of the two
new tools as a guest. If `test_live_comments_guest` fails with a risk-control
message, re-run after a short pause; if guest comments are consistently blocked,
note it in the README (do not make SESSDATA mandatory).

- [ ] **Step 4: Confirm default run still skips live**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: live tests show as deselected; unit tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_live.py pyproject.toml
git commit -m "test: add live end-to-end tests for all tools

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"
      - name: Run unit tests (live excluded by default)
        run: python -m pytest -v
```

- [ ] **Step 2: Verify the install + test command works locally as CI would**

Run:
```
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -v
```
Expected: install succeeds; unit tests pass; live tests deselected.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run unit tests on push and PR

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 11: README + pyproject metadata for v1.1

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Bump version and refresh description/keywords**

In `pyproject.toml`, set `version = "0.2.0"` and update the description to
mention danmaku, hotwords, and comments:

```toml
version = "0.2.0"
description = "An MCP server that lets any AI client read public Bilibili data: video info, subtitles, danmaku, danmaku hotwords, comments, and search."
```

- [ ] **Step 2: Add the two new tools to the README tools table**

In `README.md`, add these rows to the `## Tools` table (after the danmaku row):

```markdown
| `get_danmaku_hotwords(bvid, top=20, segments=5)` | Aggregates danmaku into a top repeated-comment ranking plus the highest-density "高能" time segments — a quick read on what viewers spam and which moments spike. **Guest, no login.** |
| `get_video_comments(bvid, sort="hot", limit=20)` | Top-level video comments (username, likes, content), sorted by likes (`hot`) or newest (`time`) — great for summarizing reception or finding debate. **Guest, no login.** |
```

- [ ] **Step 3: Add a `uvx` one-line run path**

In `README.md`, add a subsection under `## Install` (before
`## Configure your MCP client`):

```markdown
### Run without cloning (uvx)

If you have [uv](https://docs.astral.sh/uv/), you can run the server directly
from GitHub — no clone, no manual venv:

```
uvx --from git+https://github.com/haotongliu58-sudo/bilibili-mcp bilibili-mcp
```

MCP client config using uvx:

```json
{
  "mcpServers": {
    "bilibili": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/haotongliu58-sudo/bilibili-mcp", "bilibili-mcp"]
    }
  }
}
```

The clone + `pip install -e .` path below is still recommended for development.
```

- [ ] **Step 4: Verify the markdown table and code fences render sanely**

Run: `.\.venv\Scripts\python.exe -m pytest -v` (sanity: nothing broke)
Then visually skim `README.md` for balanced code fences.

- [ ] **Step 5: Commit**

```bash
git add README.md pyproject.toml
git commit -m "docs: document hotwords + comments tools and uvx install; bump to 0.2.0

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 12: final verification + cleanup

**Files:** none (verification only)

- [ ] **Step 1: Full unit suite green**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: PASS, live deselected.

- [ ] **Step 2: Live suite green (manual gate)**

Run: `.\.venv\Scripts\python.exe -m pytest -m live -v`
Expected: PASS (5 passed).

- [ ] **Step 3: Confirm no stray temp files**

Run: `git status -s`
Expected: clean working tree (all changes committed; no `_live_e2e.py` or
`__pycache__` noise tracked).

- [ ] **Step 4: Push to GitHub (proxy required)**

```powershell
$env:HTTPS_PROXY="http://127.0.0.1:7897"; $env:HTTP_PROXY="http://127.0.0.1:7897"
git push origin master
```
Expected: includes the spec commit `fccf666` and all v1.1 commits. Confirm CI
goes green on GitHub.

---

## Verification checklist (maps to spec success criteria)

- [ ] `get_danmaku_hotwords` returns hotword ranking + high-energy segments for a real video, guest. (Task 9 live test)
- [ ] `get_video_comments` returns hot/newest top-level comments for a real video, guest. (Task 9 live test)
- [ ] Default `pytest` runs unit tests only and passes; `pytest -m live` passes. (Tasks 8, 9, 12)
- [ ] CI green on push. (Tasks 10, 12)
- [ ] README shows a working one-line `uvx` run. (Task 11)
```
