#!/bin/bash

# setup.sh - Setup script for Linux/macOS
# This script sets up the Python environment and installs dependencies

set -e

echo "===================================="
echo "Setting up Python Environment"
echo "===================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or later."
    exit 1
fi

python_version=$(python3 --version | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "===================================="
echo "Setup completed successfully!"
echo "===================================="
echo ""
echo "To activate the environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the tests, use:"
echo "  ./run_test.sh"
echo ""
echo "To run automatic testing with environment detection, use:"
echo "  python3 auto_test.py"
