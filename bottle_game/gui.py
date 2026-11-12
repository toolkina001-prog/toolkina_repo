"""Tkinter-based game UI for the bottle-pouring puzzle."""

from __future__ import annotations

import json
import os
import time
import colorsys
import tkinter as tk
import zlib
from pathlib import Path
from tkinter import messagebox

from .campaign import LevelDefinition, generate_campaign, load_campaign
from .audio import SoundManager
from .engine import apply_pour, can_pour, is_solved, legal_moves
from .solver import solve_level

TEXT = {
    "EN": {
        "play": "Play", "levels": "Level selection", "settings": "Settings", "exit": "Exit",
        "progress": "Completed: {done} / {total}", "tagline": "A calm puzzle of color and flow",
        "undo": "Undo", "restart": "Restart", "hint": "Hint", "check": "Check solution",
        "menu": "Main menu", "moves": "Moves: {count}", "time": "Time: {value}",
        "sound": "Sound effects", "music": "Background music", "patterns": "Color patterns",
        "language": "Language", "save": "Save settings", "back": "Back", "reset": "Reset progress",
        "campaign": "Choose a level", "level": "Level {number}", "level_solved": "Puzzle solved!",
        "dead_title": "No moves left", "dead_body": "This position has no legal moves.",
        "restart_prompt": "Restart level", "no_hint": "No hint available for this position.",
        "hint_move": "Try bottle {source} → bottle {target}", "hint_limit": "No hints left for this level.",
        "solvable": "A solution is available in {count} moves.",
        "unsolved": "Could not find a solution within the search time limit.",
        "progress_error": "Could not load saved progress: {error}",
        "settings_saved": "Settings saved.", "progress_reset": "Progress reset.",
        "select_level": "Click a level to start", "open": "Open",
    },
    "RU": {
        "play": "Играть", "levels": "Выбор уровня", "settings": "Настройки", "exit": "Выход",
        "progress": "Пройдено: {done} / {total}", "tagline": "Спокойная головоломка о цвете и движении",
        "undo": "Отменить", "restart": "Заново", "hint": "Подсказка", "check": "Проверить решение",
        "menu": "Главное меню", "moves": "Ходы: {count}", "time": "Время: {value}",
        "sound": "Звуковые эффекты", "music": "Фоновая музыка", "patterns": "Узоры для цветов",
        "language": "Язык", "save": "Сохранить настройки", "back": "Назад", "reset": "Сбросить прогресс",
        "campaign": "Выбор уровня", "level": "Уровень {number}", "level_solved": "Уровень пройден!",
        "dead_title": "Ходы закончились", "dead_body": "В этой позиции нет доступных ходов.",
        "restart_prompt": "Начать заново", "no_hint": "Для этой позиции нет подсказки.",
        "hint_move": "Попробуйте перелить из бутылки {source} в бутылку {target}",
        "hint_limit": "Подсказки для этого уровня закончились.",
        "solvable": "Решение найдено: {count} ходов.",
        "unsolved": "Не удалось найти решение за отведённое время.",
        "progress_error": "Не удалось загрузить сохранение: {error}",
        "settings_saved": "Настройки сохранены.", "progress_reset": "Прогресс сброшен.",
        "select_level": "Нажмите на номер уровня, чтобы начать", "open": "Открыть",
    },
}

COLOR_PALETTE = tuple(
    "#{:02x}{:02x}{:02x}".format(
        *(int(channel * 255) for channel in colorsys.hsv_to_rgb(
            (index * 0.61803398875) % 1,
            0.88,
            0.78 if index % 2 else 0.96,
        ))
    )
    for index in range(32)
)


