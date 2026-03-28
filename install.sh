#!/usr/bin/env bash
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_BIN="$HOME/.local/bin"
CURRENT_USER="$(whoami)"

info()  { printf "${CYAN}→${RESET} %s\n" "$1"; }
ok()    { printf "${GREEN}✓${RESET} %s\n" "$1"; }
warn()  { printf "${YELLOW}⚠${RESET} %s\n" "$1"; }
fail()  { printf "${RED}✗${RESET} %s\n" "$1"; }

echo -e "${BOLD}${GREEN}"
cat << 'BANNER'

  ███████╗██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ███╗   ███╗
  ██╔════╝██╔══██╗╚════██╗╚════██╗██╔══██╗██╔═══██╗████╗ ████║
  █████╗  ██████╔╝ █████╔╝ █████╔╝██║  ██║██║   ██║██╔████╔██║
  ██╔══╝  ██╔══██╗ ╚═══██╗ ╚═══██╗██║  ██║██║   ██║██║╚██╔╝██║
  ██║     ██║  ██║██████╔╝██████╔╝██████╔╝╚██████╔╝██║ ╚═╝ ██║
  ╚═╝     ╚═╝  ╚═╝╚═════╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝

BANNER
echo -e "${RESET}"
echo -e "${BOLD}  Custom Hermes Agent · Ubuntu Edition${RESET}"
echo ""

# ═════════════════════════════════════════════════════════════════════════════
# Phase 1: System prerequisites (Ubuntu)
# ═════════════════════════════════════════════════════════════════════════════

info "Checking system prerequisites..."

