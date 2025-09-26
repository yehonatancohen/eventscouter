from bot import Candidate, build_social_video_suggestion, compose_message


def test_build_social_video_suggestion_uses_video_clip():
    candidates = [
        Candidate(
            uid="vid1",
            title="Tel Aviv beach party crowd goes viral",
            link="https://example.com/party",
            score=8.4,
            videos=["https://cdn.example.com/clip.mp4"],
            platform_links=["https://www.tiktok.com/@demo/video/1"],
        ),
        Candidate(
            uid="text1",
            title="Festival lineup announced",
            link="https://example.com/lineup",
            score=7.0,
            videos=[],
            platform_links=[],
        ),
    ]

    suggestion = build_social_video_suggestion(candidates)

    assert "Suggested social upload" in suggestion
    assert "clip.mp4" in suggestion
    assert "Tel Aviv Nightlife Scoop" in suggestion


def test_compose_message_appends_suggestion_block():
    candidates = [
        Candidate(
            uid="vid1",
            title="Haifa rooftop party highlights",
            link="https://example.com/haifa",
            score=9.1,
            videos=["https://cdn.example.com/haifa.mp4"],
            platform_links=[],
        )
    ]

    message = compose_message(candidates)

    assert "🎛️ EventScout" in message
    assert "Suggested social upload" in message