class BottleSortApp(tk.Tk):
    def __init__(self, campaign=None):
        super().__init__()
        self.title("Bottle Sort")
        self.geometry("1200x760")
        self.minsize(900, 620)
        self.configure(bg="#eaf0f7")

        self.language = "EN"
        self.sound_enabled = True
        self.music_enabled = True
        self.patterns_enabled = False
        self.hints_remaining = 3
        self.dead_end_dialog = None

        if campaign is not None:
            self.campaign = campaign
        else:
            campaign_path = Path(__file__).resolve().parents[1] / "campaign" / "levels.json"
            self.campaign = load_campaign(campaign_path) if campaign_path.exists() else generate_campaign(12)
        self.level_index = 0
        self.level_state = self.campaign[0].state if self.campaign else ()
        self.initial_state = self.level_state
        self.history: list[
            tuple[tuple[tuple[str, ...], ...], int, tuple[tuple[int, int], ...]]
        ] = []
        self.solution_path: list[tuple[int, int]] = []
        self.selected = None
        self.move_count = 0
        self.progress = {}
        self.elapsed_seconds = 0.0
        self.level_started_at: float | None = None
        self.timer_job: str | None = None
        self.current_mechanics: dict = {}
        self.animating = False
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
        self.tagline_label.config(text=self._t("tagline"))
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
        self._refresh_progress()
        if hasattr(self, "level_list"):
            self.level_list.delete(0, tk.END)
            for level in self.campaign:
                self.level_list.insert(tk.END, self._t("level", number=level.id))
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
            font=("Segoe UI", 28, "bold"),
            bg="#eaf0f7",
            fg="#14253d",
        )
        self.header.pack(pady=(42, 4))

        self.tagline_label = tk.Label(
            self.main_container,
            text=self._t("tagline"),
            font=("Segoe UI", 12),
            bg="#eaf0f7",
            fg="#61758b",
        )
        self.tagline_label.pack(pady=(0, 24))

        self.menu_buttons = tk.Frame(self.main_container, bg="#eaf0f7")
        self.menu_buttons.pack(pady=20)

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
        self.status_label.pack(pady=8)

    def _button(self, parent, key: str, command, *, width: int = 12):
        return tk.Button(
            parent,
            text=self._t(key),
            command=command,
            width=width,
            height=2,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
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
        self.settings_save = self._button(button_row, "save", self.save_settings)
        self.settings_save.pack(side="left", padx=8)
        self.settings_back = self._button(button_row, "back", self.show_menu)
        self.settings_back.pack(side="left", padx=8)
        self.settings_reset = self._button(button_row, "reset", self.reset_progress)
        self.settings_reset.pack(side="left", padx=8)

    def _build_level_select(self):
        if hasattr(self, "level_select_frame"):
            return

        self.level_select_frame = tk.Frame(self, bg="#eaf0f7")
        self.level_select_frame.pack(fill="both", expand=True)

        self.level_select_title = tk.Label(self.level_select_frame, text=self._t("campaign"), font=("Segoe UI", 24, "bold"), bg="#eaf0f7", fg="#172c46")
        self.level_select_title.pack(pady=(24, 4))
        self.level_select_hint = tk.Label(self.level_select_frame, text=self._t("select_level"), font=("Segoe UI", 11), bg="#eaf0f7", fg="#61758b")
        self.level_select_hint.pack(pady=(0, 10))

        self.level_list = tk.Listbox(
            self.level_select_frame,
            width=48,
            height=20,
            font=("Segoe UI", 12),
            bg="#ffffff",
            fg="#203650",
            selectbackground="#2d78a6",
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#d2deea",
            activestyle="none",
        )
        self.level_list.pack(fill="both", expand=True, padx=180, pady=12)
        for idx, level in enumerate(self.campaign):
            label = self._t("level", number=level.id)
            self.level_list.insert(tk.END, label)
        self.level_list.bind("<ButtonRelease-1>", lambda _event: self.after_idle(self.open_selected_level))
        self.level_list.bind("<Return>", lambda _event: self.open_selected_level())

        footer = tk.Frame(self.level_select_frame, bg="#eaf0f7")
        footer.pack(pady=8)
        self.level_select_back = self._button(footer, "back", self.show_menu)
        self.level_select_back.pack(side="left", padx=6)

    def show_menu(self):
        self._stop_timer()
        if hasattr(self, "level_state") and self.level_state:
            self._save_progress()
        self._hide_all_frames()
        self.main_container.pack(fill="both", expand=True)
        self._refresh_progress()

    def show_level_select(self):
        self._build_level_select()
        self._hide_all_frames()
        self.level_select_frame.pack(fill="both", expand=True)

    def show_settings(self):
        self._build_settings()
        self._hide_all_frames()
        self.settings_frame.pack(fill="both", expand=True)

    def _hide_all_frames(self):
        for frame_name in ["main_container", "game_frame", "settings_frame", "level_select_frame"]:
            frame = getattr(self, frame_name, None)
            if frame is not None:
                frame.pack_forget()

    def _refresh_progress(self):
        completed = len(self.progress.get("completed", []))
        self.status_label.config(text=self._t("progress", done=completed, total=len(self.campaign)))

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
            messagebox.showwarning("Bottle Sort", self._t("progress_error", error=error))
            self.progress = {"completed": [], "settings": {}}

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
        snapshot_matches = self.progress.get("current_level") == level_index
        saved_state = self.progress.get("current_state") if snapshot_matches else None
        self.level_state = (
            tuple(tuple(bottle) for bottle in saved_state)
            if saved_state
            else tuple(tuple(bottle) for bottle in level.state)
        )
        self.initial_state = tuple(tuple(bottle) for bottle in level.state)
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

    def open_selected_level(self):
        selection = self.level_list.curselection()
        if not selection:
            return
        self.start_level(selection[0])

    def _update_game_labels(self, level: LevelDefinition):
        self.level_name.config(text=self._t("level", number=level.id))
        self.moves_label.config(text=self._t("moves", count=self.move_count))

    def _render_board(self):
        for child in self.board.winfo_children():
            child.destroy()

        level = self.campaign[self.level_index]
        bottles = list(self.level_state)
        columns = max(1, min(len(bottles), max(1, (self.winfo_width() - 70) // 104)))
        self.bottle_canvases = []

        for idx, bottle in enumerate(bottles):
            bottle_frame = tk.Frame(self.board, bg="#eaf0f7", padx=3, pady=3)
            bottle_frame.grid(row=idx // columns, column=idx % columns, padx=6, pady=4)

            canvas = tk.Canvas(bottle_frame, width=86, height=226, bg="#eaf0f7", highlightthickness=0)
            canvas.pack()
            self.bottle_canvases.append(canvas)

            frozen = idx in set(self.current_mechanics.get("frozen_bottles", []))
            stone = idx in set(self.current_mechanics.get("stone_bottles", []))
            decoy = idx in set(self.current_mechanics.get("decoy_bottles", []))
            glass_shape = (31, 22, 55, 22, 55, 48, 64, 62, 64, 180, 59, 195, 27, 195, 22, 180, 22, 62, 31, 48)
            canvas.create_polygon(
                glass_shape,
                smooth=True,
                splinesteps=20,
                fill="#f9fcff",
                outline="#a9bbcc",
                width=2,
            )

            if self.selected == idx:
                canvas.create_rectangle(18, 17, 68, 199, width=3, outline="#ed9b27")

            if self.selected is not None and not idx == self.selected:
                if can_pour(self.level_state, self.selected, idx, level.capacity, self.current_mechanics):
                    canvas.create_rectangle(18, 17, 68, 199, width=3, outline="#2caa70")

            liquid_height = 108 / max(1, level.capacity)
            for layer_idx, color in enumerate(bottle):
                y_bottom = 179 - layer_idx * liquid_height
                y_top = y_bottom - liquid_height
                base_color = self._color_for(color)
                for stripe in range(6):
                    fraction = 0.1 + stripe * 0.075
                    stripe_color = self._blend_color(base_color, "#ffffff", fraction)
                    stripe_y0 = y_top + liquid_height * stripe / 6
                    stripe_y1 = y_top + liquid_height * (stripe + 1) / 6 + 1
                    canvas.create_rectangle(26, stripe_y0, 60, stripe_y1, fill=stripe_color, outline="")
                if layer_idx == len(bottle) - 1:
                    canvas.create_oval(26, y_top - 3, 60, y_top + 4, fill=self._blend_color(base_color, "#ffffff", 0.22), outline="")
                if self.patterns_enabled:
                    marks = ("●", "▲", "■", "◆", "✚", "✦")
                    pattern_ink = self._pattern_ink(base_color)
                    canvas.create_text(
                        43,
                        (y_top + y_bottom) / 2,
                        text=marks[zlib.crc32(color.encode("utf-8")) % len(marks)],
                        fill=pattern_ink,
                        font=("Segoe UI", 9, "bold"),
                    )

            canvas.create_polygon(glass_shape, smooth=True, splinesteps=20, fill="", outline="#8da5ba", width=2)
            canvas.create_line(28, 72, 28, 162, fill="#ffffff", width=2)
            canvas.create_line(31, 54, 31, 66, fill="#ffffff", width=2)
            canvas.create_line(57, 78, 57, 160, fill="#d0dfec", width=1)
            canvas.create_arc(28, 184, 58, 201, start=190, extent=160, outline="#d9e5ef", width=2)

            if frozen:
                canvas.create_rectangle(18, 18, 68, 199, outline="#35a9d8", width=3)
                canvas.create_oval(55, 17, 78, 40, fill="#d8f6ff", outline="#269ac5", width=2)
                canvas.create_text(66, 28, text="❄", fill="#087ba7", font=("Segoe UI", 12, "bold"))
            elif stone:
                canvas.create_oval(55, 17, 78, 40, fill="#e1e6eb", outline="#596979", width=2)
                canvas.create_text(66, 28, text="◆", fill="#35465a", font=("Segoe UI", 10, "bold"))
            elif decoy:
                canvas.create_oval(55, 17, 78, 40, fill="#fff1d6", outline="#cc7b1d", width=2)
                canvas.create_text(66, 28, text="?", fill="#8f4c0c", font=("Segoe UI", 11, "bold"))

            canvas.bind("<ButtonPress-1>", lambda event, idx=idx: self._begin_drag(idx))
            canvas.bind("<ButtonRelease-1>", lambda event, idx=idx: self._end_drag(idx))
            canvas.create_text(43, 211, text=str(idx + 1), fill="#52677c", font=("Segoe UI", 9, "bold"))

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
            self.campaign[self.level_index].capacity,
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
            self.campaign[self.level_index].capacity,
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
        x0 = source_canvas.winfo_rootx() + source_canvas.winfo_width() // 2 - self.winfo_rootx() - 14
        y0 = source_canvas.winfo_rooty() + 40 - self.winfo_rooty()
        x1 = target_canvas.winfo_rootx() + target_canvas.winfo_width() // 2 - self.winfo_rootx() - 14
        y1 = target_canvas.winfo_rooty() + 70 - self.winfo_rooty()
        droplet = tk.Label(self, bg=color, relief="raised", borderwidth=1)
        droplet.place(x=x0, y=y0, width=28, height=16)
        self.animating = True
        started = time.monotonic()
        duration = 0.8

        def animate() -> None:
            progress = min(1.0, (time.monotonic() - started) / duration)
            x = x0 + (x1 - x0) * progress
            y = y0 + (y1 - y0) * progress - 18 * (1 - abs(2 * progress - 1))
            droplet.place_configure(x=int(x), y=int(y))
            if progress < 1:
                self.after(16, animate)
                return
            droplet.destroy()
            self.animating = False
            self._apply_move(source, target)
            self._render_board()

        animate()

    def _apply_move(self, source, target):
        level = self.campaign[self.level_index]
        before = self.level_state
        self.history.append((before, self.move_count, tuple(self.solution_path)))
        if self.solution_path and self.solution_path[0] == (source, target):
            self.solution_path.pop(0)
        else:
            self.solution_path = []
        self.level_state = apply_pour(self.level_state, source, target, level.capacity, self.current_mechanics)
        self.move_count += 1
        self._update_game_labels(level)
        self._save_progress()
        self.audio.play_pour()
        if is_solved(self.level_state, level.capacity):
            self._stop_timer()
            self._mark_completed(level)
            self._save_progress()
            messagebox.showinfo("Bottle Sort", self._t("level_solved"))
        elif not any(legal_moves(self.level_state, level.capacity, self.current_mechanics)):
            self._show_dead_end()

    def _show_dead_end(self):
        if self.dead_end_dialog is not None and self.dead_end_dialog.winfo_exists():
            return
        self._stop_timer()
        dialog = tk.Toplevel(self)
        self.dead_end_dialog = dialog
        dialog.title(self._t("dead_title"))
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(bg="#f4f7fb")
        tk.Label(
            dialog,
            text=self._t("dead_title"),
            font=("Segoe UI", 18, "bold"),
            fg="#17324f",
            bg="#f4f7fb",
        ).pack(padx=28, pady=(22, 6))
        tk.Label(
            dialog,
            text=self._t("dead_body"),
            font=("Segoe UI", 11),
            fg="#536a80",
            bg="#f4f7fb",
        ).pack(padx=28, pady=(0, 18))
        self._button(dialog, "restart_prompt", self._restart_from_dead_end, width=22).pack(pady=(0, 22))
        dialog.protocol("WM_DELETE_WINDOW", self._restart_from_dead_end)
        dialog.grab_set()

    def _restart_from_dead_end(self):
        if self.dead_end_dialog is not None and self.dead_end_dialog.winfo_exists():
            self.dead_end_dialog.destroy()
        self.dead_end_dialog = None
        self.restart_level()

    def _mark_completed(self, level: LevelDefinition):
        if level.id not in self.progress.get("completed", []):
            self.progress.setdefault("completed", []).append(level.id)
            self._save_progress()

    def undo_move(self):
        if not self.history:
            return
        previous_state, previous_moves, previous_solution_path = self.history.pop()
        self.level_state = previous_state
        self.move_count = previous_moves
        self.solution_path = list(previous_solution_path)
        self._update_game_labels(self.campaign[self.level_index])
        self._save_progress()
        self._render_board()

    def restart_level(self):
        self.level_state = self.initial_state
        self.history = []
        self.move_count = 0
        self.solution_path = list(self.campaign[self.level_index].solution)
        self._stop_timer()
        self.elapsed_seconds = 0.0
        self.level_started_at = time.monotonic()
        self._render_board()
        self._update_game_labels(self.campaign[self.level_index])
        self._tick_timer()
        self._save_progress()

    def show_hint(self):
        if self.hints_remaining <= 0:
            messagebox.showinfo("Bottle Sort", self._t("hint_limit"))
            return
        level = self.campaign[self.level_index]
        solution = self.solution_path or solve_level(
            self.level_state, level.capacity, mechanics=self.current_mechanics
        )
        if not solution:
            messagebox.showinfo("Bottle Sort", self._t("no_hint"))
            return
        self.hints_remaining -= 1
        move = solution[0]
        messagebox.showinfo(
            "Bottle Sort",
            self._t("hint_move", source=move[0] + 1, target=move[1] + 1),
        )

    def check_solvability(self):
        level = self.campaign[self.level_index]
        solution = self.solution_path or solve_level(
            self.level_state, level.capacity, mechanics=self.current_mechanics
        )
        if solution is None:
            messagebox.showinfo("Bottle Sort", self._t("unsolved"))
        else:
            messagebox.showinfo("Bottle Sort", self._t("solvable", count=len(solution)))

    def save_settings(self):
        self.sound_enabled = self.sound_var.get()
        self.music_enabled = self.music_var.get()
        self.patterns_enabled = self.patterns_var.get()
        self.language = self.lang_var.get()
        self.audio.set_enabled(sound=self.sound_enabled, music=self.music_enabled)
        self._apply_language()
        self._render_board_if_available()
        self._save_progress()
        messagebox.showinfo("Bottle Sort", self._t("settings_saved"))

    def _render_board_if_available(self):
        if hasattr(self, "board") and self.board.winfo_ismapped():
            self._render_board()

    def reset_progress(self):
        self.progress = {"completed": []}
        self._save_progress()
        self._refresh_progress()
        messagebox.showinfo("Bottle Sort", self._t("progress_reset"))

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
