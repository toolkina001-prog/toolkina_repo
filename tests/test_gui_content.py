import unittest

from bottle_game.gui import COLOR_PALETTE, TEXT


class GuiContentTests(unittest.TestCase):
    def test_palette_has_distinct_colors_for_the_campaign(self):
        self.assertEqual(len(COLOR_PALETTE), 32)
        self.assertEqual(len(set(COLOR_PALETTE)), 32)

    def test_english_and_russian_have_matching_ui_strings(self):
        self.assertEqual(set(TEXT["EN"]), set(TEXT["RU"]))


if __name__ == "__main__":
    unittest.main()
