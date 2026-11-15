import unittest

from bottle_game.bridge import GameBridge
from bottle_game.campaign import LevelDefinition
from bottle_game.engine import is_solved


class GameBridgeTests(unittest.TestCase):
    def setUp(self):
        self.level = LevelDefinition(
            id=1,
            title="Test",
            description="",
            state=(("red", "blue"), ("red",), ("blue",)),
            capacity=2,
            color_count=2,
            empty_bottles=0,
            mechanics=[],
            solution=((1, 0), (2, 1)),
        )
        self.bridge = GameBridge([self.level])

    def test_campaign_exposes_per_bottle_capacities(self):
        campaign = self.bridge.handle("get_campaign")

        self.assertEqual(campaign[0]["capacities"], [2, 2, 2])

    def test_move_returns_authoritative_state_and_legal_moves(self):
        result = self.bridge.handle("move", {
            "level_index": 0,
            "state": [list(bottle) for bottle in self.level.state],
            "source": 0,
            "target": 2,
        })

        self.assertEqual(result["state"], [["red"], ["red"], ["blue", "blue"]])
        self.assertFalse(result["solved"])
        self.assertIn([0, 1], result["legal_moves"])

    def test_invalid_moves_are_reported(self):
        with self.assertRaises(ValueError):
            self.bridge.handle("move", {
                "level_index": 0,
                "state": [list(bottle) for bottle in self.level.state],
                "source": 0,
                "target": 1,
            })

    def test_solver_returns_a_forward_witness(self):
        level = LevelDefinition(
            id=2,
            title="Simple",
            description="",
            state=(("red",), ("red",)),
            capacity=2,
            color_count=1,
            empty_bottles=0,
            mechanics=[],
        )
        bridge = GameBridge([level])
        result = bridge.handle("solve", {"level_index": 0})

        self.assertFalse(result["timed_out"])
        self.assertIsNotNone(result["solution"])
        state = level.state
        for source, target in result["solution"]:
            state = tuple(tuple(bottle) for bottle in bridge.handle(
                "move",
                {
                    "level_index": 0,
                    "state": [list(bottle) for bottle in state],
                    "source": source,
                    "target": target,
                },
            )["state"])
        self.assertTrue(is_solved(state, level.capacities))


if __name__ == "__main__":
    unittest.main()
