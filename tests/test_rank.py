from core.rank import score_rule_based


def test_score_rule_based_rewards_keywords_and_city():
    title = "Massive techno festival arrives in Tel Aviv"
    text = "This week only: tickets on sale now for the underground rave in Tel Aviv."
    score = score_rule_based(title, text)
    assert score > 3


def test_score_rule_based_penalises_missing_keywords():
    title = "Finance news update"
    text = "Today we discuss earnings and politics in Jerusalem."
    score = score_rule_based(title, text)
    assert score < 0
