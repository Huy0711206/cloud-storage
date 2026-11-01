"""Compatibility command; implementation: scripts/maintenance/patch-viewer.py."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/maintenance/patch-viewer.py"), run_name="__main__")
