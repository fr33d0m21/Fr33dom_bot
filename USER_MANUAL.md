# Fr33d0m Bot User Manual

This guide explains how to install, configure, operate, and snapshot a Fr33d0m Bot deployment.

Fr33d0m Bot is a custom agent build powered by Hermes Agent, with:

- Fr33d0m branding and skin
- Web dashboard
- Browser terminal
- Browser-accessible Neurovision
- Messaging gateway configuration
- Custom skills, plugins, and automation support

## What Gets Installed

The installer sets up:

- `fr33d0m` CLI command
- Fr33d0m-branded dashboard
- Fr33d0m skin and persona
- Custom plugins, skills, and prisms
- Messaging gateway service
- Browser terminal service
- Browser Neurovision service
- WebUI service
- Dashboard runtime controls and skill management
- Seeded runtime editor config in `~/.hermes/fr33d0m-dashboard.yaml`

## Recommended Host

Fr33d0m Bot is designed for Ubuntu VMs. A typical deployment target is:

- Ubuntu 22.04 or 24.04
- 2 to 4 GB RAM minimum
- Public IP address
- systemd available

## Installation

Clone the repo and run the installer:

```bash
git clone https://github.com/fr33d0m21/Fr33dom_bot.git
cd Fr33dom_bot
bash install.sh
source ~/.bashrc
```

The installer:

- installs missing Ubuntu packages
- installs Hermes Agent if needed
- installs Fr33d0m wrappers
- seeds `~/.hermes/fr33d0m-dashboard.yaml` for runtime Personality and Files editors
- clones the extension repositories
- applies the Fr33d0m dashboard patch to `hermes-webui`
- builds the dashboard frontend
- enables systemd user services for autostart

## Core Commands

Fr33d0m is a branded wrapper around Hermes. These are the main commands:

```bash
fr33d0m
fr33d0m setup
fr33d0m model
fr33d0m doctor
fr33d0m config show
fr33d0m skills list
fr33d0m gateway start
fr33d0m gateway restart
fr33d0m update
```

Additional commands:

```bash
fr33d0m-refresh-dashboard
fr33d0m-update-everything
fr33d0m-webui
fr33d0m-neurovision
```

## First-Time Setup

After installation, configure your LLM provider:

```bash
fr33d0m setup
```

Or edit:

```bash
~/.hermes/.env
```

For OpenRouter, the minimum setup is:

```env
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=anthropic/claude-opus-4.6
```

Do not commit secrets into git.

### Recommended default model

The Fr33d0m dashboard is designed to set the runtime to:

```text
model.provider = openrouter
model.default = minimax/minimax-m2.7
```

The dashboard can apply this automatically after you enter your `OPENROUTER_API_KEY`.

## Dashboard

The Fr33d0m dashboard runs on port `8643`.

Open:

```text
http://YOUR_SERVER_IP:8643
```

### Dashboard Login Token

The dashboard token is stored in:

```bash
~/.hermes/auth.json
```

To print it:

```bash
python3 -c "import json, pathlib; print(json.loads((pathlib.Path.home()/'.hermes'/'auth.json').read_text())['webui_token'])"
```

## Dashboard Routes

After logging in, these are the main routes:

| Route | Purpose |
| --- | --- |
| `/` | Fr33d0m Hub dashboard with gateway controls, doctor/fix buttons, and OpenRouter MiniMax setup |
| `/sessions` | Browse chat sessions |
| `/gateway` | Configure messaging gateways and pairing approvals |
| `/terminal` | Browser terminal with reconnect controls and full shell access |
| `/neurovision` | Browser view of Neurovision with reconnect controls |
| `/personality` | Edit curated runtime-only personality files defined in dashboard settings |
| `/files` | Browse and edit files under allowlisted runtime roots |
| `/config` | View config and environment data |
| `/cron` | Manage scheduled jobs |
| `/skills` | Browse built-in skills and manage custom skills |

### Dashboard-first operator flow

