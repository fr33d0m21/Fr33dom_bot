import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "install.sh"


class InstallScriptUpdateFlowTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home"
        self.hermes_home = self.root / ".hermes"
        self.extensions_dir = self.hermes_home / "extensions"
        self.webui_dir = self.extensions_dir / "hermes-webui"
        self.frontend_dir = self.webui_dir / "frontend"
        self.command_log = self.root / "command.log"
        self.stub_bin = self.root / "stub-bin"
        self.local_bin = self.home / ".local" / "bin"

        self._create_installed_layout()
        self._create_stubs()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _create_installed_layout(self) -> None:
        repo_names = (
            "hermes-agent-self-evolution",
            "hermes-plugins",
            "hermes-skill-factory",
            "super-hermes",
            "hermes-life-os",
            "execplan-skill",
            "hermes-neurovision",
            "hermes-webui",
        )

        (self.hermes_home / "hermes-agent").mkdir(parents=True, exist_ok=True)
        for repo_name in repo_names:
            repo_dir = self.extensions_dir / repo_name
            (repo_dir / ".git").mkdir(parents=True, exist_ok=True)

        self.frontend_dir.mkdir(parents=True, exist_ok=True)
        (self.frontend_dir / "package.json").write_text('{"name":"stub-webui"}\n', encoding="utf-8")
        (self.frontend_dir / "package-lock.json").write_text('{"name":"stub-webui"}\n', encoding="utf-8")
        (self.webui_dir / "webui").mkdir(parents=True, exist_ok=True)
        (self.webui_dir / "webui" / "__init__.py").write_text("", encoding="utf-8")

    def _write_stub(self, name: str, body: str) -> None:
        path = self.stub_bin / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    def _create_stubs(self) -> None:
        self._write_stub(
            "git",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                if [ "${1:-}" = "-C" ]; then
                    cd "$2"
                    shift 2
                fi
                printf 'git\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$INSTALL_TEST_LOG"
                case "${1:-}" in
                    clone)
                        shift
                        while [ $# -gt 0 ] && [[ "$1" == -* ]]; do
                            shift
                        done
                        src="${1:-}"
                        dest="${2:-}"
                        if [ -z "$dest" ]; then
                            echo "missing clone destination" >&2
                            exit 1
                        fi
                        mkdir -p "$dest"
                        if [ -d "$src" ]; then
                            cp -R "$src"/. "$dest"/
                        else
                            mkdir -p "$dest/.git"
                        fi
                        exit 0
                        ;;
                    apply|reset|clean)
                        exit 0
                        ;;
                    *)
                        exit 0
                        ;;
                esac
                """
            ),
        )
        self._write_stub(
            "uv",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'uv\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$INSTALL_TEST_LOG"
                if [ "${1:-}" = "--version" ]; then
                    echo "uv-test 0.0.0"
                    exit 0
                fi
                if [ "${1:-}" = "venv" ]; then
                    dest="${2:-}"
                    mkdir -p "$dest/bin"
                    printf '#!/usr/bin/env bash\\nexit 0\\n' > "$dest/bin/python"
                    chmod +x "$dest/bin/python"
                    exit 0
                fi
                if [ "${1:-}" = "pip" ] && [ "${2:-}" = "install" ]; then
                    exit 0
                fi
                echo "unexpected uv args: $*" >&2
                exit 1
                """
            ),
        )
        for command_name in ("curl", "rg", "ffmpeg", "ttyd", "npm", "npx", "systemctl", "loginctl"):
            self._write_stub(
                command_name,
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '{command_name}\\tcwd=%s\\targs=%s\\n' "$PWD" "$*" >> "$INSTALL_TEST_LOG"
                    exit 0
                    """
                ),
            )

        self.local_bin.mkdir(parents=True, exist_ok=True)
        for stub_path in self.stub_bin.iterdir():
            (self.local_bin / stub_path.name).symlink_to(stub_path)

    def _prepare_existing_webui_install(self) -> None:
        live_python = self.webui_dir / "venv" / "bin" / "python"
        live_python.parent.mkdir(parents=True, exist_ok=True)
        live_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        live_python.chmod(0o755)

        service_dir = self.home / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        (service_dir / "fr33d0m-webui.service").write_text("[Unit]\nDescription=stub\n", encoding="utf-8")

    def _run_install(self) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.home),
                "HERMES_HOME": str(self.hermes_home),
                "PATH": f"{self.stub_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                "INSTALL_TEST_LOG": str(self.command_log),
            }
        )
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

    def test_existing_webui_install_uses_staged_refresh(self) -> None:
        self._prepare_existing_webui_install()

        result = self._run_install()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Creating staged hermes-webui clone", result.stdout)
        self.assertNotIn("Applying Fr33d0m dashboard patch to hermes-webui...", result.stdout)

        log_lines = self._command_log_lines()
        npm_lines = [line for line in log_lines if line.startswith("npm\t")]
        npx_lines = [line for line in log_lines if line.startswith("npx\t")]

        self.assertTrue(npm_lines, log_lines)
        self.assertTrue(npx_lines, log_lines)
        self.assertTrue(all(f"cwd={self.frontend_dir}" not in line for line in npm_lines), log_lines)
        self.assertTrue(all(f"cwd={self.frontend_dir}" not in line for line in npx_lines), log_lines)

    def test_fresh_webui_install_keeps_in_place_bootstrap(self) -> None:
        result = self._run_install()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Creating staged hermes-webui clone", result.stdout)
        self.assertIn("Applying Fr33d0m dashboard patch to hermes-webui...", result.stdout)

        log_lines = self._command_log_lines()
        self.assertTrue(any(f"cwd={self.frontend_dir}" in line for line in log_lines if line.startswith("npm\t")), log_lines)
        self.assertTrue(any(f"cwd={self.frontend_dir}" in line for line in log_lines if line.startswith("npx\t")), log_lines)


if __name__ == "__main__":
    unittest.main()
