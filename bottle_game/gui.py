"""Tkinter-based game UI for the bottle-pouring puzzle."""

from __future__ import annotations

import json
import os
import time
import colorsys
import zlib
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from .campaign import LevelDefinition, generate_campaign, load_campaign
from .engine import apply_pour, can_pour, is_solved
from .solver import solve_level


class BottleSortApp(tk.Tk):
    def __init__(self, campaign=None):
        super().__init__()
        self.title("Bottle Sort")
        self.geometry("1200x760")
        self.minsize(900, 620)
        self.configure(bg="#eef3f8")

        self.language = "EN"
        self.sound_enabled = True
        self.music_enabled = True
        self.patterns_enabled = False
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
        self.save_path = Path(os.path.expanduser("~/.bottle_sort_save.json"))

        self._build_main_menu()
        self._build_settings()
        self._build_level_select()
        self._load_progress()
        self.show_menu()

    def _build_main_menu(self):
        self.main_container = tk.Frame(self, bg="#eef3f8")
        self.main_container.pack(fill="both", expand=True)

        self.header = tk.Label(
            self.main_container,
            text="Bottle Sort",
            font=("Segoe UI", 28, "bold"),
            bg="#eef3f8",
            fg="#1d2a39",
        )
        self.header.pack(pady=(26, 18))

        self.menu_buttons = tk.Frame(self.main_container, bg="#eef3f8")
        self.menu_buttons.pack(pady=20)

        self.play_btn = tk.Button(self.menu_buttons, text="Play", command=self.start_level, width=18, height=2)
        self.play_btn.pack(pady=8)

        self.levels_btn = tk.Button(self.menu_buttons, text="Level Select", command=self.show_level_select, width=18, height=2)
        self.levels_btn.pack(pady=8)

        self.settings_btn = tk.Button(self.menu_buttons, text="Settings", command=self.show_settings, width=18, height=2)
        self.settings_btn.pack(pady=8)

        self.exit_btn = tk.Button(self.menu_buttons, text="Exit", command=self.destroy, width=18, height=2)
        self.exit_btn.pack(pady=8)

        self.status_label = tk.Label(
            self.main_container,
            text="Progress: 0 / 0",
            font=("Segoe UI", 12),
            bg="#eef3f8",
            fg="#2b3f4d",
        )
        self.status_label.pack(pady=8)

    def _build_game_screen(self):
        if hasattr(self, "game_frame"):
            return

        self.game_frame = tk.Frame(self, bg="#eef3f8")
        self.game_frame.pack(fill="both", expand=True)

        top_bar = tk.Frame(self.game_frame, bg="#eef3f8")
        top_bar.pack(fill="x", padx=20, pady=(16, 10))

        self.level_name = tk.Label(top_bar, text="Level 1", font=("Segoe UI", 18, "bold"), bg="#eef3f8")
        self.level_name.pack(side="left")

        self.moves_label = tk.Label(top_bar, text="Moves: 0", font=("Segoe UI", 12), bg="#eef3f8")
        self.moves_label.pack(side="right", padx=(0, 12))

        self.timer_label = tk.Label(top_bar, text="Time: 00:00", font=("Segoe UI", 12), bg="#eef3f8")
        self.timer_label.pack(side="right", padx=(0, 12))

        controls = tk.Frame(self.game_frame, bg="#eef3f8")
        controls.pack(fill="x", padx=20, pady=(0, 10))

        tk.Button(controls, text="Undo", command=self.undo_move, width=12).pack(side="left", padx=6)
        tk.Button(controls, text="Restart", command=self.restart_level, width=12).pack(side="left", padx=6)
        tk.Button(controls, text="Hint", command=self.show_hint, width=12).pack(side="left", padx=6)
        tk.Button(controls, text="Check solvability", command=self.check_solvability, width=16).pack(side="left", padx=6)
        tk.Button(controls, text="Menu", command=self.show_menu, width=12).pack(side="left", padx=6)

        self.board = tk.Frame(self.game_frame, bg="#eef3f8")
        self.board.pack(fill="both", expand=True, padx=20, pady=10)
        self.board.bind("<Configure>", lambda event: self._render_board())

    def _build_settings(self):
        if hasattr(self, "settings_frame"):
            return

        self.settings_frame = tk.Frame(self, bg="#eef3f8")

        header = tk.Label(self.settings_frame, text="Settings", font=("Segoe UI", 24, "bold"), bg="#eef3f8")
        header.pack(pady=20)

        self.sound_var = tk.BooleanVar(value=self.sound_enabled)
        self.music_var = tk.BooleanVar(value=self.music_enabled)
        self.patterns_var = tk.BooleanVar(value=self.patterns_enabled)
        self.lang_var = tk.StringVar(value=self.language)

        tk.Checkbutton(self.settings_frame, text="Sound", variable=self.sound_var, bg="#eef3f8").pack(anchor="w", padx=30)
        tk.Checkbutton(self.settings_frame, text="Music", variable=self.music_var, bg="#eef3f8").pack(anchor="w", padx=30)
        tk.Checkbutton(self.settings_frame, text="Color patterns", variable=self.patterns_var, bg="#eef3f8").pack(anchor="w", padx=30)

        lang_frame = tk.Frame(self.settings_frame, bg="#eef3f8")
        lang_frame.pack(anchor="w", padx=30, pady=12)
        tk.Label(lang_frame, text="Language:", bg="#eef3f8").pack(side="left")
        tk.OptionMenu(lang_frame, self.lang_var, "EN", "RU").pack(side="left")

        button_row = tk.Frame(self.settings_frame, bg="#eef3f8")
        button_row.pack(pady=24)
        tk.Button(button_row, text="Save", command=self.save_settings).pack(side="left", padx=8)
        tk.Button(button_row, text="Back", command=self.show_menu).pack(side="left", padx=8)
        tk.Button(button_row, text="Reset progress", command=self.reset_progress).pack(side="left", padx=8)

    def _build_level_select(self):
        if hasattr(self, "level_select_frame"):
            return

        self.level_select_frame = tk.Frame(self, bg="#eef3f8")
        self.level_select_frame.pack(fill="both", expand=True)

        title = tk.Label(self.level_select_frame, text="Campaign", font=("Segoe UI", 24, "bold"), bg="#eef3f8")
        title.pack(pady=(12, 6))

        self.level_list = tk.Listbox(self.level_select_frame, width=80, height=20, font=("Consolas", 11))
        self.level_list.pack(fill="both", expand=True, padx=24, pady=12)
        for idx, level in enumerate(self.campaign):
            label = f"#{idx + 1:03d} {level.title}  {level.mechanics or 'base'}"
            self.level_list.insert(tk.END, label)

        footer = tk.Frame(self.level_select_frame, bg="#eef3f8")
        footer.pack(pady=8)
        tk.Button(footer, text="Open", command=self.open_selected_level, width=12).pack(side="left", padx=6)
        tk.Button(footer, text="Back", command=self.show_menu, width=12).pack(side="left", padx=6)

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
        self.status_label.config(text=f"Progress: {completed} / {len(self.campaign)}")

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
            self.sound_var.set(self.sound_enabled)
            self.music_var.set(self.music_enabled)
            self.patterns_var.set(self.patterns_enabled)
            self.lang_var.set(self.language)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showwarning("Bottle Sort", f"Could not load saved progress: {error}")
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
            messagebox.showinfo("Bottle Sort", "Select a level first.")
            return
        self.start_level(selection[0])

    def _update_game_labels(self, level: LevelDefinition):
        self.level_name.config(text=f"Level {level.id}: {level.title}")
        self.moves_label.config(text=f"Moves: {self.move_count}")

    def _render_board(self):
        for child in self.board.winfo_children():
            child.destroy()

        level = self.campaign[self.level_index]
        bottles = list(self.level_state)
        columns = max(1, min(len(bottles), max(1, (self.winfo_width() - 70) // 88)))
        self.bottle_canvases = []

        for idx, bottle in enumerate(bottles):
            bottle_frame = tk.Frame(self.board, bg="#eef3f8", padx=4, pady=4)
            bottle_frame.grid(row=idx // columns, column=idx % columns, padx=8, pady=8)

            canvas = tk.Canvas(bottle_frame, width=64, height=200, bg="#eef3f8", highlightthickness=0)
            canvas.pack()
            self.bottle_canvases.append(canvas)

            # Bottle outline
            canvas.create_rectangle(10, 20, 54, 180, width=2, outline="#3a4857", fill="#f7fbff")
            canvas.create_rectangle(12, 22, 52, 178, width=1, outline="#dfe9f3", fill="")

            if self.selected == idx:
                canvas.create_rectangle(8, 18, 56, 182, width=3, outline="#f0aa30")

            # valid target highlight
            if self.selected is not None and not idx == self.selected:
                if can_pour(self.level_state, self.selected, idx, level.capacity, self.current_mechanics):
                    canvas.create_rectangle(8, 18, 56, 182, width=3, outline="#48b86f")

            # Render layers
            for layer_idx, color in enumerate(reversed(bottle)):
                y_top = 175 - ((layer_idx + 1) * (150 / max(1, level.capacity)))
                y_bottom = 175 - (layer_idx * (150 / max(1, level.capacity)))
                canvas.create_rectangle(16, y_top, 48, y_bottom, fill=self._color_for(color), outline="")
                if self.patterns_enabled:
                    marks = ("●", "▲", "■", "◆", "✚", "✦")
                    canvas.create_text(
                        32,
                        (y_top + y_bottom) / 2,
                        text=marks[zlib.crc32(color.encode("utf-8")) % len(marks)],
                        fill="#ffffff",
                        font=("Segoe UI", 9, "bold"),
                    )

            canvas.bind("<ButtonPress-1>", lambda event, idx=idx: self._begin_drag(idx))
            canvas.bind("<ButtonRelease-1>", lambda event, idx=idx: self._end_drag(idx))
            canvas.create_text(32, 188, text=str(idx), fill="#334862", font=("Segoe UI", 9))

    def _color_for(self, color: str) -> str:
        palette = {
            "R": "#d94d4d",
            "G": "#4ebf7d",
            "B": "#4d8bf0",
            "Y": "#f3d14b",
            "P": "#b36cff",
            "C": "#68d3d9",
            "O": "#ff9f43",
            "K": "#3d4357",
            "A": "#ff5ca8",
            "M": "#5cd57d",
            "T": "#a67c52",
            "Q": "#d0d6ff",
            "S": "#00a9a5",
        }
        if color in palette:
            return palette[color]
        hue = zlib.crc32(color.encode("utf-8")) / 0x100000000
        red, green, blue = colorsys.hsv_to_rgb(hue, 0.68, 0.92)
        return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"

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
        if is_solved(self.level_state, level.capacity):
            self._stop_timer()
            self._mark_completed(level)
            self._save_progress()
            messagebox.showinfo("Bottle Sort", "Level solved!")

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
            messagebox.showinfo("Bottle Sort", "Hint limit reached for this level.")
            return
        level = self.campaign[self.level_index]
        solution = self.solution_path or solve_level(
            self.level_state, level.capacity, mechanics=self.current_mechanics
        )
        if not solution:
            messagebox.showinfo("Bottle Sort", "No solution was found for this board.")
            return
        self.hints_remaining -= 1
        move = solution[0]
        messagebox.showinfo("Bottle Sort", f"Next suggested move: {move[0]} -> {move[1]}")

    def check_solvability(self):
        level = self.campaign[self.level_index]
        solution = self.solution_path or solve_level(
            self.level_state, level.capacity, mechanics=self.current_mechanics
        )
        if solution is None:
            messagebox.showinfo("Bottle Sort", "No solution was found within the solver time limit.")
        else:
            messagebox.showinfo("Bottle Sort", f"This board is solvable in {len(solution)} moves.")

    def save_settings(self):
        self.sound_enabled = self.sound_var.get()
        self.music_enabled = self.music_var.get()
        self.patterns_enabled = self.patterns_var.get()
        self.language = self.lang_var.get()
        self._save_progress()
        messagebox.showinfo("Bottle Sort", "Settings saved.")

    def reset_progress(self):
        self.progress = {"completed": []}
        self._save_progress()
        self._refresh_progress()
        messagebox.showinfo("Bottle Sort", "Progress reset.")

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
        self.timer_label.config(text=f"Time: {minutes:02d}:{seconds:02d}")
        self.timer_job = self.after(500, self._tick_timer)


if __name__ == "__main__":
    try:
        app = BottleSortApp()
        app.mainloop()
    except tk.TclError:
        print("Tkinter is not available in this headless environment.")
