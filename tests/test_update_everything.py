import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "bin" / "fr33d0m-update-everything"


class UpdateEverythingScriptTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home"
        self.home.mkdir(parents=True)
        self.hermes_home = self.home / ".hermes"
        self.extensions_dir = self.hermes_home / "extensions"
        self.extensions_dir.mkdir(parents=True)
        self.fr33dom_repo = self.home / "Fr33dom_bot"
        self.fr33dom_repo.mkdir(parents=True)
        self.command_log = self.root / "command.log"
        self.stub_bin = self.root / "stub-bin"
        self.local_bin = self.home / ".local" / "bin"
        self.status_path = self.root / "update-status.json"
        self.logs_dir = self.hermes_home / "logs"
        self.default_status_path = self.logs_dir / "update-everything.status.json"
        self.default_refresh_status_path = self.logs_dir / "dashboard-refresh.status.json"
        self.real_git = shutil.which("git")
        if not self.real_git:
            raise RuntimeError("git is required for update-everything tests")

        self._init_fr33dom_git_repo()
        self._create_hermes_layout()
        self._create_stubs()
        self._install_repo_scripts_for_packaged_only()

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

    def _init_fr33dom_git_repo(self) -> None:
        subprocess.run([self.real_git, "init"], cwd=self.fr33dom_repo, env=self._git_env(), check=True)
        (self.fr33dom_repo / "README.txt").write_text("packaged\n", encoding="utf-8")
        subprocess.run([self.real_git, "add", "."], cwd=self.fr33dom_repo, env=self._git_env(), check=True)
        subprocess.run(
            [self.real_git, "commit", "-m", "init"],
            cwd=self.fr33dom_repo,
            env=self._git_env(),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _install_repo_scripts_for_packaged_only(self) -> None:
        shutil.copy2(REPO_ROOT / "install.sh", self.fr33dom_repo / "install.sh")
        (self.fr33dom_repo / "bin").mkdir(exist_ok=True)
        shutil.copy2(SCRIPT_PATH, self.fr33dom_repo / "bin" / "fr33d0m-update-everything")
        shutil.copy2(self.stub_bin / "fr33d0m", self.fr33dom_repo / "bin" / "fr33d0m")
        shutil.copy2(self.stub_bin / "fr33d0m-refresh-dashboard", self.fr33dom_repo / "bin" / "fr33d0m-refresh-dashboard")
        for name in (
            "fr33d0m-webui",
            "fr33d0m-neurovision",
            "fr33d0m-neurovision-shell",
            "fr33d0m-terminal-shell",
        ):
            src = REPO_ROOT / "bin" / name
            if src.exists():
                shutil.copy2(src, self.fr33dom_repo / "bin" / name)
        minimal = self.fr33dom_repo / "minimal-packaged"
        minimal.mkdir(exist_ok=True)
        (minimal / "fr33d0m-skin.yaml").write_text("skin: test\n", encoding="utf-8")
        skins = self.fr33dom_repo / "skins"
        skins.mkdir(exist_ok=True)
        shutil.copy2(minimal / "fr33d0m-skin.yaml", skins / "fr33d0m-skin.yaml")
        for sub in ("config", "plugins", "skills", "prisms", "patches"):
            d = self.fr33dom_repo / sub
            d.mkdir(exist_ok=True)
            (d / "packaged-stub.txt").write_text("stub\n", encoding="utf-8")
        (self.fr33dom_repo / "config" / "config.yaml").write_text("x: 1\n", encoding="utf-8")
        (self.fr33dom_repo / "config" / "SOUL.md").write_text("soul\n", encoding="utf-8")
        (self.fr33dom_repo / "config" / "fr33d0m-dashboard.yaml").write_text("dash: 1\n", encoding="utf-8")
        patch_src = REPO_ROOT / "patches" / "hermes-webui.patch"
        if patch_src.exists():
            shutil.copy2(patch_src, self.fr33dom_repo / "patches" / "hermes-webui.patch")
        else:
            (self.fr33dom_repo / "patches" / "hermes-webui.patch").write_text("", encoding="utf-8")

    def _create_hermes_layout(self) -> None:
        (self.hermes_home / "hermes-agent" / "venv" / "bin").mkdir(parents=True)
        hp = self.hermes_home / "hermes-agent" / "venv" / "bin" / "python"
        hp.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                LOG="${UPDATE_TEST_LOG:-}"
                if [ "${1:-}" = "-m" ] && [ "${2:-}" = "pip" ]; then
                    [ -n "$LOG" ] && printf 'hermes-python-pip\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$LOG"
                    exit 0
                fi
                exit 0
                """
            ),
            encoding="utf-8",
        )
        hp.chmod(0o755)
        (self.hermes_home / "auth.json").write_text(json.dumps({"webui_token": "test-token-xyz"}), encoding="utf-8")
        (self.hermes_home / "patches").mkdir(exist_ok=True)
        patch = REPO_ROOT / "patches" / "hermes-webui.patch"
        if patch.exists():
            shutil.copy2(patch, self.hermes_home / "patches" / "hermes-webui.patch")
        else:
            (self.hermes_home / "patches" / "hermes-webui.patch").write_text("", encoding="utf-8")

        webui = self.extensions_dir / "hermes-webui"
        webui.mkdir(parents=True)
        (webui / ".git").mkdir()
        (webui / "frontend").mkdir()
        (webui / "venv" / "bin").mkdir(parents=True)
        wp = webui / "venv" / "bin" / "python"
        wp.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        wp.chmod(0o755)

        ext_other = self.extensions_dir / "sample-ext"
        ext_other.mkdir()
        subprocess.run([self.real_git, "init"], cwd=ext_other, env=self._git_env(), check=True)
        (ext_other / "requirements.txt").write_text("noop\n", encoding="utf-8")
        (ext_other / "f.py").write_text("# ext\n", encoding="utf-8")
        subprocess.run([self.real_git, "add", "."], cwd=ext_other, env=self._git_env(), check=True)
        subprocess.run(
            [self.real_git, "commit", "-m", "e"],
            cwd=ext_other,
            env=self._git_env(),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        pyonly = self.extensions_dir / "pyproject-only-ext"
        pyonly.mkdir()
        (pyonly / "pyproject.toml").write_text(
            '[project]\nname = "pyonly"\nversion = "0"\n',
            encoding="utf-8",
        )
        subprocess.run([self.real_git, "init"], cwd=pyonly, env=self._git_env(), check=True)
        subprocess.run([self.real_git, "add", "."], cwd=pyonly, env=self._git_env(), check=True)
        subprocess.run(
            [self.real_git, "commit", "-m", "pyonly"],
            cwd=pyonly,
            env=self._git_env(),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

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
                repo_root="{self.fr33dom_repo}"
                if [ "${{1:-}}" = "-C" ]; then
                    cd "$2"
                    shift 2
                fi
                printf 'git\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$UPDATE_TEST_LOG"
                case "${{1:-}}" in
                    diff-index)
                        if [ "${{GIT_DIRTY_FR33DOM:-0}}" = "1" ] && [ "$PWD" = "$repo_root" ]; then
                            exit 1
                        fi
                        exec "{self.real_git}" "$@"
                        ;;
                    fetch|pull)
                        if [ "${{GIT_FAIL_REPO_SYNC:-0}}" = "1" ] && [ "$PWD" = "$repo_root" ]; then
                            exit 1
                        fi
                        if ! "{self.real_git}" -C "$PWD" remote get-url origin >/dev/null 2>&1; then
                            exit 0
                        fi
                        exec "{self.real_git}" "$@"
                        ;;
                    *)
                        exec "{self.real_git}" "$@"
                        ;;
                esac
                """
            ),
        )
        self._write_stub(
            "bash",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'bash\tcwd=%s\targs=%s\n' "$PWD" "$*" >> "$UPDATE_TEST_LOG"
                exec /bin/bash "$@"
                """
            ),
        )
        self._write_stub(
            "fr33d0m",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'fr33d0m\tcwd=%s\targs=%s\n' "$PWD" "$*" >> "$UPDATE_TEST_LOG"
                if [ "${1:-}" = "update" ]; then
                    if [ "${FR33DOM_HERMES_UPDATE_FAIL:-0}" = "1" ]; then
                        echo "update failed" >&2
                        exit 1
                    fi
                    if [ "${FR33DOM_HERMES_ALREADY_CURRENT:-0}" = "1" ]; then
                        echo "Already up to date."
                        exit 0
                    fi
                    echo "Updated hermes core."
                    exit 0
                fi
                exit 0
                """
            ),
        )
        self._write_stub(
            "fr33d0m-refresh-dashboard",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'fr33d0m-refresh-dashboard\tcwd=%s\targs=%s\n' "$PWD" "$*" >> "$UPDATE_TEST_LOG"
                exit "${FR33DOM_REFRESH_EXIT:-0}"
                """
            ),
        )
        self._write_stub(
            "uv",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'uv\tcwd=%s\targs=%s\n' "$PWD" "$*" >> "$UPDATE_TEST_LOG"
                exit 0
                """
            ),
        )
        self._write_stub(
            "systemctl",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'systemctl\tcwd=%s\targs=%s\n' "$PWD" "$*" >> "$UPDATE_TEST_LOG"
                if [ "${1:-}" = "--user" ]; then
                    shift
                fi
                action="${1:-}"
                case "$action" in
                    is-active)
                        svc="${2:-}"
                        case "$svc" in
                            fr33d0m-webui.service)
                                exit "${SYSTEMCTL_WEBUI_ACTIVE:-0}"
                                ;;
                            fr33d0m-gateway.service)
                                exit "${SYSTEMCTL_GATEWAY_ACTIVE:-0}"
                                ;;
                            fr33d0m-terminal.service)
                                exit "${SYSTEMCTL_TERMINAL_ACTIVE:-0}"
                                ;;
                            fr33d0m-neurovision-web.service)
                                exit "${SYSTEMCTL_NEURO_ACTIVE:-0}"
                                ;;
                            *)
                                exit 0
                                ;;
                        esac
                        ;;
                    restart)
                        exit "${SYSTEMCTL_RESTART_EXIT:-0}"
                        ;;
                    *)
                        exit 0
                        ;;
                esac
                """
            ),
        )
        self._write_stub(
            "curl",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'curl\tcwd=%s\targs=%s\n' "$PWD" "$*" >> "$UPDATE_TEST_LOG"
                url="${@: -1}"
                case "$url" in
                    */api/health)
                        exit "${CURL_HEALTH_EXIT:-0}"
                        ;;
                    */api/admin/update-everything/status)
                        exit "${CURL_PROTECTED_EXIT:-0}"
                        ;;
                    *)
                        exit "${CURL_DEFAULT_EXIT:-0}"
                        ;;
                esac
                """
            ),
        )

        self.local_bin.mkdir(parents=True, exist_ok=True)
        for name in ("fr33d0m", "fr33d0m-refresh-dashboard"):
            dest = self.local_bin / name
            if dest.exists() or dest.is_symlink():
                dest.unlink()
            dest.symlink_to(self.stub_bin / name)

    def _write_initial_status(self, path: Path | None = None) -> None:
        import time

        target = path or self.status_path
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "job_type": "update_everything",
            "state": "running",
            "running": True,
            "pid": None,
            "current_phase": None,
            "phases": [],
            "started_at": time.time(),
            "completed_at": None,
            "last_updated_at": time.time(),
            "stale_after_seconds": 900,
            "log": "",
        }
        target.write_text(json.dumps(payload), encoding="utf-8")

    def _run_script(
        self,
        *,
        skip_preflight_lock_check: bool = True,
        initial_status: dict | None = None,
        provide_status_env: bool = True,
        status_path: Path | None = None,
        stub_bin_dir: Path | None = None,
        **env_overrides: str,
    ) -> subprocess.CompletedProcess[str]:
        target_status_path = status_path or self.status_path
        if initial_status is not None:
            target_status_path.parent.mkdir(parents=True, exist_ok=True)
            target_status_path.write_text(json.dumps(initial_status), encoding="utf-8")
        elif provide_status_env:
            self._write_initial_status(target_status_path)
        stub = stub_bin_dir or self.stub_bin
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.home),
                "HERMES_HOME": str(self.hermes_home),
                "PATH": f"{stub}:{self.local_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                "UPDATE_TEST_LOG": str(self.command_log),
                "FR33DOM_BOT_REPO": str(self.fr33dom_repo),
            }
        )
        if provide_status_env:
            env["FR33DOM_UPDATE_EVERYTHING_STATUS_FILE"] = str(target_status_path)
        if skip_preflight_lock_check:
            env["FR33DOM_SKIP_PREFLIGHT_LOCK_CHECK"] = "1"
        env.update(env_overrides)
        return subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def _command_log_lines(self) -> list[str]:
        if not self.command_log.exists():
            return []
        return self.command_log.read_text(encoding="utf-8").splitlines()

    def _status(self, path: Path | None = None) -> dict:
        target = path or self.status_path
        return json.loads(target.read_text(encoding="utf-8"))

    def _assert_job_status_failed_terminal(self, path: Path | None = None) -> None:
        st = self._status(path)
        self.assertEqual(st.get("state"), "failure")
        self.assertIs(st.get("running"), False)
        self.assertIsNotNone(st.get("completed_at"))

    def test_update_everything_runs_repo_sync_first(self) -> None:
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = self._command_log_lines()
        git_lines = [ln for ln in lines if ln.startswith("git\t")]
        self.assertTrue(git_lines, lines)
        fr_fetch_i = next(
            (i for i, ln in enumerate(lines) if f"cwd={self.fr33dom_repo}" in ln and "fetch" in ln and ln.startswith("git\t")),
            -1,
        )
        fr_pull_i = next(
            (i for i, ln in enumerate(lines) if f"cwd={self.fr33dom_repo}" in ln and "pull" in ln and ln.startswith("git\t")),
            -1,
        )
        self.assertGreaterEqual(fr_fetch_i, 0, lines)
        self.assertGreater(fr_pull_i, fr_fetch_i, lines)

    def test_update_everything_runs_packaged_install_refresh_after_repo_sync(self) -> None:
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = self._command_log_lines()
        git_lines = [ln for ln in lines if ln.startswith("git\t") and f"cwd={self.fr33dom_repo}" in ln]
        bash_lines = [ln for ln in lines if ln.startswith("bash\t")]
        install_hits = [ln for ln in bash_lines if "install.sh" in ln]
        self.assertTrue(install_hits, bash_lines)
        last_git_before_install = max(i for i, ln in enumerate(lines) if ln in git_lines and "pull" in ln)
        first_install = min(i for i, ln in enumerate(lines) if ln in install_hits)
        self.assertLess(last_git_before_install, first_install, lines)

    def test_update_everything_fails_on_dirty_repo_sync(self) -> None:
        result = self._run_script(GIT_DIRTY_FR33DOM="1")
        self.assertNotEqual(result.returncode, 0)
        self._assert_job_status_failed_terminal()
        lines = self._command_log_lines()
        self.assertFalse(any("install.sh" in ln for ln in lines if ln.startswith("bash\t")), lines)

    def test_update_everything_stops_on_repo_sync_git_failure_before_packaged_install(self) -> None:
        result = self._run_script(GIT_FAIL_REPO_SYNC="1")
        self.assertNotEqual(result.returncode, 0)
        self._assert_job_status_failed_terminal()
        lines = self._command_log_lines()
        self.assertFalse(any("install.sh" in ln for ln in lines if ln.startswith("bash\t")), lines)

    def test_update_everything_updates_extensions_before_dependency_refresh(self) -> None:
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = self._command_log_lines()
        ext_path = self.extensions_dir / "sample-ext"
        ext_pull_idx = next(
            (i for i, ln in enumerate(lines) if ln.startswith("git\t") and f"cwd={ext_path}" in ln and "pull" in ln),
            -1,
        )
        uv_idx = next(
            (
                i
                for i, ln in enumerate(lines)
                if ln.startswith("uv\t") and "sample-ext" in ln and "pip" in ln
            ),
            -1,
        )
        self.assertGreaterEqual(ext_pull_idx, 0, lines)
        self.assertGreater(uv_idx, ext_pull_idx, lines)

        webui_path = self.extensions_dir / "hermes-webui"
        webui_pulls = [
            ln
            for ln in lines
            if ln.startswith("git\t") and f"cwd={webui_path}" in ln and "pull" in ln
        ]
        self.assertEqual(webui_pulls, [], lines)

    def test_update_everything_extensions_skipped_when_pulls_report_no_updates(self) -> None:
        """Managed repos exist but HEAD unchanged after each pull → phase skipped per spec."""
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        phases = {p["name"]: p for p in self._status().get("phases", [])}
        ext = phases.get("extensions", {})
        self.assertEqual(ext.get("state"), "skipped")
        self.assertIn("no extension updates needed", ext.get("detail", ""))

    def test_dependency_refresh_uses_pip_editable_for_pyproject_when_uv_missing(self) -> None:
        stub_no_uv = self.root / "stub-no-uv"
        stub_no_uv.mkdir(parents=True)
        for item in self.stub_bin.iterdir():
            if item.name == "uv":
                continue
            (stub_no_uv / item.name).symlink_to(item)
        result = self._run_script(stub_bin_dir=stub_no_uv)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = self._command_log_lines()
        pip_lines = [ln for ln in lines if ln.startswith("hermes-python-pip\t")]
        self.assertTrue(pip_lines, lines)
        blob = "\n".join(pip_lines)
        self.assertIn("pyproject-only-ext", blob)
        self.assertIn("-e", blob)
        self.assertIn("sample-ext", blob)

    def test_dependency_refresh_fails_when_pyproject_needs_refresh_but_no_uv_and_no_hermes_python(self) -> None:
        stub_no_uv = self.root / "stub-no-uv-b"
        stub_no_uv.mkdir(parents=True)
        for item in self.stub_bin.iterdir():
            if item.name == "uv":
                continue
            (stub_no_uv / item.name).symlink_to(item)
        hp = self.hermes_home / "hermes-agent" / "venv" / "bin" / "python"
        hp.chmod(0o644)
        try:
            result = self._run_script(stub_bin_dir=stub_no_uv)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self._assert_job_status_failed_terminal()
            out = result.stdout + result.stderr
            self.assertIn("ERROR:", out)
            self.assertIn("pyproject.toml needs uv or Hermes venv python", out)
        finally:
            hp.chmod(0o755)

    def test_preflight_fails_when_update_everything_status_shows_other_running_pid(self) -> None:
        sleeper = subprocess.Popen(["sleep", "60"])
        try:
            status = {
                "job_type": "update_everything",
                "state": "running",
                "running": True,
                "pid": sleeper.pid,
                "current_phase": "repo_sync",
                "phases": [],
                "started_at": time.time(),
                "completed_at": None,
                "last_updated_at": time.time(),
                "stale_after_seconds": 900,
                "log": "",
            }
            result = self._run_script(skip_preflight_lock_check=False, initial_status=status)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self._assert_job_status_failed_terminal()
            self.assertIn("Another update-everything job", result.stdout + result.stderr)
            lines = self._command_log_lines()
            self.assertFalse(any("install.sh" in ln for ln in lines if ln.startswith("bash\t")), lines)
        finally:
            sleeper.kill()
            try:
                sleeper.wait(timeout=5)
            except subprocess.TimeoutExpired:
                sleeper.kill()

    def test_direct_cli_run_creates_default_status_file_under_logs(self) -> None:
        result = self._run_script(provide_status_env=False)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.default_status_path.exists())
        st = self._status(self.default_status_path)
        self.assertEqual(st.get("job_type"), "update_everything")
        self.assertIs(st.get("running"), False)
        self.assertIsNotNone(st.get("completed_at"))

    def test_preflight_uses_default_update_status_file_lock_without_env_override(self) -> None:
        sleeper = subprocess.Popen(["sleep", "60"])
        try:
            status = {
                "job_type": "update_everything",
                "state": "running",
                "running": True,
                "pid": sleeper.pid,
                "current_phase": "repo_sync",
                "phases": [],
                "started_at": time.time(),
                "completed_at": None,
                "last_updated_at": time.time(),
                "stale_after_seconds": 900,
                "log": "",
            }
            result = self._run_script(
                skip_preflight_lock_check=False,
                provide_status_env=False,
                status_path=self.default_status_path,
                initial_status=status,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self._status(self.default_status_path), status)
            self.assertIn("Another update-everything job", result.stdout + result.stderr)
            lines = self._command_log_lines()
            self.assertFalse(any("install.sh" in ln for ln in lines if ln.startswith("bash\t")), lines)
        finally:
            sleeper.kill()
            try:
                sleeper.wait(timeout=5)
            except subprocess.TimeoutExpired:
                sleeper.kill()

    def test_preflight_uses_default_refresh_status_file_without_env_override(self) -> None:
        sleeper = subprocess.Popen(["sleep", "60"])
        try:
            self.default_refresh_status_path.parent.mkdir(parents=True, exist_ok=True)
            self.default_refresh_status_path.write_text(
                json.dumps(
                    {
                        "job_type": "refresh_dashboard",
                        "state": "running",
                        "pid": sleeper.pid,
                    }
                ),
                encoding="utf-8",
            )

            result = self._run_script(skip_preflight_lock_check=False, provide_status_env=False)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self._assert_job_status_failed_terminal(self.default_status_path)
            self.assertIn("Another dashboard refresh job", result.stdout + result.stderr)
        finally:
            sleeper.kill()
            try:
                sleeper.wait(timeout=5)
            except subprocess.TimeoutExpired:
                sleeper.kill()

    def test_preflight_ignores_stale_default_refresh_status_file_when_refresh_pid_is_dead(self) -> None:
        stale_ts = time.time() - 901.0
        self.default_refresh_status_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_refresh_status_path.write_text(
            json.dumps(
                {
                    "job_type": "refresh_dashboard",
                    "state": "running",
                    "running": True,
                    "pid": 999999,
                    "started_at": stale_ts,
                    "completed_at": None,
                }
            ),
            encoding="utf-8",
        )
        (self.logs_dir / "dashboard-refresh.log").write_text(
            "Waiting for detached refresh process to start...\n",
            encoding="utf-8",
        )

        result = self._run_script(skip_preflight_lock_check=False, provide_status_env=False)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        st = self._status(self.default_status_path)
        self.assertEqual(st.get("state"), "success")
        lines = self._command_log_lines()
        self.assertTrue(any(ln.startswith("fr33d0m-refresh-dashboard\t") for ln in lines), lines)

    def test_update_everything_calls_staged_dashboard_refresh(self) -> None:
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = self._command_log_lines()
        self.assertTrue(
            any(ln.startswith("fr33d0m-refresh-dashboard\t") for ln in lines),
            lines,
        )

    def test_update_everything_uses_x_hermes_token_for_dashboard_auth_checks(self) -> None:
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = self._command_log_lines()
        curl_lines = [ln for ln in lines if ln.startswith("curl\t")]
        self.assertTrue(curl_lines, lines)
        self.assertTrue(all("X-Hermes-Token: test-token-xyz" in ln for ln in curl_lines), curl_lines)
        self.assertTrue(all("Authorization: Bearer" not in ln for ln in curl_lines), curl_lines)

    def test_update_everything_checks_protected_dashboard_status_during_post_checks(self) -> None:
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = self._command_log_lines()
        curl_lines = [ln for ln in lines if ln.startswith("curl\t")]
        health_idx = next((i for i, ln in enumerate(curl_lines) if "/api/health" in ln), -1)
        protected_idx = next(
            (i for i, ln in enumerate(curl_lines) if "/api/admin/update-everything/status" in ln),
            -1,
        )
        self.assertGreaterEqual(health_idx, 0, curl_lines)
        self.assertGreater(protected_idx, health_idx, curl_lines)

    def test_update_everything_stops_after_blocking_phase_failure(self) -> None:
        result = self._run_script(FR33DOM_HERMES_UPDATE_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self._assert_job_status_failed_terminal()
        lines = self._command_log_lines()
        self.assertFalse(any(ln.startswith("fr33d0m-refresh-dashboard\t") for ln in lines), lines)

    def test_update_everything_restarts_non_webui_services_after_dashboard_refresh(self) -> None:
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = self._command_log_lines()
        dash_i = next((i for i, ln in enumerate(lines) if ln.startswith("fr33d0m-refresh-dashboard\t")), -1)
        restarts = [
            (i, ln)
            for i, ln in enumerate(lines)
            if ln.startswith("systemctl\t") and "restart" in ln and "fr33d0m-gateway.service" in ln
        ]
        self.assertTrue(restarts, lines)
        self.assertLess(dash_i, restarts[0][0], lines)
        names = " ".join(lines)
        self.assertIn("fr33d0m-terminal.service", names)
        self.assertIn("fr33d0m-neurovision-web.service", names)

    def test_update_everything_marks_postcheck_degradation_as_partial_failure_with_failed_phase(self) -> None:
        result = self._run_script(CURL_HEALTH_EXIT="22")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        st = self._status()
        self.assertEqual(st.get("state"), "partial_failure")
        phases = {p["name"]: p for p in st.get("phases", [])}
        self.assertEqual(phases.get("post_checks", {}).get("state"), "failure")
        self.assertIn("detail", phases.get("post_checks", {}))

    def test_update_everything_marks_postcheck_degradation_when_protected_dashboard_check_fails(self) -> None:
        result = self._run_script(CURL_PROTECTED_EXIT="22")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        st = self._status()
        self.assertEqual(st.get("state"), "partial_failure")
        phases = {p["name"]: p for p in st.get("phases", [])}
        self.assertEqual(phases.get("post_checks", {}).get("state"), "failure")
        self.assertIn("detail", phases.get("post_checks", {}))

    def test_update_everything_status_contract_matches_backend_schema(self) -> None:
        result = self._run_script(CURL_HEALTH_EXIT="22")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        st = self._status()
        self.assertEqual(st.get("job_type"), "update_everything")
        self.assertEqual(st.get("state"), "partial_failure")
        self.assertIs(st.get("running"), False)
        phases = {p["name"]: p for p in st.get("phases", [])}
        post_checks = phases.get("post_checks", {})
        self.assertEqual(post_checks.get("state"), "failure")
        self.assertIn("detail", post_checks)
        self.assertNotIn("summary", post_checks)


if __name__ == "__main__":
    unittest.main()
