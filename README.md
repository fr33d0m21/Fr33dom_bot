# Fr33d0m Bot

A custom Hermes Agent build with extended skills, plugins, analytical prisms, and the `fr33d0m-skin` theme.

Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research.

## What's included

### Custom Skin
- **fr33d0m-skin** — Green/blue terminal theme with braille hero art and custom branding

### 34 Plugins (from [hermes-plugins](https://github.com/42-evey/hermes-plugins))
Autonomy, observability, quality, learning, and integration plugins:
- `evey-autonomy` — Core autonomous decision-making
- `evey-council` — Multi-model debate for hard decisions
- `evey-delegate-model` — Smart model routing with fallback chains
- `evey-telemetry` — Structured logging of every tool call
- `evey-reflect` — Self-correction loop
- `evey-validate` — Hallucination detection
- `evey-learner` — Experiential learning from interactions
- `evey-memory-adaptive` — Importance-scored memory with decay
- `evey-goals` — Autonomous goal management
- `skill_factory.py` — Auto-generate skills from workflows
- ...and 24 more

### 12 Custom Skills
| Skill | Source | What it does |
|-------|--------|-------------|
| `prism-scan` | [super-hermes](https://github.com/Cranot/super-hermes) | Generate + execute a custom analytical lens |
| `prism-full` | super-hermes | Multi-pass pipeline with adversarial self-correction |
| `prism-3way` | super-hermes | WHERE/WHEN/WHY three-angle analysis |
| `prism-discover` | super-hermes | Map every possible analysis domain |
| `prism-reflect` | super-hermes | Analysis + meta-analysis of blind spots |
| `execplan` | [execplan-skill](https://github.com/tiann/execplan-skill) | Autonomous execution plans for complex tasks |
| `life-os` | [hermes-life-os](https://github.com/Lethe044/hermes-life-os) | Life management OS |
| `meta/skill-factory` | [hermes-skill-factory](https://github.com/Romanescu11/hermes-skill-factory) | Watch workflows, auto-generate skills |

### 7 Analytical Prisms (from [super-hermes](https://github.com/Cranot/super-hermes))
Battle-tested lenses: `l12.md`, `error_resilience.md`, `optimize.md`, `identity.md`, `deep_scan.md`, `claim.md`, `simulation.md`

### Standalone Tools
| Tool | Source | What it does |
|------|--------|-------------|
| `hermes-neurovision` | [hermes-neurovision](https://github.com/Tranquil-Flow/hermes-neurovision) | 85-theme terminal visualizer that reacts to agent activity |
| `hermes-webui` | [hermes-webui](https://github.com/sanchomuzax/hermes-webui) | Web dashboard for sessions, config, cron, skills |
| Self-evolution | [hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) | DSPy + GEPA evolutionary skill optimizer |

## Install

```bash
git clone https://github.com/fr33d0m21/Fr33dom_bot.git
cd Fr33dom_bot
bash install.sh
```

Then configure your API key:
```bash
hermes setup
```

## Quick start

```bash
hermes                          # Start chatting
hermes-neurovision --gallery    # Browse 85 terminal themes
hermes-webui --localhost        # Launch web dashboard
```

## File structure

```
Fr33dom_bot/
├── install.sh              # One-command setup
├── .env.example            # API key template
├── config/
│   ├── config.yaml         # Hermes display config (fr33d0m-skin active)
│   └── SOUL.md             # Agent persona
├── skins/
│   └── fr33d0m-skin.yaml   # Custom green/blue theme
├── plugins/                # 34 evey plugins + skill_factory
├── skills/                 # execplan, life-os, prism-*, skill-factory
└── prisms/                 # 7 analytical lenses
```

## Extension repos

All cloned to `~/.hermes/extensions/` by the installer:

| Repo | Purpose |
|------|---------|
| [hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) | Evolutionary skill optimization via DSPy + GEPA |
| [hermes-plugins](https://github.com/42-evey/hermes-plugins) | 34 autonomy/observability/quality plugins |
| [hermes-skill-factory](https://github.com/Romanescu11/hermes-skill-factory) | Auto-generate skills from workflow patterns |
| [super-hermes](https://github.com/Cranot/super-hermes) | Self-writing analytical prompts |
| [hermes-life-os](https://github.com/Lethe044/hermes-life-os) | Life management skill |
| [execplan-skill](https://github.com/tiann/execplan-skill) | Autonomous execution plans |
| [hermes-neurovision](https://github.com/Tranquil-Flow/hermes-neurovision) | Terminal neurovisualizer |
| [hermes-webui](https://github.com/sanchomuzax/hermes-webui) | Process monitoring dashboard |

## License

Extensions retain their original licenses. See each repo for details.
