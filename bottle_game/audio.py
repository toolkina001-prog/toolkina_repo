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
                pygame.mixer.music.set_volume(0.36)
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
        self._play(self.pour_path, 500)

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
        duration = 16.0
        chords = (
            tuple(value / 16 for value in (2349, 2960, 3520, 4435)),
            tuple(value / 16 for value in (1976, 2349, 2960, 3520)),
            tuple(value / 16 for value in (1568, 1976, 2349, 2960)),
            tuple(value / 16 for value in (1760, 1976, 2637, 3520)),
        )
        arpeggios = (
            tuple(value / 16 for value in (4698, 5920, 7040, 8870, 7040, 5920, 4698, 5920)),
            tuple(value / 16 for value in (3952, 4698, 5920, 7040, 5920, 4698, 3952, 4698)),
            tuple(value / 16 for value in (3136, 3952, 4698, 5920, 4698, 3952, 3136, 3952)),
            tuple(value / 16 for value in (3520, 3952, 5274, 7040, 5274, 3952, 3520, 3952)),
        )
        sample_count = int(duration * self._sample_rate)
        samples = []
        chord_transition = 0.18

        def smoothstep(value: float) -> float:
            return value * value * (3 - 2 * value)

        for index in range(sample_count):
            time = index / self._sample_rate
            bar_position = time % 4.0
            bar_index = int(time // 4.0) % len(chords)
            current_chord = chords[bar_index]
            previous_chord = chords[(bar_index - 1) % len(chords)]
            next_chord = chords[(bar_index + 1) % len(chords)]
            if bar_position < chord_transition:
                blend = smoothstep(bar_position / chord_transition)
                active_chord = tuple(
                    before * (1 - blend) + current * blend
                    for before, current in zip(previous_chord, current_chord)
                )
            elif bar_position > 4.0 - chord_transition:
                blend = smoothstep((bar_position - (4.0 - chord_transition)) / chord_transition)
                active_chord = tuple(
                    current * (1 - blend) + after * blend
                    for current, after in zip(current_chord, next_chord)
                )
            else:
                active_chord = current_chord

            breathing = 0.86 + 0.14 * math.sin(2 * math.pi * time / duration)
            pad = sum(
                math.sin(2 * math.pi * frequency * time) * amplitude
                for frequency, amplitude in zip(active_chord, (0.17, 0.1, 0.075, 0.04))
            )
            step_position = (time % 4.0) / 0.5
            step_index = int(step_position)
            note_time = (step_position - step_index) * 0.5
            melody_frequency = arpeggios[bar_index][step_index]
            note_envelope = min(1.0, note_time / 0.018) * math.exp(-note_time * 4.2)
            piano = (
                math.sin(2 * math.pi * melody_frequency * note_time)
                + math.sin(2 * math.pi * melody_frequency * 2.01 * note_time) * 0.24
                + math.sin(2 * math.pi * melody_frequency * 4.0 * note_time) * 0.08
            ) * note_envelope * 0.12
            bass_frequency = active_chord[0] / 2
            bass = math.sin(2 * math.pi * bass_frequency * time) * 0.055
            sample = (pad * breathing + piano + bass) * 0.42
            samples.append(max(-1.0, min(1.0, sample)))

        fade_samples = int(0.04 * self._sample_rate)
        for offset in range(fade_samples):
            blend = smoothstep(offset / (fade_samples - 1))
            start_index = offset
            end_index = sample_count - fade_samples + offset
            samples[start_index] = samples[0] * (1 - blend) + samples[start_index] * blend
            samples[end_index] = samples[end_index] * (1 - blend) + samples[-1] * blend
        seam_value = (samples[0] + samples[-1]) / 2
        samples[0] = seam_value
        samples[-1] = seam_value

        with wave.open(os.fspath(self.music_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self._sample_rate)
            pcm = bytearray()
            for sample in samples:
                pcm.extend(struct.pack("<h", int(sample * 32767)))
            output.writeframes(pcm)

    def _write_effects(self) -> None:
        self._write_tone(self.click_path, duration=0.055, frequency=760.0, volume=0.12)
        with wave.open(os.fspath(self.pour_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self._sample_rate)
            duration = 0.5
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
