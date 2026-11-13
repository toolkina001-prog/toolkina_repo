"""Tkinter-based game UI for the bottle-pouring puzzle."""

from __future__ import annotations

import colorsys
import json
import math
import os
import time
import tkinter as tk
import zlib
from pathlib import Path

from .campaign import LevelDefinition, generate_campaign, load_campaign
from .audio import SoundManager
from .engine import apply_pour, can_pour, is_bottle_complete, is_solved, legal_moves
from .solver import solve_level

TEXT = {
    "EN": {
        "play": "Play", "levels": "Level selection", "settings": "Settings", "exit": "Exit",
        "progress": "Completed: {done} / {total}",
        "colors": "colors",
        "undo": "Undo", "restart": "Restart", "hint": "Hint", "check": "Check solution",
        "menu": "Main menu", "moves": "Moves: {count}", "time": "Time: {value}",
        "sound": "Sound effects", "music": "Background music", "patterns": "Color patterns",
        "language": "Language", "save": "Save settings", "back": "Back", "reset": "Reset progress",
        "campaign": "Choose a level", "level": "Level {number}", "level_solved": "Puzzle solved!",
        "dead_title": "Game over", "dead_body": "This position cannot be solved. Start the level again.",
        "progress_error": "Could not load saved progress: {error}",
        "select_level": "Click a level to start", "open": "Open",
        "previous": "Previous", "next": "Next level",
        "mechanic_ice": "ICE", "mechanic_stone": "STONE", "mechanic_mystery": "MYSTERY",
        "mechanic_decoy": "DECOY",
        "hint_status": "Hint: bottle {source} → bottle {target}",
        "hint_unavailable": "No hint available for this position.",
        "solvable_status": "Solution found: {count} moves.",
        "unsolved_status": "No solution found within the search time limit.",
    },
    "RU": {
        "play": "Играть", "levels": "Выбор уровня", "settings": "Настройки", "exit": "Выход",
        "progress": "Пройдено: {done} / {total}",
        "colors": "цветов",
        "undo": "Отменить", "restart": "Заново", "hint": "Подсказка", "check": "Проверить решение",
        "menu": "Главное меню", "moves": "Ходы: {count}", "time": "Время: {value}",
        "sound": "Звуковые эффекты", "music": "Фоновая музыка", "patterns": "Узоры для цветов",
        "language": "Язык", "save": "Сохранить настройки", "back": "Назад", "reset": "Сбросить прогресс",
        "campaign": "Выбор уровня", "level": "Уровень {number}", "level_solved": "Уровень пройден!",
        "dead_title": "Игра окончена", "dead_body": "Эту позицию нельзя решить. Начните уровень заново.",
        "progress_error": "Не удалось загрузить сохранение: {error}",
        "select_level": "Нажмите на номер уровня, чтобы начать", "open": "Открыть",
        "previous": "Предыдущий", "next": "Следующий уровень",
        "mechanic_ice": "ЛЁД", "mechanic_stone": "КАМЕНЬ", "mechanic_mystery": "ТАЙНА",
        "mechanic_decoy": "ОБМАНКА",
        "hint_status": "Подсказка: бутылка {source} → бутылка {target}",
        "hint_unavailable": "Для этой позиции нет подсказки.",
        "solvable_status": "Решение найдено: {count} ходов.",
        "unsolved_status": "Решение не найдено за отведённое время.",
    },
}

COLOR_PALETTE = (
    "#D61E11", "#00F5F5", "#5A00F5", "#49F500", "#F5D236", "#F536BC",
    "#006BB2", "#00F56E", "#B28900", "#B20077", "#00B21E", "#369FF5",
    "#ABF500", "#BC00F5", "#0025F5", "#F56C36", "#2FD6B2", "#6FB227",
    "#7F27B2", "#2E27B2", "#27B264", "#F5366F", "#00F500", "#3656F5",
    "#F5A300", "#8F36F5", "#7CF536", "#36F543", "#F50045", "#B25327",
    "#00B6D6", "#F50097",
)


