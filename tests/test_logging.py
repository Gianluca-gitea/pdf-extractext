import importlib
import logging
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"
APP_MODULES = [
    ".".join(path.relative_to(APP_DIR.parent).with_suffix("").parts)
    for path in sorted(APP_DIR.rglob("*.py"))
]


@pytest.mark.parametrize("module_name", APP_MODULES)
def test_module_logger_inherits_level_from_root(module_name) -> None:
    importlib.import_module(module_name)

    assert logging.getLogger(module_name).level == logging.NOTSET
