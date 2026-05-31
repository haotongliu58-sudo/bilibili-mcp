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
