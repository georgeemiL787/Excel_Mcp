"""Compatibility wrapper for the src-based sample generator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_FILE = ROOT / "src" / "scripts" / "create_sample.py"

spec = importlib.util.spec_from_file_location("_src_scripts_create_sample", SRC_FILE)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load sample generator from {SRC_FILE}")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
main = module.main

if __name__ == "__main__":
    main()
