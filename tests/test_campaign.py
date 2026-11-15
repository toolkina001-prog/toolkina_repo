import unittest
from pathlib import Path

from bottle_game.campaign import (
    generate_campaign,
    generate_level_definition,
    load_campaign,
    verify_campaign,
)
from bottle_game.engine import apply_pour, is_bottle_complete, is_solved, legal_moves
from bottle_game.mechanics import build_mechanics
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

    def test_progression_never_generates_stone_or_frozen_bottles(self):
        for level_index in range(1, 141):
            mechanics = build_mechanics(level_index)
            self.assertFalse(mechanics.stone_bottles, f"Level {level_index} contains stone.")
            self.assertFalse(mechanics.frozen_bottles, f"Level {level_index} contains ice.")

    def test_bundled_campaign_has_no_prefilled_completed_bottles(self):
        campaign_path = Path(__file__).resolve().parents[1] / "campaign" / "levels.json"
        levels = load_campaign(campaign_path)
        self.assertEqual(len(levels), 140)
        self.assertEqual([level.id for level in levels[-20:]], list(range(121, 141)))
        verify_campaign(levels)
        for level in levels:
            self.assertFalse(
                level.mechanics_config.get("frozen_bottles", []),
                f"Level {level.id} contains frozen bottles.",
            )
            self.assertFalse(
                level.mechanics_config.get("stone_bottles", []),
                f"Level {level.id} contains stone bottles.",
            )
            self.assertNotIn("frozen_layer", level.mechanics, f"Level {level.id} uses ice.")
            self.assertNotIn("stone_layer", level.mechanics, f"Level {level.id} uses stone.")
            self.assertFalse(
                any(
                    is_bottle_complete(bottle, capacity)
                    for bottle, capacity in zip(level.state, level.capacities)
                ),
                f"Level {level.id} starts with a completed bottle.",
            )
            self.assertTrue(
                any(legal_moves(level.state, level.capacities, level.mechanics_config)),
                f"Level {level.id} starts in a dead end.",
            )
            for giant_index in level.mechanics_config.get("giant_bottles", []):
                self.assertEqual(
                    len(level.state[giant_index]),
                    level.capacities[giant_index],
                    f"Level {level.id} has a partially filled large bottle.",
                )

    def test_every_mystery_level_has_a_verified_solution(self):
        campaign_path = Path(__file__).resolve().parents[1] / "campaign" / "levels.json"
        levels = load_campaign(campaign_path)
        mystery_levels = [
            level for level in levels
            if level.mechanics_config and level.mechanics_config.get("hidden_bottles")
        ]

        self.assertTrue(mystery_levels)
        verify_campaign(mystery_levels)

    def test_giant_bottle_levels_are_three_times_capacity_and_solvable(self):
        levels = [
            generate_level_definition(level_id)
            for level_id in (10, 30, 50, 70, 90, 110, 125, 130, 135, 140)
        ]
        verify_campaign(levels)
        for level in levels:
            giant_index = level.mechanics_config["giant_bottles"][0]
            self.assertEqual(level.capacities[giant_index], level.capacity * 3)
            self.assertEqual(len(level.state[giant_index]), level.capacities[giant_index])
            self.assertFalse(
                is_bottle_complete(level.state[giant_index], level.capacities[giant_index])
            )

    def test_level_46_solution_move_preserves_a_solution(self):
        campaign_path = Path(__file__).resolve().parents[1] / "campaign" / "levels.json"
        level = load_campaign(campaign_path)[45]
        self.assertEqual(level.empty_bottles, 3)
        move = level.solution[0]
        self.assertIn(move, legal_moves(level.state, level.capacities, level.mechanics_config))

        state = apply_pour(level.state, *move, level.capacities, level.mechanics_config)
        for source, target in level.solution[1:]:
            state = apply_pour(state, source, target, level.capacities, level.mechanics_config)
        self.assertTrue(is_solved(state, level.capacities))


if __name__ == "__main__":
    unittest.main()
