"""Original procedural audio for the Windows desktop game."""

from __future__ import annotations

import math
import os
import random
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
        beat_duration = 0.75
        chords = (
            tuple(value / 12 for value in (1570, 1978, 2352, 2962)),
            tuple(value / 12 for value in (1320, 1570, 1978, 2352)),
            tuple(value / 12 for value in (1048, 1320, 1570, 1978)),
            tuple(value / 12 for value in (1176, 1480, 1760, 2093)),
        )
        melody = tuple(value / 12 for value in (
            4704, 0, 3956, 0, 3520, 0, 3136, 0,
            4184, 0, 4704, 0, 3956, 0, 3520, 0,
        ))
        random_source = random.Random(12)
        sample_count = int(duration * self._sample_rate)
        samples = []
        chord_transition = 0.12

        def smoothstep(value: float) -> float:
            return value * value * (3 - 2 * value)

        for index in range(sample_count):
            time = index / self._sample_rate
            bar_position = time % 3.0
            bar_index = int(time // 3.0) % len(chords)
            current_chord = chords[bar_index]
            previous_chord = chords[(bar_index - 1) % len(chords)]
            next_chord = chords[(bar_index + 1) % len(chords)]
            if bar_position < chord_transition:
                blend = smoothstep(bar_position / chord_transition)
                active_chord = tuple(
                    before * (1 - blend) + current * blend
                    for before, current in zip(previous_chord, current_chord)
                )
            elif bar_position > 3.0 - chord_transition:
                blend = smoothstep((bar_position - (3.0 - chord_transition)) / chord_transition)
                active_chord = tuple(
                    current * (1 - blend) + after * blend
                    for current, after in zip(current_chord, next_chord)
                )
            else:
                active_chord = current_chord

            chord = sum(
                math.sin(2 * math.pi * frequency * time) * amplitude
                for frequency, amplitude in zip(active_chord, (0.13, 0.08, 0.07, 0.035))
            )
            beat_index = int(time / beat_duration) % 16
            beat_phase = (time / beat_duration) % 1.0
            kick = 0.0
            if beat_index % 4 in (0, 2):
                kick_time = beat_phase * beat_duration
                kick_frequency = 58 - 20 * min(1.0, kick_time * 5)
                kick = math.sin(2 * math.pi * kick_frequency * kick_time) * math.exp(-kick_time * 15) * 0.3

            snare = 0.0
            if beat_index % 4 in (1, 3):
                snare_time = beat_phase * beat_duration
                snare = (random_source.random() * 2 - 1) * math.exp(-snare_time * 34) * 0.12

            hat_phase = time % (beat_duration / 2)
            hat = (random_source.random() * 2 - 1) * math.exp(-hat_phase * 85) * 0.028
            melody_frequency = melody[beat_index]
            melody_note = 0.0
            if melody_frequency:
                note_time = beat_phase * beat_duration
                note_envelope = min(1.0, note_time / 0.025) * math.exp(-note_time * 3.4)
                melody_note = math.sin(2 * math.pi * melody_frequency * note_time) * note_envelope * 0.07

            sample = (chord + kick + snare + hat + melody_note) * 0.38
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
