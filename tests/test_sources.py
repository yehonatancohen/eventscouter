from sources.google_news import _extract_direct_link


def test_extract_direct_link_returns_original_for_non_google():
    url = "https://example.com/article"
    assert _extract_direct_link(url) == url


def test_extract_direct_link_strips_google_redirect():
    url = (
        "https://news.google.com/rss/articles/CBMiQGh0dHBzOi8vZXhhbXBsZS5jb20vYXJ0P2hlPTE&url=https%3A%2F%2Ffoo.bar&oc=5"
    )
    expected = "https://foo.bar"
    assert _extract_direct_link(url) == expected
