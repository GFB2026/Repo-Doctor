#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Repo Doctor — One-Shot Installer
#  Sets up the registry database and tools at ~/.repo-doctor/
# ═══════════════════════════════════════════════════════════

set -e

INSTALL_DIR="$HOME/.repo-doctor"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║       🩺 Repo Doctor — Setup                 ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Create directory
mkdir -p "$INSTALL_DIR"

# Copy registry tool
cp "$SCRIPT_DIR/repo-registry.py" "$INSTALL_DIR/repo-registry.py"
chmod +x "$INSTALL_DIR/repo-registry.py"

# Initialize database
python "$INSTALL_DIR/repo-registry.py" init

# Create shell alias helper
ALIAS_LINE='alias repo-doctor="python ~/.repo-doctor/repo-registry.py"'

echo ""
echo "✅ Repo Doctor installed to $INSTALL_DIR"
echo ""
echo "📁 Files:"
echo "   $INSTALL_DIR/repo-registry.py   — CLI registry tool"
echo "   $INSTALL_DIR/registry.db        — SQLite database"
echo ""
echo "🔧 Optional: Add a shell alias for convenience:"
echo ""
echo "   $ALIAS_LINE"
echo ""
echo "   Add it to your ~/.bashrc or ~/.zshrc, then you can run:"
echo "     repo-doctor status"
echo "     repo-doctor dashboard"
echo "     repo-doctor search react"
echo "     repo-doctor history my-project"
echo ""
echo "📋 To audit a repo with Claude Code:"
echo "   1. Copy REPO-DOCTOR.md to any repo root"
echo "   2. cd into the repo"
echo "   3. Run: claude -p REPO-DOCTOR.md"
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║       ✅ Setup Complete                      ║"
echo "╚══════════════════════════════════════════════╝"