def concealed_bottle_indices(mechanics: dict) -> set[int]:
    return set(mechanics.get("hidden_bottles", [])) | set(mechanics.get("decoy_bottles", []))


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        *,
        text: str,
        command,
        width: int,
        height: int,
        font=("Segoe UI", 10, "bold"),
        fg="#ffffff",
        bg="#245c82",
        activeforeground="#ffffff",
        activebackground="#3479a5",
        cursor="hand2",
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            cursor=cursor,
            takefocus=True,
        )
        self._button_options = {
            "text": text,
            "command": command,
            "font": font,
            "fg": fg,
            "bg": bg,
            "activeforeground": activeforeground,
            "activebackground": activebackground,
            "state": tk.NORMAL,
        }
        self._hovered = False
        self._pressed = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", self._on_key)
        self.bind("<space>", self._on_key)
        self._redraw()

    def config(self, **options):
        unknown = set(options) - set(self._button_options)
        if unknown:
            super().configure(**options)
            return
        self._button_options.update(options)
        self._redraw()

    configure = config

    def _on_enter(self, _event):
        self._hovered = True
        self._redraw()

    def _on_leave(self, _event):
        self._hovered = False
        self._pressed = False
        self._redraw()

    def _on_press(self, _event):
        if self._button_options["state"] != tk.DISABLED:
            self._pressed = True
            self._redraw()

    def _on_release(self, event):
        was_pressed = self._pressed
        self._pressed = False
        self._redraw()
        if (
            was_pressed
            and self._button_options["state"] != tk.DISABLED
            and 0 <= event.x <= self.winfo_width()
            and 0 <= event.y <= self.winfo_height()
        ):
            self._button_options["command"]()

    def _on_key(self, _event):
        if self._button_options["state"] != tk.DISABLED:
            self._button_options["command"]()
            return "break"

    @staticmethod
    def _rounded_points(x1, y1, x2, y2, radius):
        points = []
        for center_x, center_y, start in (
            (x2 - radius, y1 + radius, -90),
            (x2 - radius, y2 - radius, 0),
            (x1 + radius, y2 - radius, 90),
            (x1 + radius, y1 + radius, 180),
        ):
            for step in range(7):
                angle = math.radians(start + step * 15)
                points.extend(
                    (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
                )
        return points

    def _redraw(self):
        self.delete("all")
        width = max(self.winfo_width(), int(self.cget("width")))
        height = max(self.winfo_height(), int(self.cget("height")))
        disabled = self._button_options["state"] == tk.DISABLED
        face = "#9caebd" if disabled else (
            self._button_options["activebackground"]
            if self._hovered
            else self._button_options["bg"]
        )
        text_color = "#e7edf2" if disabled else self._button_options["fg"]
        offset = 2 if self._pressed and not disabled else 0
        radius = min(15, height // 3)
        self.create_polygon(
            self._rounded_points(4, 5, width - 4, height - 1, radius),
            smooth=True,
            splinesteps=12,
            fill="#a9bac8",
            outline="",
        )
        self.create_polygon(
            self._rounded_points(3, 2 + offset, width - 5, height - 5 + offset, radius),
            smooth=True,
            splinesteps=12,
            fill=face,
            outline=self._button_options["activebackground"] if self._hovered else face,
            width=2,
        )
        self.create_line(16, 5 + offset, width - 18, 5 + offset, fill="#ffffff", width=2)
        self.create_text(
            width / 2,
            height / 2 + offset,
            text=self._button_options["text"],
            fill=text_color,
            font=self._button_options["font"],
            width=width - 20,
            justify="center",
        )


class BottleSortApp(tk.Tk):
    def __init__(self, campaign=None):
        if os.name == "nt":
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        super().__init__()
        self.title("Bottle Sort")
        self.geometry("1200x760")
        self.minsize(900, 620)
        self.configure(bg="#eaf0f7")

        self.language = "EN"
        self.sound_enabled = True
        self.music_enabled = True
        self.patterns_enabled = True
        self.hints_remaining = 3

        if campaign is not None:
            self.campaign = campaign
        else:
            campaign_path = Path(__file__).resolve().parents[1] / "campaign" / "levels.json"
            self.campaign = load_campaign(campaign_path) if campaign_path.exists() else generate_campaign(12)
        self.level_index = 0
        self.level_state = self.campaign[0].state if self.campaign else ()
        self.initial_state = self.level_state
        self.history: list[
            tuple[
                tuple[tuple[str, ...], ...],
                int,
                tuple[tuple[int, int], ...],
                tuple[tuple[str, ...], ...],
                frozenset[str],
            ]
        ] = []
        self.solution_path: list[tuple[int, int]] = []
        self.selected = None
        self.move_count = 0
        self.progress = {}
        self.progress_load_error: str | None = None
        self.elapsed_seconds = 0.0
        self.level_started_at: float | None = None
        self.timer_job: str | None = None
        self.current_mechanics: dict = {}
        self.animating = False
        self._dead_end_dialog = None
        self.layer_tokens: tuple[tuple[str, ...], ...] = ()
        self.initial_layer_tokens: tuple[tuple[str, ...], ...] = ()
        self.secret_layer_tokens: set[str] = set()
        self.revealed_layer_tokens: set[str] = set()
        self._menu_animation_job: str | None = None
        self._level_animation_job: str | None = None
        self._menu_scene_requested = False
        self._level_scene_requested = False
        self.audio = SoundManager(self)
        self.save_path = Path(os.path.expanduser("~/.bottle_sort_save.json"))

        self._build_main_menu()
        self._build_settings()
        self._build_level_select()
        self._load_progress()
        self._apply_language()
        self.audio.set_enabled(sound=self.sound_enabled, music=self.music_enabled)
        self.bind_all("<ButtonRelease-1>", self._play_click_sound, add="+")
        self.protocol("WM_DELETE_WINDOW", self._close_app)
        self.show_menu()

    def _t(self, key: str, **values) -> str:
        return TEXT[self.language].get(key, TEXT["EN"][key]).format(**values)

    def _apply_language(self):
        self.play_btn.config(text=self._t("play"))
        self.levels_btn.config(text=self._t("levels"))
        self.settings_btn.config(text=self._t("settings"))
        self.exit_btn.config(text=self._t("exit"))
        self.settings_title.config(text=self._t("settings"))
        self.sound_check.config(text=self._t("sound"))
        self.music_check.config(text=self._t("music"))
        self.patterns_check.config(text=self._t("patterns"))
        self.language_label.config(text=f"{self._t('language')}:")
        self.settings_save.config(text=self._t("save"))
        self.settings_back.config(text=self._t("back"))
        self.settings_reset.config(text=self._t("reset"))
        self.level_select_title.config(text=self._t("campaign"))
        self.level_select_hint.config(text=self._t("select_level"))
        self.level_select_back.config(text=self._t("back"))
        if hasattr(self, "undo_btn"):
            self.undo_btn.config(text=self._t("undo"))
            self.restart_btn.config(text=self._t("restart"))
            self.hint_btn.config(text=self._t("hint"))
            self.check_btn.config(text=self._t("check"))
            self.menu_btn.config(text=self._t("menu"))
            self.previous_btn.config(text=self._t("previous"))
            self.next_btn.config(text=self._t("next"))
        self._refresh_progress()
        if hasattr(self, "level_buttons"):
            self._refresh_level_cards()
        if hasattr(self, "level_name"):
            self._update_game_labels(self.campaign[self.level_index])

    def _play_click_sound(self, _event=None):
        self.audio.play_click()

    def _close_app(self):
        self.audio.stop()
        self.destroy()

    def _build_main_menu(self):
        self.main_container = tk.Frame(self, bg="#eaf0f7")
        self.main_container.pack(fill="both", expand=True)

        self.header = tk.Label(
            self.main_container,
            text="Bottle Sort",
            font=("Georgia", 42, "bold"),
            bg="#eaf0f7",
            fg="#14725f",
            relief="raised",
            borderwidth=3,
            highlightthickness=1,
            highlightbackground="#a8d3c7",
            padx=14,
            pady=3,
        )
        self.header.pack(pady=(42, 4))

        self.menu_scene = tk.Canvas(
            self.main_container,
            height=230,
            bg="#eaf0f7",
            highlightthickness=0,
        )
        self.menu_scene.pack(fill="x", padx=100, pady=(0, 8))

        self.menu_buttons = tk.Frame(self.main_container, bg="#eaf0f7")
        self.menu_buttons.pack(pady=6)

        self.play_btn = self._button(self.menu_buttons, "play", self.start_level, width=24)
        self.play_btn.pack(pady=8)

        self.levels_btn = self._button(self.menu_buttons, "levels", self.show_level_select, width=24)
        self.levels_btn.pack(pady=8)

        self.settings_btn = self._button(self.menu_buttons, "settings", self.show_settings, width=24)
        self.settings_btn.pack(pady=8)

        self.exit_btn = self._button(self.menu_buttons, "exit", self._close_app, width=24)
        self.exit_btn.pack(pady=8)

        self.status_label = tk.Label(
            self.main_container,
            text=self._t("progress", done=0, total=len(self.campaign)),
            font=("Segoe UI", 12),
            bg="#eaf0f7",
            fg="#52677c",
        )
        self.status_label.pack(pady=(4, 2))
        self._animate_menu_scene()

    def _button(self, parent, key: str, command, *, width: int = 12):
        return RoundedButton(
            parent,
            text=self._t(key),
            command=command,
            width=width * 10 + 30,
            height=48,
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#245c82",
            activeforeground="#ffffff",
            activebackground="#3479a5",
        )

    def _build_game_screen(self):
        if hasattr(self, "game_frame"):
            return

        self.game_frame = tk.Frame(self, bg="#eaf0f7")
        self.game_frame.pack(fill="both", expand=True)

        top_bar = tk.Frame(self.game_frame, bg="#eaf0f7")
        top_bar.pack(fill="x", padx=20, pady=(16, 10))

        self.level_name = tk.Label(top_bar, text=self._t("level", number=1), font=("Segoe UI", 18, "bold"), bg="#eaf0f7", fg="#172c46")
        self.level_name.pack(side="left")

        self.moves_label = tk.Label(top_bar, text=self._t("moves", count=0), font=("Segoe UI", 12), bg="#eaf0f7", fg="#52677c")
        self.moves_label.pack(side="right", padx=(0, 12))

        self.timer_label = tk.Label(top_bar, text=self._t("time", value="00:00"), font=("Segoe UI", 12), bg="#eaf0f7", fg="#52677c")
        self.timer_label.pack(side="right", padx=(0, 12))

        controls = tk.Frame(self.game_frame, bg="#eaf0f7")
        controls.pack(fill="x", padx=20, pady=(0, 10))

        self.undo_btn = self._button(controls, "undo", self.undo_move)
        self.undo_btn.pack(side="left", padx=6)
        self.restart_btn = self._button(controls, "restart", self.restart_level)
        self.restart_btn.pack(side="left", padx=6)
        self.hint_btn = self._button(controls, "hint", self.show_hint)
        self.hint_btn.pack(side="left", padx=6)
        self.check_btn = self._button(controls, "check", self.check_solvability, width=16)
        self.check_btn.pack(side="left", padx=6)
        self.menu_btn = self._button(controls, "menu", self.show_menu)
        self.menu_btn.pack(side="left", padx=6)
        self.previous_btn = self._button(controls, "previous", self.previous_level, width=14)
        self.previous_btn.pack(side="left", padx=6)
        self.next_btn = self._button(controls, "next", self.next_level, width=16)
        self.next_btn.pack(side="left", padx=6)

        self.game_status = tk.Label(
            self.game_frame,
            text="",
            font=("Segoe UI", 11, "bold"),
            bg="#eaf0f7",
            fg="#235b3c",
            anchor="w",
        )
        self.game_status.pack(fill="x", padx=26, pady=(0, 4))

        self.board = tk.Frame(self.game_frame, bg="#eaf0f7")
        self.board.pack(fill="both", expand=True, padx=20, pady=10)
        self.board.bind("<Configure>", lambda event: self._render_board())

    def _build_settings(self):
        if hasattr(self, "settings_frame"):
            return

        self.settings_frame = tk.Frame(self, bg="#eaf0f7")

        self.settings_title = tk.Label(self.settings_frame, text=self._t("settings"), font=("Segoe UI", 24, "bold"), bg="#eaf0f7", fg="#172c46")
        self.settings_title.pack(pady=20)

        self.sound_var = tk.BooleanVar(value=self.sound_enabled)
        self.music_var = tk.BooleanVar(value=self.music_enabled)
        self.patterns_var = tk.BooleanVar(value=self.patterns_enabled)
        self.lang_var = tk.StringVar(value=self.language)

        self.sound_check = tk.Checkbutton(self.settings_frame, text=self._t("sound"), variable=self.sound_var, bg="#eaf0f7", activebackground="#eaf0f7")
        self.sound_check.pack(anchor="w", padx=30)
        self.music_check = tk.Checkbutton(self.settings_frame, text=self._t("music"), variable=self.music_var, bg="#eaf0f7", activebackground="#eaf0f7")
        self.music_check.pack(anchor="w", padx=30)
        self.patterns_check = tk.Checkbutton(self.settings_frame, text=self._t("patterns"), variable=self.patterns_var, bg="#eaf0f7", activebackground="#eaf0f7")
        self.patterns_check.pack(anchor="w", padx=30)

        lang_frame = tk.Frame(self.settings_frame, bg="#eaf0f7")
        lang_frame.pack(anchor="w", padx=30, pady=12)
        self.language_label = tk.Label(lang_frame, text=f"{self._t('language')}:", bg="#eaf0f7")
        self.language_label.pack(side="left")
        tk.OptionMenu(lang_frame, self.lang_var, "EN", "RU", command=lambda _value: self._set_language()).pack(side="left")

        button_row = tk.Frame(self.settings_frame, bg="#eaf0f7")
        button_row.pack(pady=24)
        self.settings_save = self._button(button_row, "save", self.save_settings, width=28)
        self.settings_save.pack(pady=5)
        self.settings_back = self._button(button_row, "back", self.show_menu, width=28)
        self.settings_back.pack(pady=5)
        self.settings_reset = self._button(button_row, "reset", self.reset_progress, width=28)
        self.settings_reset.pack(pady=5)

    def _build_level_select(self):
        if hasattr(self, "level_select_frame"):
            return

        self.level_select_frame = tk.Frame(self, bg="#eaf0f7")
        self.level_select_frame.pack(fill="both", expand=True)
        self.level_scene = tk.Canvas(
            self.level_select_frame,
            bg="#eaf0f7",
            highlightthickness=0,
        )
        self.level_scene.place(relwidth=1, relheight=1)

        self.level_select_title = tk.Label(self.level_select_frame, text=self._t("campaign"), font=("Segoe UI", 24, "bold"), bg="#eaf0f7", fg="#172c46")
        self.level_select_title.pack(pady=(24, 4))
        self.level_select_hint = tk.Label(self.level_select_frame, text=self._t("select_level"), font=("Segoe UI", 11), bg="#eaf0f7", fg="#61758b")
        self.level_select_hint.pack(pady=(0, 10))

        self.level_panel = tk.Frame(
            self.level_select_frame,
            bg="#d9e7f2",
            highlightthickness=2,
            highlightbackground="#a7bfd1",
        )
        self.level_panel.pack(fill="both", expand=True, padx=180, pady=10)
        self.level_scroll = tk.Canvas(
            self.level_panel,
            bg="#eaf2f8",
            highlightthickness=0,
        )
        self.level_scroll.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar = tk.Scrollbar(self.level_panel, orient="vertical", command=self.level_scroll.yview)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        self.level_scroll.configure(yscrollcommand=scrollbar.set)
        self.level_grid = tk.Frame(self.level_scroll, bg="#eaf2f8")
        self.level_grid_window = self.level_scroll.create_window(
            (0, 0), window=self.level_grid, anchor="nw"
        )
        self.level_grid.bind(
            "<Configure>",
            lambda _event: self.level_scroll.configure(
                scrollregion=self.level_scroll.bbox("all")
            ),
        )
        self.level_scroll.bind(
            "<Configure>",
            lambda event: self.level_scroll.itemconfigure(
                self.level_grid_window, width=event.width
            ),
        )
        self.level_scroll.bind(
            "<MouseWheel>",
            lambda event: self.level_scroll.yview_scroll(
                -1 if event.delta > 0 else 1, "units"
            ),
        )
        self.level_buttons = []
        for idx, level in enumerate(self.campaign):
            card = tk.Frame(
                self.level_grid,
                bg="#ffffff",
                highlightthickness=1,
                highlightbackground="#c4d4e0",
            )
            card.grid(row=idx // 4, column=idx % 4, padx=7, pady=7, sticky="nsew")
            button = RoundedButton(
                card,
                text="",
                command=lambda level_index=idx: self.start_level(level_index),
                width=128,
                height=82,
                font=("Segoe UI", 11, "bold"),
                fg="#214760",
                bg="#f8fcff",
                activeforeground="#ffffff",
                activebackground="#3479a5",
            )
            button.pack(fill="both", expand=True, padx=3, pady=3)
            self.level_buttons.append((button, level))
        for column in range(4):
            self.level_grid.grid_columnconfigure(column, weight=1)
        self._refresh_level_cards()

        footer = tk.Frame(self.level_select_frame, bg="#eaf0f7")
        footer.pack(pady=8)
        self.level_select_back = self._button(footer, "back", self.show_menu)
        self.level_select_back.pack(side="left", padx=6)
        self._animate_level_scene()

    def show_menu(self):
        self._stop_timer()
        if hasattr(self, "level_state") and self.level_state:
            self._save_progress()
        self._hide_all_frames()
        self.main_container.pack(fill="both", expand=True)
        self._refresh_progress()
        self._menu_scene_requested = True
        if self._menu_animation_job is None:
            self._menu_animation_job = self.after(80, self._animate_menu_scene)

    def show_level_select(self):
        self._build_level_select()
        self._hide_all_frames()
        self.level_select_frame.pack(fill="both", expand=True)
        self._level_scene_requested = True
        if self._level_animation_job is None:
            self._level_animation_job = self.after(80, self._animate_level_scene)

    def show_settings(self):
        self._build_settings()
        self._hide_all_frames()
        self.settings_frame.pack(fill="both", expand=True)

    def _hide_all_frames(self):
        self._menu_scene_requested = False
        self._level_scene_requested = False
        for frame_name in ["main_container", "game_frame", "settings_frame", "level_select_frame"]:
            frame = getattr(self, frame_name, None)
            if frame is not None:
                frame.pack_forget()

    def _animate_menu_scene(self) -> None:
        canvas = self.menu_scene
        canvas.delete("all")
        width = max(canvas.winfo_width(), self.winfo_width() - 200, 500)
        elapsed = time.monotonic()
        colors = (
            COLOR_PALETTE[2], COLOR_PALETTE[5], COLOR_PALETTE[9], COLOR_PALETTE[13],
            COLOR_PALETTE[20], COLOR_PALETTE[23], COLOR_PALETTE[27], COLOR_PALETTE[30],
        )
        centers = [
            width * (index + 1) / (len(colors) + 1) + math.sin(elapsed * 0.55 + index * 1.8) * 9
            for index in range(len(colors))
        ]
        pour_period = 1.35
        pour_cycle = elapsed % (pour_period * len(colors))
        source_index = int(pour_cycle // pour_period)
        target_index = (source_index + 1) % len(colors)
        pour_time = pour_cycle % pour_period
        pour_amount = min(0.18, pour_time / 0.95 * 0.18)
        fills = [0.35, 0.58, 0.42, 0.62, 0.3, 0.48, 0.54, 0.38]
        fills[source_index] -= pour_amount
        fills[target_index] += pour_amount
        bottle_tops = []

        for bubble in range(24):
            x = (bubble * 53 + elapsed * (12 + bubble % 7)) % width
            y = 230 - ((elapsed * (18 + bubble % 9) + bubble * 29) % 250)
            radius = 2 + bubble % 3
            canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                outline=self._blend_color(
                    COLOR_PALETTE[bubble % len(COLOR_PALETTE)], "#ffffff", 0.25
                ),
                width=1,
            )

        for index, (center_x, color) in enumerate(zip(centers, colors)):
            float_y = math.sin(elapsed * 1.05 + index * 1.3) * 13
            bottle_height = 110 + (index % 3) * 13
            top = 38 + float_y + (116 - bottle_height) / 2
            bottom = top + bottle_height
            body_width = 34 + (index % 3) * 7
            neck_width = 18
            left = center_x - body_width / 2
            right = center_x + body_width / 2
            neck_left = center_x - neck_width / 2
            neck_right = center_x + neck_width / 2
            bottle_tops.append((center_x, top + 23, bottom - 9))
            if index % 3 == 0:
                outline = (
                    neck_left, top, neck_right, top, neck_right, top + 17,
                    right - 2, top + 31, right, bottom - 8, right - 4, bottom,
                    left + 4, bottom, left, bottom - 8, left + 2, top + 31,
                    neck_left, top + 17,
                )
            elif index % 3 == 1:
                outline = (
                    neck_left, top, neck_right, top, neck_right, top + 24,
                    right, top + 34, right, bottom, left, bottom, left, top + 34,
                    neck_left, top + 24,
                )
            else:
                outline = (
                    neck_left, top, neck_right, top, neck_right, top + 18,
                    center_x + body_width * 0.47, top + 35,
                    center_x + body_width * 0.5, bottom - 22,
                    center_x + body_width * 0.34, bottom,
                    center_x - body_width * 0.34, bottom,
                    center_x - body_width * 0.5, bottom - 22,
                    center_x - body_width * 0.47, top + 35,
                    neck_left, top + 18,
                )
            canvas.create_polygon(
                outline,
                fill="#f8fcff",
                outline="#8da5ba",
                width=2,
                smooth=index % 3 == 2,
                splinesteps=12,
            )
            liquid_top = bottom - 10 - max(0.12, min(0.88, fills[index])) * (bottle_height - 42)
            canvas.create_rectangle(left + 5, liquid_top, right - 5, bottom - 10, fill=color, outline="")
            canvas.create_line(left + 7, liquid_top, right - 7, liquid_top, fill="#ffffff", width=2)
            liquid_bottom = bottom - 12
            liquid_span = max(3, liquid_bottom - liquid_top)

            for bubble in range(2):
                bubble_y = liquid_bottom - ((elapsed * 13 + bubble * 31 + index * 19) % liquid_span)
                bubble_x = center_x + math.sin(elapsed * 1.8 + bubble + index) * (body_width * 0.23)
                canvas.create_oval(
                    bubble_x - 2, bubble_y - 2, bubble_x + 2, bubble_y + 2,
                    outline=self._blend_color(color, "#ffffff", 0.42), width=1,
                )
            canvas.create_line(left + 6, top + 36, left + 6, bottom - 18, fill="#ffffff", width=2)
            canvas.create_line(neck_left, top + 6, neck_right, top + 6, fill="#8da5ba", width=2)
            for sparkle in range(2):
                sparkle_x = center_x + math.sin(elapsed * 1.8 + index + sparkle) * (body_width + 10)
                sparkle_y = top + 27 + sparkle * 34 + math.cos(elapsed + index * sparkle) * 5
                canvas.create_oval(
                    sparkle_x - 2, sparkle_y - 2, sparkle_x + 2, sparkle_y + 2,
                    fill=COLOR_PALETTE[(index * 5 + sparkle * 3) % len(COLOR_PALETTE)],
                    outline="",
                )

        if pour_time < 0.95:
            x0, y0, _ = bottle_tops[source_index]
            x1, y1, _ = bottle_tops[target_index]
            for drop_index in range(5):
                progress = (pour_time / 0.95 + drop_index * 0.19) % 1.0
                x = x0 + (x1 - x0) * progress
                y = y0 + (y1 - y0) * progress - 20 * math.sin(progress * math.pi)
                canvas.create_oval(
                    x - 3, y - 4, x + 3, y + 4,
                    fill=self._blend_color(colors[source_index], "#ffffff", 0.16),
                    outline="",
                )

        self._menu_animation_job = (
            self.after(40 if self.main_container.winfo_ismapped() else 100, self._animate_menu_scene)
            if self._menu_scene_requested
            else None
        )

    def _animate_level_scene(self) -> None:
        canvas = self.level_scene
        canvas.delete("all")
        width = max(canvas.winfo_width(), self.winfo_width(), 900)
        height = max(canvas.winfo_height(), self.winfo_height() - 100, 600)
        elapsed = time.monotonic()
        background = "#eaf0f7"
        columns = (0.045, 0.12, 0.88, 0.955)
        rows = (0.14, 0.32, 0.5, 0.68, 0.86)
        bottles = []
        for row, row_position in enumerate(rows):
            for column, column_position in enumerate(columns):
                index = row * len(columns) + column
                center_x = width * column_position + math.sin(elapsed * 0.3 + index) * 4
                center_y = height * row_position + math.sin(elapsed * 0.42 + index * 1.7) * 5
                bottle_height = 72 + (index * 17 % 43)
                body_width = 29 + (index * 11 % 17)
                neck_width = 10 + (index % 3) * 3
                top = center_y - bottle_height / 2
                bottom = center_y + bottle_height / 2
                base_fill = 0.25 + (index * 7 % 7) * 0.075
                bottles.append(
                    {
                        "index": index,
                        "center_x": center_x,
                        "center_y": center_y,
                        "top": top,
                        "bottom": bottom,
                        "height": bottle_height,
                        "width": body_width,
                        "neck": neck_width,
                        "fill": base_fill,
                        "color": COLOR_PALETTE[(index * 5 + 2) % len(COLOR_PALETTE)],
                    }
                )

        cycle_duration = 1.8
        cycle = elapsed % (len(bottles) // 2 * cycle_duration)
        active_pair = int(cycle // cycle_duration)
        pour_progress = (cycle % cycle_duration) / cycle_duration
        source_index = (active_pair // 2) * 4 + (active_pair % 2) * 2
        target_index = source_index + 1
        transfer = min(0.2, pour_progress / 0.72 * 0.2)
        bottles[source_index]["fill"] -= transfer
        bottles[target_index]["fill"] += transfer

        for bottle in bottles:
            index = bottle["index"]
            center_x = bottle["center_x"]
            center_y = bottle["center_y"]
            top = bottle["top"]
            bottom = bottle["bottom"]
            bottle_height = bottle["height"]
            body_width = bottle["width"]
            neck_width = bottle["neck"]
            color = bottle["color"]
            fill = max(0.08, min(0.86, bottle["fill"]))
            left = center_x - body_width / 2
            right = center_x + body_width / 2
            neck_left = center_x - neck_width / 2
            neck_right = center_x + neck_width / 2
            spin = abs(math.cos(elapsed * 0.85 + index * 0.73))
            x_scale = 0.56 + spin * 0.44

            def rotate_x(x):
                return center_x + (x - center_x) * x_scale

            if index % 4 == 0:
                outline = (
                    neck_left, top, neck_right, top, neck_right, top + 16,
                    right, top + 27, right, bottom - 8, right - 5, bottom,
                    left + 5, bottom, left, bottom - 8, left, top + 27,
                    neck_left, top + 16,
                )
            elif index % 4 == 1:
                outline = (
                    neck_left, top, neck_right, top, neck_right, top + 21,
                    center_x + body_width * 0.48, top + 32, right, center_y + 8,
                    right - 2, bottom - 9, center_x, bottom,
                    left + 2, bottom - 9, left, center_y + 8,
                    center_x - body_width * 0.48, top + 32, neck_left, top + 21,
                )
            elif index % 4 == 2:
                outline = (
                    neck_left, top, neck_right, top, neck_right, top + 14,
                    center_x + body_width * 0.34, top + 23, right, top + 34,
                    right, bottom - 6, right - 6, bottom,
                    left + 6, bottom, left, bottom - 6, left, top + 34,
                    center_x - body_width * 0.34, top + 23, neck_left, top + 14,
                )
            else:
                outline = (
                    neck_left, top, neck_right, top, neck_right, top + 24,
                    right, top + 34, right, bottom - 12,
                    center_x + body_width * 0.3, bottom,
                    center_x - body_width * 0.3, bottom,
                    left, bottom - 12, left, top + 34, neck_left, top + 24,
                )
            outline = tuple(
                coordinate
                for position in range(0, len(outline), 2)
                for coordinate in (rotate_x(outline[position]), outline[position + 1])
            )
            glass = self._blend_color("#6e8aa3", background, 0.3)
            canvas.create_oval(
                rotate_x(left - 7), bottom + 4, rotate_x(right + 7), bottom + 11,
                fill=self._blend_color("#afc3d4", background, 0.5),
                outline="",
            )
            canvas.create_polygon(
                outline,
                fill="#f7fafc",
                outline=glass,
                width=2,
                smooth=True,
                splinesteps=12,
                tags=("level_bottle",),
            )

            liquid_top = bottom - 8 - (bottle_height - 28) * fill
            liquid_left = rotate_x(left + 5)
            liquid_right = rotate_x(right - 5)
            canvas.create_polygon(
                liquid_left, liquid_top,
                liquid_right, liquid_top + math.sin(elapsed * 3 + index) * 1.5,
                liquid_right, bottom - 8,
                liquid_left, bottom - 8,
                fill=self._blend_color(color, background, 0.35),
                outline="",
            )
            for bubble in range(3):
                span = max(8, bottom - liquid_top - 12)
                bubble_y = bottom - 11 - (
                    (elapsed * 23 + bubble * 19 + index * 13) % span
                )
                bubble_x = rotate_x(
                    center_x + math.sin(elapsed * 2 + bubble + index) * body_width * 0.2
                )
                radius = 1.5 + bubble % 2
                canvas.create_oval(
                    bubble_x - radius,
                    bubble_y - radius,
                    bubble_x + radius,
                    bubble_y + radius,
                    outline=self._blend_color(color, "#ffffff", 0.45),
                    width=1,
                )
            canvas.create_line(
                rotate_x(left + body_width * 0.23),
                top + 30,
                rotate_x(left + body_width * 0.23),
                bottom - 17,
                fill="#ffffff",
                width=2,
            )
            canvas.create_oval(
                rotate_x(neck_left),
                top - 2,
                rotate_x(neck_right),
                top + 5,
                outline=glass,
                width=2,
            )
            canvas.create_polygon(
                outline,
                fill="",
                outline=glass,
                width=2,
                smooth=True,
                splinesteps=12,
            )

        if pour_progress < 0.72:
            source = bottles[source_index]
            target = bottles[target_index]
            x0, y0 = source["center_x"], source["top"] + 15
            x1, y1 = target["center_x"], target["top"] + 18
            stream_color = self._blend_color(source["color"], "#ffffff", 0.18)
            canvas.create_line(x0, y0, x1, y1, fill=stream_color, width=2, smooth=True)
            for drop in range(4):
                progress = (pour_progress / 0.72 + drop * 0.24) % 1.0
                x = x0 + (x1 - x0) * progress
                y = y0 + (y1 - y0) * progress - 8 * math.sin(progress * math.pi)
                canvas.create_oval(
                    x - 2,
                    y - 3,
                    x + 2,
                    y + 3,
                    fill=stream_color,
                    outline="",
                )

        self._level_animation_job = (
            self.after(110 if self.level_select_frame.winfo_ismapped() else 150, self._animate_level_scene)
            if self._level_scene_requested
            else None
        )

    def _refresh_progress(self):
        if self.progress_load_error:
            self.status_label.config(
                text=self._t("progress_error", error=self.progress_load_error),
                fg="#a44232",
            )
            return
        completed = len(self.progress.get("completed", []))
        self.status_label.config(
            text=self._t("progress", done=completed, total=len(self.campaign)),
            fg="#52677c",
        )

    def _refresh_level_cards(self):
        completed = set(self.progress.get("completed", []))
        for button, level in self.level_buttons:
            is_completed = level.id in completed
            button.config(
                text=f"{'✓' if is_completed else '✦'}\n{self._t('level', number=level.id)}\n{level.color_count} {self._t('colors')}",
                fg="#1c694f" if is_completed else "#214760",
                bg="#e5f7ed" if is_completed else "#f8fcff",
            )

    def _set_language(self):
        self.language = self.lang_var.get()
        self._apply_language()

    def _load_progress(self):
        if not self.save_path.exists():
            self.progress = {"completed": [], "settings": {}}
            return
        try:
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Progress file must contain an object.")
            self.progress = data
            settings = data.get("settings", {})
            self.sound_enabled = bool(settings.get("sound_enabled", self.sound_enabled))
            self.music_enabled = bool(settings.get("music_enabled", self.music_enabled))
            self.patterns_enabled = bool(settings.get("patterns_enabled", self.patterns_enabled))
            self.language = settings.get("language", self.language)
            if self.language not in TEXT:
                self.language = "EN"
            self.sound_var.set(self.sound_enabled)
            self.music_var.set(self.music_enabled)
            self.patterns_var.set(self.patterns_enabled)
            self.lang_var.set(self.language)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.progress = {"completed": [], "settings": {}}
            self.progress_load_error = str(error)

    @staticmethod
    def _make_layer_tokens(level_id: int, state) -> tuple[tuple[str, ...], ...]:
        return tuple(
            tuple(f"{level_id}:{bottle_index}:{layer_index}" for layer_index in range(len(bottle)))
            for bottle_index, bottle in enumerate(state)
        )

    def _reveal_hidden_top_runs(self, state, layer_tokens) -> None:
        for bottle_index in concealed_bottle_indices(self.current_mechanics):
            if bottle_index >= len(state) or not state[bottle_index]:
                continue
            bottle = state[bottle_index]
            top_color = bottle[-1]
            run_length = 1
            while run_length < len(bottle) and bottle[-run_length - 1] == top_color:
                run_length += 1
            self.revealed_layer_tokens.update(layer_tokens[bottle_index][-run_length:])

    def _save_progress(self):
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(self.progress)
        payload["settings"] = {
            "sound_enabled": self.sound_enabled,
            "music_enabled": self.music_enabled,
            "patterns_enabled": self.patterns_enabled,
            "language": self.language,
        }
        if self.level_state:
            payload["current_level"] = self.level_index
            payload["current_state"] = [list(bottle) for bottle in self.level_state]
            payload["move_count"] = self.move_count
            payload["elapsed_seconds"] = self._elapsed()
            payload["solution_path"] = [list(move) for move in self.solution_path]
            if len(self.layer_tokens) == len(self.level_state):
                payload["current_layer_tokens"] = [list(bottle) for bottle in self.layer_tokens]
                payload["revealed_layer_tokens"] = sorted(self.revealed_layer_tokens)
        self.save_path.write_text(json.dumps(payload), encoding="utf-8")
        self.progress = payload

    def start_level(self, level_index=None):
        if level_index is None:
            level_index = int(self.progress.get("current_level", self.level_index))
        if not 0 <= level_index < len(self.campaign):
            level_index = 0
        level = self.campaign[level_index]
        self.level_index = level_index
        self.current_mechanics = level.mechanics_config or {}
        self._build_game_screen()
        self._hide_all_frames()
        self.game_frame.pack(fill="both", expand=True)

        self.selected = None
        self.game_status.config(text="", fg="#235b3c")
        self.next_btn.config(state="normal")
        snapshot_matches = self.progress.get("current_level") == level_index
        saved_state = self.progress.get("current_state") if snapshot_matches else None
        self.level_state = (
            tuple(tuple(bottle) for bottle in saved_state)
            if saved_state
            else tuple(tuple(bottle) for bottle in level.state)
        )
        self.initial_state = tuple(tuple(bottle) for bottle in level.state)
        self.initial_layer_tokens = self._make_layer_tokens(level.id, self.initial_state)
        saved_tokens = self.progress.get("current_layer_tokens") if snapshot_matches else None
        valid_saved_tokens = (
            isinstance(saved_tokens, list)
            and len(saved_tokens) == len(self.level_state)
            and all(
                isinstance(tokens, list)
                and len(tokens) == len(bottle)
                and all(isinstance(token, str) for token in tokens)
                for tokens, bottle in zip(saved_tokens, self.level_state)
            )
        )
        if valid_saved_tokens:
            self.layer_tokens = tuple(tuple(tokens) for tokens in saved_tokens)
            all_tokens = [token for bottle in self.layer_tokens for token in bottle]
            valid_saved_tokens = (
                len(set(all_tokens)) == len(all_tokens)
                and set(all_tokens)
                == {token for bottle in self.initial_layer_tokens for token in bottle}
            )
        if not valid_saved_tokens:
            self.layer_tokens = self._make_layer_tokens(level.id, self.level_state)
        hidden_bottles = concealed_bottle_indices(self.current_mechanics)
        if valid_saved_tokens:
            self.secret_layer_tokens = {
                token
                for bottle_index in hidden_bottles
                if bottle_index < len(self.initial_layer_tokens)
                for token in self.initial_layer_tokens[bottle_index]
            }
            saved_revealed = self.progress.get("revealed_layer_tokens", [])
            self.revealed_layer_tokens = (
                set(saved_revealed) & self.secret_layer_tokens
                if isinstance(saved_revealed, list)
                and all(isinstance(token, str) for token in saved_revealed)
                else set()
            )
        else:
            self.secret_layer_tokens = {
                token
                for bottle_index in hidden_bottles
                if bottle_index < len(self.layer_tokens)
                for token in self.layer_tokens[bottle_index]
            }
            self.revealed_layer_tokens = set()
        self._reveal_hidden_top_runs(self.level_state, self.layer_tokens)
        self.history = []
        self.move_count = int(self.progress.get("move_count", 0)) if snapshot_matches else 0
        self.elapsed_seconds = float(self.progress.get("elapsed_seconds", 0.0)) if snapshot_matches else 0.0
        saved_path = self.progress.get("solution_path", []) if snapshot_matches else level.solution
        self.solution_path = [tuple(move) for move in saved_path]
        self.level_started_at = time.monotonic()
        self.hints_remaining = 3
        self._render_board()
        self._update_game_labels(level)
        self._tick_timer()
        self._save_progress()
        self._check_dead_end()

    def _update_game_labels(self, level: LevelDefinition):
        self.level_name.config(text=self._t("level", number=level.id))
        self.moves_label.config(text=self._t("moves", count=self.move_count))
        self.previous_btn.config(state="normal" if self.level_index > 0 else "disabled")
        self.next_btn.config(
            state="normal" if self.level_index + 1 < len(self.campaign) else "disabled"
        )

    def next_level(self):
        if self.level_index + 1 < len(self.campaign):
            self.start_level(self.level_index + 1)

    def previous_level(self):
        if self.level_index > 0:
            self.start_level(self.level_index - 1)

    @staticmethod
    def _bottle_geometry(capacities, base_capacity: int, bottle_index: int):
        scale = math.sqrt(capacities[bottle_index] / base_capacity)
        max_scale = max(math.sqrt(value / base_capacity) for value in capacities)
        baseline = 14 + (195 - 14) * max_scale
        canvas_height = math.ceil(max(14 + (250 - 14) * max_scale, baseline + 48))
        return scale, baseline, canvas_height

    def _render_board(self):
        for child in self.board.winfo_children():
            child.destroy()

        level = self.campaign[self.level_index]
        bottles = list(self.level_state)
        columns = max(1, min(len(bottles), max(1, (self.winfo_width() - 70) // 104)))
        self.bottle_canvases = []
        capacities = level.capacities
        frozen_bottles = set(self.current_mechanics.get("frozen_bottles", []))
        stone_bottles = set(self.current_mechanics.get("stone_bottles", []))
        decoy_bottles = set(self.current_mechanics.get("decoy_bottles", []))
        concealed_bottles = concealed_bottle_indices(self.current_mechanics)

        for idx, bottle in enumerate(bottles):
            bottle_frame = tk.Frame(self.board, bg="#eaf0f7", padx=3, pady=3)
            bottle_frame.grid(row=idx // columns, column=idx % columns, padx=6, pady=4)

            scale, baseline, canvas_height = self._bottle_geometry(
                capacities, level.capacity, idx
            )
            canvas = tk.Canvas(
                bottle_frame,
                width=86,
                height=canvas_height,
                bg="#eaf0f7",
                highlightthickness=0,
            )
            canvas.pack()
            self.bottle_canvases.append(canvas)

            def sy(value):
                return baseline + (value - 195) * scale

            frozen = idx in frozen_bottles
            stone = idx in stone_bottles
            decoy = idx in decoy_bottles
            concealed = idx in concealed_bottles
            glass_shape = tuple(
                coordinate
                for x, y in (
                    (31, 22), (55, 22), (55, 48), (64, 62), (64, 180),
                    (59, 195), (27, 195), (22, 180), (22, 62), (31, 48),
                )
                for coordinate in (x, sy(y))
            )
            canvas.create_polygon(
                glass_shape,
                smooth=True,
                splinesteps=20,
                fill="#dff7ff" if frozen else ("#9da9b6" if stone else "#f9fcff"),
                outline="#218cb4" if frozen else ("#455565" if stone else "#8da5ba"),
                width=2,
            )

            selection_outline = None
            if self.selected == idx:
                selection_outline = "#ed9b27"
            elif self.selected is not None and can_pour(
                self.level_state, self.selected, idx, capacities, self.current_mechanics
            ):
                selection_outline = "#16884e"

            liquid_height = 108 / max(1, capacities[idx])
            for layer_idx, color in enumerate(bottle):
                y_bottom = 179 - layer_idx * liquid_height
                y_top = y_bottom - liquid_height
                layer_token = self.layer_tokens[idx][layer_idx]
                unknown = (
                    concealed
                    and layer_token in self.secret_layer_tokens
                    and layer_token not in self.revealed_layer_tokens
                )
                base_color = "#101010" if unknown else self._color_for(color)
                canvas.create_rectangle(
                    26,
                    sy(y_top),
                    60,
                    sy(y_bottom) + 1,
                    fill=base_color,
                    outline=self._blend_color(base_color, "#15283d", 0.38),
                    width=1,
                )
                if layer_idx == len(bottle) - 1:
                    canvas.create_oval(
                        26, sy(y_top - 3), 60, sy(y_top + 4),
                        fill=self._blend_color(base_color, "#ffffff", 0.12),
                        outline="",
                    )
                if unknown:
                    canvas.create_text(
                        43,
                        sy((y_top + y_bottom) / 2),
                        text="?",
                        fill="#ffffff",
                        font=("Segoe UI", 13, "bold"),
                    )
                elif self.patterns_enabled:
                    marks = ("●", "▲", "■", "◆", "✚", "✦", "⬟", "✿")
                    canvas.create_text(
                        43,
                        sy((y_top + y_bottom) / 2),
                        text=marks[zlib.crc32(color.encode("utf-8")) % len(marks)],
                        fill=self._pattern_ink(base_color),
                        font=("Segoe UI", 10, "bold"),
                    )
            canvas.create_polygon(
                glass_shape,
                smooth=True,
                splinesteps=20,
                fill="",
                outline="#218cb4" if frozen else ("#455565" if stone else "#718ba2"),
                width=3 if frozen or stone else 2,
            )
            if selection_outline:
                canvas.create_polygon(
                    glass_shape,
                    smooth=True,
                    splinesteps=20,
                    fill="",
                    outline=selection_outline,
                    width=4,
                )
            canvas.create_oval(
                29, sy(18), 57, sy(27),
                fill="#edf8fd",
                outline="#718ba2",
                width=2,
            )
            canvas.create_oval(
                34, sy(20), 52, sy(24),
                fill="#b9cedb",
                outline="#ffffff",
                width=1,
            )
            canvas.create_line(28, sy(72), 28, sy(162), fill="#ffffff", width=2)
            canvas.create_line(31, sy(48), 31, sy(66), fill="#ffffff", width=2)
            canvas.create_line(58, sy(70), 58, sy(160), fill="#d0dfec", width=2)
            canvas.create_arc(28, sy(184), 58, sy(201), start=190, extent=160, outline="#d9e5ef", width=2)
            canvas.create_arc(30, sy(187), 56, sy(201), start=200, extent=140, outline="#ffffff", width=1)

            if frozen:
                for frost_y in (82, 122, 160):
                    canvas.create_line(22, sy(frost_y), 29, sy(frost_y - 10), 35, sy(frost_y + 4), fill="#a5efff", width=2)
                    canvas.create_line(57, sy(frost_y + 2), 64, sy(frost_y - 8), fill="#a5efff", width=2)
                badge_text = self._t("mechanic_ice")
                badge_fill, badge_outline = "#c8f4ff", "#178eb7"
            elif stone:
                for crack_y in (86, 126, 166):
                    canvas.create_line(23, sy(crack_y), 37, sy(crack_y + 7), 45, sy(crack_y - 4), fill="#586779", width=2)
                    canvas.create_line(53, sy(crack_y + 4), 63, sy(crack_y + 11), fill="#586779", width=2)
                badge_text = self._t("mechanic_stone")
                badge_fill, badge_outline = "#d5dce3", "#526273"
            elif decoy:
                badge_text = self._t("mechanic_decoy")
                badge_fill, badge_outline = "#ffe4a8", "#bd7112"
            else:
                badge_text, badge_fill, badge_outline = "", "", ""

            if badge_text:
                canvas.create_oval(56, sy(15), 79, sy(38), fill=badge_fill, outline=badge_outline, width=2)
                canvas.create_text(67.5, sy(26), text="D" if decoy else ("❄" if frozen else "◆"),
                                   fill=badge_outline, font=("Segoe UI", 10, "bold"))

            if is_bottle_complete(bottle, capacities[idx]):
                canvas.create_rectangle(
                    30, sy(15), 56, sy(29),
                    fill="#d4dee8",
                    outline="#31485f",
                    width=2,
                )
                canvas.create_line(33, sy(18), 53, sy(18), fill="#ffffff", width=2)

            canvas.bind("<ButtonPress-1>", lambda event, idx=idx: self._begin_drag(idx))
            canvas.bind("<ButtonRelease-1>", lambda event, idx=idx: self._end_drag(idx))
            canvas.create_text(43, baseline + 40, text=str(idx + 1), fill="#344b64", font=("Segoe UI", 10, "bold"))

    def _color_for(self, color: str) -> str:
        if color.startswith("C") and color[1:].isdigit():
            return COLOR_PALETTE[int(color[1:]) % len(COLOR_PALETTE)]
        hue = zlib.crc32(color.encode("utf-8")) / 0x100000000
        red, green, blue = colorsys.hsv_to_rgb(hue, 0.9, 0.78)
        return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"

    @staticmethod
    def _blend_color(first: str, second: str, amount: float) -> str:
        left = tuple(int(first[index:index + 2], 16) for index in (1, 3, 5))
        right = tuple(int(second[index:index + 2], 16) for index in (1, 3, 5))
        channels = tuple(round(a + (b - a) * amount) for a, b in zip(left, right))
        return f"#{channels[0]:02x}{channels[1]:02x}{channels[2]:02x}"

    @staticmethod
    def _pattern_ink(color: str) -> str:
        red, green, blue = (int(color[index:index + 2], 16) for index in (1, 3, 5))
        luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
        return "#ffffff" if luminance < 0.52 else "#102238"

    def _begin_drag(self, index: int):
        if self.animating:
            return
        if self.selected is not None and index != self.selected:
            self._drag_source = self.selected
        elif self.level_state[index]:
            self._drag_source = index

    def _end_drag(self, index: int):
        if self.animating:
            return
        source = getattr(self, "_drag_source", None)
        self._drag_source = None
        if source is not None and source != index and can_pour(
            self.level_state,
            source,
            index,
            self.campaign[self.level_index].capacities,
            self.current_mechanics,
        ):
            self.selected = None
            self._animate_move(source, index)
            return
        if source == index and self.selected == index:
            self.selected = None
            self._render_board()
            return
        if source == index and self.selected is None:
            self.selected = index
            self._render_board()
            return
        if self.selected is not None and index != self.selected and can_pour(
            self.level_state,
            self.selected,
            index,
            self.campaign[self.level_index].capacities,
            self.current_mechanics,
        ):
            source = self.selected
            self.selected = None
            self._animate_move(source, index)
            return
        if source is not None and self.selected is None:
            self.selected = source
        self._render_board()

    def _animate_move(self, source: int, target: int) -> None:
        source_canvas = self.bottle_canvases[source]
        target_canvas = self.bottle_canvases[target]
        color = self._color_for(self.level_state[source][-1])
        level = self.campaign[self.level_index]
        source_scale, source_baseline, _ = self._bottle_geometry(
            level.capacities, level.capacity, source
        )
        target_scale, target_baseline, _ = self._bottle_geometry(
            level.capacities, level.capacity, target
        )
        x0 = source_canvas.winfo_rootx() + source_canvas.winfo_width() // 2 - self.winfo_rootx() - 14
        y0 = source_canvas.winfo_rooty() + int(
            source_baseline + (22 - 195) * source_scale + 18
        ) - self.winfo_rooty()
        x1 = target_canvas.winfo_rootx() + target_canvas.winfo_width() // 2 - self.winfo_rootx() - 14
        y1 = target_canvas.winfo_rooty() + int(
            target_baseline + (70 - 195) * target_scale
        ) - self.winfo_rooty()
        droplet = tk.Label(self, bg=color, relief="raised", borderwidth=1)
        droplet.place(x=x0, y=y0, width=28, height=16)
        self._draw_tilting_bottle(source, target)
        self.animating = True
        started = time.monotonic()
        duration = SoundManager.pour_duration
        self.audio.play_pour()

        def animate() -> None:
            progress = min(1.0, (time.monotonic() - started) / duration)
            x = x0 + (x1 - x0) * progress
            y = y0 + (y1 - y0) * progress - 18 * (1 - abs(2 * progress - 1))
            droplet.place_configure(x=int(x), y=int(y))
            if progress < 1:
                self.after(16, animate)
                return
            droplet.destroy()
            source_canvas.delete("pour_tilt")
            self.animating = False
            self._apply_move(source, target)
            self._render_board()

        animate()

    def _draw_tilting_bottle(self, source: int, target: int) -> None:
        canvas = self.bottle_canvases[source]
        level = self.campaign[self.level_index]
        capacity = level.capacities[source]
        scale, baseline, _ = self._bottle_geometry(
            level.capacities, level.capacity, source
        )

        def sy(value):
            return baseline + (value - 195) * scale

        direction = 1 if target > source else -1
        angle = direction * 0.14
        pivot_x, pivot_y = 43, sy(180)

        def rotate(points):
            cosine, sine = math.cos(angle), math.sin(angle)
            result = []
            for index in range(0, len(points), 2):
                dx = points[index] - pivot_x
                dy = points[index + 1] - pivot_y
                result.extend((
                    pivot_x + dx * cosine - dy * sine,
                    pivot_y + dx * sine + dy * cosine,
                ))
            return result

        tags = ("pour_tilt",)
        canvas.create_rectangle(15, sy(14), 79, sy(204), fill="#eaf0f7", outline="", tags=tags)
        glass_shape = [
            31, sy(22), 55, sy(22), 55, sy(48), 64, sy(62),
            64, sy(180), 59, sy(195), 27, sy(195), 22, sy(180),
            22, sy(62), 31, sy(48),
        ]
        canvas.create_polygon(
            *rotate(glass_shape),
            fill="#f9fcff",
            outline="#718ba2",
            width=2,
            smooth=True,
            tags=tags,
        )
        bottle = self.level_state[source]
        token_row = self.layer_tokens[source]
        layer_height = 108 / max(1, capacity)
        for layer_index, color in enumerate(bottle):
            y_bottom = 179 - layer_index * layer_height
            y_top = y_bottom - layer_height
            token = token_row[layer_index]
            unknown = (
                source in concealed_bottle_indices(self.current_mechanics)
                and token in self.secret_layer_tokens
                and token not in self.revealed_layer_tokens
            )
            liquid_color = "#101010" if unknown else self._color_for(color)
            canvas.create_polygon(
                *rotate([26, sy(y_top), 60, sy(y_top), 60, sy(y_bottom), 26, sy(y_bottom)]),
                fill=liquid_color,
                outline="",
                tags=tags,
            )
            if unknown:
                question = rotate([43, sy((y_top + y_bottom) / 2)])
                canvas.create_text(
                    question[0], question[1], text="?", fill="#ffffff",
                    font=("Segoe UI", 12, "bold"), tags=tags,
                )
        canvas.create_polygon(
            *rotate(glass_shape),
            fill="",
            outline="#718ba2",
            width=2,
            smooth=True,
            tags=tags,
        )

    def _apply_move(self, source, target):
        level = self.campaign[self.level_index]
        self.game_status.config(text="")
        before = self.level_state
        self._reveal_hidden_top_runs(before, self.layer_tokens)
        self.history.append((
            before,
            self.move_count,
            tuple(self.solution_path),
            self.layer_tokens,
            frozenset(self.revealed_layer_tokens),
        ))
        if self.solution_path and self.solution_path[0] == (source, target):
            self.solution_path.pop(0)
        else:
            self.solution_path = []
        next_state = apply_pour(before, source, target, level.capacities, self.current_mechanics)
        next_tokens = [list(bottle) for bottle in self.layer_tokens]
        moved_count = len(before[source]) - len(next_state[source])
        moved_tokens = next_tokens[source][-moved_count:]
        del next_tokens[source][-moved_count:]
        next_tokens[target].extend(moved_tokens)
        self.level_state = next_state
        self.layer_tokens = tuple(tuple(bottle) for bottle in next_tokens)
        self._reveal_hidden_top_runs(self.level_state, self.layer_tokens)
        self.move_count += 1
        self._update_game_labels(level)
        self._save_progress()
        if is_solved(self.level_state, level.capacities):
            self._stop_timer()
            self._mark_completed(level)
            self._save_progress()
            self.game_status.config(text=self._t("level_solved"), fg="#16884e")
            self.next_btn.pack(side="left", padx=6)
            if self.level_index + 1 >= len(self.campaign):
                self.next_btn.config(state="disabled")
        else:
            self._check_dead_end()

    def _show_dead_end(self):
        self._stop_timer()
        self.game_status.config(text=self._t("dead_body"), fg="#ad3d35")
        if self._dead_end_dialog is not None and self._dead_end_dialog.winfo_exists():
            return

        dialog = tk.Toplevel(self)
        dialog.title(self._t("dead_title"))
        dialog.configure(bg="#eaf0f7")
        dialog.resizable(False, False)
        dialog.transient(self)
        tk.Label(
            dialog,
            text=self._t("dead_title"),
            font=("Segoe UI", 19, "bold"),
            fg="#9c392f",
            bg="#eaf0f7",
        ).pack(padx=30, pady=(24, 8))
        tk.Label(
            dialog,
            text=self._t("dead_body"),
            font=("Segoe UI", 11),
            fg="#344b64",
            bg="#eaf0f7",
            wraplength=320,
        ).pack(padx=30, pady=(0, 18))

        def restart():
            dialog.grab_release()
            dialog.destroy()
            self._dead_end_dialog = None
            self.restart_level()

        self._button(dialog, "restart", restart, width=24).pack(pady=(0, 24))
        dialog.protocol("WM_DELETE_WINDOW", restart)
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        self._dead_end_dialog = dialog
        dialog.grab_set()
        dialog.focus_set()

    def _check_dead_end(self) -> bool:
        level = self.campaign[self.level_index]
        if is_solved(self.level_state, level.capacities):
            return False
        if not any(legal_moves(self.level_state, level.capacities, self.current_mechanics)):
            self._show_dead_end()
            return True
        if self.solution_path:
            return False
        try:
            solution = solve_level(
                self.level_state,
                level.capacities,
                mechanics=self.current_mechanics,
                raise_on_timeout=True,
            )
        except TimeoutError:
            return False
        if solution is None:
            self._show_dead_end()
            return True
        self.solution_path = solution
        self._save_progress()
        return False

    def _mark_completed(self, level: LevelDefinition):
        if level.id not in self.progress.get("completed", []):
            self.progress.setdefault("completed", []).append(level.id)
            self._save_progress()
            if hasattr(self, "level_buttons"):
                self._refresh_level_cards()

    def undo_move(self):
        if not self.history:
            return
        (
            previous_state,
            previous_moves,
            previous_solution_path,
            previous_tokens,
            previous_revealed,
        ) = self.history.pop()
        self.level_state = previous_state
        self.move_count = previous_moves
        self.solution_path = list(previous_solution_path)
        self.layer_tokens = previous_tokens
        self.revealed_layer_tokens = set(previous_revealed)
        self._reveal_hidden_top_runs(self.level_state, self.layer_tokens)
        self.game_status.config(text="", fg="#235b3c")
        self._update_game_labels(self.campaign[self.level_index])
        self._save_progress()
        self._render_board()
        self._check_dead_end()

    def restart_level(self):
        self.level_state = self.initial_state
        self.history = []
        self.move_count = 0
        self.solution_path = list(self.campaign[self.level_index].solution)
        self.layer_tokens = self.initial_layer_tokens
        self.revealed_layer_tokens = set()
        self._reveal_hidden_top_runs(self.level_state, self.layer_tokens)
        self.next_btn.config(state="normal")
        self.game_status.config(text="", fg="#235b3c")
        self._stop_timer()
        self.elapsed_seconds = 0.0
        self.level_started_at = time.monotonic()
        self._render_board()
        self._update_game_labels(self.campaign[self.level_index])
        self._tick_timer()
        self._save_progress()
        self._check_dead_end()

    def show_hint(self):
        level = self.campaign[self.level_index]
        if is_solved(self.level_state, level.capacities):
            self.game_status.config(text=self._t("level_solved"), fg="#16884e")
            return
        if self.hints_remaining <= 0:
            self.game_status.config(text=self._t("hint_limit"), fg="#ad6b19")
            return
        solution = self.solution_path or solve_level(
            self.level_state, level.capacities, mechanics=self.current_mechanics
        )
        if solution is None:
            self.game_status.config(text=self._t("hint_unavailable"), fg="#ad6b19")
            return
        if not solution:
            self.game_status.config(text=self._t("level_solved"), fg="#16884e")
            return
        self.hints_remaining -= 1
        move = solution[0]
        self.game_status.config(
            text=self._t("hint_status", source=move[0] + 1, target=move[1] + 1),
            fg="#245c82",
        )

    def check_solvability(self):
        level = self.campaign[self.level_index]
        solution = self.solution_path or solve_level(
            self.level_state, level.capacities, mechanics=self.current_mechanics
        )
        if solution is None:
            self.game_status.config(text=self._t("unsolved_status"), fg="#ad6b19")
        else:
            self.game_status.config(
                text=self._t("solvable_status", count=len(solution)), fg="#16884e"
            )

    def save_settings(self):
        self.sound_enabled = self.sound_var.get()
        self.music_enabled = self.music_var.get()
        self.patterns_enabled = self.patterns_var.get()
        self.language = self.lang_var.get()
        self.audio.set_enabled(sound=self.sound_enabled, music=self.music_enabled)
        self._apply_language()
        self._render_board_if_available()
        self._save_progress()

    def _render_board_if_available(self):
        if hasattr(self, "board") and self.board.winfo_ismapped():
            self._render_board()

    def reset_progress(self):
        self.progress = {"completed": []}
        self._save_progress()
        self._refresh_progress()

    def _elapsed(self) -> float:
        if self.level_started_at is None:
            return self.elapsed_seconds
        return self.elapsed_seconds + time.monotonic() - self.level_started_at

    def _stop_timer(self) -> None:
        if self.level_started_at is not None:
            self.elapsed_seconds = self._elapsed()
            self.level_started_at = None
        if self.timer_job is not None:
            self.after_cancel(self.timer_job)
            self.timer_job = None

    def _tick_timer(self) -> None:
        if self.level_started_at is None:
            return
        seconds = int(self._elapsed())
        minutes, seconds = divmod(seconds, 60)
        self.timer_label.config(text=self._t("time", value=f"{minutes:02d}:{seconds:02d}"))
        self.timer_job = self.after(500, self._tick_timer)


if __name__ == "__main__":
    try:
        app = BottleSortApp()
        app.mainloop()
    except tk.TclError:
        print("Tkinter is not available in this headless environment.")
