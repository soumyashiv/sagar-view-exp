"""Shared pytest fixtures for SAGAR-VIEW backend tests."""
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
