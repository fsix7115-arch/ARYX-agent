#!/usr/bin/env bash
# ==============================================================================
# ARYx AGENT — One-Command Installer
# Guaranteed zero-friction, idempotent installation for Linux, macOS, and WSL.
# ==============================================================================
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check for NO_COLOR environment variable
if [ -n "${NO_COLOR:-}" ] || [ ! -t 1 ]; then
    BOLD=''
    GREEN=''
    YELLOW=''
    RED=''
    CYAN=''
    NC=''
fi

echo -e "${CYAN}"
cat << 'EOF'
    █████╗ ██████╗ ██╗   ██╗██╗  ██╗
   ██╔══██╗██╔══██╗╚██╗ ██╔╝╚██╗██╔╝
   ███████║██████╔╝ ╚████╔╝  ╚███╔╝ 
   ██╔══██║██╔══██╗  ╚██╔╝   ██╔██╗ 
   ██║  ██║██║  ██║   ██║   ██╔╝ ██╗
   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝
       A G E N T  ·  v0.1.0
EOF
echo -e "${NC}"
echo "Installing ARYx AGENT with zero friction..."
echo ""

# ------------------------------------------------------------------------------
# 1. Detect OS
# ------------------------------------------------------------------------------
OS="unknown"
case "$(uname -s)" in
    Linux*)     OS="Linux";;
    Darwin*)    OS="macOS";;
    CYGWIN*|MINGW*|MSYS*) OS="Windows";;
    *)          OS="unknown";;
esac

# Check for WSL
if [ "$OS" = "Linux" ] && [ -f /proc/version ] && grep -qi microsoft /proc/version; then
    OS="WSL"
fi

# ------------------------------------------------------------------------------
# 2. Check Python >= 3.10
# ------------------------------------------------------------------------------
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}✗ Python 3.10+ is required but was not found on your system.${NC}"
    echo ""
    echo "To install Python on your system:"
    if [ "$OS" = "macOS" ]; then
        echo "  brew install python@3.11"
    elif [ "$OS" = "Linux" ] || [ "$OS" = "WSL" ]; then
        if command -v apt-get >/dev/null 2>&1; then
            echo "  sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
        elif command -v dnf >/dev/null 2>&1; then
            echo "  sudo dnf install -y python3 python3-pip"
        elif command -v pacman >/dev/null 2>&1; then
            echo "  sudo pacman -S python python-pip"
        else
            echo "  Install Python 3.10+ via your package manager or https://www.python.org"
        fi
    else
        echo "  Download Python 3.10+ from https://www.python.org/downloads/"
    fi
    exit 1
fi

# Check version
PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    echo -e "${RED}✗ Detected Python ${PY_VER}, but ARYx AGENT requires Python 3.10 or newer.${NC}"
    echo "Please upgrade Python to 3.10+ and re-run this script."
    exit 1
fi

echo -e "${GREEN}✓${NC} Python ${PY_VER} detected ($PYTHON_BIN)"

# ------------------------------------------------------------------------------
# 3. Check / Install pipx
# ------------------------------------------------------------------------------
if ! command -v pipx >/dev/null 2>&1; then
    echo "Checking for pipx (recommended for isolated CLI tools)..."
    if $PYTHON_BIN -m pip --version >/dev/null 2>&1; then
        echo "Installing pipx via $PYTHON_BIN -m pip --user pipx..."
        $PYTHON_BIN -m pip install --user --upgrade pipx || {
            echo -e "${YELLOW}! pipx install skipped, will install in user environment.${NC}"
        }
    fi
fi

# ------------------------------------------------------------------------------
# 4. Install or Upgrade ARYx AGENT
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v pipx >/dev/null 2>&1; then
    if pipx list | grep -q "aryx-agent"; then
        echo "Already installed. Updating ARYx AGENT..."
        pipx install --force "$SCRIPT_DIR"
    else
        echo "Installing ARYx AGENT with pipx..."
        pipx install "$SCRIPT_DIR"
    fi
    pipx ensurepath >/dev/null 2>&1 || true
else
    # Fallback to standard pip user install or venv install
    echo "Installing ARYx AGENT with $PYTHON_BIN -m pip install --user..."
    $PYTHON_BIN -m pip install --user -e "$SCRIPT_DIR" || {
        echo -e "${YELLOW}! Pip user install requires python venv/pip. Installing dependencies...${NC}"
        $PYTHON_BIN -m pip install -e "$SCRIPT_DIR" --break-system-packages 2>/dev/null || \
        $PYTHON_BIN -m pip install -e "$SCRIPT_DIR"
    }
fi

# ------------------------------------------------------------------------------
# 5. Ensure ~/.local/bin is on PATH
# ------------------------------------------------------------------------------
LOCAL_BIN="$HOME/.local/bin"
PATH_NEEDS_UPDATE=false

if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    PATH_NEEDS_UPDATE=true
fi

if [ "$PATH_NEEDS_UPDATE" = true ]; then
    echo ""
    echo -e "${YELLOW}! Note: ${LOCAL_BIN} is not yet in your current PATH.${NC}"
    EXPORT_CMD="export PATH=\"\$HOME/.local/bin:\$PATH\""
    
    # Identify shell rc file
    SHELL_RC=""
    if [ -n "${ZSH_VERSION:-}" ] || [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "${BASH_VERSION:-}" ] || [[ "$SHELL" == *"bash"* ]]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.profile" ]; then
        SHELL_RC="$HOME/.profile"
    fi

    if [ -n "$SHELL_RC" ]; then
        echo "Adding PATH export to ${SHELL_RC}..."
        echo "" >> "$SHELL_RC"
        echo "# ARYx AGENT PATH" >> "$SHELL_RC"
        echo "$EXPORT_CMD" >> "$SHELL_RC"
        echo -e "${GREEN}✓${NC} Appended to ${SHELL_RC}"
    fi

    echo "For this current session, please run:"
    echo "  ${CYAN}${EXPORT_CMD}${NC}"
fi

# ------------------------------------------------------------------------------
# 6. Verify & Success Banner
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}✓ ARYx AGENT installed successfully!${NC}"
echo ""
echo "Next step: just type"
echo -e "    ${CYAN}${BOLD}aryx${NC}"
echo ""
echo "That's it. The agent will guide you."
echo ""
exit 0
