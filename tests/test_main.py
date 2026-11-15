import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import call, patch

import main


class MainLauncherTests(unittest.TestCase):
    @patch("main.Path.is_file", side_effect=[False, True])
    @patch("main.subprocess.run")
    def test_installs_electron_before_starting_ui(self, run, _binary_exists):
        run.side_effect = [
            CompletedProcess([], 0),
            CompletedProcess([], 0),
        ]
        project_root = Path(main.__file__).resolve().parent

        with patch.object(sys, "argv", ["main.py"]), self.assertRaises(SystemExit) as exit_error:
            main.main()

        self.assertEqual(exit_error.exception.code, 0)
        self.assertEqual(run.call_args_list, [
            call(main._npm_command("install"), cwd=project_root, check=False),
            call(main._npm_command("start"), cwd=project_root, check=False),
        ])

    @patch("main.Path.is_file", side_effect=[False, False, True, True])
    @patch("main.subprocess.run")
    def test_runs_electron_installer_if_npm_did_not_fetch_binary(self, run, _binary_exists):
        run.side_effect = [
            CompletedProcess([], 0),
            CompletedProcess([], 0),
            CompletedProcess([], 0),
        ]
        project_root = Path(main.__file__).resolve().parent

        with patch.object(sys, "argv", ["main.py"]), self.assertRaises(SystemExit) as exit_error:
            main.main()

        self.assertEqual(exit_error.exception.code, 0)
        self.assertEqual(run.call_args_list, [
            call(main._npm_command("install"), cwd=project_root, check=False),
            call(["node", str(project_root / "node_modules" / "electron" / "install.js")],
                 cwd=project_root, check=False),
            call(main._npm_command("start"), cwd=project_root, check=False),
        ])

    @patch("main.Path.is_file", return_value=False)
    @patch("main.subprocess.run")
    def test_does_not_start_app_when_dependency_install_fails(self, run, _binary_exists):
        run.return_value = CompletedProcess([], 1)

        with patch.object(sys, "argv", ["main.py"]), self.assertRaises(SystemExit) as exit_error:
            main.main()

        self.assertEqual(exit_error.exception.code, 1)
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
