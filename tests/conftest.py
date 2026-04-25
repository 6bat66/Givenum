"""
Shared pytest configuration.

GivEnum.py lives at the repo root (not inside a package). To let the test
modules `import GivEnum`, we add the parent directory to sys.path here.

We also expose a few common fixtures (tmp_path is built-in and reused).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
