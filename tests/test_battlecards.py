"""
Unit tests for Competitor Battlecards Module in AutoVend Agent.
"""

from src.agent.battlecards import match_battlecards


def test_match_tesla_battlecard():
    """Test matching Tesla Model Y competitor mention."""
    text = "我之前一直在看 特斯拉 Model Y，不知你们有什么推荐的车型？"
    cards = match_battlecards(text)
    assert len(cards) > 0
    assert "特斯拉" in cards[0].name
    note = cards[0].to_system_note()
    assert "[系统竞品战术卡提示]" in note
    assert "二排乘坐空间" in note or "内饰豪华感" in note


def test_match_ideal_l7_battlecard():
    """Test matching Li Auto L7 competitor mention."""
    text = "理想L7的大沙发挺吸引我的，对比下你推荐的车如何"
    cards = match_battlecards(text)
    assert len(cards) > 0
    assert "理想" in cards[0].name


def test_no_battlecard_matched():
    """Test standard query with no competitor mentions."""
    text = "我想买一辆20万左右的大空间家用SUV，平时上下班用"
    cards = match_battlecards(text)
    assert len(cards) == 0
