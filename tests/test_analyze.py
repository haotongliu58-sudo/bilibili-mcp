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
