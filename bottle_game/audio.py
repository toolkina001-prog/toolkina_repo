"""Original procedural audio for the Windows desktop game."""

from __future__ import annotations

import math
import os
import struct
import sys
import tempfile
import wave
from pathlib import Path

try:
    import pygame
except ImportError:
    pygame = None

if sys.platform == "win32":
    import winsound
else:
    winsound = None


class SoundManager:
    _sample_rate = 22050

    def __init__(self, root) -> None:
        self.root = root
        self.sound_enabled = True
        self.music_enabled = True
        self.music_path = Path(tempfile.gettempdir()) / "bottle_sort_ambient.wav"
        self.click_path = Path(tempfile.gettempdir()) / "bottle_sort_click.wav"
        self.pour_path = Path(tempfile.gettempdir()) / "bottle_sort_pour.wav"
        self._write_music()
        self._write_effects()
        self._pygame = None
        self._pygame_sounds = {}
        if pygame is not None:
            try:
                pygame.mixer.init(frequency=self._sample_rate, size=-16, channels=2, buffer=512)
                pygame.mixer.music.load(os.fspath(self.music_path))
                pygame.mixer.music.set_volume(0.24)
                self._pygame_sounds = {
                    self.click_path: pygame.mixer.Sound(os.fspath(self.click_path)),
                    self.pour_path: pygame.mixer.Sound(os.fspath(self.pour_path)),
                }
                self._pygame_sounds[self.click_path].set_volume(0.55)
                self._pygame_sounds[self.pour_path].set_volume(0.72)
                self._pygame = pygame
            except pygame.error:
                self._pygame = None
                self._pygame_sounds = {}

    def set_enabled(self, *, sound: bool, music: bool) -> None:
        self.sound_enabled = sound
        self.music_enabled = music
        if music:
            self.start_music()
        else:
            self.stop_music()

    def start_music(self) -> None:
        if self._pygame is not None and self.music_enabled:
            if not self._pygame.mixer.music.get_busy():
                self._pygame.mixer.music.play(-1)
            return
        if winsound is not None and self.music_enabled:
            winsound.PlaySound(
                str(self.music_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
            )

    def stop(self) -> None:
        self.stop_music()
        if self._pygame is not None:
            self._pygame.mixer.stop()
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)

    def stop_music(self) -> None:
        if self._pygame is not None:
            self._pygame.mixer.music.stop()
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)

    def play_click(self) -> None:
        self._play(self.click_path, 120)

    def play_pour(self) -> None:
        self._play(self.pour_path, 800)

    def _play(self, path: Path, resume_after_ms: int) -> None:
        if not self.sound_enabled:
            return
        if self._pygame is not None:
            self._pygame_sounds[path].play()
            return
        if winsound is None:
            return
        was_music_playing = self.music_enabled
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        if was_music_playing:
            self.root.after(resume_after_ms, self.start_music)

    def _write_music(self) -> None:
        duration = 12.0
        frequencies = (110.0, 165.0, 220.0, 330.0)
        with wave.open(os.fspath(self.music_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self._sample_rate)
            samples = bytearray()
            for index in range(int(duration * self._sample_rate)):
                time = index / self._sample_rate
                phrase_time = time % 4.0
                note = frequencies[int(phrase_time // 1.0)]
                fade = min(1.0, time * 2.0, (duration - time) * 2.0)
                breath = 0.8 + 0.2 * math.sin(2 * math.pi * time / duration)
                sample = (
                    math.sin(2 * math.pi * note * time) * 0.42
                    + math.sin(2 * math.pi * note * 1.5 * time) * 0.12
                    + math.sin(2 * math.pi * 55 * time) * 0.08
                )
                value = int(sample * breath * max(0.0, fade) * 0.23 * 32767)
                samples.extend(struct.pack("<h", value))
            output.writeframes(samples)

    def _write_effects(self) -> None:
        self._write_tone(self.click_path, duration=0.055, frequency=760.0, volume=0.12)
        with wave.open(os.fspath(self.pour_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self._sample_rate)
            duration = 0.8
            samples = bytearray()
            for index in range(int(duration * self._sample_rate)):
                time = index / self._sample_rate
                envelope = min(1.0, time * 18) * max(0.0, 1 - time / duration)
                frequency = 620 - 360 * time / duration
                ripple = math.sin(2 * math.pi * frequency * time)
                shimmer = math.sin(2 * math.pi * (frequency * 1.51) * time) * 0.25
                value = int((ripple + shimmer) * envelope * 0.06 * 32767)
                samples.extend(struct.pack("<h", value))
            output.writeframes(samples)

    def _write_tone(self, path: Path, *, duration: float, frequency: float, volume: float) -> None:
        with wave.open(os.fspath(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self._sample_rate)
            samples = bytearray()
            for index in range(int(duration * self._sample_rate)):
                time = index / self._sample_rate
                envelope = max(0.0, 1 - time / duration)
                value = int(math.sin(2 * math.pi * frequency * time) * envelope * volume * 32767)
                samples.extend(struct.pack("<h", value))
            output.writeframes(samples)