install_system_deps() {
    local missing=()
    command -v git    &>/dev/null || missing+=(git)
    command -v curl   &>/dev/null || missing+=(curl)
    command -v rg     &>/dev/null || missing+=(ripgrep)
    command -v ffmpeg &>/dev/null || missing+=(ffmpeg)
    command -v ttyd   &>/dev/null || missing+=(ttyd)
    command -v npm    &>/dev/null || missing+=(nodejs npm)

    if [ ${#missing[@]} -gt 0 ]; then
        local wait_round=0
        info "Installing system packages: ${missing[*]}"
        while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1; do
            wait_round=$((wait_round + 1))
            if [ $wait_round -eq 1 ] || [ $((wait_round % 6)) -eq 0 ]; then
                warn "apt is busy (usually unattended-upgrades on first boot). Waiting for the lock to clear..."
            fi
            sleep 10
        done
        sudo apt-get update -qq
        sudo apt-get install -y -qq "${missing[@]}"
    fi
    ok "System dependencies ready"
}

install_uv() {
    if ! command -v uv &>/dev/null; then
        info "Installing uv package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
    ok "uv ready ($(uv --version 2>/dev/null || echo 'installed'))"
}

install_system_deps
install_uv

# ═════════════════════════════════════════════════════════════════════════════
# Phase 2: Install Hermes Agent core
# ═════════════════════════════════════════════════════════════════════════════

if [ -d "$HERMES_HOME/hermes-agent" ]; then
    ok "Hermes Agent already installed"
else
    info "Installing Hermes Agent (this may take a few minutes)..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
    ok "Hermes Agent installed"
fi

# Reload PATH in case hermes installer added ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"

# ═════════════════════════════════════════════════════════════════════════════
# Phase 3: Directory structure
# ═════════════════════════════════════════════════════════════════════════════

mkdir -p "$HERMES_HOME"/{skins,plugins,prisms,skills,extensions}
mkdir -p "$LOCAL_BIN"
ok "Directory structure ready"

# ═════════════════════════════════════════════════════════════════════════════
# Phase 4: Fr33d0m customizations (skin, config, persona, plugins, skills)
# ═════════════════════════════════════════════════════════════════════════════

cp "$SCRIPT_DIR/skins/fr33d0m-skin.yaml" "$HERMES_HOME/skins/"
ok "Installed fr33d0m-skin"

cp "$SCRIPT_DIR/config/config.yaml" "$HERMES_HOME/config.yaml"
cp "$SCRIPT_DIR/config/SOUL.md" "$HERMES_HOME/SOUL.md"
ok "Config and persona installed"

cp -r "$SCRIPT_DIR/plugins/"* "$HERMES_HOME/plugins/" 2>/dev/null || true
ok "Installed plugins ($(ls -d "$HERMES_HOME/plugins/evey-"* 2>/dev/null | wc -l) evey + skill_factory)"

cp -r "$SCRIPT_DIR/skills/"* "$HERMES_HOME/skills/"
ok "Installed custom skills"

cp -r "$SCRIPT_DIR/prisms/"* "$HERMES_HOME/prisms/"
ok "Installed $(ls "$HERMES_HOME/prisms/"*.md 2>/dev/null | wc -l) analytical prisms"

# ═════════════════════════════════════════════════════════════════════════════
# Phase 5: Clone extension repos
# ═════════════════════════════════════════════════════════════════════════════

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
        git clone --depth 1 "$repo_url" "$HERMES_HOME/extensions/$repo_name" 2>/dev/null
        ok "Cloned $repo_name"
    fi
done

apply_webui_patch() {
    local patch_file="$SCRIPT_DIR/patches/hermes-webui.patch"
    local target_dir="$HERMES_HOME/extensions/hermes-webui"

    if [ ! -f "$patch_file" ] || [ ! -d "$target_dir/.git" ]; then
        return
    fi

    info "Applying Fr33d0m dashboard patch to hermes-webui..."
    if git -C "$target_dir" apply --check "$patch_file" 2>/dev/null; then
        git -C "$target_dir" apply --whitespace=nowarn "$patch_file"
        ok "Applied Fr33d0m dashboard patch"
    elif git -C "$target_dir" apply --reverse --check "$patch_file" 2>/dev/null; then
        ok "Fr33d0m dashboard patch already applied"
    else
        warn "Dashboard patch state diverged; resetting managed hermes-webui clone to upstream HEAD"
        git -C "$target_dir" reset --hard HEAD >/dev/null 2>&1 || true
        git -C "$target_dir" clean -fd >/dev/null 2>&1 || true
        if git -C "$target_dir" apply --check "$patch_file" 2>/dev/null; then
            git -C "$target_dir" apply --whitespace=nowarn "$patch_file"
            ok "Re-applied Fr33d0m dashboard patch after reset"
        else
            warn "Could not apply Fr33d0m dashboard patch automatically"
        fi
    fi
}

apply_webui_patch

# ═════════════════════════════════════════════════════════════════════════════
# Phase 6: Install Python packages into Hermes venv
# ═════════════════════════════════════════════════════════════════════════════

HERMES_PYTHON="$HERMES_HOME/hermes-agent/venv/bin/python"

if [ -f "$HERMES_PYTHON" ]; then
    info "Installing self-evolution into Hermes venv..."
    uv pip install -e "$HERMES_HOME/extensions/hermes-agent-self-evolution[dev]" \
        --python "$HERMES_PYTHON" 2>/dev/null \
        && ok "self-evolution installed" \
        || warn "self-evolution install failed (non-critical)"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Phase 7: Install WebUI (own venv + frontend build)
# ═════════════════════════════════════════════════════════════════════════════

WEBUI_DIR="$HERMES_HOME/extensions/hermes-webui"
if [ -d "$WEBUI_DIR" ]; then
    if [ ! -d "$WEBUI_DIR/venv" ]; then
        info "Setting up WebUI Python environment..."
        uv venv "$WEBUI_DIR/venv" --python 3.11 2>/dev/null
        ok "WebUI backend environment created"
    else
        ok "WebUI backend environment already set up"
    fi
    uv pip install -e "$WEBUI_DIR" --python "$WEBUI_DIR/venv/bin/python" 2>/dev/null
    ok "WebUI backend installed"
    if [ -d "$WEBUI_DIR/frontend" ] && command -v npm &>/dev/null; then
        info "Building WebUI frontend..."
        (cd "$WEBUI_DIR/frontend" && npm install --silent 2>/dev/null && npx vite build 2>/dev/null)
        ok "WebUI frontend built"
    fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# Phase 8: Install fr33d0m commands
# ═════════════════════════════════════════════════════════════════════════════

info "Installing fr33d0m commands..."

cp "$SCRIPT_DIR/bin/fr33d0m"              "$LOCAL_BIN/fr33d0m"
cp "$SCRIPT_DIR/bin/fr33d0m-webui"        "$LOCAL_BIN/fr33d0m-webui"
cp "$SCRIPT_DIR/bin/fr33d0m-neurovision"  "$LOCAL_BIN/fr33d0m-neurovision"
cp "$SCRIPT_DIR/bin/fr33d0m-terminal-shell" "$LOCAL_BIN/fr33d0m-terminal-shell"
chmod +x "$LOCAL_BIN/fr33d0m" "$LOCAL_BIN/fr33d0m-webui" "$LOCAL_BIN/fr33d0m-neurovision" "$LOCAL_BIN/fr33d0m-terminal-shell"

# Also keep hermes-* aliases for compatibility
ln -sf "$LOCAL_BIN/fr33d0m-webui"        "$LOCAL_BIN/hermes-webui"
ln -sf "$LOCAL_BIN/fr33d0m-neurovision"  "$LOCAL_BIN/hermes-neurovision"

ok "Installed: fr33d0m, fr33d0m-webui, fr33d0m-neurovision"

# Ensure ~/.local/bin is on PATH
if ! echo "$PATH" | grep -q "$LOCAL_BIN"; then
    SHELL_RC=""
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.profile" ]; then
        SHELL_RC="$HOME/.profile"
    fi
    if [ -n "$SHELL_RC" ]; then
        if ! grep -q 'local/bin' "$SHELL_RC" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
            ok "Added ~/.local/bin to PATH in $SHELL_RC"
        fi
    fi
    export PATH="$LOCAL_BIN:$PATH"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Phase 9: systemd services (autostart on boot)
# ═════════════════════════════════════════════════════════════════════════════

install_systemd_services() {
    info "Setting up systemd services for autostart..."

    local SYSTEMD_DIR="$HOME/.config/systemd/user"
    local TTYD_BIN
    mkdir -p "$SYSTEMD_DIR"
    TTYD_BIN="$(command -v ttyd || true)"

    if command -v systemctl &>/dev/null && systemctl list-unit-files ttyd.service >/dev/null 2>&1; then
        sudo systemctl disable --now ttyd.service >/dev/null 2>&1 || true
    fi

    # ── fr33d0m-webui ────────────────────────────────────────────────────
    cat > "$SYSTEMD_DIR/fr33d0m-webui.service" << UNIT
[Unit]
Description=Fr33d0m WebUI Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=HERMES_HOME=$HERMES_HOME
WorkingDirectory=$HERMES_HOME/extensions/hermes-webui
ExecStart=$HERMES_HOME/extensions/hermes-webui/venv/bin/python -m webui --port 8643
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
UNIT

    # ── fr33d0m-gateway ──────────────────────────────────────────────────
    cat > "$SYSTEMD_DIR/fr33d0m-gateway.service" << UNIT
[Unit]
Description=Fr33d0m Messaging Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=HERMES_HOME=$HERMES_HOME
Environment=PATH=$LOCAL_BIN:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=$HERMES_HOME/hermes-agent
ExecStart=$LOCAL_BIN/hermes gateway run --replace
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
UNIT

    # ── fr33d0m-terminal ─────────────────────────────────────────────────
    if [ -n "$TTYD_BIN" ]; then
        cat > "$SYSTEMD_DIR/fr33d0m-terminal.service" << UNIT
[Unit]
Description=Fr33d0m Browser Terminal
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=HERMES_HOME=$HERMES_HOME
Environment=PATH=$LOCAL_BIN:/usr/local/bin:/usr/bin:/bin
ExecStart=$TTYD_BIN -p 7681 -i lo -b /terminal -t fontSize=14 -t cursorStyle=bar $LOCAL_BIN/fr33d0m-terminal-shell
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
UNIT

        cat > "$SYSTEMD_DIR/fr33d0m-neurovision-web.service" << UNIT
[Unit]
Description=Fr33d0m Browser Neurovision
After=network.target

[Service]
Type=simple
Environment=HERMES_HOME=$HERMES_HOME
Environment=PATH=$LOCAL_BIN:/usr/local/bin:/usr/bin:/bin
ExecStart=$TTYD_BIN -p 7682 -i lo -b /neurovision -t fontSize=14 -t cursorStyle=bar bash -lc 'source "$HOME/.bashrc" >/dev/null 2>&1; fr33d0m-neurovision --gallery'
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
UNIT
    fi

    # Reload and enable
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    if [ -S "$XDG_RUNTIME_DIR/bus" ]; then
        export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
    fi
    systemctl --user daemon-reload

    systemctl --user enable fr33d0m-webui.service    2>/dev/null && ok "fr33d0m-webui    → enabled (autostart)" || warn "fr33d0m-webui enable failed"
    systemctl --user enable fr33d0m-gateway.service  2>/dev/null && ok "fr33d0m-gateway  → enabled (autostart)" || warn "fr33d0m-gateway enable failed"
    if [ -n "$TTYD_BIN" ]; then
        systemctl --user enable fr33d0m-terminal.service 2>/dev/null && ok "fr33d0m-terminal → enabled (autostart)" || warn "fr33d0m-terminal enable failed"
        systemctl --user enable fr33d0m-neurovision-web.service 2>/dev/null && ok "fr33d0m-neurovision-web → enabled (autostart)" || warn "fr33d0m-neurovision-web enable failed"
    else
        warn "ttyd not found — terminal and neurovision web services were skipped"
    fi
    systemctl --user disable --now fr33d0m-neurovision.service 2>/dev/null || true

    # Enable lingering so user services run without a login session
    if command -v loginctl &>/dev/null; then
        sudo loginctl enable-linger "$CURRENT_USER" 2>/dev/null \
            && ok "Lingering enabled — services run at boot without login" \
            || warn "Could not enable lingering (services will only run when logged in)"
    fi

    # Restart web-facing services so code updates take effect immediately
    systemctl --user restart fr33d0m-webui.service 2>/dev/null \
        && ok "fr33d0m-webui restarted on port 8643" \
        || systemctl --user start fr33d0m-webui.service 2>/dev/null \
        && ok "fr33d0m-webui started on port 8643" \
        || warn "fr33d0m-webui could not start now (will start on next boot)"
    if [ -n "$TTYD_BIN" ]; then
        systemctl --user restart fr33d0m-terminal.service 2>/dev/null \
            && ok "fr33d0m-terminal restarted on localhost:7681" \
            || systemctl --user start fr33d0m-terminal.service 2>/dev/null \
            && ok "fr33d0m-terminal started on localhost:7681" \
            || warn "fr33d0m-terminal could not start now"
        systemctl --user restart fr33d0m-neurovision-web.service 2>/dev/null \
            && ok "fr33d0m-neurovision-web restarted on localhost:7682" \
            || systemctl --user start fr33d0m-neurovision-web.service 2>/dev/null \
            && ok "fr33d0m-neurovision-web started on localhost:7682" \
            || warn "fr33d0m-neurovision-web could not start now"
    fi
}

if command -v systemctl &>/dev/null; then
    install_systemd_services
else
    warn "systemd not found — skipping autostart setup"
    warn "You can start services manually:"
    echo "    fr33d0m-webui --port 8643 &"
    echo "    fr33d0m gateway start &"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Phase 10: .env setup
# ═════════════════════════════════════════════════════════════════════════════

if [ ! -f "$HERMES_HOME/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$HERMES_HOME/.env"
    ok "Created ~/.hermes/.env from template"
elif ! grep -q "OPENROUTER_API_KEY=." "$HERMES_HOME/.env" 2>/dev/null; then
    warn "No API key configured yet"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Done
# ═════════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${BOLD}${GREEN}┌─────────────────────────────────────────────────────────────┐${RESET}"
echo -e "${BOLD}${GREEN}│                                                             │${RESET}"
echo -e "${BOLD}${GREEN}│   Fr33d0m Bot is ready!                                     │${RESET}"
echo -e "${BOLD}${GREEN}│                                                             │${RESET}"
echo -e "${BOLD}${GREEN}├─────────────────────────────────────────────────────────────┤${RESET}"
echo -e "${BOLD}│${RESET}                                                             ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}fr33d0m${RESET}                    Start chatting               ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}fr33d0m setup${RESET}              Configure API keys           ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}fr33d0m model${RESET}              Choose LLM model             ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}fr33d0m doctor${RESET}             Diagnose issues              ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}fr33d0m gateway start${RESET}      Start messaging gateway      ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}fr33d0m-neurovision${RESET}        Terminal visualizer           ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}fr33d0m-webui${RESET}              Web dashboard (:8643)        ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}fr33d0m-terminal-shell${RESET}      Full login shell banner       ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${CYAN}Dashboard routes${RESET}           /terminal  /neurovision     ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}                                                             ${BOLD}│${RESET}"
echo -e "${BOLD}├─────────────────────────────────────────────────────────────┤${RESET}"
echo -e "${BOLD}│${RESET}  Services (autostart on boot):                              ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}    systemctl --user status fr33d0m-webui                    ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}    systemctl --user status fr33d0m-gateway                  ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}    systemctl --user status fr33d0m-terminal                 ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}    systemctl --user status fr33d0m-neurovision-web          ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}                                                             ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}  ${YELLOW}Next: run 'source ~/.bashrc' then 'fr33d0m setup'${RESET}          ${BOLD}│${RESET}"
echo -e "${BOLD}│${RESET}                                                             ${BOLD}│${RESET}"
echo -e "${BOLD}${GREEN}└─────────────────────────────────────────────────────────────┘${RESET}"
