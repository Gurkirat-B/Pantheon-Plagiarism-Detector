#!/bin/bash
# Quick test runner script for Pantheon tests

cd "$(dirname "$0")" || exit 1

# Activate venv if it exists
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH="$PWD/Backend/Pantheon_API"

# Run tests with nice output
python -m pytest tests/ -v --tb=short "$@"
