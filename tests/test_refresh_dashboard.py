import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "bin" / "fr33d0m-refresh-dashboard"


class RefreshDashboardScriptTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home"
        self.hermes_home = self.root / ".hermes"
        self.extensions_dir = self.hermes_home / "extensions"
        self.webui_dir = self.extensions_dir / "hermes-webui"
        self.frontend_dir = self.webui_dir / "frontend"
        self.patch_file = self.hermes_home / "patches" / "hermes-webui.patch"
        self.command_log = self.root / "command.log"
        self.stub_bin = self.root / "stub-bin"
        self.real_git = shutil.which("git")
        if not self.real_git:
            raise RuntimeError("git is required for refresh dashboard tests")

        self._create_live_webui_repo()
        self._create_stubs()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _git_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "Test Runner",
                "GIT_AUTHOR_EMAIL": "tests@example.com",
                "GIT_COMMITTER_NAME": "Test Runner",
                "GIT_COMMITTER_EMAIL": "tests@example.com",
            }
        )
        return env

    def _create_live_webui_repo(self) -> None:
        (self.frontend_dir).mkdir(parents=True, exist_ok=True)
        (self.webui_dir / "webui").mkdir(parents=True, exist_ok=True)
        (self.hermes_home / "patches").mkdir(parents=True, exist_ok=True)

        (self.webui_dir / "marker.txt").write_text("base\n", encoding="utf-8")
        (self.frontend_dir / "package.json").write_text('{"name":"stub-webui"}\n', encoding="utf-8")
        (self.frontend_dir / "package-lock.json").write_text('{"name":"stub-webui"}\n', encoding="utf-8")
        (self.webui_dir / "webui" / "__init__.py").write_text("", encoding="utf-8")

        subprocess.run([self.real_git, "init"], cwd=self.webui_dir, env=self._git_env(), check=True)
        subprocess.run([self.real_git, "add", "."], cwd=self.webui_dir, env=self._git_env(), check=True)
        subprocess.run(
            [self.real_git, "commit", "-m", "Base webui"],
            cwd=self.webui_dir,
            env=self._git_env(),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        marker = self.webui_dir / "marker.txt"
        marker.write_text("patched\n", encoding="utf-8")
        patch = subprocess.run(
            [self.real_git, "diff", "HEAD", "--", "marker.txt"],
            cwd=self.webui_dir,
            env=self._git_env(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.patch_file.write_text(patch, encoding="utf-8")
        marker.write_text("base\n", encoding="utf-8")

        live_python = self.webui_dir / "venv" / "bin" / "python"
        live_python.parent.mkdir(parents=True, exist_ok=True)
        live_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        live_python.chmod(0o755)

    def _write_stub(self, name: str, body: str) -> None:
        path = self.stub_bin / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    def _create_stubs(self) -> None:
        self._write_stub(
            "git",
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'git\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$REFRESH_TEST_LOG"
                exec "{self.real_git}" "$@"
                """
            ),
        )
        self._write_stub(
            "uv",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'uv\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$REFRESH_TEST_LOG"
                if [ "${1:-}" = "venv" ]; then
                    dest="${2:-}"
                    mkdir -p "$dest/bin"
                    printf '#!/usr/bin/env bash\\nexit 0\\n' > "$dest/bin/python"
                    chmod +x "$dest/bin/python"
                    exit 0
                fi
                if [ "${1:-}" = "pip" ] && [ "${2:-}" = "install" ]; then
                    exit "${UV_PIP_EXIT_CODE:-0}"
                fi
                echo "unexpected uv args: $*" >&2
                exit 1
                """
            ),
        )
        self._write_stub(
            "npm",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'npm\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$REFRESH_TEST_LOG"
                exit "${NPM_EXIT_CODE:-0}"
                """
            ),
        )
        self._write_stub(
            "npx",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'npx\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$REFRESH_TEST_LOG"
                exit "${NPX_EXIT_CODE:-0}"
                """
            ),
        )
        self._write_stub(
            "systemctl",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'systemctl\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$REFRESH_TEST_LOG"
                if [ "${1:-}" = "--user" ]; then
                    shift
                fi
                action="${1:-}"
                case "$action" in
                    restart)
                        exit "${SYSTEMCTL_RESTART_EXIT_CODE:-0}"
                        ;;
                    start)
                        exit "${SYSTEMCTL_START_EXIT_CODE:-0}"
                        ;;
                    *)
                        exit 0
                        ;;
                esac
                """
            ),
        )

    def _run_script(self, **overrides: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.home),
                "HERMES_HOME": str(self.hermes_home),
                "PATH": f"{self.stub_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                "REFRESH_TEST_LOG": str(self.command_log),
            }
        )
        env.update(overrides)
        return subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def _live_marker(self) -> str:
        return (self.webui_dir / "marker.txt").read_text(encoding="utf-8")

    def _command_log_lines(self) -> list[str]:
        if not self.command_log.exists():
            return []
        return self.command_log.read_text(encoding="utf-8").splitlines()

    def test_refresh_builds_in_staging_before_swap(self) -> None:
        result = self._run_script()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self._live_marker(), "patched\n")
        self.assertIn("Creating staged hermes-webui clone", result.stdout)
        self.assertIn("Refreshing backend dependencies in staging", result.stdout)
        self.assertIn("Building frontend in staging", result.stdout)
        self.assertIn("Swapping staged hermes-webui into place", result.stdout)

        log_lines = self._command_log_lines()
        npm_lines = [line for line in log_lines if line.startswith("npm\t")]
        npx_lines = [line for line in log_lines if line.startswith("npx\t")]
        uv_install_lines = [line for line in log_lines if line.startswith("uv\t") and "pip install" in line]

        self.assertTrue(npm_lines, log_lines)
        self.assertTrue(npx_lines, log_lines)
        self.assertTrue(uv_install_lines, log_lines)
        self.assertTrue(all(f"cwd={self.frontend_dir}" not in line for line in npm_lines), log_lines)
        self.assertTrue(all(f"cwd={self.frontend_dir}" not in line for line in npx_lines), log_lines)
        self.assertTrue(all(f"-e {self.webui_dir}" not in line for line in uv_install_lines), log_lines)

    def test_build_failure_keeps_live_tree_untouched(self) -> None:
        result = self._run_script(NPX_EXIT_CODE="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._live_marker(), "base\n")
        self.assertIn("Building frontend in staging", result.stdout)
        self.assertNotIn("Swapping staged hermes-webui into place", result.stdout)

    def test_start_failure_after_swap_rolls_back_previous_tree(self) -> None:
        result = self._run_script(SYSTEMCTL_RESTART_EXIT_CODE="1", SYSTEMCTL_START_EXIT_CODE="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._live_marker(), "base\n")
        self.assertIn("Swapping staged hermes-webui into place", result.stdout)
        self.assertIn("Rolling back previous live hermes-webui tree", result.stdout)

        systemctl_lines = [line for line in self._command_log_lines() if line.startswith("systemctl\t")]
        self.assertTrue(any("args=--user restart fr33d0m-webui.service" in line for line in systemctl_lines))
        self.assertTrue(any("args=--user start fr33d0m-webui.service" in line for line in systemctl_lines))


if __name__ == "__main__":
    unittest.main()
