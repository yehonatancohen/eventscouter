import datetime as dt

from sources.google_news import _extract_direct_link
from sources.reddit import _looks_like_scoop, _looks_like_video
from sources.tiktok import _normalize_video, _parse_timestamp, fetch_hashtag


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


def test_tiktok_parse_timestamp_handles_string():
    moment = _parse_timestamp("1700000000")
    assert isinstance(moment, dt.datetime)
    assert moment.tzinfo == dt.timezone.utc


def test_tiktok_normalize_requires_link():
    video = {"title": "Cool", "create_time": 1700000000}
    assert _normalize_video(video) is None


def test_fetch_hashtag_filters_old(monkeypatch):
    class DummyResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    recent = int(dt.datetime.now(dt.timezone.utc).timestamp())
    old = int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=10)).timestamp())

    payload = {
        "data": {
            "videos": [
                {
                    "title": "Fresh clip",
                    "share_url": "https://www.tiktok.com/@foo/video/1",
                    "create_time": recent,
                    "play_count": 1000,
                    "digg_count": 50,
                },
                {
                    "title": "Old clip",
                    "share_url": "https://www.tiktok.com/@foo/video/2",
                    "create_time": old,
                    "play_count": 999999,
                },
            ]
        }
    }

    def fake_get(url, params, timeout):
        assert "keywords" in params
        return DummyResponse(payload)

    monkeypatch.setattr("sources.tiktok.requests.get", fake_get)

    results = fetch_hashtag("club", limit=3, days=7)
    assert len(results) == 1
    assert results[0]["link"].endswith("/video/1")
