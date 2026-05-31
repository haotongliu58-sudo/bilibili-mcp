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
