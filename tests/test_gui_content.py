import math
import unittest
from types import SimpleNamespace

from bottle_game.gui import BottleSortApp, COLOR_PALETTE, TEXT


class RecordingCanvas:
    def __init__(self):
        self.created = []

    def winfo_width(self):
        return 0

    def winfo_height(self):
        return 0

    def delete(self, _tag):
        self.created.clear()

    def __getattr__(self, name):
        if name.startswith("create_"):
            return lambda *_args, **_kwargs: self.created.append(name)
        raise AttributeError(name)


class StubWidget:
    def __init__(self, mapped=False):
        self.mapped = mapped

    def winfo_ismapped(self):
        return self.mapped


class GuiContentTests(unittest.TestCase):
    def test_palette_has_distinct_colors_for_the_campaign(self):
        self.assertEqual(len(COLOR_PALETTE), 32)
        self.assertEqual(len(set(COLOR_PALETTE)), 32)
        rgb = [
            tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
            for color in COLOR_PALETTE
        ]
        minimum_distance = min(
            math.dist(rgb[first], rgb[second])
            for first in range(len(rgb))
            for second in range(first)
        )
        self.assertGreaterEqual(minimum_distance, 60)

    def test_english_and_russian_have_matching_ui_strings(self):
        self.assertEqual(set(TEXT["EN"]), set(TEXT["RU"]))
        self.assertNotIn("minecraft", TEXT["RU"])

    def test_menu_scene_draws_bottles_before_the_animation_starts(self):
        canvas = RecordingCanvas()
        app = SimpleNamespace(
            menu_scene=canvas,
            main_container=StubWidget(),
            _menu_scene_requested=False,
            _blend_color=lambda first, second, amount: BottleSortApp._blend_color(
                first, second, amount
            ),
            winfo_width=lambda: 1200,
            after=lambda *_args: None,
        )

        BottleSortApp._animate_menu_scene(app)

        self.assertGreaterEqual(canvas.created.count("create_polygon"), 8)

    def test_level_selection_scene_draws_colored_bottle_background(self):
        canvas = RecordingCanvas()
        app = SimpleNamespace(
            level_scene=canvas,
            level_select_frame=StubWidget(),
            _level_scene_requested=False,
            _blend_color=lambda first, second, amount: BottleSortApp._blend_color(
                first, second, amount
            ),
            winfo_width=lambda: 1200,
            winfo_height=lambda: 760,
            after=lambda *_args: None,
        )

        BottleSortApp._animate_level_scene(app)

        self.assertGreaterEqual(canvas.created.count("create_polygon"), 8)

    def test_layer_textures_draw_shimmer_and_lava_details(self):
        canvas = RecordingCanvas()
        sy = lambda value: value

        BottleSortApp._draw_layer_texture(
            SimpleNamespace(), canvas, "C0", 10, 30, sy
        )
        self.assertEqual(canvas.created.count("create_line"), 2)

        canvas.created.clear()
        BottleSortApp._draw_layer_texture(
            SimpleNamespace(), canvas, "C3", 10, 30, sy
        )
        self.assertEqual(canvas.created.count("create_line"), 2)

    def test_in_level_navigation_buttons_respect_campaign_boundaries(self):
        class ConfigWidget:
            def __init__(self):
                self.options = {}

            def config(self, **options):
                self.options.update(options)

        app = SimpleNamespace(
            level_name=ConfigWidget(),
            moves_label=ConfigWidget(),
            previous_btn=ConfigWidget(),
            next_btn=ConfigWidget(),
            campaign=[object(), object()],
            level_index=0,
            move_count=3,
            _t=lambda key, **values: f"{key}:{values}",
        )

        BottleSortApp._update_game_labels(app, SimpleNamespace(id=1))
        self.assertEqual(app.previous_btn.options["state"], "disabled")
        self.assertEqual(app.next_btn.options["state"], "normal")

        app.level_index = 1
        BottleSortApp._update_game_labels(app, SimpleNamespace(id=2))
        self.assertEqual(app.previous_btn.options["state"], "normal")
        self.assertEqual(app.next_btn.options["state"], "disabled")

    def test_mystery_layers_reveal_when_they_reach_the_top(self):
        app = SimpleNamespace(
            current_mechanics={"hidden_bottles": [0]},
            revealed_layer_tokens=set(),
        )
        state = (("red", "blue"), ())
        tokens = (("bottom", "top"), ())

        BottleSortApp._reveal_hidden_top_runs(app, state, tokens)
        self.assertEqual(app.revealed_layer_tokens, {"top"})

        remaining_state = (("red",), ("blue",))
        remaining_tokens = (("bottom",), ("top",))
        BottleSortApp._reveal_hidden_top_runs(app, remaining_state, remaining_tokens)
        self.assertEqual(app.revealed_layer_tokens, {"bottom", "top"})

    def test_mystery_layer_tokens_follow_pours_and_undo(self):
        level = SimpleNamespace(capacities=(2, 2, 2))
        app = SimpleNamespace(
            campaign=[level],
            level_index=0,
            level_state=(("red", "blue"), (), ()),
            layer_tokens=(("bottom", "top"), (), ()),
            current_mechanics={"hidden_bottles": [0]},
            secret_layer_tokens={"bottom", "top"},
            revealed_layer_tokens={"top"},
            history=[],
            move_count=0,
            solution_path=[],
            game_status=SimpleNamespace(config=lambda **_kwargs: None),
            next_btn=SimpleNamespace(pack_forget=lambda: None),
            _update_game_labels=lambda _level: None,
            _save_progress=lambda: None,
            _render_board=lambda: None,
        )
        app._reveal_hidden_top_runs = lambda state, tokens: (
            BottleSortApp._reveal_hidden_top_runs(app, state, tokens)
        )

        BottleSortApp._apply_move(app, 0, 1)

        self.assertEqual(app.layer_tokens, (("bottom",), ("top",), ()))
        self.assertEqual(app.revealed_layer_tokens, {"bottom", "top"})
        BottleSortApp.undo_move(app)
        self.assertEqual(app.layer_tokens, (("bottom", "top"), (), ()))
        self.assertEqual(app.revealed_layer_tokens, {"top"})


if __name__ == "__main__":
    unittest.main()