For most day-to-day administration, you can stay in the dashboard:

1. Open `/`
2. Enter your `OPENROUTER_API_KEY`
3. Apply `minimax/minimax-m2.7`
4. Use Start, Stop, Restart, Doctor, or Doctor Fix buttons
5. Go to `/gateway` to configure platforms and approve/revoke pairing entries
6. Go to `/personality` for curated runtime personality updates and `/files` for allowlisted file access
7. Go to `/skills` to create, edit, or delete custom skills
8. Use `/terminal` only when you need raw shell access

### Runtime editors

`/personality` is for runtime-only editing. It writes curated files listed in `~/.hermes/fr33d0m-dashboard.yaml`, such as `SOUL.md`, and is meant to update the live Hermes runtime rather than the packaging repo.

`/files` is an allowlist-based file manager. It only exposes roots declared in `~/.hermes/fr33d0m-dashboard.yaml`, keeps `Personality`-owned files on the dedicated editor path, and hides seeded dashboard-maintenance paths such as `~/.hermes/fr33d0m-dashboard.yaml`, `~/.hermes/extensions/hermes-webui`, and `~/.hermes/patches`.

The dashboard has no git push or git commit flow for Personality, Files, or other runtime editors. Runtime edits stay local to the VM. The hub can start **Update Everything**, which only runs the server-side `fr33d0m-update-everything` script in the background and shows phase status in the UI—it does not turn the dashboard into a git client for your content.

If you only need to reapply the packaged patch, refresh backend dependencies, rebuild the frontend, and restart the local WebUI service, use `fr33d0m-refresh-dashboard`.

**Warning:** `fr33d0m-refresh-dashboard` now stages a fresh `hermes-webui` clone outside the live tree, reapplies the packaged patch there, refreshes backend dependencies, and rebuilds the frontend before swapping it into place. A successful refresh replaces the installed `~/.hermes/extensions/hermes-webui` tree; if startup fails after the swap, the script attempts to roll back to the previous live tree.

## Messaging Gateways

The dashboard provides a user-friendly gateway setup page at:

```text
/gateway
```

The current UI supports:

- Telegram
- Discord
- Slack
- WhatsApp
- Signal
- Email

The dashboard also shows pending pairing requests and approved users with buttons for:

- approve
- revoke
- clear pending

### Typical Inputs Per Platform

#### Telegram

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USERS`
- optional `TELEGRAM_HOME_CHANNEL`

#### Discord

- `DISCORD_BOT_TOKEN`
- `DISCORD_ALLOWED_USERS`
- optional `DISCORD_HOME_CHANNEL`
- optional `DISCORD_REQUIRE_MENTION`
- optional `DISCORD_FREE_RESPONSE_CHANNELS`

#### Slack

- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`
- `SLACK_ALLOWED_USERS`
- optional `SLACK_HOME_CHANNEL`

#### WhatsApp

- `WHATSAPP_ENABLED`
- `WHATSAPP_MODE`
- `WHATSAPP_ALLOWED_USERS`

After saving WhatsApp config, pairing still happens from the CLI:

```bash
fr33d0m whatsapp
```

#### Signal

- `SIGNAL_HTTP_URL`
- `SIGNAL_ACCOUNT`
- `SIGNAL_ALLOWED_USERS`
- optional group and home channel settings

#### Email

- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD`
- `EMAIL_IMAP_HOST`
- `EMAIL_SMTP_HOST`
- optional ports, allowed senders, and home address

### Pairing and Security

Fr33d0m follows Hermes’ deny-by-default model.

That means:

- no allowlist usually means no one is authorized by default
- DM pairing can be used instead of preloading every user ID
- global allow-all exists, but should be used carefully

Useful commands:

```bash
fr33d0m pairing list
fr33d0m pairing approve telegram CODE
fr33d0m pairing revoke telegram USER_ID
fr33d0m gateway restart
```

## Browser Terminal

The browser terminal is available at:

```text
/terminal
```

Use it for:

- full shell access
- interactive chat with Fr33d0m
- running setup commands
- gateway restarts
- pairing flows
- diagnostics

On startup, the browser terminal shows a Fr33d0m welcome banner with common commands.

## Neurovision

The browser-served Neurovision view is available at:

```text
/neurovision
```

This uses `ttyd` to expose the curses interface in a browser.

Use it for:

- monitoring the visualizer without SSH
- browsing the visualizer in gallery mode
- showing the agent status visually

## Services and Autostart

Fr33d0m installs systemd user services and enables lingering so they can survive reboot and logout.

Services:

- `fr33d0m-webui`
- `fr33d0m-gateway`
- `fr33d0m-terminal`
- `fr33d0m-neurovision-web`

Check status:

```bash
systemctl --user status fr33d0m-webui
systemctl --user status fr33d0m-gateway
systemctl --user status fr33d0m-terminal
systemctl --user status fr33d0m-neurovision-web
```

Restart services:

```bash
systemctl --user restart fr33d0m-webui
systemctl --user restart fr33d0m-gateway
systemctl --user restart fr33d0m-terminal
systemctl --user restart fr33d0m-neurovision-web
```

Follow logs:

```bash
journalctl --user -u fr33d0m-webui -f
journalctl --user -u fr33d0m-gateway -f
journalctl --user -u fr33d0m-terminal -f
journalctl --user -u fr33d0m-neurovision-web -f
```

## Important Paths

Main runtime home:

```bash
~/.hermes/
```

Important files:

```bash
~/.hermes/.env
~/.hermes/config.yaml
~/.hermes/SOUL.md
~/.hermes/fr33d0m-dashboard.yaml
~/.hermes/auth.json
~/.hermes/skins/fr33d0m-skin.yaml
~/.hermes/extensions/
~/.hermes/logs/
```

Repo clone:

```bash
~/Fr33dom_bot
```

## Updating Fr33d0m

To update the deployment:

```bash
cd ~/Fr33dom_bot
git pull --ff-only
bash install.sh
```

This refreshes:

- wrapper commands
- dashboard patch application
- frontend build
- service definitions
- browser terminal shell wrapper

On an already provisioned dashboard, `bash install.sh` now routes the WebUI patch and rebuild work through the same staged clone/build/swap path used by `fr33d0m-refresh-dashboard` whenever that safer path is available. Fresh installs still use the direct bootstrap path.

To reapply the already-packaged dashboard patch and rebuild the installed WebUI without doing a repo update, run:

```bash
fr33d0m-refresh-dashboard
```

This is a local maintenance command for the installed runtime. It does not commit changes, push branches, or update the packaging repo.

**Warning:** It stages and rebuilds a fresh `hermes-webui` clone before the final swap, but a successful refresh still replaces the installed `~/.hermes/extensions/hermes-webui` tree. If startup fails after the swap, the script attempts to restore the previous live tree.

## Update Everything

**Update Everything** is the automated maintenance job implemented by `fr33d0m-update-everything`. You can run it from a shell on the VM or start it from the Fr33d0m hub in the dashboard (same script, detached, with live phase status when a status file is in use).

### What it updates

1. **Fr33dom_bot git checkout** — Fast-forwards `main` from `origin` (`git fetch` / `git pull --ff-only`). The packaging directory must have a **clean** working tree or the job stops in preflight.
2. **Packaged files on disk** — Runs `install.sh` with `FR33DOM_INSTALL_MODE=packaged-only`, which copies wrappers, `patches/hermes-webui.patch`, skin, seeded `fr33d0m-dashboard.yaml`, plugins, skills, and prisms into `~/.hermes`. This path **does not** run the full installer or Ubuntu apt dependency phase.
3. **Hermes Agent core** — Runs `fr33d0m update`.
4. **Other Hermes extensions** — For each `~/.hermes/extensions/*` directory that is a git repository **except** `hermes-webui`, runs `git pull --ff-only`.
5. **Python dependencies** — Refreshes editable installs or `requirements.txt` installs into the Hermes venv for those extensions (again skipping the WebUI tree here).
6. **Dashboard** — Invokes `fr33d0m-refresh-dashboard` so the WebUI is rebuilt from a **staged** clone with the packaged patch applied, then swapped into place and the `fr33d0m-webui` service restarted.
7. **Companion services** — Restarts `fr33d0m-gateway`, `fr33d0m-terminal`, and `fr33d0m-neurovision-web` so they pick up refreshed assets.

### What it does not do

- **Operating system** — No `apt upgrade`, no distribution upgrade, and no automatic **reboot**. It is an application-level maintainer, not an OS updater.
- **Direct upstream sync of `hermes-webui`** — The installed dashboard track is defined by the **packaged patch** plus the staged refresh; the job does not `git pull` the upstream `hermes-webui` remote for you.
- **Git commits or pushes from the dashboard** — The dashboard still does not expose commit/push for runtime edits. Update Everything may **pull** your existing `~/Fr33dom_bot` clone forward, but it does not push changes to GitHub or create commits for operator file edits.

### Safety guarantees and failure reporting

- **Preflight** — Verifies tools, paths, minimum free disk space under `HOME`, and avoids overlapping runs when refresh/update status files show another job in progress.
- **Staged WebUI build** — Matches `fr33d0m-refresh-dashboard`: build in a temporary clone, then swap; failed post-swap startup attempts **rollback** to the previous live `hermes-webui` tree.
- **Phased status** — When driven from the dashboard, the script records phases, log tail, and completion state under `~/.hermes/logs/` (for example `update-everything.status.json` and the companion log). The UI polls this so you can see which step failed.
- **Outcomes** — Blocking failures stop later phases and mark the job as **failure**. If the pipeline completes but post-checks report inactive units or a failed authenticated health probe, the job may still end as **partial_failure** while exiting `0`, signaling “finished with warnings—inspect logs and service status.”

## Snapshot Workflow

Once the VM is configured the way you want:

1. Configure your API key
2. Configure gateways you want enabled
3. Test the dashboard
4. Test `/terminal` and `/neurovision`
5. Verify the services are active
6. Create a cloud snapshot

That snapshot becomes your reusable Fr33d0m image.

## Troubleshooting

### Dashboard loads but chat does not work

Cause: no API key configured

Fix:

```bash
fr33d0m setup
```

Or use the dashboard AI setup panel on `/`.

### Dashboard login fails

Cause: wrong dashboard token

Fix: read the token from `~/.hermes/auth.json`

### Gateway is inactive

Check:

```bash
fr33d0m doctor
fr33d0m gateway restart
journalctl --user -u fr33d0m-gateway -f
```

You can also use the dashboard buttons on `/`:

- Start
- Stop
- Restart
- Doctor
- Doctor Fix

### WhatsApp is configured but not paired

Run:

```bash
fr33d0m whatsapp
```

### Browser terminal or Neurovision does not load

Check:

```bash
systemctl --user status fr33d0m-terminal
systemctl --user status fr33d0m-neurovision-web
```

Then use the dashboard Reconnect button.

### WebUI is not responding

Check:

```bash
systemctl --user status fr33d0m-webui
journalctl --user -u fr33d0m-webui -f
```

### Installer waits on apt locks

On fresh Ubuntu machines, `unattended-upgrades` may hold the package lock for a while. The installer now waits for that lock to clear automatically.

## Recommended Operator Flow

For a new VM:

1. Provision Ubuntu
2. Clone `Fr33dom_bot`
3. Run `bash install.sh`
4. Run `fr33d0m setup`
5. Log into the dashboard
6. Enter `OPENROUTER_API_KEY`
7. Apply `minimax/minimax-m2.7`
8. Start the gateway from the dashboard
9. Configure gateways in `/gateway`
10. Verify `/terminal` and `/neurovision`
11. Verify services
12. Snapshot the machine
