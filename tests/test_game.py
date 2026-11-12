import unittest

from bottle_game.engine import apply_pour, can_pour, is_solved
from bottle_game.generator import generate_level
from bottle_game.solver import solve_level


class BottlePuzzleTests(unittest.TestCase):
    def test_can_pour_empty_source_is_false(self):
        state = ((), ("R", "R"), ("B", "B"))
        self.assertFalse(can_pour(state, 0, 1, 4))

    def test_same_color_pour_is_legal(self):
        state = (("R", "B"), ("B",), ())
        self.assertTrue(can_pour(state, 0, 1, 4))

    def test_partial_pour_moves_only_top_run(self):
        state = (("R", "R", "G"), ("G",), ("B", "B"))
        result = apply_pour(state, 0, 1, 4)
        self.assertEqual(result[0], ("R", "R"))
        self.assertEqual(result[1], ("G", "G"))

    def test_top_layer_moves_and_bottom_layer_stays(self):
        state = (("red", "blue"), ())
        result = apply_pour(state, 0, 1, 4)
        self.assertEqual(result[0], ("red",))
        self.assertEqual(result[1], ("blue",))

    def test_solved_state_is_detected(self):
        state = (("R", "R", "R", "R"), ("G", "G", "G", "G"), (), ())
        self.assertTrue(is_solved(state, 4))

    def test_generate_level_is_solvable(self):
        state = generate_level(3, 4, empty_bottles=2, shuffle_steps=12)
        self.assertIsNotNone(solve_level(state, 4))

    def test_solver_returns_a_valid_path(self):
        state = generate_level(3, 4, empty_bottles=2, shuffle_steps=10)
        solution = solve_level(state, 4)
        self.assertIsNotNone(solution)
        self.assertGreaterEqual(len(solution), 1)
        for source, target in solution:
            state = apply_pour(state, source, target, 4)
        self.assertTrue(is_solved(state, 4))

    def test_solver_respects_mechanic_bottles(self):
        state = (("R", "B"), ("B", "R"), (), ())
        blocked = {"stone_bottles": [2, 3]}
        self.assertIsNone(solve_level(state, 2, mechanics=blocked))

    def test_advanced_mechanics_block_illegal_moves(self):
        state = (("R",), ("G",), ("B",), ())
        self.assertFalse(can_pour(state, 0, 1, 4, {"decoy_bottles": [1]}))
        self.assertFalse(can_pour(state, 0, 2, 4, {"stone_bottles": [2]}))
        self.assertFalse(can_pour(state, 0, 0, 4, {"frozen_bottles": [0]}))
        self.assertTrue(can_pour(state, 0, 3, 4, {"decoy_bottles": [0]}))


if __name__ == "__main__":
    unittest.main()
