"""Original procedural audio for the Windows desktop game."""

from __future__ import annotations

import math
import os
import struct
import sys
import tempfile
import wave
from pathlib import Path

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

    def set_enabled(self, *, sound: bool, music: bool) -> None:
        self.sound_enabled = sound
        self.music_enabled = music
        if music:
            self.start_music()
        else:
            self.stop()

    def start_music(self) -> None:
        if winsound is not None and self.music_enabled:
            winsound.PlaySound(
                str(self.music_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
            )

    def stop(self) -> None:
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)

    def play_click(self) -> None:
        self._play(self.click_path, 120)

    def play_pour(self) -> None:
        self._play(self.pour_path, 700)

    def _play(self, path: Path, resume_after_ms: int) -> None:
        if not self.sound_enabled or winsound is None:
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
                envelope = 0.62 + 0.25 * math.sin(2 * math.pi * time / duration)
                sample = sum(
                    math.sin(2 * math.pi * frequency * time) * amplitude
                    for frequency, amplitude in zip(frequencies, (0.25, 0.16, 0.1, 0.05))
                )
                value = int(max(-1.0, min(1.0, sample * envelope * 0.09)) * 32767)
                samples.extend(struct.pack("<h", value))
            output.writeframes(samples)

    def _write_effects(self) -> None:
        self._write_tone(self.click_path, duration=0.055, frequency=760.0, volume=0.12)
        with wave.open(os.fspath(self.pour_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self._sample_rate)
            duration = 0.62
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
