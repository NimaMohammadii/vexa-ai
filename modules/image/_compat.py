"""Compatibility helpers for the image module.

This module currently provides a safe way to import :mod:`imghdr` while also
registering a backwards-compatible alias for the common ``imgdhr`` typo that
appears in some deployments.  When the alias is present, environments still
running the buggy import line will transparently receive the standard library
module instead of crashing with ``ModuleNotFoundError``.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType


def _load_imghdr() -> ModuleType:
    """Return the :mod:`imghdr` module and register an alias for ``imgdhr``."""

    module = importlib.import_module("imghdr")
    # Some historical deployments imported ``imgdhr`` by mistake.  Making the
    # alias available keeps those environments working while we roll out the fix
    # everywhere else.
    sys.modules.setdefault("imgdhr", module)
    return module


imghdr = _load_imghdr()

__all__ = ["imghdr"]
