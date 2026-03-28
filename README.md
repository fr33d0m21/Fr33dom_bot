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

The installer handles everything: Hermes Agent, Python/Node.js dependencies, all extensions, the `fr33d0m` command, the Fr33d0m dashboard patch for `hermes-webui`, and systemd autostart services.

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
| `/skills` | Manage custom skills: create, edit `SKILL.md`, and delete |

### Dashboard-first setup flow

1. Log into the dashboard
2. Enter `OPENROUTER_API_KEY`
3. Apply the default model `minimax/minimax-m2.7`
4. Use the dashboard buttons to start or restart the gateway
5. Configure messaging platforms in `/gateway`
6. Use `/terminal` for shell access and `/skills` for custom skill management

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
systemctl --user journal -u fr33d0m-webui -f
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
│   ├── fr33d0m               # Main command (wraps hermes)
│   ├── fr33d0m-terminal-shell # Shell banner used by the browser terminal
│   ├── fr33d0m-webui         # Web dashboard launcher
│   └── fr33d0m-neurovision   # Terminal visualizer launcher
├── patches/
│   └── hermes-webui.patch    # Rebrand + dashboard extensions applied after clone
├── systemd/                  # Reference service unit files
├── config/
│   ├── config.yaml           # Display config (fr33d0m-skin active)
│   └── SOUL.md               # Agent persona
├── skins/
│   └── fr33d0m-skin.yaml     # Custom theme
├── plugins/                  # 34 evey plugins + skill_factory
├── skills/                   # execplan, life-os, prism-*, skill-factory
└── prisms/                   # 7 analytical lenses
```

## License

Extensions retain their original licenses. See each source repo for details.
