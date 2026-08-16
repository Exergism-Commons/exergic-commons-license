#!/usr/bin/env python3
"""Safe bootstrap for the content-addressed Schedule renderer.

Only the built-in ``sys`` module is imported before the repository's ``tools``
directory is removed from the import search path. This prevents sibling modules
such as ``tools/hashlib.py`` or ``tools/yaml/`` from shadowing the standard
library or pinned PyYAML when the renderer is launched as a script.
"""

from __future__ import annotations

import sys

_WRAPPER_PATH = __file__.replace("\\", "/")
_WRAPPER_DIR = _WRAPPER_PATH.rsplit("/", 1)[0]
_IMPL_PATH = f"{_WRAPPER_DIR}/render_schedule_impl.py"
_ORIGINAL_NAME = globals().get("__name__", "render_schedule")
_ORIGINAL_SPEC = globals().get("__spec__")
_ORIGINAL_SYS_PATH = list(sys.path)


def _normalise_import_path(entry: str) -> str:
    return entry.replace("\\", "/").rstrip("/")


# The demonstrated bypass relies on Python prepending the script directory to
# sys.path. Remove every exact occurrence while the implementation performs its
# imports. No repository-local module is a supported renderer dependency.
sys.path[:] = [
    entry
    for entry in sys.path
    if not entry or _normalise_import_path(entry) != _WRAPPER_DIR.rstrip("/")
]

_globals = globals()
_globals["__file__"] = _IMPL_PATH
_globals["__name__"] = "_ecl_render_schedule_impl"
_globals["__spec__"] = None
try:
    with open(_IMPL_PATH, "r", encoding="utf-8") as _handle:
        _source = _handle.read()
    exec(compile(_source, _IMPL_PATH, "exec"), _globals)
finally:
    # Import resolution is needed only while loading the implementation's
    # complete top-level dependency set. Restore the caller's path afterwards
    # so importing the renderer as a module does not mutate its host process.
    sys.path[:] = _ORIGINAL_SYS_PATH
    _globals["__name__"] = _ORIGINAL_NAME
    _globals["__spec__"] = _ORIGINAL_SPEC

_impl_control_paths = schedule_renderer_control_paths
_impl_validate_environment = validate_renderer_environment


def _repository_local_module(label, module) -> None:
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str) or not origin:
        raise ValueError(f"Schedule renderer cannot verify imported {label} origin")
    origin_path = Path(origin).resolve()
    try:
        origin_path.relative_to(ROOT)
    except ValueError:
        return
    raise ValueError(
        f"Schedule renderer refuses repository-local shadowing of imported {label}: {origin_path}"
    )


def validate_renderer_environment() -> None:
    """Fail closed if a host process supplied a repository-local shadow module."""

    _repository_local_module("hashlib", hashlib)
    _repository_local_module("yaml", yaml)
    _impl_validate_environment()


def schedule_renderer_control_paths() -> list[Path]:
    """Bind both the bootstrap and implementation as material renderer code."""

    paths = list(_impl_control_paths())
    wrapper = Path(_WRAPPER_PATH).resolve()
    if wrapper not in {path.resolve() for path in paths}:
        paths.append(wrapper)
    return paths


if _ORIGINAL_NAME == "__main__":
    main()
