#!/usr/bin/env bash
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RESET='\033[0m'

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

info()  { printf "${CYAN}→${RESET} %s\n" "$1"; }
ok()    { printf "${GREEN}✓${RESET} %s\n" "$1"; }
warn()  { printf "${YELLOW}⚠${RESET} %s\n" "$1"; }

echo -e "${BOLD}"
echo '┌─────────────────────────────────────────────────────────┐'
echo '│            Fr33d0m Bot — Installer                      │'
echo '│  Custom Hermes Agent with extensions & fr33d0m-skin     │'
echo '└─────────────────────────────────────────────────────────┘'
echo -e "${RESET}"

# ─── Step 1: Install Hermes Agent (if not present) ───────────────────────────

if [ -d "$HERMES_HOME/hermes-agent" ]; then
    ok "Hermes Agent already installed at $HERMES_HOME/hermes-agent"
else
    info "Installing Hermes Agent..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
    ok "Hermes Agent installed"
fi

# ─── Step 2: Ensure directories ──────────────────────────────────────────────

mkdir -p "$HERMES_HOME/skins"
mkdir -p "$HERMES_HOME/plugins"
mkdir -p "$HERMES_HOME/prisms"
mkdir -p "$HERMES_HOME/skills"
mkdir -p "$HERMES_HOME/extensions"
ok "Directory structure ready"

# ─── Step 3: Copy custom skin ────────────────────────────────────────────────

cp "$SCRIPT_DIR/skins/fr33d0m-skin.yaml" "$HERMES_HOME/skins/"
ok "Installed fr33d0m-skin"

# ─── Step 4: Copy config + persona ───────────────────────────────────────────

cp "$SCRIPT_DIR/config/config.yaml" "$HERMES_HOME/config.yaml"
cp "$SCRIPT_DIR/config/SOUL.md" "$HERMES_HOME/SOUL.md"
ok "Config and persona installed"

# ─── Step 5: Copy plugins ────────────────────────────────────────────────────

cp -r "$SCRIPT_DIR/plugins/"* "$HERMES_HOME/plugins/" 2>/dev/null || true
ok "Installed $(ls -d "$HERMES_HOME/plugins/evey-"* 2>/dev/null | wc -l | tr -d ' ') evey plugins + skill_factory"

# ─── Step 6: Copy custom skills ──────────────────────────────────────────────

cp -r "$SCRIPT_DIR/skills/"* "$HERMES_HOME/skills/"
ok "Installed custom skills (execplan, life-os, prism-*, skill-factory)"

# ─── Step 7: Copy prisms ─────────────────────────────────────────────────────

cp -r "$SCRIPT_DIR/prisms/"* "$HERMES_HOME/prisms/"
ok "Installed $(ls "$HERMES_HOME/prisms/"*.md 2>/dev/null | wc -l | tr -d ' ') analytical prisms"

# ─── Step 8: Clone extension repos ───────────────────────────────────────────

EXTENSIONS=(
    "https://github.com/NousResearch/hermes-agent-self-evolution.git"
    "https://github.com/42-evey/hermes-plugins.git"
    "https://github.com/Romanescu11/hermes-skill-factory.git"
    "https://github.com/Cranot/super-hermes.git"
    "https://github.com/Lethe044/hermes-life-os.git"
    "https://github.com/tiann/execplan-skill.git"
    "https://github.com/Tranquil-Flow/hermes-neurovision.git"
    "https://github.com/sanchomuzax/hermes-webui.git"
)

for repo_url in "${EXTENSIONS[@]}"; do
    repo_name=$(basename "$repo_url" .git)
    if [ -d "$HERMES_HOME/extensions/$repo_name" ]; then
        ok "Extension $repo_name already cloned"
    else
        info "Cloning $repo_name..."
        git clone "$repo_url" "$HERMES_HOME/extensions/$repo_name" 2>/dev/null
        ok "Cloned $repo_name"
    fi
done

# ─── Step 9: Install self-evolution (Python package) ─────────────────────────

HERMES_PYTHON="$HERMES_HOME/hermes-agent/venv/bin/python"
if [ -f "$HERMES_PYTHON" ] && command -v uv &>/dev/null; then
    info "Installing hermes-agent-self-evolution into Hermes venv..."
    uv pip install -e "$HERMES_HOME/extensions/hermes-agent-self-evolution[dev]" \
        --python "$HERMES_PYTHON" 2>/dev/null && ok "self-evolution installed" || warn "self-evolution install failed (non-critical)"
fi

# ─── Step 10: Install neurovision wrapper ─────────────────────────────────────

mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/hermes-neurovision" << 'WRAPPER'
#!/bin/bash
PYTHONPATH="$HOME/.hermes/extensions/hermes-neurovision" exec "$HOME/.hermes/hermes-agent/venv/bin/python" -m hermes_neurovision.cli "$@"
WRAPPER
chmod +x "$HOME/.local/bin/hermes-neurovision"
ok "hermes-neurovision command installed"

# ─── Step 11: Install webui ──────────────────────────────────────────────────

WEBUI_DIR="$HERMES_HOME/extensions/hermes-webui"
if [ -d "$WEBUI_DIR" ] && command -v uv &>/dev/null; then
    if [ ! -d "$WEBUI_DIR/venv" ]; then
        info "Setting up hermes-webui..."
        uv venv "$WEBUI_DIR/venv" --python 3.11 2>/dev/null
        uv pip install -e "$WEBUI_DIR" --python "$WEBUI_DIR/venv/bin/python" 2>/dev/null
    fi
    if [ -d "$WEBUI_DIR/frontend" ] && command -v npm &>/dev/null; then
        (cd "$WEBUI_DIR/frontend" && npm install --silent 2>/dev/null && npx vite build 2>/dev/null)
    fi
    cat > "$HOME/.local/bin/hermes-webui" << 'WRAPPER'
#!/bin/bash
cd "$HOME/.hermes/extensions/hermes-webui"
exec ./venv/bin/python -m webui "$@"
WRAPPER
    chmod +x "$HOME/.local/bin/hermes-webui"
    ok "hermes-webui command installed"
fi

# ─── Step 12: .env reminder ──────────────────────────────────────────────────

if [ ! -f "$HERMES_HOME/.env" ] || ! grep -q "OPENROUTER_API_KEY=." "$HERMES_HOME/.env" 2>/dev/null; then
    echo ""
    warn "No API key configured yet."
    echo "  Add your key to $HERMES_HOME/.env"
    echo "  Or run: hermes setup"
fi

# ─── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}┌─────────────────────────────────────────────────────────┐${RESET}"
echo -e "${BOLD}│  ${GREEN}Fr33d0m Bot is ready!${RESET}${BOLD}                                   │${RESET}"
echo -e "${BOLD}├─────────────────────────────────────────────────────────┤${RESET}"
echo -e "${BOLD}│${RESET}  hermes                  Start chatting                ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  hermes setup             Configure API keys           ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  hermes-neurovision       Terminal visualizer           ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  hermes-webui --localhost  Web dashboard                ${BOLD}│${RESET}"
echo -e "${BOLD}└─────────────────────────────────────────────────────────┘${RESET}"
