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
