"""Pytest configuration.

Some modules load the global Settings singleton at import time, which
requires a ga.json config file. Fall back to ga.json.example so the test
suite can be collected and run on a fresh checkout (and in CI) without a
personal config.
"""
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

if 'GENETRADER_CONFIG' not in os.environ and not (_PROJECT_ROOT / 'ga.json').exists():
    os.environ['GENETRADER_CONFIG'] = str(_PROJECT_ROOT / 'ga.json.example')
