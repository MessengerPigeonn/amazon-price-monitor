#!/usr/bin/env python3
"""Amazon Price Monitor - Entry point."""

import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli.main import app

if __name__ == "__main__":
    app()
