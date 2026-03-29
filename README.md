# Fr33d0m Bot

```
  ███████╗██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ███╗   ███╗
  ██╔════╝██╔══██╗╚════██╗╚════██╗██╔══██╗██╔═══██╗████╗ ████║
  █████╗  ██████╔╝ █████╔╝ █████╔╝██║  ██║██║   ██║██╔████╔██║
  ██╔══╝  ██╔══██╗ ╚═══██╗ ╚═══██╗██║  ██║██║   ██║██║╚██╔╝██║
  ██║     ██║  ██║██████╔╝██████╔╝██████╔╝╚██████╔╝██║ ╚═╝ ██║
  ╚═╝     ╚═╝  ╚═╝╚═════╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝
```

A custom AI agent build powered by [Hermes Agent](https://github.com/NousResearch/hermes-agent), with extended skills, plugins, analytical prisms, and the `fr33d0m-skin` theme. Designed for Ubuntu VMs with services that autostart on boot.

## Install (Ubuntu)

```bash
git clone https://github.com/fr33d0m21/Fr33dom_bot.git
cd Fr33dom_bot
bash install.sh
source ~/.bashrc
fr33d0m setup
```

The installer handles everything: Hermes Agent, Python/Node.js dependencies, all extensions, the `fr33d0m` command, the Fr33d0m dashboard patch for `hermes-webui`, the seeded runtime dashboard config at `~/.hermes/fr33d0m-dashboard.yaml`, and systemd autostart services.

## Documentation

- [User Manual](USER_MANUAL.md)

## Commands

| Command | What it does |
|---------|-------------|
| `fr33d0m` | Start an interactive chat session |
| `fr33d0m setup` | Configure API keys and LLM provider |
| `fr33d0m model` | Choose your LLM model |
| `fr33d0m tools` | Configure which tools are enabled |
| `fr33d0m doctor` | Diagnose any issues |
| `fr33d0m config show` | Show current configuration |
| `fr33d0m skills list` | Browse available skills |
| `fr33d0m gateway start` | Start messaging gateway (Telegram, Discord, etc.) |
| `fr33d0m update` | Update Hermes Agent to latest |
| `fr33d0m-update-everything` | Full local maintenance: sync `Fr33dom_bot` from `origin/main`, refresh packaged files, update Hermes core, pull other extensions, refresh Python deps, run staged dashboard refresh, restart non-WebUI services (see below) |
| `fr33d0m-refresh-dashboard` | Reapply the packaged WebUI patch, refresh backend deps, rebuild the frontend, and restart the local dashboard service |
| `fr33d0m-webui` | Launch the web dashboard (port 8643) |
| `fr33d0m-neurovision` | Launch the terminal visualizer |

All `fr33d0m` commands map directly to `hermes` — every Hermes command works.

## Dashboard Views

The Fr33d0m dashboard on port `8643` now acts as the main hub:

| Route | What it does |
|-------|---------------|
| `/` | Fr33d0m Hub dashboard with gateway controls, doctor/fix buttons, and OpenRouter MiniMax setup |
| `/gateway` | Configure messaging gateways with cards, tests, and pairing approval buttons |
| `/terminal` | Browser terminal with reconnect controls and a full shell welcome banner |
| `/neurovision` | Browser view of the curses visualizer via `ttyd` with reconnect support |
| `/personality` | Edit curated runtime-only personality files such as `SOUL.md` |
| `/files` | Browse and edit files under allowlisted runtime roots without exposing the packaging repo |
| `/skills` | Manage custom skills: create, edit `SKILL.md`, and delete |

### Dashboard-first setup flow

1. Log into the dashboard
2. Enter `OPENROUTER_API_KEY`
3. Apply the default model `minimax/minimax-m2.7`
4. Use the dashboard buttons to start or restart the gateway
5. Configure messaging platforms in `/gateway`
6. Use `/personality` for curated runtime personality edits and `/files` for allowlisted runtime file management
7. Use `/terminal` for shell access and `/skills` for custom skill management

### Runtime editors

`/personality` is runtime-only. It edits curated files from `~/.hermes/fr33d0m-dashboard.yaml` and is intended for the live VM, not the packaging repo.

`/files` is an allowlist-based file manager. It only exposes configured roots such as `~/.hermes` and `~/Downloads`, blocks any path managed by `Personality`, and hides seeded dashboard-maintenance paths such as `~/.hermes/fr33d0m-dashboard.yaml`, `~/.hermes/extensions/hermes-webui`, and `~/.hermes/patches`.

The dashboard does not create commits, push branches, or manage git remotes. Personality, Files, and other runtime editors only change local paths under your allowlists. The hub can start **Update Everything** in the background; that runs `fr33d0m-update-everything` on the server and streams phase status into the UI—it still does not add any git commit or push flow for dashboard edits.

Use `fr33d0m-refresh-dashboard` when you only need to reapply the packaged WebUI patch, refresh backend dependencies, rebuild the frontend, and restart `fr33d0m-webui`.

### Update Everything (CLI or dashboard)

**What it updates**

- **Fr33dom_bot repo** — `git fetch` / `git pull --ff-only origin main` (requires a clean working tree).
- **Packaged runtime files** — `install.sh` in `FR33DOM_INSTALL_MODE=packaged-only` copies wrappers, `hermes-webui.patch`, skin, seeded config, plugins, skills, and prisms into `~/.hermes` (no full installer path).
- **Hermes core** — `fr33d0m update`.
- **Other extensions** — every `~/.hermes/extensions/*` directory that is a git repo except `hermes-webui` gets `git pull --ff-only`.
- **Extension Python deps** — `uv pip` or `pip` refresh for extensions that ship `pyproject.toml` or `requirements.txt` (again excluding `hermes-webui` here; the WebUI is handled next).
- **Dashboard** — `fr33d0m-refresh-dashboard` (staged clone, apply patch, reinstall WebUI deps, build frontend, swap into `~/.hermes/extensions/hermes-webui`, restart `fr33d0m-webui`).
- **Services** — user `systemctl restart` for gateway, browser terminal, and Neurovision web units (WebUI was restarted by the refresh step).

**What it does not do**

- **No OS upgrades** — it does not run `apt upgrade`, distribution updates, or kernel refreshes. Packaged-only install does not invoke the full installer’s apt phase.
- **No reboot** — the machine is not restarted.
- **No upstream `git pull` on `hermes-webui`** — the installed WebUI track is the packaged patch plus staged refresh, not a direct pull of upstream `hermes-webui`.
- **No packaging git writes from the dashboard** — the UI does not commit, push, or open PRs; Update Everything only fast-forwards your existing `~/Fr33dom_bot` clone when you run the script (including from the dashboard).

**Safety, locks, and failure reporting**

- **Preflight** — refuses to start if `~/Fr33dom_bot` has local tracked changes, free disk under `HOME` is below about 500 MiB, or another Update Everything / dashboard refresh job is already marked running (see logs under `~/.hermes/logs/`).
- **Staged WebUI refresh** — same behavior as `fr33d0m-refresh-dashboard`: work happens in a throwaway clone before swap; failed service start attempts rollback to the previous live tree.
- **Status file** — when started with a status path (as the dashboard does), phases, log tail, timestamps, and final state (`success`, `partial_failure`, or `failure`) are written for the UI to poll. Hard phase failures stop the pipeline and mark the job as `failure`; if services or authenticated health checks degrade after an otherwise successful run, the job can still finish as `partial_failure` (while exiting `0`) so you can inspect warnings without treating the whole run as a crash.

**Warning:** `fr33d0m-refresh-dashboard` (and therefore the Update Everything dashboard step) replaces the installed `~/.hermes/extensions/hermes-webui` tree after a successful build; if startup fails after the swap, the script attempts to roll back to the previous live tree.

## Services (autostart on boot)

Four systemd user services are enabled during install:

| Service | Port | What it does |
|---------|------|-------------|
| `fr33d0m-webui` | 8643 | Web dashboard — sessions, config, cron, skills |
| `fr33d0m-gateway` | — | Messaging gateway (Telegram, Discord, Slack, WhatsApp, Signal) |
| `fr33d0m-terminal` | 7681 (localhost only) | `ttyd` browser terminal with a full Fr33d0m shell |
| `fr33d0m-neurovision-web` | 7682 (localhost only) | `ttyd` browser view of neurovision |

```bash
systemctl --user status fr33d0m-webui
systemctl --user status fr33d0m-gateway
systemctl --user status fr33d0m-terminal
systemctl --user status fr33d0m-neurovision-web

systemctl --user restart fr33d0m-webui
systemctl --user stop fr33d0m-gateway
journalctl --user -u fr33d0m-webui -f
```

Services survive reboot via `loginctl enable-linger`.

## What's included

### Custom Skin
- **fr33d0m-skin** — Green (#2bfd1c) / blue (#8ea3ff) terminal theme with braille hero art

### 34 Plugins ([hermes-plugins](https://github.com/42-evey/hermes-plugins))
Autonomy, observability, quality, learning, and integration plugins including:
- `evey-autonomy` — Autonomous decision-making
- `evey-council` — Multi-model debate
- `evey-delegate-model` — Smart model routing with fallback chains
- `evey-telemetry` — Structured logging
- `evey-reflect` — Self-correction loop
- `evey-validate` — Hallucination detection
- `evey-learner` — Experiential learning
- `evey-memory-adaptive` — Importance-scored memory with decay
- `evey-goals` — Goal management
- `skill_factory.py` — Auto-generate skills from workflows

### 12 Custom Skills

| Skill | Source |
|-------|--------|
| `prism-scan` / `prism-full` / `prism-3way` / `prism-discover` / `prism-reflect` | [super-hermes](https://github.com/Cranot/super-hermes) |
| `execplan` | [execplan-skill](https://github.com/tiann/execplan-skill) |
| `life-os` | [hermes-life-os](https://github.com/Lethe044/hermes-life-os) |
| `meta/skill-factory` | [hermes-skill-factory](https://github.com/Romanescu11/hermes-skill-factory) |

### 7 Analytical Prisms
`l12.md` · `error_resilience.md` · `optimize.md` · `identity.md` · `deep_scan.md` · `claim.md` · `simulation.md`

### Standalone Tools

| Tool | Source |
|------|--------|
| Web dashboard | [hermes-webui](https://github.com/sanchomuzax/hermes-webui) |
| Terminal visualizer (85 themes) | [hermes-neurovision](https://github.com/Tranquil-Flow/hermes-neurovision) |
| Evolutionary skill optimizer | [hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) |

## File structure

```
Fr33dom_bot/
├── install.sh                # One-command Ubuntu installer
├── .env.example              # API key template
├── bin/
│   ├── fr33d0m                    # Main command (wraps hermes)
│   ├── fr33d0m-refresh-dashboard  # Reapply WebUI patch, rebuild frontend, restart fr33d0m-webui
│   ├── fr33d0m-update-everything # Full sync + extensions + staged dashboard refresh (see README)
│   ├── fr33d0m-webui              # Web dashboard launcher
│   ├── fr33d0m-neurovision        # Terminal visualizer launcher
│   ├── fr33d0m-neurovision-shell  # Shell wrapper for ttyd browser neurovision
│   └── fr33d0m-terminal-shell     # Shell banner used by the browser terminal
├── patches/
│   └── hermes-webui.patch    # Rebrand + dashboard extensions applied after clone
├── systemd/                  # Reference service unit files
├── config/
│   ├── config.yaml           # Display config (fr33d0m-skin active)
│   ├── SOUL.md               # Agent persona
│   └── fr33d0m-dashboard.yaml # Seeded runtime editor config
├── skins/
│   └── fr33d0m-skin.yaml     # Custom theme
├── plugins/                  # 34 evey plugins + skill_factory
├── skills/                   # execplan, life-os, prism-*, skill-factory
└── prisms/                   # 7 analytical lenses
```

## License

Extensions retain their original licenses. See each source repo for details.
