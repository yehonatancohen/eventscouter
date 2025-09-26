from sources.google_news import _extract_direct_link
from sources.reddit import _looks_like_scoop, _looks_like_video


def test_extract_direct_link_returns_original_for_non_google():
    url = "https://example.com/article"
    assert _extract_direct_link(url) == url


def test_extract_direct_link_strips_google_redirect():
    url = (
        "https://news.google.com/rss/articles/CBMiQGh0dHBzOi8vZXhhbXBsZS5jb20vYXJ0P2hlPTE&url=https%3A%2F%2Ffoo.bar&oc=5"
    )
    expected = "https://foo.bar"
    assert _extract_direct_link(url) == expected


def test_reddit_video_detection_by_domain():
    payload = {"domain": "v.redd.it", "post_hint": "hosted:video"}
    assert _looks_like_video(payload, "https://v.redd.it/clip")


def test_reddit_scoop_detection_keywords():
    assert _looks_like_scoop("Breaking: New lineup announced for Tel Aviv")
