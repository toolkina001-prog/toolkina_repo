import struct
import tempfile
import unittest
import wave
from pathlib import Path

from bottle_game.audio import SoundManager


class AudioTests(unittest.TestCase):
    def test_ambient_track_has_a_continuous_loop_boundary(self):
        manager = SoundManager.__new__(SoundManager)
        with tempfile.TemporaryDirectory() as directory:
            manager.music_path = Path(directory) / "ambient.wav"
            manager._write_music()

            with wave.open(str(manager.music_path), "rb") as track:
                self.assertEqual(track.getnframes(), 12 * manager._sample_rate)
                first = struct.unpack("<h", track.readframes(1))[0]
                track.setpos(track.getnframes() - 1)
                last = struct.unpack("<h", track.readframes(1))[0]

        self.assertEqual(first, last)


if __name__ == "__main__":
    unittest.main()
