import struct
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from bottle_game.audio import SoundManager


class AudioTests(unittest.TestCase):
    def test_ambient_track_has_a_continuous_loop_boundary(self):
        manager = SoundManager.__new__(SoundManager)
        with tempfile.TemporaryDirectory() as directory:
            manager.music_path = Path(directory) / "ambient.wav"
            manager._write_music()

            with wave.open(str(manager.music_path), "rb") as track:
                self.assertEqual(track.getnframes(), 16 * manager._sample_rate)
                first = struct.unpack("<h", track.readframes(1))[0]
                track.setpos(track.getnframes() - 1)
                last = struct.unpack("<h", track.readframes(1))[0]

        self.assertEqual(first, last)

    def test_pour_effect_matches_the_faster_animation_duration(self):
        manager = SoundManager.__new__(SoundManager)
        with tempfile.TemporaryDirectory() as directory:
            manager.click_path = Path(directory) / "click.wav"
            manager.pour_path = Path(directory) / "pour.wav"
            manager._write_effects()

            with wave.open(str(manager.pour_path), "rb") as effect:
                self.assertEqual(
                    effect.getnframes(),
                    int(SoundManager.pour_duration * manager._sample_rate),
                )

    def test_click_effect_does_not_interrupt_or_restart_background_music(self):
        manager = SoundManager.__new__(SoundManager)
        manager.click_path = Path("click.wav")
        manager.sound_enabled = True
        manager.music_enabled = True
        manager._pygame = None
        root = SimpleNamespace(after=Mock())
        manager.root = root
        winsound = SimpleNamespace(PlaySound=Mock())

        with patch("bottle_game.audio.winsound", winsound):
            manager.play_click()

        winsound.PlaySound.assert_not_called()
        root.after.assert_not_called()


if __name__ == "__main__":
    unittest.main()
