import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sender", ROOT / "functions/__done_tg_notify.py"
)
sender = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sender)
COMMAND = 'printf "%s" \'a`b\\c<&\'\necho done'


class TelegramTests(unittest.TestCase):
    def test_formatting_and_timeout(self):
        with patch.object(sender, "urlopen", return_value=io.BytesIO(b'{"ok":true}')) as post:
            sender.send_notification("fake-token", "123", "Failed (1) after 6s", COMMAND)
        request = post.call_args.args[0]
        payload = parse_qs(request.data.decode())
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(post.call_args.kwargs, {"timeout": 10})
        self.assertEqual(payload["chat_id"], ["123"])
        self.assertEqual(payload["parse_mode"], ["HTML"])
        self.assertIn("Failed (1) after 6s", payload["text"][0])
        self.assertIn("&lt;&amp;", payload["text"][0])
        self.assertIn("`b\\c", payload["text"][0])

    def test_rejections_and_network_errors_exit_without_exposing_token(self):
        for failure in (
            HTTPError("https://example/fake-token", 400, "Bad Request", None, None),
            URLError("https://example/fake-token"),
            TimeoutError("https://example/fake-token"),
        ):
            with self.subTest(failure=type(failure).__name__):
                self.check_main_failure(failure=failure)
        self.check_main_failure(body=b'{"ok":false,"description":"chat not found"}')
        self.check_main_failure(body=b"not json")
        self.check_main_failure(body=b"{}")

    def check_main_failure(self, failure=None, body=b""):
        stderr = io.StringIO()
        with (
            patch.dict(os.environ, DONE_TG_BOT_TOKEN="fake-token", DONE_TG_CHAT_ID="123"),
            patch.object(sys, "argv", ["sender", "--", "Failed (1)", COMMAND]),
            patch.object(sender, "urlopen", side_effect=failure, return_value=io.BytesIO(body)),
            patch("sys.stderr", stderr),
            self.assertRaises(SystemExit) as exit_status,
        ):
            sender.main()
        self.assertEqual(exit_status.exception.code, 1)
        self.assertIn("done_tg:", stderr.getvalue())
        self.assertNotIn("fake-token", stderr.getvalue())

    def test_missing_credentials_fail_before_network_access(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(sys, "argv", ["sender", "title", "command"]),
            patch.object(sender, "urlopen") as post,
            patch("sys.stderr", io.StringIO()),
            self.assertRaises(SystemExit) as exit_status,
        ):
            sender.main()
        self.assertEqual(exit_status.exception.code, 2)
        post.assert_not_called()


@unittest.skipUnless(shutil.which("fish"), "fish is required for integration checks")
class FishTests(unittest.TestCase):
    def run_fish(self, script, **environment):
        return subprocess.run(
            ["fish", "--no-config", "-c", script],
            env={**os.environ, **environment},
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout

    def notification(self, backend, command=COMMAND, duration="6000", focused="1", status="0"):
        source = (ROOT / "conf.d/done.fish").read_text()
        duration_function = source[
            source.index("function __done_humanize_duration"):
            source.index('\nif test -z "$SSH_CLIENT"')
        ]
        handler = source[
            source.index("    function __done_ended"):
            source.index("\nend\n\nfunction __done_uninstall")
        ]
        script = duration_function + handler + r'''
set -g cmd_duration $TEST_DURATION
set -g __done_min_cmd_duration 5000
set -g __done_notify_sound 0
set -g __done_exclude '^git (?!push|pull|fetch)'
set -g __done_initial_window_id test
set -eg TMUX_PANE
set -eg TMUX
set -eg KITTY_WINDOW_ID
set -eg TERM_PROGRAM
set -e __done_notification_command
function __done_is_process_window_focused
    return $TEST_FOCUSED
end
function __done_tg_notify
    printf 'telegram-title:%s\ntelegram-command:%s\n' "$argv[1]" "$argv[2]"
end
function __review_desktop
    printf 'desktop:%s\n' "$argv[1]"
end
function uname
    echo Darwin
end
''' + backend + '\nsh -c "exit $TEST_STATUS"\n__done_ended "$TEST_COMMAND"'
        return self.run_fish(
            script, TEST_COMMAND=command, TEST_DURATION=duration,
            TEST_FOCUSED=focused, TEST_STATUS=status,
        )

    def test_telegram_and_desktop_receive_unmodified_arguments(self):
        for backend, marker in (
            ('set -g __done_notification_command \'__review_desktop "$message"\'', "desktop:"),
            ("set -g KITTY_WINDOW_ID 1", "\x1b]99;"),
            ("set -g TERM_PROGRAM ghostty", "\x1b]777;notify;"),
            ("set -g TERM_PROGRAM WezTerm", "\x1b]777;notify;"),
            ("set -g TERM_PROGRAM iTerm.app", "\x1b]9;"),
            ("", "\x1b]777;notify;"),
        ):
            with self.subTest(backend=marker):
                output = self.notification(backend, status="1")
                self.assertIn("telegram-title:Failed (1) after 6s", output)
                self.assertIn("telegram-command:" + COMMAND, output)
                self.assertIn(marker, output)
                self.assertIn(COMMAND, output.split("telegram-command:", 1)[1][len(COMMAND):])

    def test_short_focused_and_excluded_commands_remain_silent(self):
        for overrides in ({"duration": "1000"}, {"focused": "0"}, {"command": "git status"}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.notification("", **overrides), "")

    def test_sender_is_disowned_and_errors_go_to_log(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            fake_python = directory / "python3"
            fake_python.write_text('''#!/bin/sh
printf '%s\\n' "$@" > "$TEST_CAPTURE"
while [ ! -f "$TEST_RELEASE" ]; do /bin/sleep 0.02; done
printf 'mock delivery failure\\n' >&2
''')
            fake_python.chmod(0o755)
            release = directory / "release"
            capture = directory / "capture"
            log = directory / "data/fish/done_tg.log"
            try:
                output = self.run_fish(r'''
set -g fish_function_path "$TEST_FUNCTIONS" $fish_function_path
set -gx PATH "$TEST_BIN" $PATH
__done_tg_notify 'Failed (1)' "$TEST_COMMAND"
echo returned
''', TEST_BIN=str(directory),
                    DONE_TG_BOT_TOKEN="fake-token", DONE_TG_CHAT_ID="123",
                    TEST_FUNCTIONS=str(ROOT / "functions"), XDG_DATA_HOME=str(directory / "data"),
                    TEST_CAPTURE=str(capture), TEST_RELEASE=str(release), TEST_COMMAND=COMMAND,
                )
                self.assertEqual(output, "returned\n")
                self.wait_for(lambda: capture.exists())
                self.assertEqual(
                    capture.read_text(),
                    f"{ROOT / 'functions/__done_tg_notify.py'}\n--\nFailed (1)\n{COMMAND}\n",
                )
            finally:
                release.touch()
                self.wait_for(lambda: log.exists() and "mock delivery failure" in log.read_text())

    def wait_for(self, predicate):
        deadline = time.monotonic() + 2
        while not predicate() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(predicate())


if __name__ == "__main__":
    unittest.main()
