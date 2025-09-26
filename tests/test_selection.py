import sys
import types

readability_stub = types.ModuleType("readability")


class _DummyDocument:
    def __init__(self, html: str):
        self.html = html

    def summary(self) -> str:
        return "<html></html>"


readability_stub.Document = _DummyDocument
sys.modules.setdefault("readability", readability_stub)

import bot


def make_candidate(uid: str, score: float, videos: list[str]):
    return bot.Candidate(
        uid=uid,
        title=uid,
        link=f"https://example.com/{uid}",
        score=score,
        videos=videos,
        platform_links=[],
    )


def reset_streak():
    bot.NO_VIDEO_STREAK = 0


def test_select_top_candidates_promotes_lower_rank_video():
    reset_streak()
    candidates = [
        make_candidate("high", 8.0, []),
        make_candidate("mid", 7.5, []),
        make_candidate("video", 7.0, ["https://video.example/video.mp4"]),
    ]

    selected = bot.select_top_candidates(candidates, limit=2, min_score=7.0)

    assert len(selected) == 2
    assert any(c.videos for c in selected)
    assert bot.NO_VIDEO_STREAK == 0



def test_select_top_candidates_lowers_threshold_for_video():
    reset_streak()
    candidates = [
        make_candidate("text", 6.0, []),
        make_candidate("video", 5.5, ["https://video.example/clip.mp4"]),
        make_candidate("extra", 5.0, []),
    ]

    selected = bot.select_top_candidates(candidates, limit=1, min_score=7.0)

    assert len(selected) == 1
    assert selected[0].videos
    assert bot.NO_VIDEO_STREAK == 0



def test_select_top_candidates_tracks_dry_spells():
    reset_streak()
    candidates = [
        make_candidate("top", 8.0, []),
        make_candidate("runner", 7.0, []),
    ]

    selected = bot.select_top_candidates(candidates, limit=1, min_score=7.5)

    assert selected[0].uid == "top"
    assert bot.NO_VIDEO_STREAK >= 1
