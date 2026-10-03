#!/usr/bin/env python3
"""Quick launcher — runs the production build."""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).parent
    subprocess.run([sys.executable, "-m", "backend.main"] + sys.argv[1:], cwd=root)
