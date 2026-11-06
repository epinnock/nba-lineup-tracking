#!/bin/bash

# NBA Lineup Tracker - Automated Setup Script (macOS/Linux)
# This script sets up a Python virtual environment and installs all dependencies

set -e  # Exit on any error

echo "🏀 NBA Lineup Tracker - Environment Setup"
echo "=========================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    echo "✅ Found Python $PYTHON_VERSION"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    echo "✅ Found Python $PYTHON_VERSION"
else
    echo "❌ Python not found. Please install Python 3.9 or higher."
    exit 1
fi

# Check if Python version is 3.9+
MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]; }; then
    echo "❌ Python 3.9 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Remove 'venv' directory to recreate."
    read -p "Do you want to remove and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        $PYTHON_CMD -m venv venv
        echo "✅ Virtual environment recreated"
    else
        echo "Using existing virtual environment"
    fi
else
    $PYTHON_CMD -m venv venv
    echo "✅ Virtual environment created"
fi

echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"

echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded to $(pip --version | awk '{print $2}')"

echo ""

# Install dependencies
echo "📥 Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt

echo ""

# Verify installation
echo "🔍 Verifying installation..."
if $PYTHON_CMD -c "import nba_api" 2>/dev/null; then
    echo "✅ nba_api installed successfully"
else
    echo "❌ nba_api installation failed"
    exit 1
fi

if $PYTHON_CMD -c "import pandas" 2>/dev/null; then
    echo "✅ pandas installed successfully"
else
    echo "❌ pandas installation failed"
    exit 1
fi

if $PYTHON_CMD -c "import pytest" 2>/dev/null; then
    echo "✅ pytest installed successfully"
else
    echo "❌ pytest installation failed"
    exit 1
fi

echo ""

# Show installed packages
echo "📚 Installed packages:"
pip list | grep -E "(nba-api|pandas|numpy|pytest|black|flake8|mypy)"

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the application:"
echo "  python main.py 0022500032"
echo ""
echo "To run tests:"
echo "  pytest tests/ -v"
echo ""
echo "To deactivate when done:"
echo "  deactivate"
echo "=========================================="