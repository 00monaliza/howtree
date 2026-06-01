"""
Unit-test conftest: inject a stub `ultralytics` module so that
`patch("ultralytics.YOLO", ...)` works without the package installed.
"""
from __future__ import annotations

import sys
import types

# Only inject if ultralytics is not already installed
if "ultralytics" not in sys.modules:
    stub = types.ModuleType("ultralytics")
    stub.YOLO = None  # placeholder; tests always patch this
    sys.modules["ultralytics"] = stub
