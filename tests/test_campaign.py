import unittest

from bottle_game.campaign import generate_campaign, generate_level_definition, verify_campaign
from bottle_game.solver import solve_level


class CampaignTests(unittest.TestCase):
    def test_campaign_has_geometric_growth_and_solved_levels(self):
        levels = generate_campaign(12)
        self.assertEqual(len(levels), 12)
        self.assertGreater(levels[0].color_count, 0)
        self.assertGreater(levels[-1].color_count, levels[0].color_count)
        self.assertIsNotNone(solve_level(levels[0].state, levels[0].capacity, time_limit=2.0))
        verify_campaign(levels)

    def test_advanced_mechanic_campaign_solutions_replay(self):
        levels = [generate_level_definition(index) for index in (25, 45, 70, 90)]
        verify_campaign(levels)

    def test_campaign_color_curve_matches_milestones(self):
        levels = [generate_level_definition(index) for index in (1, 10, 25, 45, 70, 100, 120)]
        self.assertEqual(
            [level.color_count for level in levels],
            [3, 5, 8, 12, 18, 26, 28],
        )


if __name__ == "__main__":
    unittest.main()
