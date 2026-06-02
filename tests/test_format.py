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
    # one "BV号：" label per entry → counts entries unambiguously
    assert out.count("BV号：") == 3


def test_format_search_empty():
    assert "没有搜到" in _format_search({"result": []}, limit=10)


from bilibili_mcp.format import _friendly_error


def test_friendly_error_detects_risk_control():
    out = _friendly_error(Exception("response code: -412 请求被拦截"))
    assert "限流" in out


def test_friendly_error_passes_through_other():
    out = _friendly_error(ValueError("boom"))
    assert "ValueError" in out
    assert "boom" in out


from bilibili_mcp.format import no_credential_message


def test_no_credential_message_mentions_sessdata():
    out = no_credential_message()
    assert "SESSDATA" in out
    assert "BILI_SESSDATA" in out


from bilibili_mcp.format import _format_danmaku


def test_format_danmaku_plain_sorts_by_time_and_shows_count():
    items = [
        {"text": "草", "time": 12.0},
        {"text": "前排", "time": 1.0},
    ]
    out = _format_danmaku(items)
    assert "共 2 条弹幕" in out
    # sorted by appearance time: 前排 (1s) before 草 (12s)
    assert out.index("前排") < out.index("草")


def test_format_danmaku_with_timestamp():
    items = [{"text": "高能", "time": 65.0}]
    out = _format_danmaku(items, with_timestamp=True)
    assert "[1:05] 高能" in out


def test_format_danmaku_respects_limit():
    items = [{"text": str(i), "time": float(i)} for i in range(20)]
    out = _format_danmaku(items, limit=5)
    assert "共 20 条弹幕" in out
    # only 5 lines rendered after the header
    body = out.split("\n")[1:]
    assert len([ln for ln in body if ln.strip()]) == 5


def test_format_danmaku_empty_returns_friendly_message():
    assert "无弹幕" in _format_danmaku([])


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
