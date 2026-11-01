"""Compatibility command; implementation: scripts/diagnostics/verify-ui.py."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/diagnostics/verify-ui.py"), run_name="__main__")
