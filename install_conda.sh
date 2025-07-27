#!/bin/bash

# Miniconda Installation Script for macOS (Apple Silicon)
echo "=============================================="
echo "Miniconda Installer for macOS (Apple Silicon)"
echo "=============================================="
echo ""

# Check if conda is already installed
if command -v conda &> /dev/null; then
    echo "⚠️  Conda is already installed!"
    conda --version
    echo ""
    echo "To use existing conda, run:"
    echo "  conda env create -f environment.yml"
    echo "  conda activate book-keeper"
    exit 0
fi

# Set installation directory
CONDA_DIR="$HOME/miniconda3"

echo "📦 Downloading Miniconda for Apple Silicon..."
echo ""

# Download Miniconda installer
curl -o Miniconda3-latest-MacOSX-arm64.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh

echo ""
echo "🔧 Installing Miniconda to $CONDA_DIR..."
echo ""

# Install Miniconda
bash Miniconda3-latest-MacOSX-arm64.sh -b -p "$CONDA_DIR"

# Remove installer
rm Miniconda3-latest-MacOSX-arm64.sh

echo ""
echo "⚙️  Configuring shell..."

# Initialize conda for different shells
"$CONDA_DIR/bin/conda" init bash
"$CONDA_DIR/bin/conda" init zsh

echo ""
echo "✅ Miniconda installation complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Restart your terminal or run:"
echo "   source ~/.zshrc"
echo ""
echo "2. Create the book-keeper environment:"
echo "   conda env create -f environment.yml"
echo ""
echo "3. Activate the environment:"
echo "   conda activate book-keeper"
echo ""
echo "==============================================" 