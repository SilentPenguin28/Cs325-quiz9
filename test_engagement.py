import pytest
from engagement import EngagementEngine

class TestEngagementEngineInit:
    def test_default_initialization(self):
        eng = EngagementEngine("alice")
        assert eng.user_handle == "alice"
        assert eng.score == 0.0
        assert eng.verified is False

    def test_verified_initialization(self):
        eng = EngagementEngine("bob", verified=True)
        assert eng.verified is True

    def test_score_starts_at_zero(self):
        eng = EngagementEngine("carol", verified=True)
        assert eng.score == 0.0


class TestProcessInteraction:
    def test_like_adds_correct_points(self):
        eng = EngagementEngine("user1")
        eng.process_interaction("like", 1)
        assert eng.score == 1.0

    def test_comment_adds_correct_points(self):
        eng = EngagementEngine("user1")
        eng.process_interaction("comment", 1)
        assert eng.score == 5.0

    def test_share_adds_correct_points(self):
        eng = EngagementEngine("user1")
        eng.process_interaction("share", 1)
        assert eng.score == 10.0

    def test_multiple_count(self):
        eng = EngagementEngine("user1")
        eng.process_interaction("like", 10)
        assert eng.score == 10.0

    def test_verified_multiplier_applied(self):
        eng = EngagementEngine("user1", verified=True)
        eng.process_interaction("like", 10)
        assert eng.score == 15.0  # 10 * 1.5

    def test_verified_multiplier_on_share(self):
        eng = EngagementEngine("user1", verified=True)
        eng.process_interaction("share", 2)
        assert eng.score == 30.0  # 20 * 1.5

    def test_valid_interaction_returns_true(self):
        eng = EngagementEngine("user1")
        assert eng.process_interaction("like") is True

    def test_invalid_interaction_returns_false(self):
        eng = EngagementEngine("user1")
        assert eng.process_interaction("retweet") is False

    def test_invalid_interaction_does_not_change_score(self):
        eng = EngagementEngine("user1")
        eng.process_interaction("retweet")
        assert eng.score == 0.0

    def test_negative_count_raises_value_error(self):
        eng = EngagementEngine("user1")
        with pytest.raises(ValueError, match="Negative count"):
            eng.process_interaction("like", -1)

    def test_zero_count_adds_nothing(self):
        eng = EngagementEngine("user1")
        eng.process_interaction("like", 0)
        assert eng.score == 0.0

    def test_interactions_accumulate(self):
        eng = EngagementEngine("user1")
        eng.process_interaction("like", 5)    # 5
        eng.process_interaction("comment", 2) # +10
        eng.process_interaction("share", 1)   # +10
        assert eng.score == 25.0

    def test_default_count_is_one(self):
        eng = EngagementEngine("user1")
        eng.process_interaction("comment")
        assert eng.score == 5.0


class TestGetTier:
    def test_newbie_at_zero(self):
        eng = EngagementEngine("user1")
        assert eng.get_tier() == "Newbie"

    def test_newbie_just_below_threshold(self):
        eng = EngagementEngine("user1")
        eng.score = 99.9
        assert eng.get_tier() == "Newbie"

    def test_influencer_at_exactly_100(self):
        eng = EngagementEngine("user1")
        eng.score = 100
        assert eng.get_tier() == "Influencer"

    def test_influencer_at_midrange(self):
        eng = EngagementEngine("user1")
        eng.score = 500
        assert eng.get_tier() == "Influencer"

    def test_influencer_at_exactly_1000(self):
        eng = EngagementEngine("user1")
        eng.score = 1000
        assert eng.get_tier() == "Influencer"

    def test_icon_just_above_1000(self):
        eng = EngagementEngine("user1")
        eng.score = 1000.1
        assert eng.get_tier() == "Icon"

    def test_icon_at_high_score(self):
        eng = EngagementEngine("user1")
        eng.score = 99999
        assert eng.get_tier() == "Icon"


class TestApplyPenalty:
    def test_score_reduced_by_report(self):
        eng = EngagementEngine("user1")
        eng.score = 100.0
        eng.apply_penalty(1)
        assert eng.score == 80.0  # 100 - (100 * 0.20 * 1)

    def test_multiple_reports_compound_reduction(self):
        eng = EngagementEngine("user1")
        eng.score = 100.0
        eng.apply_penalty(2)
        assert eng.score == 60.0  # 100 - (100 * 0.40)

    def test_score_floored_at_zero(self):
        eng = EngagementEngine("user1")
        eng.score = 50.0
        eng.apply_penalty(10)  # 200% reduction — should clamp to 0
        assert eng.score == 0.0

    def test_score_never_goes_negative(self):
        eng = EngagementEngine("user1")
        eng.score = 10.0
        eng.apply_penalty(100)
        assert eng.score >= 0.0

    def test_verified_stripped_above_10_reports(self):
        eng = EngagementEngine("user1", verified=True)
        eng.apply_penalty(11)
        assert eng.verified is False

    def test_verified_kept_at_exactly_10_reports(self):
        eng = EngagementEngine("user1", verified=True)
        eng.score = 100.0
        eng.apply_penalty(10)
        assert eng.verified is True  # boundary: >10, not >=10

    def test_zero_reports_no_change(self):
        eng = EngagementEngine("user1")
        eng.score = 100.0
        eng.apply_penalty(0)
        assert eng.score == 100.0


class TestIntegration:
    def test_tier_upgrades_through_interactions(self):
        eng = EngagementEngine("user1")
        assert eng.get_tier() == "Newbie"
        eng.process_interaction("share", 10)  # +100
        assert eng.get_tier() == "Influencer"
        eng.process_interaction("share", 91)  # +910
        assert eng.get_tier() == "Icon"

    def test_penalty_can_downgrade_tier(self):
        eng = EngagementEngine("user1")
        eng.score = 500.0
        assert eng.get_tier() == "Influencer"
        eng.apply_penalty(3)  # -60% → 200
        assert eng.get_tier() == "Influencer"
        eng.apply_penalty(5)  # -100% → 0
        assert eng.get_tier() == "Newbie"

    def test_verified_status_affects_future_interactions_after_penalty(self):
        eng = EngagementEngine("user1", verified=True)
        eng.score = 50.0
        eng.apply_penalty(11)          # strips verified
        eng.process_interaction("share", 1)
        assert eng.score == 10.0       # no 1.5x multiplier